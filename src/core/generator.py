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
            "2k": (2560, 1440),
            "1080p": (1920, 1080),
            "720p": (1280, 720)
        }
        return resolutions.get(preset, (1920, 1080))

    # --- VIDEO FUNCTIONS ---
    def generate_video(self, image_path, audio_path, output_path, quality_preset="1080p"):
        if not os.path.exists(image_path) or not os.path.exists(audio_path):
            raise FileNotFoundError("Input files not found.")

        with Image.open(image_path) as img:
            width, height = img.size
            is_wide = width >= height

        target_w, target_h = self._get_resolution(quality_preset)
        if not is_wide:
            target_w, target_h = target_h, target_w 

        duration = self.get_audio_duration(audio_path)
        
        cmd = [
            'ffmpeg', '-y', '-loop', '1', '-i', image_path, '-i', audio_path,
            '-c:v', self.encoder, '-t', str(duration), '-pix_fmt', 'yuv420p',
            '-vf', f'scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2',
            '-c:a', 'aac', '-b:a', '192k', '-shortest', output_path
        ]
        self._run_ffmpeg(cmd)

    def upscale_video(self, input_video, output_path, quality_preset="1080p"):
        target_w, target_h = self._get_resolution(quality_preset)
        cmd = [
            'ffmpeg', '-y', '-i', input_video, '-c:v', self.encoder,
            '-vf', f'scale={target_w}:{target_h}:flags=lanczos:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2',
            '-c:a', 'copy', output_path
        ]
        self._run_ffmpeg(cmd)

    # --- IMAGE FUNCTIONS (NEW) ---
    def upscale_image_batch(self, image_paths, output_folder, quality_preset):
        """ Resizes a list of images to the target resolution using High-Quality Lanczos """
        target_w, target_h = self._get_resolution(quality_preset)
        
        for img_path in image_paths:
            filename = os.path.basename(img_path)
            name, ext = os.path.splitext(filename)
            save_path = os.path.join(output_folder, f"{name}_{quality_preset}{ext}")

            with Image.open(img_path) as img:
                # Calculate new size maintaining aspect ratio
                img.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
                
                # Create a blank background (black) to center the image if aspect ratio differs
                # Or just save the resized image directly. Here we save directly to keep it clean.
                # If you want forced 16:9 padding like video, let me know. 
                # For now, standard resize is usually what people want for images.
                img.save(save_path, quality=95)

    def concat_images(self, img1_path, img2_path, output_path):
        """ Stitches two images side-by-side """
        img1 = Image.open(img1_path)
        img2 = Image.open(img2_path)

        # Resize img2 to match img1's height for a clean stitch
        # Ratio = img1_h / img2_h
        if img1.height != img2.height:
            ratio = img1.height / img2.height
            new_w = int(img2.width * ratio)
            img2 = img2.resize((new_w, img1.height), Image.Resampling.LANCZOS)

        # Create new canvas
        total_width = img1.width + img2.width
        max_height = img1.height # They match now

        new_img = Image.new('RGB', (total_width, max_height))
        new_img.paste(img1, (0, 0))
        new_img.paste(img2, (img1.width, 0))

        new_img.save(output_path, quality=95)

    # --- HELPERS ---
    def _run_ffmpeg(self, cmd):
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise Exception(f"FFmpeg Error: {stderr}")

    def get_audio_duration(self, audio_path):
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', audio_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8', errors='replace')
        return float(result.stdout.strip())