# -*- coding: utf-8 -*-
"""accessibility_overlay.py — Controls the floating accessibility bar / overlay for MIN."""

def accessibility_overlay(parameters: dict, player=None) -> str:
    """
    Controla el overlay flotante de accesibilidad.
    Acciones: show (mostrar), hide (ocultar), toggle (alternar), status (estado)
    """
    action = str(parameters.get("action", "show")).lower().strip()
    
    if action not in ("show", "hide", "toggle", "status"):
        action = "show"
        
    if player and hasattr(player, "broadcast"):
        player.broadcast({
            "type": "accessibility_overlay",
            "action": action
        })
        player.write_log(f"ACC: Estado de la barra flotante de accesibilidad cambiado a: {action}")
        
    return f"Estado del panel flotante de accesibilidad: {action}."
