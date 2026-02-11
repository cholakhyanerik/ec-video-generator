import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QPushButton, QFileDialog, 
                               QComboBox, QProgressBar, QMessageBox, QGroupBox, QTabWidget)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon

from ..core.generator import VideoGenerator
from .styles import DARK_THEME

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    path = os.path.join(base_path, relative_path)
    if not os.path.exists(path):
        alt_path = os.path.join(base_path, "src", relative_path)
        if os.path.exists(alt_path):
            return alt_path
    return path

class WorkerThread(QThread):
    finished = Signal(bool, str) # success, message

    def __init__(self, mode, generator, output_path, quality, **kwargs):
        super().__init__()
        self.mode = mode # 'create' or 'upscale'
        self.generator = generator
        self.output_path = output_path
        self.quality = quality
        self.kwargs = kwargs

    def run(self):
        try:
            if self.mode == 'create':
                self.generator.generate_video(self.kwargs['img'], self.kwargs['audio'], self.output_path, self.quality)
            elif self.mode == 'upscale':
                self.generator.upscale_video(self.kwargs['video'], self.output_path, self.quality)
            
            self.finished.emit(True, "Task completed successfully!")
        except Exception as e:
            self.finished.emit(False, str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EC Video Generator")
        self.resize(600, 550)
        
        icon_path = resource_path(os.path.join("assets", "icon.png"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.generator = VideoGenerator()
        
        # State variables
        self.image_path = None
        self.audio_path = None
        self.video_input_path = None

        self.setup_ui()
        self.setStyleSheet(DARK_THEME)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel("Video Generator Studio")
        header.setObjectName("Header")
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

        # --- TABS ---
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #3e3e3e; border-radius: 6px; }")
        
        # TAB 1: Create Video (Image + Audio)
        self.tab_create = QWidget()
        self.setup_create_tab()
        self.tabs.addTab(self.tab_create, "Create Video")

        # TAB 2: Upscale Video
        self.tab_upscale = QWidget()
        self.setup_upscale_tab()
        self.tabs.addTab(self.tab_upscale, "Upscale Video")

        main_layout.addWidget(self.tabs)
        # ------------

        # Shared Settings Group (Applies to both tabs)
        settings_group = QGroupBox("Global Settings")
        settings_layout = QHBoxLayout()
        
        settings_layout.addWidget(QLabel("Target Quality:"))
        self.combo_quality = QComboBox()
        self.combo_quality.addItems(["1080p", "4k", "2k", "720p"]) # Added 2k
        settings_layout.addWidget(self.combo_quality)
        
        settings_layout.addWidget(QLabel("GPU:"))
        lbl_encoder = QLabel(self.generator.encoder.upper())
        lbl_encoder.setStyleSheet("color: #00ff00; font-weight: bold;")
        settings_layout.addWidget(lbl_encoder)
        
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        # Action Area
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        main_layout.addWidget(self.progress)

        self.btn_run = QPushButton("Start Processing")
        self.btn_run.setFixedHeight(45)
        self.btn_run.clicked.connect(self.start_process)
        main_layout.addWidget(self.btn_run)

    def setup_create_tab(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Image Picker
        self.lbl_image = QLabel("No Image Selected")
        self.lbl_image.setStyleSheet("color: #888;")
        btn_image = QPushButton("Select Image (16:9 or 9:16)")
        btn_image.clicked.connect(self.select_image)
        layout.addWidget(btn_image)
        layout.addWidget(self.lbl_image)

        # Audio Picker
        self.lbl_audio = QLabel("No Audio Selected")
        self.lbl_audio.setStyleSheet("color: #888;")
        btn_audio = QPushButton("Select Audio (MP3)")
        btn_audio.clicked.connect(self.select_audio)
        layout.addWidget(btn_audio)
        layout.addWidget(self.lbl_audio)
        
        layout.addStretch()
        self.tab_create.setLayout(layout)

    def setup_upscale_tab(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)

        lbl_info = QLabel("Upload any video to upscale it to the selected quality.\nSupports 720p -> 1080p/2k/4k.")
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)

        # Video Picker
        self.lbl_video = QLabel("No Video Selected")
        self.lbl_video.setStyleSheet("color: #888;")
        btn_video = QPushButton("Select Video File")
        btn_video.clicked.connect(self.select_video_input)
        layout.addWidget(btn_video)
        layout.addWidget(self.lbl_video)

        layout.addStretch()
        self.tab_upscale.setLayout(layout)

    # --- File Selection Handlers ---
    def select_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.image_path = path
            self.lbl_image.setText(f"✅ {os.path.basename(path)}")

    def select_audio(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Audio", "", "Audio (*.mp3 *.wav)")
        if path:
            self.audio_path = path
            self.lbl_audio.setText(f"✅ {os.path.basename(path)}")

    def select_video_input(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Video (*.mp4 *.avi *.mov)")
        if path:
            self.video_input_path = path
            self.lbl_video.setText(f"✅ {os.path.basename(path)}")

    # --- Main Logic ---
    def start_process(self):
        current_tab_index = self.tabs.currentIndex()
        quality = self.combo_quality.currentText()
        
        # TAB 0: CREATE MODE
        if current_tab_index == 0:
            if not self.image_path or not self.audio_path:
                QMessageBox.warning(self, "Missing Files", "Please select an Image and Audio file.")
                return
            
            save_path, _ = QFileDialog.getSaveFileName(self, "Save Video", "output_created.mp4", "Video (*.mp4)")
            if not save_path: return

            self.run_worker('create', output=save_path, quality=quality, img=self.image_path, audio=self.audio_path)

        # TAB 1: UPSCALE MODE
        elif current_tab_index == 1:
            if not self.video_input_path:
                QMessageBox.warning(self, "Missing File", "Please select a Video file to upscale.")
                return
            
            save_path, _ = QFileDialog.getSaveFileName(self, "Save Upscaled Video", "output_upscaled.mp4", "Video (*.mp4)")
            if not save_path: return

            self.run_worker('upscale', output=save_path, quality=quality, video=self.video_input_path)

    def run_worker(self, mode, output, quality, **kwargs):
        self.btn_run.setDisabled(True)
        self.progress.setRange(0, 0) # Loading animation
        
        self.worker = WorkerThread(mode, self.generator, output, quality, **kwargs)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, success, message):
        self.btn_run.setDisabled(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(100 if success else 0)
        
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)