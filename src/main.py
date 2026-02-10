import sys
import os
import ctypes
from PySide6.QtWidgets import QApplication, QMessageBox

# Import your setup script logic
try:
    import setup_ffmpeg
except ImportError:
    setup_ffmpeg = None

from src.ui.main_window import MainWindow

def show_ffmpeg_error():
    """Shows a graphical error message if FFmpeg is missing."""
    app = QApplication.instance() or QApplication(sys.argv)
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle("Missing Component")
    msg.setText("Critical Error: FFmpeg is not found.")
    msg.setInformativeText(
        "This application requires FFmpeg to generate videos.\n\n"
        "Please install FFmpeg manually or run the 'setup_ffmpeg.py' script provided with this app."
    )
    msg.exec()

if __name__ == "__main__":
    # 1. Create the App
    app = QApplication(sys.argv)

    # 2. Fix Windows Taskbar Icon
    if sys.platform == 'win32':
        myappid = 'mycompany.ecvideogenerator.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    # 3. Check for FFmpeg BEFORE opening the main window
    # We use the check function from your script, but we handle the failure with a GUI popup
    if setup_ffmpeg:
        # We only CHECK here. We don't auto-install because it might freeze the GUI.
        if not setup_ffmpeg.check_ffmpeg():
            show_ffmpeg_error()
            sys.exit(1) # Stop the app
    
    # 4. Launch the Window
    window = MainWindow()
    window.show()
    sys.exit(app.exec())