import subprocess
import sys

def get_best_encoder():
    """
    Detects available hardware acceleration.
    Returns the ffmpeg video codec string (e.g., 'h264_nvenc', 'libx264').
    """
    # Common hardware encoders
    encoders = [
        ('h264_nvenc', 'NVIDIA GPU'), # Nvidia
        ('h264_amf', 'AMD GPU'),      # AMD
        ('h264_qsv', 'Intel QSV'),    # Intel
        ('videotoolbox', 'MacOS'),    # Mac
    ]

    print("Checking for GPU acceleration...")
    for encoder, name in encoders:
        try:
            # We try to run ffmpeg with the encoder to see if it errors out immediately
            subprocess.run(
                ['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=black:s=64x64', 
                 '-c:v', encoder, '-frames:v', '1', '-f', 'null', '-'],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            print(f"Success: Found {name} acceleration ({encoder}).")
            return encoder
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue

    print("No GPU acceleration found. Falling back to CPU (libx264).")
    return 'libx264'