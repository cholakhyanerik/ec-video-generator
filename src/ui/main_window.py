import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QPushButton, QFileDialog, 
                               QComboBox, QProgressBar, QMessageBox, QGroupBox)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon

from ..core.generator import VideoGenerator
from .styles import DARK_THEME

def resource_path(relative_path):
    """ 
    Get absolute path to resource, works for dev and for PyInstaller.
    Handles the difference between 'src/assets' (Dev) and 'assets' (Exe).
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    # 1. Try finding it at the root (standard for Exe)
    path = os.path.join(base_path, relative_path)
    
    # 2. If not found, try looking inside 'src' (standard for Dev/VS Code)
    if not os.path.exists(path):
        alt_path = os.path.join(base_path, "src", relative_path)
        if os.path.exists(alt_path):
            return alt_path

    return path

class WorkerThread(QThread):
    finished = Signal(bool, str) # success, message

    def __init__(self, generator, img, audio, out, quality):
        super().__init__()
        self.generator = generator
        self.img = img
        self.audio = audio
        self.out = out
        self.quality = quality

    def run(self):
        try:
            self.generator.generate_video(self.img, self.audio, self.out, self.quality)
            self.finished.emit(True, "Video generated successfully!")
        except Exception as e:
            self.finished.emit(False, str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EC Video Generator")
        self.resize(600, 500)
        
        # --- ICON LOGIC ---
        # We look for "assets/icon.png". The smart function handles if it's in src/assets
        icon_path = resource_path(os.path.join("assets", "icon.png"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        # ------------------

        self.generator = VideoGenerator()
        
        self.setup_ui()
        self.setStyleSheet(DARK_THEME)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel("Video Generator Studio")
        header.setObjectName("Header")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # File Selection Group
        file_group = QGroupBox("Inputs")
        file_layout = QVBoxLayout()
        
        # Image Picker
        self.lbl_image = QLabel("No Image Selected")
        btn_image = QPushButton("Select Image")
        btn_image.clicked.connect(self.select_image)
        h_img = QHBoxLayout()
        h_img.addWidget(btn_image)
        h_img.addWidget(self.lbl_image)
        file_layout.addLayout(h_img)

        # Audio Picker
        self.lbl_audio = QLabel("No Audio Selected")
        btn_audio = QPushButton("Select Audio (MP3)")
        btn_audio.clicked.connect(self.select_audio)
        h_aud = QHBoxLayout()
        h_aud.addWidget(btn_audio)
        h_aud.addWidget(self.lbl_audio)
        file_layout.addLayout(h_aud)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Settings Group
        settings_group = QGroupBox("Settings")
        settings_layout = QHBoxLayout()
        
        settings_layout.addWidget(QLabel("Quality:"))
        self.combo_quality = QComboBox()
        self.combo_quality.addItems(["1080p", "4k", "720p"])
        settings_layout.addWidget(self.combo_quality)
        
        settings_layout.addWidget(QLabel("Encoder:"))
        lbl_encoder = QLabel(self.generator.encoder.upper())
        lbl_encoder.setStyleSheet("color: #00ff00; font-weight: bold;")
        settings_layout.addWidget(lbl_encoder)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Action Area
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        self.btn_generate = QPushButton("Generate Video")
        self.btn_generate.setFixedHeight(40)
        self.btn_generate.clicked.connect(self.start_generation)
        layout.addWidget(self.btn_generate)

        layout.addStretch()

        # State variables
        self.image_path = None
        self.audio_path = None

    def select_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.image_path = path
            self.lbl_image.setText(os.path.basename(path))

    def select_audio(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Audio", "", "Audio (*.mp3 *.wav)")
        if path:
            self.audio_path = path
            self.lbl_audio.setText(os.path.basename(path))

    def start_generation(self):
        if not self.image_path or not self.audio_path:
            QMessageBox.warning(self, "Missing Files", "Please select both an image and an audio file.")
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "Save Video", "output.mp4", "Video (*.mp4)")
        if not save_path:
            return

        self.btn_generate.setDisabled(True)
        self.progress.setRange(0, 0) # Infinite loading animation

        # Run in separate thread to keep UI responsive
        self.worker = WorkerThread(self.generator, self.image_path, self.audio_path, save_path, self.combo_quality.currentText())
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, success, message):
        self.btn_generate.setDisabled(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(100 if success else 0)
        
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)