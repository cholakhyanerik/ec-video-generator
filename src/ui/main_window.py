import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QPushButton, QFileDialog, 
                               QComboBox, QProgressBar, QMessageBox, QGroupBox, QTabWidget, QStackedWidget)
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
    finished = Signal(bool, str)

    def __init__(self, mode, generator, **kwargs):
        super().__init__()
        self.mode = mode
        self.generator = generator
        self.kwargs = kwargs

    def run(self):
        try:
            if self.mode == 'create_video':
                self.generator.generate_video(self.kwargs['img'], self.kwargs['audio'], self.kwargs['output'], self.kwargs['quality'])
            elif self.mode == 'upscale_video':
                self.generator.upscale_video(self.kwargs['video'], self.kwargs['output'], self.kwargs['quality'])
            elif self.mode == 'upscale_images':
                self.generator.upscale_image_batch(self.kwargs['images'], self.kwargs['output_folder'], self.kwargs['quality'])
            elif self.mode == 'concat_images':
                self.generator.concat_images(self.kwargs['img1'], self.kwargs['img2'], self.kwargs['output'])
            
            self.finished.emit(True, "Task completed successfully!")
        except Exception as e:
            self.finished.emit(False, str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EC Video Generator")
        self.resize(650, 600)
        
        icon_path = resource_path(os.path.join("assets", "icon.png"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.generator = VideoGenerator()
        
        # UI State Variables
        self.image_path = None
        self.audio_path = None
        self.video_input_path = None
        self.img_batch_paths = []
        self.concat_img1 = None
        self.concat_img2 = None

        self.setup_ui()
        self.setStyleSheet(DARK_THEME)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)

        # Header
        header = QLabel("Video Generator Studio")
        header.setObjectName("Header")
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

        # --- TABS ---
        self.tabs = QTabWidget()
        
        # Tab 1: Create Video
        self.tab_create = QWidget()
        self.setup_create_tab()
        self.tabs.addTab(self.tab_create, "Create Video")

        # Tab 2: Upscale Video
        self.tab_upscale = QWidget()
        self.setup_upscale_tab()
        self.tabs.addTab(self.tab_upscale, "Upscale Video")

        # Tab 3: Image Tools
        self.tab_images = QWidget()
        self.setup_image_tools_tab()
        self.tabs.addTab(self.tab_images, "Image Tools")

        main_layout.addWidget(self.tabs)

        # --- GLOBAL SETTINGS & RUN ---
        # We put the "Run" button inside each tab logic or keep a global one?
        # A global button is tricky because the inputs change.
        # Let's put specific Run buttons inside the tabs for clarity, 
        # OR keep the global one and read the current tab index.
        # Global is cleaner for code, but let's add the Global Progress Bar here.
        
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        main_layout.addWidget(self.progress)

    def setup_create_tab(self):
        layout = QVBoxLayout(self.tab_create)
        
        # Inputs
        self.lbl_image = QLabel("No Image Selected")
        btn_image = QPushButton("Select Image")
        btn_image.clicked.connect(self.select_image)
        layout.addWidget(btn_image)
        layout.addWidget(self.lbl_image)

        self.lbl_audio = QLabel("No Audio Selected")
        btn_audio = QPushButton("Select Audio (MP3)")
        btn_audio.clicked.connect(self.select_audio)
        layout.addWidget(btn_audio)
        layout.addWidget(self.lbl_audio)

        # Quality
        layout.addWidget(QLabel("Target Quality:"))
        self.combo_quality_video = QComboBox()
        self.combo_quality_video.addItems(["1080p", "4k", "2k", "720p"])
        layout.addWidget(self.combo_quality_video)

        # Run Button
        btn_run = QPushButton("Generate Video")
        btn_run.setFixedHeight(40)
        btn_run.clicked.connect(self.run_create_video)
        layout.addWidget(btn_run)
        layout.addStretch()

    def setup_upscale_tab(self):
        layout = QVBoxLayout(self.tab_upscale)
        
        self.lbl_video = QLabel("No Video Selected")
        btn_video = QPushButton("Select Video File")
        btn_video.clicked.connect(self.select_video_input)
        layout.addWidget(btn_video)
        layout.addWidget(self.lbl_video)

        layout.addWidget(QLabel("Target Quality:"))
        self.combo_quality_upscale = QComboBox()
        self.combo_quality_upscale.addItems(["1080p", "4k", "2k", "720p"])
        layout.addWidget(self.combo_quality_upscale)

        btn_run = QPushButton("Upscale Video")
        btn_run.setFixedHeight(40)
        btn_run.clicked.connect(self.run_upscale_video)
        layout.addWidget(btn_run)
        layout.addStretch()

    def setup_image_tools_tab(self):
        layout = QVBoxLayout(self.tab_images)
        
        # Mode Selection
        layout.addWidget(QLabel("Select Tool:"))
        self.combo_img_mode = QComboBox()
        self.combo_img_mode.addItems(["Upscale Images (Batch)", "Concat 2 Images (Side-by-Side)"])
        self.combo_img_mode.currentIndexChanged.connect(self.switch_image_mode)
        layout.addWidget(self.combo_img_mode)

        # Stacked Widget to flip between modes
        self.stack_img = QStackedWidget()
        
        # --- Page 1: Upscale ---
        page_upscale = QWidget()
        p1_layout = QVBoxLayout(page_upscale)
        self.lbl_batch = QLabel("No Images Selected")
        btn_batch = QPushButton("Select Images (Select Multiple)")
        btn_batch.clicked.connect(self.select_batch_images)
        p1_layout.addWidget(btn_batch)
        p1_layout.addWidget(self.lbl_batch)
        
        p1_layout.addWidget(QLabel("Target Resolution:"))
        self.combo_quality_img = QComboBox()
        self.combo_quality_img.addItems(["4k", "2k", "1080p"])
        p1_layout.addWidget(self.combo_quality_img)

        btn_run_img = QPushButton("Upscale Images")
        btn_run_img.setFixedHeight(40)
        btn_run_img.clicked.connect(self.run_upscale_images)
        p1_layout.addWidget(btn_run_img)
        p1_layout.addStretch()
        
        # --- Page 2: Concat ---
        page_concat = QWidget()
        p2_layout = QVBoxLayout(page_concat)
        
        # Img 1
        self.lbl_c1 = QLabel("Image 1: None")
        btn_c1 = QPushButton("Select Left Image")
        btn_c1.clicked.connect(lambda: self.select_concat_img(1))
        p2_layout.addWidget(btn_c1)
        p2_layout.addWidget(self.lbl_c1)

        # Img 2
        self.lbl_c2 = QLabel("Image 2: None")
        btn_c2 = QPushButton("Select Right Image")
        btn_c2.clicked.connect(lambda: self.select_concat_img(2))
        p2_layout.addWidget(btn_c2)
        p2_layout.addWidget(self.lbl_c2)

        btn_run_cat = QPushButton("Merge Images")
        btn_run_cat.setFixedHeight(40)
        btn_run_cat.clicked.connect(self.run_concat_images)
        p2_layout.addWidget(btn_run_cat)
        p2_layout.addStretch()

        self.stack_img.addWidget(page_upscale)
        self.stack_img.addWidget(page_concat)
        layout.addWidget(self.stack_img)

    def switch_image_mode(self, index):
        self.stack_img.setCurrentIndex(index)

    # --- File Handlers ---
    def select_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg)")
        if path:
            self.image_path = path
            self.lbl_image.setText(os.path.basename(path))

    def select_audio(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Audio", "", "Audio (*.mp3)")
        if path:
            self.audio_path = path
            self.lbl_audio.setText(os.path.basename(path))

    def select_video_input(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Video (*.mp4)")
        if path:
            self.video_input_path = path
            self.lbl_video.setText(os.path.basename(path))

    def select_batch_images(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Images", "", "Images (*.png *.jpg)")
        if paths:
            self.img_batch_paths = paths
            self.lbl_batch.setText(f"{len(paths)} images selected")

    def select_concat_img(self, num):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg)")
        if path:
            if num == 1:
                self.concat_img1 = path
                self.lbl_c1.setText(f"Left: {os.path.basename(path)}")
            else:
                self.concat_img2 = path
                self.lbl_c2.setText(f"Right: {os.path.basename(path)}")

    # --- Runners ---
    def run_create_video(self):
        if not self.image_path or not self.audio_path:
            QMessageBox.warning(self, "Error", "Missing files")
            return
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Video", "output.mp4", "Video (*.mp4)")
        if save_path:
            self.start_worker('create_video', img=self.image_path, audio=self.audio_path, output=save_path, quality=self.combo_quality_video.currentText())

    def run_upscale_video(self):
        if not self.video_input_path:
            QMessageBox.warning(self, "Error", "Missing video")
            return
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Video", "upscaled.mp4", "Video (*.mp4)")
        if save_path:
            self.start_worker('upscale_video', video=self.video_input_path, output=save_path, quality=self.combo_quality_upscale.currentText())

    def run_upscale_images(self):
        if not self.img_batch_paths:
            QMessageBox.warning(self, "Error", "No images selected")
            return
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.start_worker('upscale_images', images=self.img_batch_paths, output_folder=folder, quality=self.combo_quality_img.currentText())

    def run_concat_images(self):
        if not self.concat_img1 or not self.concat_img2:
            QMessageBox.warning(self, "Error", "Select both images")
            return
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Image", "merged.png", "Image (*.png)")
        if save_path:
            self.start_worker('concat_images', img1=self.concat_img1, img2=self.concat_img2, output=save_path)

    def start_worker(self, mode, **kwargs):
        self.progress.setRange(0, 0)
        self.worker = WorkerThread(mode, self.generator, **kwargs)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, success, message):
        self.progress.setRange(0, 100)
        self.progress.setValue(100 if success else 0)
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)