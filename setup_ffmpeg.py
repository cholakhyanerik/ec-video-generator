import os
import platform
import subprocess
import shutil
import sys

def check_ffmpeg():
    """Checks if ffmpeg is accessible."""
    if shutil.which("ffmpeg"):
        return True
    
    # Common Winget install locations (fallback check)
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    possible_paths = [
        os.path.join(local_app_data, "Microsoft", "WinGet", "Packages", "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe", "ffmpeg-6.1.1-full_build", "bin"),
        os.path.join(local_app_data, "Microsoft", "WinGet", "Links"),
        "C:\\Program Files\\ffmpeg\\bin",
    ]
    
    for path in possible_paths:
        if os.path.exists(os.path.join(path, "ffmpeg.exe")):
            print(f"✅ Found FFmpeg at: {path}")
            # Add to PATH for this session only
            os.environ["PATH"] += os.pathsep + path
            return True
            
    return False

def install_ffmpeg():
    system = platform.system()
    print(f"Detected OS: {system}")
    
    try:
        if system == "Windows":
            print("Attempting to install via Winget...")
            # We use 'upgrade' just in case it's installed but broken, 
            # and ignore return codes because Winget returns weird codes for "Already Installed"
            subprocess.run(["winget", "install", "Gyan.FFmpeg"], check=False)
            print("⚠️ Installation command finished. If you see an error above about 'existing package', that is fine.")
            
        elif system == "Darwin": # MacOS
            subprocess.run(["brew", "install", "ffmpeg"], check=True)
            
        elif system == "Linux":
            subprocess.run(["sudo", "apt", "update"], check=True)
            subprocess.run(["sudo", "apt", "install", "-y", "ffmpeg"], check=True)
            
    except Exception as e:
        print(f"❌ Setup Warning: {e}")

def validate_environment():
    """Runs the check and install if needed."""
    if check_ffmpeg():
        return True

    print("⚠️ FFmpeg not found in PATH. Attempting auto-setup...")
    install_ffmpeg()
    
    # Check again after install
    if check_ffmpeg():
        print("✅ FFmpeg setup complete.")
        return True
    else:
        print("❌ CRITICAL ERROR: FFmpeg is installed but not found.")
        print("👉 PLEASE RESTART YOUR TERMINAL (Close VS Code and re-open) to refresh your system PATH.")
        return False

if __name__ == "__main__":
    validate_environment()