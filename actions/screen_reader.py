# -*- coding: utf-8 -*-
"""screen_reader.py — Screen reader utility using AI vision OCR for MIN."""
import json
import base64
import urllib.request
import urllib.error
from pathlib import Path
from mss import mss
from PIL import Image
import io

API_FILE = Path("config/api_keys.json")

def _get_api_key() -> str:
    try:
        data = json.loads(API_FILE.read_text(encoding="utf-8"))
        return data.get("openrouter_api_key", "") or data.get("gemini_api_key", "")
    except Exception:
        return ""


def _get_model() -> str:
    try:
        data = json.loads(API_FILE.read_text(encoding="utf-8"))
        return data.get("vision_model", "google/gemini-2.5-flash")
    except Exception:
        return "google/gemini-2.5-flash"


def _capture_screen_base64() -> str:
    """
    Captura la pantalla principal, la redimensiona y la devuelve en base64.
    """
    with mss() as sct:
        monitor = sct.monitors[1] # Monitor principal
        screenshot = sct.grab(monitor)
        
        # Convertir a imagen de Pillow
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        
        # Redimensionar si es muy grande para ahorrar tokens/ancho de banda
        max_size = (1280, 720)
        img.thumbnail(max_size, Image.Resampling.BILINEAR)
        
        # Guardar en buffer en memoria como JPEG
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=65)
        
        # Codificar a base64
        img_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return img_b64


def screen_reader(parameters: dict = None, player=None) -> str:
    """
    Captura la pantalla y usa IA para transcribir y estructurar todo el texto visible.
    """
    api_key = _get_api_key()
    if not api_key:
        return (
            "Error: No se encontró una clave de API (OpenRouter/Gemini) en config/api_keys.json. "
            "Asegúrate de configurar tus credenciales."
        )
        
    query = (
        "Actúa como un lector de pantalla inteligente para personas con discapacidad visual. "
        "Lee y transcribe todo el texto visible en esta captura de pantalla de forma ordenada (de arriba a abajo, de izquierda a derecha). "
        "Resume las secciones principales y describe de forma sencilla los elementos gráficos o botones visibles. Responde en español."
    )
    
    if player:
        player.write_log("🔊 Capturando pantalla para el lector inteligente...")
        
    try:
        b64_image = _capture_screen_base64()
    except Exception as e:
        return f"Error al capturar la pantalla para el lector de pantalla: {e}"
        
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/min-beta",
        "X-Title": "MIN AI Assistant",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": _get_model(),
        "max_tokens": 1500,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": query
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_image}"
                        }
                    }
                ]
            }
        ]
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=40) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            if "choices" in response_data and len(response_data["choices"]) > 0:
                result = response_data["choices"][0]["message"]["content"]
                if player:
                    player.write_log("🔊 Lectura de pantalla completada.")
                return result
            else:
                return "Error: Respuesta inesperada del lector de pantalla."
    except urllib.error.HTTPError as e:
        error_info = e.read().decode("utf-8")
        return f"Error al analizar la pantalla (HTTP {e.code}): {error_info}"
    except Exception as e:
        return f"Error al conectar con la API para el lector de pantalla: {str(e)}"
