# -*- coding: utf-8 -*-
"""
camera_bus.py — Tool action to interact with the holographic gesture camera control via voice commands.
"""

def camera_bus(parameters: dict, player=None) -> str:
    """
    Voice tool action to toggle camera gesture control.
    """
    action = parameters.get("action", "toggle").lower().strip()
    
    if player:
        is_open = hasattr(player, "_gesture_thread") and player._gesture_thread is not None
        
        if action in ("enable", "show", "on", "activar", "conectar"):
            if is_open:
                return "El subsistema de pilotaje gestual ya está activo en pantalla, señor."
            else:
                player._toggle_camera_gestures()
                return "Entendido. He iniciado el subsistema de pilotaje gestual por cámara, señor."
        elif action in ("disable", "hide", "off", "desactivar", "apagar"):
            if not is_open:
                return "El subsistema de pilotaje gestual ya está apagado, señor."
            else:
                player.stop_gesture_thread()
                return "Apagando el subsistema de pilotaje gestual por cámara, señor."
        else: # toggle
            if is_open:
                player.stop_gesture_thread()
                return "He desactivado el subsistema de pilotaje gestual por cámara, señor."
            else:
                player._toggle_camera_gestures()
                return "He activado el subsistema de pilotaje gestual por cámara, señor."
            
    return "La cámara gestual no está disponible en la interfaz actual, señor."
