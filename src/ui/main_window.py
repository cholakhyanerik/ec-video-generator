import sys
import os
import shutil
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QPushButton, QFileDialog, 
                               QComboBox, QProgressBar, QMessageBox, QGroupBox, 
                               QTabWidget, QStackedWidget, QLineEdit, QTextEdit, QSplitter)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon, QPixmap

from ..core.generator import VideoGenerator

# Lazy load placeholder
AIImageEditor = None 

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
    progress_update = Signal(int)       
    log_update = Signal(str)            

    def __init__(self, mode, **kwargs):
        super().__init__()
        self.mode = mode
        self.kwargs = kwargs
        self.generator = VideoGenerator()

    def run(self):
        try:
            self.log_update.emit(f"--- Starting Task: {self.mode} ---")
            
            if self.mode == 'ai_edit':
                self.run_ai_edit()
            
            elif self.mode == 'create_video':
                self.log_update.emit("Generating video from image + audio...")
                self.progress_update.emit(10) 
                self.generator.generate_video(self.kwargs['img'], self.kwargs['audio'], self.kwargs['output'], self.kwargs['quality'])
                self.progress_update.emit(100)

            elif self.mode == 'upscale_video':
                self.log_update.emit("Upscaling video (this may take time)...")
                self.progress_update.emit(10)
                self.generator.upscale_video(self.kwargs['video'], self.kwargs['output'], self.kwargs['quality'])
                self.progress_update.emit(100)

            elif self.mode == 'upscale_images':
                total = len(self.kwargs['images'])
                self.log_update.emit(f"Processing batch of {total} images...")
                for i, img_path in enumerate(self.kwargs['images']):
                    self.log_update.emit(f"Upscaling: {os.path.basename(img_path)}")
                    self.generator.upscale_image_batch([img_path], self.kwargs['output_folder'], self.kwargs['quality'])
                    progress = int(((i + 1) / total) * 100)
                    self.progress_update.emit(progress)
            
            elif self.mode == 'concat_images':
                self.log_update.emit("Merging images...")
                self.generator.concat_images(self.kwargs['img1'], self.kwargs['img2'], self.kwargs['output'])
                self.progress_update.emit(100)
            
            self.log_update.emit("--- Task Finished Successfully ---")
            self.finished.emit(True, "Task completed successfully!")

        except ImportError as e:
             self.log_update.emit(f"CRITICAL ERROR: Missing Libraries. {str(e)}")
             self.finished.emit(False, f"Missing AI Libraries: {e}")
        except Exception as e:
            self.log_update.emit(f"ERROR: {str(e)}")
            self.finished.emit(False, f"Error: {e}")

    def run_ai_edit(self):
        input_path = self.kwargs['img'] 
        output_path = self.kwargs['output']
        prompt = self.kwargs['prompt']
        
        # Check if input is video or image
        is_video = input_path.lower().endswith(('.mp4', '.avi', '.mov'))
        
        self.log_update.emit("Initializing AI Engine... (Check terminal if downloading models)")
        global AIImageEditor
        if AIImageEditor is None:
                from ..core.ai_editor import AIImageEditor as AIEngine
                AIImageEditor = AIEngine
        
        ai_engine = AIImageEditor()
        self.log_update.emit("AI Model Loaded.")

        if is_video:
            # VIDEO MODE
            temp_dir = os.path.join(os.path.dirname(output_path), "temp_frames_ai")
            
            # 1. Extract Frames
            self.log_update.emit("Extracting video frames...")
            frames = self.generator.extract_frames(input_path, temp_dir)
            total_frames = len(frames)
            
            self.log_update.emit(f"Processing {total_frames} frames. This will take time!")
            
            # 2. Process Each Frame
            for i, frame_path in enumerate(frames):
                self.log_update.emit(f"AI Edit: Frame {i+1}/{total_frames}")
                
                # We overwrite the frame with the edited version
                # Reduced steps to 10 for video speed, guidance 7.5
                ai_engine.edit_image(frame_path, prompt, frame_path, steps=10)
                
                # Update progress
                progress = int(((i + 1) / total_frames) * 100)
                self.progress_update.emit(progress)
            
            # 3. Stitch back
            self.log_update.emit("Reassembling video...")
            self.generator.frames_to_video(temp_dir, input_path, output_path)
            
            # 4. Cleanup
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            
        else:
            # IMAGE MODE
            def callback(step, total_steps):
                progress = int(((step + 1) / total_steps) * 100)
                self.progress_update.emit(progress)
                self.log_update.emit(f"AI Processing: Step {step + 1}/{total_steps}")

            ai_engine.edit_image(input_path, prompt, output_path, status_callback=callback)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EC Video Generator Studio")
        self.resize(900, 750) 
        
        icon_path = resource_path(os.path.join("assets", "icon.png"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # UI State Variables
        self.image_path = None
        self.audio_path = None
        self.video_input_path = None
        self.img_batch_paths = []
        self.concat_img1 = None
        self.concat_img2 = None
        self.ai_input_path = None

        self.setup_ui()
        self.setStyleSheet(DARK_THEME)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)

        # Header
        header = QLabel("Video & AI Studio")
        header.setObjectName("Header")
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

        # --- TABS ---
        self.tabs = QTabWidget()
        self.tab_create = QWidget(); self.setup_create_tab(); self.tabs.addTab(self.tab_create, "Create Video")
        self.tab_upscale = QWidget(); self.setup_upscale_tab(); self.tabs.addTab(self.tab_upscale, "Upscale Video")
        self.tab_images = QWidget(); self.setup_image_tools_tab(); self.tabs.addTab(self.tab_images, "Image Tools")
        self.tab_ai = QWidget(); self.setup_ai_tab(); self.tabs.addTab(self.tab_ai, "✨ AI Editor")
        main_layout.addWidget(self.tabs)

        # --- PROGRESS & LOGS ---
        progress_group = QGroupBox("Status & Logs")
        pg_layout = QVBoxLayout()

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setStyleSheet("text-align: center; color: black; font-weight: bold;")
        pg_layout.addWidget(self.progress)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setFixedHeight(120)
        self.log_console.setStyleSheet("background-color: #111; color: #00ff00; font-family: Consolas; font-size: 12px;")
        self.log_console.setPlaceholderText("System logs will appear here...")
        pg_layout.addWidget(self.log_console)

        progress_group.setLayout(pg_layout)
        main_layout.addWidget(progress_group)

    # --- TAB SETUP FUNCTIONS ---
    def setup_create_tab(self):
        layout = QVBoxLayout(self.tab_create)
        self.lbl_image = QLabel("No Image Selected")
        btn_image = QPushButton("Select Image"); btn_image.clicked.connect(self.select_image)
        layout.addWidget(btn_image); layout.addWidget(self.lbl_image)
        self.lbl_audio = QLabel("No Audio Selected")
        btn_audio = QPushButton("Select Audio (MP3)"); btn_audio.clicked.connect(self.select_audio)
        layout.addWidget(btn_audio); layout.addWidget(self.lbl_audio)
        layout.addWidget(QLabel("Target Quality:"))
        self.combo_quality_video = QComboBox(); self.combo_quality_video.addItems(["1080p", "4k", "2k", "720p"])
        layout.addWidget(self.combo_quality_video)
        btn_run = QPushButton("Generate Video"); btn_run.setFixedHeight(40); btn_run.clicked.connect(self.run_create_video)
        layout.addWidget(btn_run); layout.addStretch()

    def setup_upscale_tab(self):
        layout = QVBoxLayout(self.tab_upscale)
        self.lbl_video = QLabel("No Video Selected")
        btn_video = QPushButton("Select Video File"); btn_video.clicked.connect(self.select_video_input)
        layout.addWidget(btn_video); layout.addWidget(self.lbl_video)
        layout.addWidget(QLabel("Target Quality:"))
        self.combo_quality_upscale = QComboBox(); self.combo_quality_upscale.addItems(["1080p", "4k", "2k", "720p"])
        layout.addWidget(self.combo_quality_upscale)
        btn_run = QPushButton("Upscale Video"); btn_run.setFixedHeight(40); btn_run.clicked.connect(self.run_upscale_video)
        layout.addWidget(btn_run); layout.addStretch()

    def setup_image_tools_tab(self):
        layout = QVBoxLayout(self.tab_images)
        layout.addWidget(QLabel("Select Tool:"))
        self.combo_img_mode = QComboBox(); self.combo_img_mode.addItems(["Upscale Images (Batch)", "Concat 2 Images"])
        self.combo_img_mode.currentIndexChanged.connect(self.switch_image_mode)
        layout.addWidget(self.combo_img_mode)
        self.stack_img = QStackedWidget()
        
        p1 = QWidget(); p1_layout = QVBoxLayout(p1)
        self.lbl_batch = QLabel("No Images Selected")
        btn_batch = QPushButton("Select Images"); btn_batch.clicked.connect(self.select_batch_images)
        p1_layout.addWidget(btn_batch); p1_layout.addWidget(self.lbl_batch)
        p1_layout.addWidget(QLabel("Target Resolution:"))
        self.combo_quality_img = QComboBox(); self.combo_quality_img.addItems(["4k", "2k", "1080p"])
        p1_layout.addWidget(self.combo_quality_img)
        btn_run_img = QPushButton("Upscale Images"); btn_run_img.setFixedHeight(40); btn_run_img.clicked.connect(self.run_upscale_images)
        p1_layout.addWidget(btn_run_img); p1_layout.addStretch()
        
        p2 = QWidget(); p2_layout = QVBoxLayout(p2)
        self.lbl_c1 = QLabel("Left: None"); btn_c1 = QPushButton("Select Left"); btn_c1.clicked.connect(lambda: self.select_concat_img(1))
        p2_layout.addWidget(btn_c1); p2_layout.addWidget(self.lbl_c1)
        self.lbl_c2 = QLabel("Right: None"); btn_c2 = QPushButton("Select Right"); btn_c2.clicked.connect(lambda: self.select_concat_img(2))
        p2_layout.addWidget(btn_c2); p2_layout.addWidget(self.lbl_c2)
        btn_run_cat = QPushButton("Merge Images"); btn_run_cat.setFixedHeight(40); btn_run_cat.clicked.connect(self.run_concat_images)
        p2_layout.addWidget(btn_run_cat); p2_layout.addStretch()

        self.stack_img.addWidget(p1); self.stack_img.addWidget(p2)
        layout.addWidget(self.stack_img)

    def setup_ai_tab(self):
        layout = QVBoxLayout(self.tab_ai)
        input_group = QGroupBox("1. Select Image or Video")
        ig_layout = QHBoxLayout()
        self.btn_ai_input = QPushButton("Select Image/Video to Edit"); self.btn_ai_input.clicked.connect(self.select_ai_input)
        ig_layout.addWidget(self.btn_ai_input)
        input_group.setLayout(ig_layout)
        layout.addWidget(input_group)

        splitter = QSplitter(Qt.Horizontal)
        self.lbl_ai_preview_before = QLabel("Before"); self.lbl_ai_preview_before.setAlignment(Qt.AlignCenter); self.lbl_ai_preview_before.setStyleSheet("border: 2px dashed #444; background: #222;"); self.lbl_ai_preview_before.setMinimumSize(300, 300)
        self.lbl_ai_preview_after = QLabel("After Result"); self.lbl_ai_preview_after.setAlignment(Qt.AlignCenter); self.lbl_ai_preview_after.setStyleSheet("border: 2px solid #0078d4; background: #222;"); self.lbl_ai_preview_after.setMinimumSize(300, 300)
        splitter.addWidget(self.lbl_ai_preview_before); splitter.addWidget(self.lbl_ai_preview_after)
        layout.addWidget(splitter)

        prompt_group = QGroupBox("2. Describe the edit")
        pg_layout = QVBoxLayout()
        self.txt_prompt = QLineEdit(); self.txt_prompt.setPlaceholderText("e.g., 'make the jacket red', 'make it look like a cartoon'")
        self.txt_prompt.setFixedHeight(40); self.txt_prompt.setStyleSheet("font-size: 14px; padding: 5px;")
        pg_layout.addWidget(self.txt_prompt)
        prompt_group.setLayout(pg_layout)
        layout.addWidget(prompt_group)

        self.btn_run_ai = QPushButton("✨ Apply Magic Edit ✨"); self.btn_run_ai.setFixedHeight(50); self.btn_run_ai.setStyleSheet("background-color: #6a00ff; font-size: 16px;"); self.btn_run_ai.clicked.connect(self.run_ai_edit)
        layout.addWidget(self.btn_run_ai)

    def switch_image_mode(self, index): self.stack_img.setCurrentIndex(index)

    # --- HANDLERS ---
    def select_image(self): self._select_file(self.lbl_image, "image_path", "Images (*.png *.jpg)")
    def select_audio(self): self._select_file(self.lbl_audio, "audio_path", "Audio (*.mp3)")
    def select_video_input(self): self._select_file(self.lbl_video, "video_input_path", "Video (*.mp4)")
    def _select_file(self, label, var_name, filter_str):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", filter_str)
        if path: setattr(self, var_name, path); label.setText(os.path.basename(path))

    def select_batch_images(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Images", "", "Images (*.png *.jpg)")
        if paths: self.img_batch_paths = paths; self.lbl_batch.setText(f"{len(paths)} files")

    def select_concat_img(self, num):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg)")
        if path:
            if num == 1: self.concat_img1 = path; self.lbl_c1.setText(os.path.basename(path))
            else: self.concat_img2 = path; self.lbl_c2.setText(os.path.basename(path))

    def select_ai_input(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image/Video", "", "Files (*.png *.jpg *.jpeg *.mp4 *.avi)")
        if path:
            self.ai_input_path = path
            self.btn_ai_input.setText(os.path.basename(path))
            
            if path.lower().endswith(('.mp4', '.avi')):
                self.lbl_ai_preview_before.setText("🎥 Video Selected\n(No Preview)")
            else:
                pixmap = QPixmap(path).scaled(self.lbl_ai_preview_before.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.lbl_ai_preview_before.setPixmap(pixmap)

    # --- RUNNERS ---
    def run_create_video(self): self.start_worker('create_video', img=self.image_path, audio=self.audio_path, output=self._save("Video (*.mp4)"), quality=self.combo_quality_video.currentText())
    def run_upscale_video(self): self.start_worker('upscale_video', video=self.video_input_path, output=self._save("Video (*.mp4)"), quality=self.combo_quality_upscale.currentText())
    def run_concat_images(self): self.start_worker('concat_images', img1=self.concat_img1, img2=self.concat_img2, output=self._save("Image (*.png)"))
    def run_upscale_images(self): 
        folder = QFileDialog.getExistingDirectory(self, "Output Folder")
        if folder: self.start_worker('upscale_images', images=self.img_batch_paths, output_folder=folder, quality=self.combo_quality_img.currentText())

    def run_ai_edit(self):
        if not self.ai_input_path or not self.txt_prompt.text():
            QMessageBox.warning(self, "Error", "Missing Input or Prompt"); return
        
        is_video = self.ai_input_path.lower().endswith(('.mp4', '.avi'))
        filter_str = "Video (*.mp4)" if is_video else "Image (*.png)"
        default_name = "ai_result.mp4" if is_video else "ai_result.png"
        
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Result", default_name, filter_str)
        if save_path:
            self.ai_output_path = save_path
            self.start_worker('ai_edit', img=self.ai_input_path, prompt=self.txt_prompt.text(), output=save_path)

    def _save(self, filter_str):
        path, _ = QFileDialog.getSaveFileName(self, "Save File", "", filter_str)
        return path

    def start_worker(self, mode, **kwargs):
        if mode != 'upscale_images' and not kwargs.get('output'): return 
        self.set_ui_busy(True)
        self.log_console.clear()
        self.worker = WorkerThread(mode, **kwargs)
        self.worker.finished.connect(self.on_finished)
        self.worker.progress_update.connect(self.update_progress)
        self.worker.log_update.connect(self.append_log)
        self.worker.start()

    def update_progress(self, val): self.progress.setValue(val)
    def append_log(self, text): self.log_console.append(text)
    
    def set_ui_busy(self, busy):
        self.tabs.setDisabled(busy)
        self.btn_run_ai.setDisabled(busy)

    def on_finished(self, success, message):
        self.set_ui_busy(False)
        if success:
            self.progress.setValue(100)
            self.append_log("✅ DONE.")
            if self.tabs.currentIndex() == 3 and hasattr(self, 'ai_output_path') and os.path.exists(self.ai_output_path):
                 if self.ai_output_path.endswith('.png'):
                     pixmap = QPixmap(self.ai_output_path).scaled(self.lbl_ai_preview_after.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                     self.lbl_ai_preview_after.setPixmap(pixmap)
                 else:
                     self.lbl_ai_preview_after.setText("✅ Video Saved!")
            QMessageBox.information(self, "Success", message)
        else:
            self.append_log(f"❌ ERROR: {message}")
            QMessageBox.critical(self, "Error", message)