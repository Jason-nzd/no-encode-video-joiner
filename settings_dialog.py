from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QLineEdit, QFileDialog
)

class SettingsDialog(QDialog):
    def __init__(self, parent=None, ffmpeg_path="", ffprobe_path="", manual_override=False):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        layout = QVBoxLayout()

        # Manual override checkbox
        self.manual_override_checkbox = QCheckBox("Manually set ffmpeg.exe and ffprobe.exe paths")
        self.manual_override_checkbox.setChecked(manual_override)
        layout.addWidget(self.manual_override_checkbox)

        self.ffmpeg_edit = QLineEdit(ffmpeg_path)
        self.ffprobe_edit = QLineEdit(ffprobe_path)

        ffmpeg_layout = QHBoxLayout()
        ffmpeg_layout.addWidget(QLabel("ffmpeg.exe path:"))
        ffmpeg_layout.addWidget(self.ffmpeg_edit)
        ffmpeg_browse = QPushButton("Browse")
        ffmpeg_browse.clicked.connect(self.browse_ffmpeg)
        ffmpeg_layout.addWidget(ffmpeg_browse)
        layout.addLayout(ffmpeg_layout)

        ffprobe_layout = QHBoxLayout()
        ffprobe_layout.addWidget(QLabel("ffprobe.exe path:"))
        ffprobe_layout.addWidget(self.ffprobe_edit)
        ffprobe_browse = QPushButton("Browse")
        ffprobe_browse.clicked.connect(self.browse_ffprobe)
        ffprobe_layout.addWidget(ffprobe_browse)
        layout.addLayout(ffprobe_layout)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Set initial enabled/disabled state
        self.set_manual_override_enabled(self.manual_override_checkbox.isChecked())
        self.manual_override_checkbox.stateChanged.connect(
            lambda state: self.set_manual_override_enabled(state == Qt.CheckState.Checked)
        )

    def set_manual_override_enabled(self, enabled):
        self.ffmpeg_edit.setEnabled(enabled)
        self.ffprobe_edit.setEnabled(enabled)
        # Find browse buttons and disable them too
        for layout in self.findChildren(QHBoxLayout):
            for widget in layout.findChildren(QPushButton):
                widget.setEnabled(enabled)

    def browse_ffmpeg(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select ffmpeg.exe", "", "Executable (*.exe)")
        if path:
            self.ffmpeg_edit.setText(path)

    def browse_ffprobe(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select ffprobe.exe", "", "Executable (*.exe)")
        if path:
            self.ffprobe_edit.setText(path)

    def get_paths(self):
        return self.ffmpeg_edit.text(), self.ffprobe_edit.text(), self.manual_override_checkbox.isChecked()