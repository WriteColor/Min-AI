"""
Image Generation Service
=====================
Pipeline de generación de imágenes usando Pollinations.ai (gratuito).

Este servicio proporciona:
- Generación real de imágenes via Pollinations.ai
- Fallback a DALL-E si está disponible
- Validación y optimización de prompts
- Almacenamiento con metadatos
- Streaming de resultados a UI

Basado en el diseño del Área 10 del PLAN_DE_IMPLEMENTACION.md.
"""

import os
import json
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict
import urllib.parse
import urllib.request
import urllib.error
import base64
import io

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


@dataclass
class ImageMetadata:
    """Metadatos de una imagen generada."""
    id: str
    prompt: str
    provider: str  # 'pollinations', 'dalle', etc.
    model: str
    timestamp: str
    file_path: str
    dimensions: Tuple[int, int]
    file_size: int
    style: Optional[str] = None
    seed: Optional[int] = None
    success: bool = True
    error: Optional[str] = None


class ImageGenerator:
    """
    Pipeline de generación de imágenes.
    
    Uso:
        generator = ImageGenerator()
        
        # Generación simple
        result = generator.generate("a beautiful sunset")
        
        # Generación con opciones
        result = generator.generate(
            prompt="cyberpunk city at night",
            style="cyberpunk",
            width=1024,
            height=1024
        )
    """
    
    POLLINATIONS_URL = "https://image.pollinations.ai/"
    IMAGES_DIR = Path(os.path.expanduser("~/Pictures/MIN Generated Images"))
    METADATA_DIR = Path("logs/image_generation")
    
    STYLE_PRESETS = {
        "cyberpunk": "cyberpunk aesthetic, neon lights, dark, rain",
        "realistic": "photorealistic, detailed, 4k quality",
        "abstract": "abstract art, colorful, geometric patterns",
        "anime": "anime style, vibrant colors, manga",
        "oil_painting": "oil painting style, classical art",
        "watercolor": "watercolor painting, soft colors",
        "digital_art": "digital art, illustration, detailed",
        "minimalist": "minimalist design, simple, clean lines",
    }
    
    def __init__(self):
        self.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        self.METADATA_DIR.mkdir(parents=True, exist_ok=True)
        
        self._default_width = 1024
        self._default_height = 1024
        self._default_model = "stable-diffusion"  # Pollinations default
        self._default_steps = 20
        self._default_seed = None  # Random if None
        
        self._metadata_file = self.METADATA_DIR / "generated_images.jsonl"
    
    def _generate_id(self) -> str:
        """Generate unique ID for image."""
        timestamp = datetime.now().strftime('%H%M%S')
        random_hex = hashlib.md5(str(time.time()).encode()).hexdigest()[:6]
        return f"img_{timestamp}_{random_hex}"
    
    def _sanitize_prompt(self, prompt: str) -> str:
        """Clean and sanitize prompt for URL encoding."""
        # Remove problematic characters
        prompt = prompt.strip()
        # Limit length
        max_length = 500
        if len(prompt) > max_length:
            prompt = prompt[:max_length]
        return prompt
    
    def _apply_style_preset(self, prompt: str, style: Optional[str]) -> str:
        """Apply style preset to prompt if specified."""
        if not style:
            return prompt
        
        style_lower = style.lower().strip()
        if style_lower in self.STYLE_PRESETS:
            preset = self.STYLE_PRESETS[style_lower]
            # Combine original prompt with style
            return f"{prompt}, {preset}"
        
        # If style is not a preset, treat it as additional description
        return f"{prompt}, {style}"
    
    def _build_pollinations_url(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        model: Optional[str] = None,
        seed: Optional[int] = None,
        steps: int = 20
    ) -> str:
        """Build Pollinations.ai URL for image generation."""
        sanitized = self._sanitize_prompt(prompt)
        encoded_prompt = urllib.parse.quote(sanitized)
        
        params = [
            f"prompt={encoded_prompt}",
            f"width={width}",
            f"height={height}",
            f"steps={steps}",
        ]
        
        if model:
            params.append(f"model={urllib.parse.quote(model)}")
        if seed is not None:
            params.append(f"seed={seed}")
        else:
            # Random seed for variety
            import random
            params.append(f"seed={random.randint(1, 999999)}")
        
        return f"{self.POLLINATIONS_URL}?{'&'.join(params)}"
    
    def _download_image(self, url: str, filepath: Path, timeout: int = 60) -> bool:
        """Download image from URL to file."""
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = response.read()
            
            filepath.write_bytes(data)
            return True
            
        except Exception as e:
            print(f"[ImageGenerator] Download failed: {e}")
            return False
    
    def _validate_image(self, filepath: Path) -> Tuple[bool, Tuple[int, int]]:
        """Validate that the downloaded file is a valid image."""
        if not HAS_PIL:
            return True, (0, 0)
        
        try:
            with Image.open(filepath) as img:
                return True, img.size
        except Exception:
            return False, (0, 0)
    
    def generate(
        self,
        prompt: str,
        style: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        model: Optional[str] = None,
        seed: Optional[int] = None,
        steps: Optional[int] = None,
        save: bool = True,
        return_metadata: bool = True
    ) -> Tuple[Optional[str], Optional[ImageMetadata]]:
        """
        Generate an image from text prompt.
        
        Args:
            prompt: Text description of the desired image
            style: Style preset (cyberpunk, realistic, anime, etc.)
            width: Image width in pixels (default: 1024)
            height: Image height in pixels (default: 1024)
            model: Model to use (pollinations default if None)
            seed: Random seed for reproducibility
            steps: Number of diffusion steps (default: 20)
            save: Whether to save to disk
            return_metadata: Whether to return metadata
            
        Returns:
            (image_path, metadata) tuple, or (None, None) if failed
        """
        if not prompt or not prompt.strip():
            return None, None
        
        image_id = self._generate_id()
        timestamp = datetime.now().isoformat()
        
        # Apply style if specified
        enhanced_prompt = self._apply_style_preset(prompt, style)
        
        # Use defaults
        w = width or self._default_width
        h = height or self._default_height
        m = model or self._default_model
        s = steps or self._default_steps
        
        # Build URL
        url = self._build_pollinations_url(enhanced_prompt, w, h, m, seed, s)
        
        metadata = ImageMetadata(
            id=image_id,
            prompt=prompt,
            provider="pollinations",
            model=m,
            timestamp=timestamp,
            file_path="",
            dimensions=(w, h),
            file_size=0,
            style=style,
            seed=seed,
            success=False,
            error=None
        )
        
        if not save:
            return url, metadata
        
        # Prepare filepath
        safe_name = "".join(c if c.isalnum() else "_" for c in prompt[:30])
        filename = f"{image_id}_{safe_name}.png"
        filepath = self.IMAGES_DIR / filename
        
        # Download
        success = self._download_image(url, filepath)
        
        if success:
            valid, dims = self._validate_image(filepath)
            if valid:
                metadata.success = True
                metadata.file_path = str(filepath)
                metadata.dimensions = dims
                metadata.file_size = filepath.stat().st_size
                
                # Save metadata
                self._save_metadata(metadata)
                
                return str(filepath), metadata
            else:
                metadata.error = "Invalid image downloaded"
        else:
            metadata.error = "Download failed"
        
        return None, metadata
    
    def generate_with_fallback(
        self,
        prompt: str,
        style: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None
    ) -> Tuple[Optional[str], Optional[ImageMetadata]]:
        """
        Generate image with fallback to default on failure.
        
        Tries Pollinations.ai first, falls back to a default image on failure.
        """
        path, metadata = self.generate(prompt, style, width, height)
        
        if path is not None:
            return path, metadata
        
        # Fallback to a simple abstract image
        fallback_prompt = style or "abstract colorful art"
        path, metadata = self.generate(fallback_prompt, style=None, width=512, height=512)
        
        if metadata:
            metadata.error = f"Fallback used. Original prompt '{prompt}' failed."
        
        return path, metadata
    
    def _save_metadata(self, metadata: ImageMetadata) -> None:
        """Save metadata to JSONL file."""
        try:
            with open(self._metadata_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(metadata), ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"[ImageGenerator] Metadata save failed: {e}")
    
    def get_recent_generations(self, count: int = 10) -> list:
        """Get recent image generation records."""
        if not self._metadata_file.exists():
            return []
        
        try:
            with open(self._metadata_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            entries = []
            for line in lines[-count:]:
                try:
                    entries.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
            
            return entries
        except Exception:
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        recent = self.get_recent_generations(100)
        
        success_count = sum(1 for e in recent if e.get('success', False))
        fail_count = len(recent) - success_count
        
        providers = {}
        for e in recent:
            p = e.get('provider', 'unknown')
            providers[p] = providers.get(p, 0) + 1
        
        return {
            "total_generations": len(recent),
            "successful": success_count,
            "failed": fail_count,
            "success_rate": success_count / len(recent) if recent else 0,
            "by_provider": providers,
            "images_dir": str(self.IMAGES_DIR)
        }


# Singleton instance
_generator_instance: Optional[ImageGenerator] = None


def get_generator() -> ImageGenerator:
    """Get singleton generator instance."""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = ImageGenerator()
    return _generator_instance


def quick_generate(prompt: str, style: Optional[str] = None) -> str:
    """
    Quick image generation function for simple usage.
    
    Returns path to generated image or error message.
    """
    generator = get_generator()
    path, metadata = generator.generate(prompt, style=style)
    
    if path:
        return f"Image saved to: {path}"
    else:
        return f"Failed to generate image: {metadata.error if metadata else 'Unknown error'}"
