import os
import torch
from PIL import Image, ImageOps
from diffusers import (
    StableDiffusionInstructPix2PixPipeline, 
    EulerAncestralDiscreteScheduler,
    StableVideoDiffusionPipeline
)
from diffusers.utils import export_to_video

class AIImageEditor:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            print("Initializing AI Engine Wrapper...")
            cls._instance = super(AIImageEditor, cls).__new__(cls)
            cls._instance.device = "cuda" if torch.cuda.is_available() else "cpu"
            cls._instance.edit_pipe = None
            cls._instance.video_pipe = None
        return cls._instance

    def _load_edit_model(self):
        """ Loads InstructPix2Pix (Image Editing) """
        if self.edit_pipe is not None: return

        print("Loading Edit Model (InstructPix2Pix)...")
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        
        self.edit_pipe = StableDiffusionInstructPix2PixPipeline.from_pretrained(
            "timbrooks/instruct-pix2pix", 
            torch_dtype=dtype, 
            safety_checker=None
        )
        self.edit_pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(self.edit_pipe.scheduler.config)
        
        if self.device == "cuda":
            self.edit_pipe.enable_model_cpu_offload()

    def _load_video_model(self):
        """ Loads SVD (Image to Video) from an OPEN MIRROR """
        if self.video_pipe is not None: return

        print("Loading Video Model (SVD Open Mirror)...")
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        
        model_id = "vdo/stable-video-diffusion-img2vid-xt-1-1" 
        
        try:
            self.video_pipe = StableVideoDiffusionPipeline.from_pretrained(
                model_id, 
                torch_dtype=dtype, 
                variant="fp16"
            )
        except Exception as e:
            print(f"Mirror download failed, trying fallback... Error: {e}")
            self.video_pipe = StableVideoDiffusionPipeline.from_pretrained(
                "mkshing/svd-xt", 
                torch_dtype=dtype, 
                variant="fp16"
            )
        
        if self.device == "cuda":
            self.video_pipe.enable_model_cpu_offload() 
            self.video_pipe.unet.enable_forward_chunking()

    def _overlay_image(self, bg_image, ref_path):
        """ Pastes the reference image onto the background for the AI to fix """
        if not ref_path or not os.path.exists(ref_path):
            return bg_image
            
        try:
            fg_image = Image.open(ref_path).convert("RGBA")
            bg_image = bg_image.convert("RGBA")
            
            # Resize foreground to be roughly 50% of background size
            bg_w, bg_h = bg_image.size
            target_w = bg_w // 2
            ratio = target_w / fg_image.width
            target_h = int(fg_image.height * ratio)
            
            fg_image = fg_image.resize((target_w, target_h), Image.Resampling.LANCZOS)
            
            # Center it
            offset_x = (bg_w - target_w) // 2
            offset_y = (bg_h - target_h) // 2
            
            # Paste
            bg_image.alpha_composite(fg_image, (offset_x, offset_y))
            return bg_image.convert("RGB")
        except Exception as e:
            print(f"Overlay Error: {e}")
            return bg_image.convert("RGB")

    def edit_image(self, image_path, prompt, output_path, steps=20, image_guidance_scale=1.5, reference_path=None, status_callback=None):
        """ 
        Runs the Image Edit.
        - reference_path: Optional path to an image to 'add' to the scene.
        """
        self._load_edit_model()
             
        input_image = Image.open(image_path)
        input_image = ImageOps.exif_transpose(input_image).convert("RGB")
        
        # --- NEW: APPLY REFERENCE OVERLAY ---
        if reference_path:
            print(f"Applying Reference Image: {reference_path}")
            input_image = self._overlay_image(input_image, reference_path)
        
        max_dim = 768
        if max(input_image.size) > max_dim:
             input_image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        def pipe_callback(step, timestep, latents):
            if status_callback: status_callback(step, steps)

        with torch.autocast(self.device):
            res = self.edit_pipe(
                prompt, image=input_image, num_inference_steps=steps, 
                guidance_scale=7.5, 
                image_guidance_scale=image_guidance_scale, 
                callback=pipe_callback, callback_steps=1 
            ).images[0]

        res.save(output_path)

    def animate_image(self, image_path, output_path, steps=25, status_callback=None):
        self._load_video_model()

        input_image = Image.open(image_path).convert("RGB")
        input_image = ImageOps.exif_transpose(input_image)
        input_image = input_image.resize((1024, 576), Image.Resampling.LANCZOS)

        def pipe_callback(pipe, step, timestep, callback_kwargs):
            if status_callback: status_callback(step, steps)
            return callback_kwargs

        frames = self.video_pipe(
            input_image, 
            decode_chunk_size=2, 
            num_inference_steps=steps,
            motion_bucket_id=127, 
            generator=torch.manual_seed(42),
            callback_on_step_end=pipe_callback 
        ).frames[0]

        export_to_video(frames, output_path, fps=7)