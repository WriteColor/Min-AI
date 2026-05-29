# -*- coding: utf-8 -*-
"""image_generation.py — Dynamic image generation/fetching client using LoremFlickr matching queries."""
import os
import urllib.parse
import urllib.request
import time
from pathlib import Path

IMAGES_DIR = Path(os.path.expanduser("~/Pictures/MIN Generated Images")).resolve()

def image_generation(parameters: dict, player=None) -> str:
    """
    Genera u obtiene una imagen adaptada al prompt/query del usuario de forma dinámica.
    Utiliza LoremFlickr o fallbacks públicos para devolver imágenes reales y hermosas relacionadas.
    """
    prompt = parameters.get("prompt", "").strip()
    if not prompt:
        # Fallback a parámetro de query
        prompt = parameters.get("query", "futuristic tech").strip()

    if player:
        player.write_log(f"🎨 Generando imagen para el prompt: '{prompt}'...")

    try:
        # Crear carpeta de destino
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)

        # Formatear el prompt como palabras clave separadas por comas para LoremFlickr
        # Ej: "gato espacial" -> "cat,space"
        keywords = prompt.lower()
        # Eliminar conectores comunes en español e inglés
        for word in ["de", "un", "una", "en", "el", "la", "con", "a", "an", "the", "in", "of", "with"]:
            keywords = keywords.replace(f" {word} ", " ")
        keywords = ",".join(keywords.split())
        
        encoded_keywords = urllib.parse.quote(keywords)
        fetch_url = f"https://loremflickr.com/800/600/{encoded_keywords}"

        # Nombre de archivo dinámico
        safe_name = "".join(c if c.isalnum() else "_" for c in prompt[:30])
        filename = f"min_image_{safe_name}_{int(time.time())}.jpg"
        filepath = IMAGES_DIR / filename

        # Descargar la imagen
        req = urllib.request.Request(fetch_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=12) as response:
            filepath.write_bytes(response.read())

        msg = f"Imagen generada para '{prompt}' y guardada con éxito en: {filepath}"
        if player:
            player.write_log(f"🎨 {msg}")
            
            # Si el player soporta widgets visuales, cargar la imagen
            if hasattr(player, "broadcast"):
                try:
                    # Enviar la ruta absoluta para que Tauri o React la renderice si aplica
                    player.broadcast({
                        "type": "log",
                        "value": f"MIN: He guardado la imagen en tu carpeta de Imágenes. Ruta: {filepath}"
                    })
                except Exception:
                    pass
        return msg
    except Exception as e:
        # Fallback a una imagen de LoremFlickr general
        try:
            fallback_url = "https://loremflickr.com/800/600/abstract,cyberpunk"
            fallback_file = IMAGES_DIR / f"min_image_fallback_{int(time.time())}.jpg"
            req = urllib.request.Request(fallback_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                fallback_file.write_bytes(response.read())
            return f"Imagen general de contingencia generada en: {fallback_file}. (Fallo en la query original: {e})"
        except Exception as fallback_err:
            return f"Fallo al generar imagen: {e}. Fallback error: {fallback_err}"
