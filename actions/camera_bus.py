# -*- coding: utf-8 -*-
"""camera_bus.py — Webcam interface client using OpenCV."""
import os
import time
from pathlib import Path

try:
    import cv2
except ImportError:
    cv2 = None

SNAPSHOTS_DIR = Path(os.path.expanduser("~/Pictures/MIN Snapshots")).resolve()

def camera_bus(parameters: dict, player=None) -> str:
    """
    Captura una imagen o snapshot de la cámara web (webcam) activa usando OpenCV.
    Guarda el archivo resultante en el directorio 'Pictures/MIN Snapshots/' del usuario.
    """
    action = parameters.get("action", "capture").lower().strip()
    camera_index = int(parameters.get("camera_index", 0))

    if not cv2:
        return "Error: OpenCV ('opencv-python') no está instalado en el entorno de Python de MIN."

    if action == "capture":
        if player:
            player.write_log("📷 Inicializando cámara web para captura...")

        try:
            # Crear directorio si no existe
            SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

            # Iniciar captura de video en el índice indicado
            cap = cv2.VideoCapture(camera_index)
            if not cap.isOpened():
                return f"Error: No se pudo abrir la cámara web en el índice {camera_index}."

            # Dar tiempo a la cámara para ajustar el balance de blancos / brillo
            time.sleep(1.0)
            
            # Tomar frame
            ret, frame = cap.read()
            # Segunda lectura para asegurar un frame limpio y enfocado
            ret, frame = cap.read()
            
            cap.release()

            if not ret or frame is None:
                return "Error: No se pudo leer ningún cuadro (frame) de la cámara web."

            # Nombre de archivo dinámico con marca de tiempo
            filename = f"min_snapshot_{int(time.time())}.jpg"
            filepath = SNAPSHOTS_DIR / filename
            
            # Guardar el frame
            cv2.imwrite(str(filepath), frame)
            
            msg = f"Foto capturada exitosamente y guardada en: {filepath}"
            if player:
                player.write_log(f"📷 {msg}")
            return msg
        except Exception as e:
            return f"Excepción durante la captura de cámara web: {str(e)}"

    else:
        return f"Acción de cámara '{action}' no es compatible con el bus de cámara."
