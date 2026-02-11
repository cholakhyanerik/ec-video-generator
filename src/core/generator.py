import subprocess
import os
from PIL import Image
from .gpu_utils import get_best_encoder

class VideoGenerator:
    def __init__(self):
        self.encoder = get_best_encoder()

    def _get_resolution(self, preset):
        resolutions = {
            "4k": (3840, 2160),
            "2k": (2560, 1440), # Standard QHD
            "1080p": (1920, 1080),
            "720p": (1280, 720)
        }
        return resolutions.get(preset, (1920, 1080))

    def generate_video(self, image_path, audio_path, output_path, quality_preset="1080p"):
        """ Generates video from Image + Audio """
        if not os.path.exists(image_path) or not os.path.exists(audio_path):
            raise FileNotFoundError("Input files not found.")

        # 1. Detect Aspect Ratio
        with Image.open(image_path) as img:
            width, height = img.size
            is_wide = width >= height

        target_w, target_h = self._get_resolution(quality_preset)

        if not is_wide:
            target_w, target_h = target_h, target_w # Swap for vertical

        print(f"Generating {quality_preset} video ({target_w}x{target_h}) using {self.encoder}...")

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

        self._run_ffmpeg(cmd)

    def upscale_video(self, input_video, output_path, quality_preset="1080p"):
        """ Upscales an existing video """
        if not os.path.exists(input_video):
            raise FileNotFoundError("Input video not found.")

        target_w, target_h = self._get_resolution(quality_preset)
        
        print(f"Upscaling video to {target_w}x{target_h} using {self.encoder}...")

        # We use 'flags=lanczos' for better upscaling quality than default
        cmd = [
            'ffmpeg', '-y',
            '-i', input_video,
            '-c:v', self.encoder,
            '-vf', f'scale={target_w}:{target_h}:flags=lanczos:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2',
            '-c:a', 'copy', # Copy audio track without re-encoding (faster)
            output_path
        ]

        self._run_ffmpeg(cmd)

    def _run_ffmpeg(self, cmd):
        """ Helper to run commands safely """
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
            print("FFMPEG ERROR LOG:", stderr)
            raise Exception(f"FFmpeg Error: {stderr}")

    def get_audio_duration(self, audio_path):
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
             '-of', 'default=noprint_wrappers=1:nokey=1', audio_path],
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            encoding='utf-8',
            errors='replace'
        )
        return float(result.stdout.strip())