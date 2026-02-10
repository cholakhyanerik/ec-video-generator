import subprocess
import os
from PIL import Image
from .gpu_utils import get_best_encoder

class VideoGenerator:
    def __init__(self):
        self.encoder = get_best_encoder()

    def generate_video(self, image_path, audio_path, output_path, quality_preset="1080p", progress_callback=None):
        """
        Generates video from image + audio.
        quality_preset options: '4k', '1080p', '720p'
        """
        if not os.path.exists(image_path) or not os.path.exists(audio_path):
            raise FileNotFoundError("Input files not found.")

        # 1. Detect Aspect Ratio
        with Image.open(image_path) as img:
            width, height = img.size
            is_wide = width >= height

        # 2. Set Resolution based on Quality & Aspect Ratio
        resolutions = {
            "4k": (3840, 2160),
            "1080p": (1920, 1080),
            "720p": (1280, 720)
        }
        
        target_w, target_h = resolutions.get(quality_preset, (1920, 1080))

        if not is_wide:
            # Swap for 9:16 vertical video
            target_w, target_h = target_h, target_w

        print(f"Generating {quality_preset} video ({target_w}x{target_h}) using {self.encoder}...")

        # 3. Construct FFmpeg Command
        # -t is safer than -shortest for exact duration match
        duration = self.get_audio_duration(audio_path)
        
        cmd = [
            'ffmpeg', '-y',
            '-loop', '1', '-i', image_path,
            '-i', audio_path,
            '-c:v', self.encoder,
            '-t', str(duration), 
            '-pix_fmt', 'yuv420p',
            '-vf', f'scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2',
            '-c:a', 'aac', '-b:a', '192k',
            '-shortest',
            output_path
        ]

        # 4. Run Command with SAFE ENCODING
        # encoding='utf-8' fixes the crash
        # errors='replace' prevents crashing if a weird character appears
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            encoding='utf-8', 
            errors='replace'
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            # Print stderr to console so we can see what happened if it fails
            print("FFMPEG ERROR LOG:", stderr)
            raise Exception(f"FFmpeg Error: {stderr}")

    def get_audio_duration(self, audio_path):
        # Helper to get duration string for ffmpeg
        # We also use safe encoding here just in case
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
             '-of', 'default=noprint_wrappers=1:nokey=1', audio_path],
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            encoding='utf-8',
            errors='replace'
        )
        return float(result.stdout.strip())