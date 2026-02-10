import sys
import os
from PySide6.QtWidgets import QApplication

# --- ADDED: Auto-Run FFmpeg Check ---
# We treat the setup script as a module to run its validation function
try:
    import setup_ffmpeg
    if not setup_ffmpeg.validate_environment():
        print("Cannot start application without FFmpeg.")
        # We don't exit here because sometimes the check fails falsely, 
        # we let the user try the GUI anyway, but it might crash on generation.
except ImportError:
    print("Warning: setup_ffmpeg.py not found. Skipping dependency check.")
# ------------------------------------

from src.ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Windows Taskbar Icon Fix
    if sys.platform == 'win32':
        import ctypes
        myappid = 'mycompany.ecvideogenerator.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())