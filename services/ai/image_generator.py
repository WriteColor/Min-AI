"""
Image Generation Service
=====================
Generación de imágenes vía Pollinations.ai (https://gen.pollinations.ai).

Basado en la documentación oficial:
  Base URL: https://gen.pollinations.ai
  GET /image/{prompt}?model={model}
  Auth: Authorization: Bearer sk_... o ?key=...
"""

import os
import json
import time
import hashlib
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict
import urllib.parse
import urllib.request
import urllib.error

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


POLLINATIONS_BASE = "https://gen.pollinations.ai"
IMAGES_DIR = Path(os.path.expanduser("~/Pictures/MIN Generated Images"))

AVAILABLE_MODELS = [
    "flux", "gptimage", "gptimage-large", "gpt-image-2",
    "seedream5", "seedream", "seedream-pro",
    "kontext", "nanobanana", "nanobanana-2", "nanobanana-pro",
    "zimage", "wan-image", "wan-image-pro", "qwen-image",
    "grok-imagine", "grok-imagine-pro", "klein",
    "p-image", "p-image-edit", "nova-canvas",
]

ASPECT_RATIOS = {
    "1:1": (1024, 1024),
    "4:3": (1152, 864),
    "3:4": (864, 1152),
    "16:9": (1280, 720),
    "9:16": (720, 1280),
}

METADATA_DIR = Path("logs/image_generation")


def _get_api_key_from_config() -> str:
    try:
        from core.config_manager import get_config
        return get_config().pollinations_api_key.strip()
    except Exception:
        return ""


def _get_default_model_from_config() -> str:
    try:
        from core.config_manager import get_config
        return get_config().pollinations_default_model.strip() or "flux"
    except Exception:
        return "flux"


@dataclass
class ImageMetadata:
    id: str
    prompt: str
    provider: str
    model: str
    timestamp: str
    file_path: str
    dimensions: Tuple[int, int]
    file_size: int
    style: Optional[str] = None
    seed: Optional[int] = None
    success: bool = True
    error: Optional[str] = None
    url: str = ""


class ImageGenerator:
    STYLE_PRESETS = {
        "cyberpunk":    "cyberpunk aesthetic, neon lights, dark, rain, futuristic city",
        "realistic":    "photorealistic, ultra detailed, 8k, natural lighting, sharp focus",
        "abstract":     "abstract art, vibrant colors, geometric patterns, modern",
        "anime":        "anime style, vibrant colors, manga aesthetic, cel shaded",
        "oil_painting": "oil painting, classical art, textured brushstrokes, canvas",
        "watercolor":   "watercolor painting, soft colors, paper texture, flowing",
        "digital_art":  "digital illustration, detailed, crisp, professional concept art",
        "minimalist":   "minimalist, simple, clean lines, negative space, elegant",
        "fantasy":      "fantasy art, magical, ethereal, epic, otherworldly",
        "cinematic":    "cinematic, film grain, dramatic lighting, movie still, 35mm",
    }

    def __init__(self):
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        METADATA_DIR.mkdir(parents=True, exist_ok=True)
        self._metadata_file = METADATA_DIR / "generated_images.jsonl"

    def _generate_id(self) -> str:
        ts = datetime.now().strftime('%H%M%S')
        r = hashlib.md5(str(time.time()).encode()).hexdigest()[:6]
        return f"img_{ts}_{r}"

    def _get_api_key(self) -> str:
        return _get_api_key_from_config()

    def _get_default_model(self) -> str:
        return _get_default_model_from_config()

    def _build_url(self, prompt: str, model: str, width: int, height: int,
                   seed: Optional[int] = None, negative_prompt: Optional[str] = None,
                   enhance: bool = False) -> str:
        encoded = urllib.parse.quote(prompt)
        url = f"{POLLINATIONS_BASE}/image/{encoded}?model={urllib.parse.quote(model)}"
        url += f"&width={width}&height={height}"
        if seed is not None:
            url += f"&seed={seed}"
        if negative_prompt:
            url += f"&negative_prompt={urllib.parse.quote(negative_prompt)}"
        if enhance:
            url += "&enhance=true"
        api_key = self._get_api_key()
        if api_key:
            url += f"&key={api_key}"
        return url

    def _download_image(self, url: str, filepath: Path, timeout: int = 90) -> bool:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "MIN-AI/2.0"
            })
            api_key = self._get_api_key()
            if api_key:
                req.add_header("Authorization", f"Bearer {api_key}")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            if len(data) < 256:
                return False
            filepath.write_bytes(data)
            return True
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:200]
            print(f"[ImageGenerator] HTTP {e.code}: {body}")
            return False
        except Exception as e:
            print(f"[ImageGenerator] Download failed: {e}")
            return False

    def _validate_image(self, filepath: Path) -> Tuple[bool, Tuple[int, int]]:
        if not HAS_PIL:
            return True, (0, 0)
        try:
            with Image.open(filepath) as img:
                return True, img.size
        except Exception:
            return False, (0, 0)

    def generate(self, prompt: str, style: Optional[str] = None,
                 width: Optional[int] = None, height: Optional[int] = None,
                 model: Optional[str] = None, seed: Optional[int] = None,
                 negative_prompt: Optional[str] = None, enhance: bool = False,
                 aspect_ratio: Optional[str] = None) -> Dict[str, Any]:
        if not prompt or not prompt.strip():
            return {"success": False, "error": "Empty prompt"}

        image_id = self._generate_id()

        if aspect_ratio and aspect_ratio in ASPECT_RATIOS:
            w, h = ASPECT_RATIOS[aspect_ratio]
        else:
            w = width or 1024
            h = height or 1024

        m = model or self._get_default_model()
        enhanced_prompt = self._apply_style(prompt, style)
        seed_val = seed if seed is not None else random.randint(1, 999999)

        url = self._build_url(enhanced_prompt, m, w, h, seed_val, negative_prompt, enhance)
        safe_name = "".join(c if c.isalnum() else "_" for c in prompt[:40])
        filename = f"{image_id}_{safe_name}.png"
        filepath = IMAGES_DIR / filename

        ok = self._download_image(url, filepath)
        dims = (w, h)
        error = None

        if ok:
            valid, dims = self._validate_image(filepath)
            if not valid:
                ok = False
                error = "Invalid image data"
                try:
                    filepath.unlink()
                except Exception:
                    pass

        if ok:
            metadata = ImageMetadata(
                id=image_id, prompt=prompt, provider="pollinations",
                model=m, timestamp=datetime.now().isoformat(),
                file_path=str(filepath), dimensions=dims,
                file_size=filepath.stat().st_size,
                style=style, seed=seed_val, success=True, url=url,
            )
            self._save_metadata(metadata)
            return {
                "success": True,
                "path": str(filepath),
                "url": url,
                "model": m,
                "dimensions": dims,
                "seed": seed_val,
                "metadata": asdict(metadata),
            }
        else:
            return {"success": False, "error": error or "Download failed"}

    def _apply_style(self, prompt: str, style: Optional[str]) -> str:
        if not style:
            return prompt
        key = style.lower().strip()
        if key in self.STYLE_PRESETS:
            return f"{prompt}, {self.STYLE_PRESETS[key]}"
        return f"{prompt}, {style}"

    def _save_metadata(self, metadata: ImageMetadata) -> None:
        try:
            with open(self._metadata_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(metadata), ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"[ImageGenerator] Metadata save failed: {e}")

    def get_recent(self, count: int = 10) -> list:
        if not self._metadata_file.exists():
            return []
        try:
            lines = self._metadata_file.read_text(encoding='utf-8').strip().splitlines()
            entries = []
            for line in lines[-count:]:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return entries
        except Exception:
            return []

    def get_stats(self) -> Dict[str, Any]:
        recent = self.get_recent(100)
        successes = sum(1 for e in recent if e.get('success'))
        return {
            "total": len(recent),
            "successful": successes,
            "failed": len(recent) - successes,
            "rate": successes / len(recent) if recent else 0,
            "images_dir": str(IMAGES_DIR),
        }


_generator_instance: Optional[ImageGenerator] = None


def get_generator() -> ImageGenerator:
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = ImageGenerator()
    return _generator_instance


def quick_generate(prompt: str, style: Optional[str] = None,
                   model: Optional[str] = None, save_dir: Optional[str] = None,
                   aspect_ratio: Optional[str] = None,
                   width: Optional[int] = None, height: Optional[int] = None) -> Dict[str, Any]:
    g = get_generator()
    return g.generate(prompt, style=style, model=model,
                      aspect_ratio=aspect_ratio, width=width, height=height)
