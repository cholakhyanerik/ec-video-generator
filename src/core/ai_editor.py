import os
import torch
from PIL import Image, ImageOps
from diffusers import StableDiffusionInstructPix2PixPipeline, EulerAncestralDiscreteScheduler

class AIImageEditor:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            print("Initializing AI Engine... (This will take time on first run)")
            cls._instance = super(AIImageEditor, cls).__new__(cls)
            cls._instance._load_model()
        return cls._instance

    def _load_model(self):
        model_id = "timbrooks/instruct-pix2pix"
        
        if torch.cuda.is_available():
            self.device = "cuda"
            dtype = torch.float16
        else:
            self.device = "cpu"
            dtype = torch.float32

        # Load the pipeline
        self.pipe = StableDiffusionInstructPix2PixPipeline.from_pretrained(
            model_id, 
            torch_dtype=dtype, 
            safety_checker=None
        )
        self.pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(self.pipe.scheduler.config)
        self.pipe.to(self.device)
        
        if self.device == "cuda":
            self.pipe.enable_attention_slicing()

    def edit_image(self, image_path, prompt, output_path, steps=20, guidance_scale=7.5, image_guidance_scale=1.5, status_callback=None):
        """
        Runs the edit with progress reporting.
        status_callback: function(step, total_steps)
        """
        if not self.pipe:
             raise Exception("AI Model not initialized.")
             
        input_image = Image.open(image_path)
        input_image = ImageOps.exif_transpose(input_image)
        input_image = input_image.convert("RGB")

        # Resize safety
        max_dim = 768
        if max(input_image.size) > max_dim:
             input_image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        # Define the callback for the AI pipeline
        def pipe_callback(step, timestep, latents):
            if status_callback:
                # step is the current step index
                status_callback(step, steps)

        with torch.autocast(self.device):
            images = self.pipe(
                prompt, 
                image=input_image, 
                num_inference_steps=steps, 
                guidance_scale=guidance_scale,
                image_guidance_scale=image_guidance_scale,
                callback=pipe_callback,
                callback_steps=1 # Report every single step
            ).images

        images[0].save(output_path, quality=95)