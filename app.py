import sys
import os
import subprocess
import tempfile
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QIcon
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QAbstractItemView, QMessageBox, QCheckBox,
    QSizePolicy
)
from ffmpeg_utilities import get_video_info, get_thumbnail, seconds_to_hms
from settings_dialog import SettingsDialog

# No-Encode Video Joiner
# ------------------------------
# A PyQt6 application to join/concatenate video files without re-encoding using ffmpeg.

# Drag and drop video files, reorder them, then join them with a single click.
# (Videos must have the same codec, dimensions, fps, etc.)

# Requires PyQt6. Install with:
# pip install PyQt6

# Requires ffmpeg and ffprobe to be installed and accessible in the system PATH,
# or manually specify their paths in the settings.
# ------------------------------

# Represents a video file as a thumbnail with title and duration
class VideoItemWidget(QWidget):    
    def __init__(self, filepath, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.title, self.duration = get_video_info(filepath)
        self.thumb_path = get_thumbnail(filepath)
        layout = QVBoxLayout()
        pixmap = QPixmap(self.thumb_path) if self.thumb_path else QPixmap()
        thumb_label = QLabel()
        thumb_label.setPixmap(pixmap.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio))
        layout.addWidget(thumb_label)
        layout.addWidget(QLabel(self.title))
        layout.addWidget(QLabel(seconds_to_hms(self.duration)))
        self.setLayout(layout)

    def cleanup(self):
        if self.thumb_path and os.path.exists(self.thumb_path):
            os.remove(self.thumb_path)

class VideoConcatApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("No-Encode Video Joiner")
        self.setAcceptDrops(True)
        self.video_files = []
        self.ffmpeg_path = "ffmpeg"
        self.ffprobe_path = "ffprobe"
        self.manual_override = False

        main_layout = QVBoxLayout()

        # Top bar with instructions and gear icon
        top_bar = QHBoxLayout()
        instruction_label = QLabel(
            "Drag and drop video files, then hit 'Join Videos' - Videos must be the same dimensions, codec, fps, etc."
        )
        instruction_label.setWordWrap(True)
        instruction_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        #instruction_label.setStyleSheet("font-weight: bold; color: #fff; margin-bottom: 8px;")
        top_bar.addWidget(instruction_label)

        # Gear icon button
        gear_btn = QPushButton()
        gear_icon = QIcon.fromTheme("settings")
        if gear_icon.isNull():
            # fallback to a unicode gear if no icon theme
            gear_btn.setText("⚙")
        else:
            gear_btn.setIcon(gear_icon)
        gear_btn.setFixedSize(32, 32)
        gear_btn.setToolTip("Settings")
        gear_btn.clicked.connect(self.show_settings)
        top_bar.addWidget(gear_btn, alignment=Qt.AlignmentFlag.AlignRight)
        main_layout.addLayout(top_bar)

        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.ViewMode.IconMode)
        self.list_widget.setMovement(QListWidget.Movement.Free)
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_widget.setSpacing(10)
        self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list_widget.setFixedHeight(180)
        main_layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.clear_btn = QPushButton("Clear List")
        self.clear_btn.clicked.connect(self.clear_list)
        btn_layout.addWidget(self.clear_btn)
        main_layout.addLayout(btn_layout)

        self.delete_old_checkbox = QCheckBox("Delete old video files after successful join")
        main_layout.addWidget(self.delete_old_checkbox)

        self.ffmpeg_cmd_label = QLabel("FFmpeg Command Preview:")
        main_layout.addWidget(self.ffmpeg_cmd_label)

        run_layout = QHBoxLayout()
        self.run_btn = QPushButton("Join Videos")
        self.run_btn.clicked.connect(self.run_concat)
        run_layout.addWidget(self.run_btn)
        main_layout.addLayout(run_layout)

        self.setLayout(main_layout)
        self.update_ffmpeg_cmd()

    def show_settings(self):
        dlg = SettingsDialog(self, self.ffmpeg_path, self.ffprobe_path, self.manual_override)
        if dlg.exec():
            ffmpeg_path, ffprobe_path, manual_override = dlg.get_paths()
            self.manual_override = manual_override
            if self.manual_override:
                if ffmpeg_path:
                    self.ffmpeg_path = ffmpeg_path
                if ffprobe_path:
                    self.ffprobe_path = ffprobe_path
            else:
                self.ffmpeg_path = "ffmpeg"
                self.ffprobe_path = "ffprobe"
            self.update_ffmpeg_cmd()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            filepath = url.toLocalFile()
            if filepath.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
                self.add_video(filepath)
        self.update_ffmpeg_cmd()

    def add_video(self, filepath):
        if filepath not in self.video_files:
            item = QListWidgetItem()
            widget = VideoItemWidget(filepath)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
            self.video_files.append(filepath)

    def clear_list(self):
        for i in range(self.list_widget.count()):
            widget = self.list_widget.itemWidget(self.list_widget.item(i))
            if widget:
                widget.cleanup()
        self.list_widget.clear()
        self.video_files.clear()
        self.update_ffmpeg_cmd()

    def get_current_file_order(self):
        order = []
        for i in range(self.list_widget.count()):
            widget = self.list_widget.itemWidget(self.list_widget.item(i))
            if widget:
                order.append(widget.filepath)
        return order

    def update_ffmpeg_cmd(self):
        files = self.get_current_file_order()
        if not files:
            self.ffmpeg_cmd_label.setText("FFmpeg Command Preview:")
            return
        concat_file = tempfile.mktemp(suffix=".txt")
        with open(concat_file, "w", encoding="utf-8") as f:
            for file in files:
                f.write(f"file '{file.replace('\'', '\\\'')}'\n")
        out_dir = os.path.dirname(files[0])
        base_name = os.path.splitext(os.path.basename(files[0]))[0]
        out_file = os.path.join(out_dir, f"{base_name}-combined.mp4")
        cmd = f"{self.ffmpeg_path} -f concat -safe 0 -i {concat_file} -c copy \"{out_file}\""
        self.ffmpeg_cmd_label.setText(f"FFmpeg Command Preview:\n{cmd}")
        self.concat_file = concat_file
        self.out_file = out_file

    def run_concat(self):
        self.update_ffmpeg_cmd()
        files = self.get_current_file_order()
        if not files or not hasattr(self, 'concat_file'):
            QMessageBox.warning(self, "Error", "No video files to concatenate.")
            return
        try:
            subprocess.run([
                self.ffmpeg_path, "-f", "concat", "-safe", "0", "-i", self.concat_file,
                "-c", "copy", self.out_file
            ], check=True)
            QMessageBox.information(self, "Done", f"Concatenation complete!\nSaved to:\n{self.out_file}")
            if self.delete_old_checkbox.isChecked():
                for file in files:
                    try:
                        os.remove(file)
                    except Exception as e:
                        QMessageBox.warning(self, "Warning", f"Could not delete {file}:\n{e}")
            self.clear_list()
        except subprocess.CalledProcessError:
            QMessageBox.critical(self, "Error", "FFmpeg failed to concatenate the videos.")
        finally:
            if os.path.exists(self.concat_file):
                os.remove(self.concat_file)

    def closeEvent(self, event):
        self.clear_list()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoConcatApp()

    icon = QIcon("app-logo.png")
    window.setWindowIcon(icon)
    window.resize(900, 350)
    window.show()
    sys.exit(app.exec())