"""
Music Generation Service
=====================
Generación de música vía MiniMax API (https://api.minimax.io/v1/music_generation).

Modelos disponibles:
  - music-2.6: Text-to-Music con vocals
  - music-cover: Cover generation desde audio de referencia

Documentación: https://platform.minimax.io/docs/api-reference/music-generation
"""

import os
import json
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict

import urllib.request
import urllib.parse
import urllib.error


MINIMAX_BASE = "https://api.minimax.io/v1"
MUSIC_DIR = Path(os.path.expanduser("~/Music/MIN Generated Music"))
METADATA_DIR = Path("logs/music_generation")

AVAILABLE_MODELS = [
    "music-2.6",
    "music-cover",
]

AUDIO_SETTINGS = {
    "sample_rate": 44100,
    "bitrate": 256000,
    "format": "mp3",
}


def _get_api_key_from_config() -> str:
    try:
        from core.config_manager import get_config
        return get_config().minimax_api_key.strip()
    except Exception:
        return os.environ.get("MINIMAX_API_KEY", "")


def _get_default_model_from_config() -> str:
    try:
        from core.config_manager import get_config
        return get_config().minimax_music_model.strip() or "music-2.6"
    except Exception:
        return "music-2.6"


def _get_output_dir_from_config() -> Path:
    try:
        from core.config_manager import get_config
        path = get_config().minimax_music_output_dir
        if path:
            return Path(os.path.expanduser(path))
    except Exception:
        pass
    return MUSIC_DIR


@dataclass
class MusicMetadata:
    id: str
    prompt: str
    lyrics: str
    provider: str
    model: str
    timestamp: str
    file_path: str
    duration: float
    file_size: int
    style: Optional[str] = None
    success: bool = True
    error: Optional[str] = None
    url: str = ""
    is_instrumental: bool = False


class MusicGenerator:
    def __init__(self):
        out_dir = _get_output_dir_from_config()
        out_dir.mkdir(parents=True, exist_ok=True)
        METADATA_DIR.mkdir(parents=True, exist_ok=True)
        self._metadata_file = METADATA_DIR / "generated_music.jsonl"

    def _generate_id(self) -> str:
        ts = datetime.now().strftime('%H%M%S')
        r = hashlib.md5(str(time.time()).encode()).hexdigest()[:6]
        return f"music_{ts}_{r}"

    def _get_api_key(self) -> str:
        return _get_api_key_from_config()

    def _get_default_model(self) -> str:
        return _get_default_model_from_config()

    def _build_filename(self, music_id: str, prompt: str, fmt: str = "mp3") -> str:
        safe_name = "".join(c if c.isalnum() else "_" for c in prompt[:30])
        return f"{music_id}_{safe_name}.{fmt}"

    def generate(self, prompt: str, lyrics: Optional[str] = None,
                 model: Optional[str] = None,
                 is_instrumental: bool = False,
                 audio_url: Optional[str] = None,
                 cover_feature_id: Optional[str] = None,
                 lyrics_optimizer: bool = False) -> Dict[str, Any]:
        if not prompt or not prompt.strip():
            return {"success": False, "error": "Empty prompt"}

        music_id = self._generate_id()
        m = model or self._get_default_model()
        out_dir = _get_output_dir_from_config()

        payload = {
            "model": m,
            "prompt": prompt[:300],
            "audio_setting": {
                "sample_rate": AUDIO_SETTINGS["sample_rate"],
                "bitrate": AUDIO_SETTINGS["bitrate"],
                "format": AUDIO_SETTINGS["format"],
            },
            "output_format": "url",
        }

        if is_instrumental:
            payload["is_instrumental"] = True
        elif lyrics:
            payload["lyrics"] = lyrics[:1000]
        else:
            payload["lyrics_optimizer"] = lyrics_optimizer

        if audio_url:
            payload["audio_url"] = audio_url

        if cover_feature_id:
            payload["cover_feature_id"] = cover_feature_id

        api_key = self._get_api_key()
        if not api_key:
            return {"success": False, "error": "MiniMax API key not configured. Set minimax_api_key in config."}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        url = f"{MINIMAX_BASE}/music_generation"
        data = json.dumps(payload).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:500]
            print(f"[MusicGenerator] HTTP {e.code}: {body}")
            return {"success": False, "error": f"HTTP {e.code}: {body}"}
        except Exception as e:
            print(f"[MusicGenerator] Request failed: {e}")
            return {"success": False, "error": str(e)}

        audio_url_result = result.get("data", {}).get("audio_url") if isinstance(result, dict) else None
        if isinstance(result, dict) and "data" in result:
            audio_url_result = result["data"].get("audio_url")

        if not audio_url_result:
            return {
                "success": False,
                "error": result.get("base_resp", {}).get("msg", "No audio URL in response")
                if isinstance(result, dict) else "Unknown error",
            }

        filename = self._build_filename(music_id, prompt, "mp3")
        filepath = out_dir / filename

        downloaded, file_size = self._download_audio(audio_url_result, filepath)

        if not downloaded:
            return {
                "success": False,
                "error": "Download failed",
                "url": audio_url_result,
            }

        metadata = MusicMetadata(
            id=music_id,
            prompt=prompt,
            lyrics=lyrics or "",
            provider="minimax",
            model=m,
            timestamp=datetime.now().isoformat(),
            file_path=str(filepath),
            duration=0,
            file_size=file_size,
            success=True,
            url=audio_url_result,
            is_instrumental=is_instrumental,
        )
        self._save_metadata(metadata)

        return {
            "success": True,
            "path": str(filepath),
            "url": audio_url_result,
            "model": m,
            "metadata": asdict(metadata),
        }

    def generate_cover(self, audio_url: str, prompt: str,
                       model: str = "music-cover") -> Dict[str, Any]:
        if not audio_url:
            return {"success": False, "error": "audio_url required for cover generation"}
        return self.generate(prompt=prompt, model=model, audio_url=audio_url)

    def preprocess_cover(self, audio_url: str,
                        model: str = "music-cover") -> Dict[str, Any]:
        api_key = self._get_api_key()
        if not api_key:
            return {"success": False, "error": "MiniMax API key not configured"}

        payload = {
            "model": model,
            "audio_url": audio_url,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        url = f"{MINIMAX_BASE}/music_cover_preprocess"

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            return {
                "success": True,
                "cover_feature_id": result.get("cover_feature_id"),
                "formatted_lyrics": result.get("formatted_lyrics"),
                "structure_result": result.get("structure_result"),
                "audio_duration": result.get("audio_duration"),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_lyrics(self, prompt: str, mode: str = "write_full_song") -> Dict[str, Any]:
        api_key = self._get_api_key()
        if not api_key:
            return {"success": False, "error": "MiniMax API key not configured"}

        payload = {
            "mode": mode,
            "prompt": prompt[:300],
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        url = f"{MINIMAX_BASE}/lyrics_generation"

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            lyrics_text = result.get("lyrics", "") if isinstance(result, dict) else ""
            return {
                "success": True,
                "lyrics": lyrics_text,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _download_audio(self, url: str, filepath: Path, timeout: int = 180) -> Tuple[bool, int]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MIN-AI/2.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            filepath.write_bytes(data)
            return True, len(data)
        except Exception as e:
            print(f"[MusicGenerator] Download failed: {e}")
            return False, 0

    def _save_metadata(self, metadata: MusicMetadata) -> None:
        try:
            with open(self._metadata_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(metadata), ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"[MusicGenerator] Metadata save failed: {e}")

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
            "music_dir": str(_get_output_dir_from_config()),
        }


_generator_instance: Optional[MusicGenerator] = None


def get_generator() -> MusicGenerator:
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = MusicGenerator()
    return _generator_instance


def quick_generate(prompt: str, lyrics: Optional[str] = None,
                   model: Optional[str] = None,
                   is_instrumental: bool = False) -> Dict[str, Any]:
    g = get_generator()
    return g.generate(prompt, lyrics=lyrics, model=model,
                      is_instrumental=is_instrumental)


def quick_cover(audio_url: str, prompt: str,
                model: str = "music-cover") -> Dict[str, Any]:
    g = get_generator()
    return g.generate_cover(audio_url, prompt, model=model)


def quick_lyrics(prompt: str) -> Dict[str, Any]:
    g = get_generator()
    return g.generate_lyrics(prompt)
