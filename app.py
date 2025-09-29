import sys
import os
import subprocess
import tempfile
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QIcon
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QAbstractItemView, QMessageBox, QCheckBox,
    QSizePolicy, QScrollArea, QGraphicsDropShadowEffect
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

# Represents a video file as a thumbnail with title and other video info
class VideoItemWidget(QWidget):    
    def __init__(self, filepath=None, parent=None):
        super().__init__(parent)
        self.filepath = filepath

        # If filepath is provided, show video info and thumbnail
        if filepath:
            self.title, self.duration, self.codec = get_video_info(filepath)
            self.thumb_path = get_thumbnail(filepath)
        else:
            self.title, self.duration, self.codec = "", 0, ""
            self.thumb_path = None

        # Layout
        layout = QVBoxLayout()
        layout.alignment = Qt.AlignmentFlag.AlignLeft
        desiredWidgetWidth = 280

        # Video thumbnail or placeholder
        thumb_label = QLabel()
        thumb_label.setFixedSize(desiredWidgetWidth, desiredWidgetWidth)
        if self.thumb_path:
            pixmap = QPixmap(self.thumb_path)
            thumb_label.setPixmap(pixmap.scaled(desiredWidgetWidth, desiredWidgetWidth, Qt.AspectRatioMode.KeepAspectRatio))
            
        else:
            # Draw a placeholder square with a dashed border and icon/text
            placeholder = QPixmap(desiredWidgetWidth, desiredWidgetWidth)
            placeholder.fill(Qt.GlobalColor.transparent)
            from PyQt6.QtGui import QPainter, QPen, QColor, QFont
            painter = QPainter(placeholder)
            pen = QPen(QColor("gray"), 3, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRect(10, 10, desiredWidgetWidth-20, desiredWidgetWidth-20)
            painter.setPen(QColor("gray"))
            font = QFont()
            font.setPointSize(18)
            painter.setFont(font)
            painter.drawText(placeholder.rect(), Qt.AlignmentFlag.AlignCenter, "＋")
            painter.end()
            thumb_label.setPixmap(placeholder)

        thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(thumb_label)

        # Video title label with horizontal scrolling if too long
        title_label = QLabel(self.title)
        title_label.setWordWrap(False)
        scroll_area = QScrollArea()
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setFixedWidth(desiredWidgetWidth-10)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        scroll_area.setFixedHeight(36)
        scroll_area.setWidget(title_label)
        scroll_area.setStyleSheet("""
            QScrollArea { background: transparent; }
            QLabel { background: transparent; 
                    color: white; 
                    font-weight: bold; }
            """)
        
        # Add drop shadow to title text for better visibility
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(4)
        shadow.setOffset(2, 2)
        shadow.setColor(0)
        scroll_area.setGraphicsEffect(shadow)
        
        layout.addWidget(scroll_area)

        # Duration and Codec in a single row
        info_row = QHBoxLayout()
        duration_label = QLabel("Duration: " + seconds_to_hms(self.duration) if self.duration else "")
        info_row.addWidget(duration_label, alignment=Qt.AlignmentFlag.AlignLeft)
        codec_label = QLabel(self.codec)
        codec_label.setStyleSheet("QLabel { color: white; font-weight: bold; }")
        info_row.addWidget(codec_label, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addLayout(info_row)

        self.setLayout(layout)
        self.setFixedHeight(desiredWidgetWidth)  # Ensure fixed height

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
            "Drag and drop video files, re-order as needed, then hit 'Join Videos' - " \
            "Videos must be the same dimensions, codec, fps, etc."
        )
        instruction_label.setWordWrap(True)
        instruction_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_bar.addWidget(instruction_label)

        # Gear icon button
        gear_btn = QPushButton()
        gear_icon = QIcon.fromTheme("settings")
        if gear_icon.isNull():
            # fallback to a unicode gear if no icon theme
            gear_btn.setText("⚙")
        else:
            gear_btn.setIcon(gear_icon)
        gear_btn.setFixedSize(40, 40)
        gear_btn.setToolTip("Settings")
        gear_btn.clicked.connect(self.show_settings)
        top_bar.addWidget(gear_btn, alignment=Qt.AlignmentFlag.AlignRight)
        main_layout.addLayout(top_bar)

        # List widget for video items
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.ViewMode.IconMode)
        self.list_widget.setMovement(QListWidget.Movement.Snap)
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_widget.setFlow(QListWidget.Flow.LeftToRight)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setWrapping(False)

        # set list widget items to have a fixed size of 300x300
        self.list_widget.setGridSize(QPixmap(300, 300).size())

        main_layout.addWidget(self.list_widget)

        # Add 3 empty placeholders at start
        for _ in range(3):
            item = QListWidgetItem()
            widget = VideoItemWidget()  # No filepath = placeholder
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

        # --- Bottom Controls ---
        controls_row = QHBoxLayout()
        controls_row.setContentsMargins(8, 12, 8, 8)
        button_height = 40

        # Left: Delete old videos checkbox
        self.delete_old_checkbox = QCheckBox("Delete old video files after successful join")
        controls_row.addWidget(self.delete_old_checkbox, alignment=Qt.AlignmentFlag.AlignCenter)

        # Center: Join Videos button
        self.run_btn = QPushButton("Join Videos")
        self.run_btn.clicked.connect(self.run_concat)
        self.run_btn.setFixedSize(200, button_height)
        controls_row.addWidget(self.run_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        # Shadow effect on the button
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setOffset(2, 2)
        shadow.setColor(0)
        self.run_btn.setGraphicsEffect(shadow)

        # Right: Clear List button
        self.clear_btn = QPushButton("Clear List")
        self.clear_btn.clicked.connect(self.clear_list)
        self.clear_btn.setFixedSize(200, button_height)
        controls_row.addWidget(self.clear_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addLayout(controls_row)
        # --- End Bottom Controls ---

        self.ffmpeg_cmd_label = QLabel("FFmpeg Command Preview:")
        self.ffmpeg_cmd_label.setContentsMargins(8, 0, 8, 8)
        main_layout.addWidget(self.ffmpeg_cmd_label)

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
                # Find first placeholder and replace it, else append
                for i in range(self.list_widget.count()):
                    widget = self.list_widget.itemWidget(self.list_widget.item(i))
                    if isinstance(widget, VideoItemWidget) and not widget.filepath:
                        new_widget = VideoItemWidget(filepath)
                        self.list_widget.setItemWidget(self.list_widget.item(i), new_widget)
                        self.list_widget.item(i).setSizeHint(new_widget.sizeHint())
                        self.video_files.append(filepath)
                        break
                else:
                    item = QListWidgetItem()
                    widget = VideoItemWidget(filepath)
                    item.setSizeHint(widget.sizeHint())
                    self.list_widget.addItem(item)
                    self.list_widget.setItemWidget(item, widget)
                    self.video_files.append(filepath)
        self.update_ffmpeg_cmd()

    def clear_list(self):
        for i in range(self.list_widget.count()):
            widget = self.list_widget.itemWidget(self.list_widget.item(i))
            if widget:
                widget.cleanup()
        self.list_widget.clear()
        self.video_files.clear()
        # Re-add 3 empty placeholders
        for _ in range(3):
            item = QListWidgetItem()
            widget = VideoItemWidget()
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
        self.update_ffmpeg_cmd()

    def get_current_file_order(self):
        order = []
        for i in range(self.list_widget.count()):
            widget = self.list_widget.itemWidget(self.list_widget.item(i))
            if widget and widget.filepath:
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
    
    window.setMinimumSize(930, 470)
    window.show()
    sys.exit(app.exec())