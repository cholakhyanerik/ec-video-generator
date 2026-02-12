import subprocess
import os
import shutil
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

    # --- IMAGE FUNCTIONS ---
    def upscale_image_batch(self, image_paths, output_folder, quality_preset):
        target_w, target_h = self._get_resolution(quality_preset)
        
        for img_path in image_paths:
            filename = os.path.basename(img_path)
            name, ext = os.path.splitext(filename)
            save_path = os.path.join(output_folder, f"{name}_{quality_preset}{ext}")

            with Image.open(img_path) as img:
                img.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
                img.save(save_path, quality=95)

    def concat_images(self, img1_path, img2_path, output_path):
        img1 = Image.open(img1_path)
        img2 = Image.open(img2_path)

        if img1.height != img2.height:
            ratio = img1.height / img2.height
            new_w = int(img2.width * ratio)
            img2 = img2.resize((new_w, img1.height), Image.Resampling.LANCZOS)

        total_width = img1.width + img2.width
        max_height = img1.height 

        new_img = Image.new('RGB', (total_width, max_height))
        new_img.paste(img1, (0, 0))
        new_img.paste(img2, (img1.width, 0))
        new_img.save(output_path, quality=95)

    # --- AI VIDEO HELPERS ---
    def extract_frames(self, video_path, output_folder):
        """ Extracts all frames from a video into a folder """
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)
        os.makedirs(output_folder)
            
        print(f"Extracting frames from {video_path}...")
        
        # Extract at 30fps
        cmd = [
            'ffmpeg', '-i', video_path, 
            '-vf', 'fps=30', 
            os.path.join(output_folder, 'frame_%04d.png')
        ]
        self._run_ffmpeg(cmd)
        
        # Return sorted list of frames
        return sorted([
            os.path.join(output_folder, f) 
            for f in os.listdir(output_folder) 
            if f.endswith('.png')
        ])

    def frames_to_video(self, frames_folder, audio_source_video, output_path):
        """ Stitches frames back into a video """
        print(f"Stitching video to {output_path}...")
        
        has_audio = self.has_audio_stream(audio_source_video)
        
        # Start command with input frames
        cmd = [
            'ffmpeg', '-y',
            '-framerate', '30', 
            '-i', os.path.join(frames_folder, 'frame_%04d.png'),
        ]
        
        # Add audio map if exists
        if has_audio:
            cmd.extend(['-i', audio_source_video, '-map', '0:v', '-map', '1:a', '-c:a', 'copy'])
            
        cmd.extend([
            '-c:v', self.encoder, 
            '-pix_fmt', 'yuv420p', 
            output_path
        ])
        
        self._run_ffmpeg(cmd)

    def has_audio_stream(self, video_path):
        try:
            cmd = [
                'ffprobe', '-v', 'error', 
                '-select_streams', 'a', 
                '-show_entries', 'stream=codec_name', 
                '-of', 'default=noprint_wrappers=1:nokey=1', 
                video_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return len(result.stdout.strip()) > 0
        except:
            return False

    # --- CORE HELPERS ---
    def _run_ffmpeg(self, cmd):
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise Exception(f"FFmpeg Error: {stderr}")

    def get_audio_duration(self, audio_path):
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', audio_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8', errors='replace')
        return float(result.stdout.strip())