import urllib.parse
from actions.web.browser_registry import launch_url


def google_maps(parameters: dict, player=None) -> str:
    action = parameters.get("action", "").lower().strip()
    if not action:
        return "Error: Falta la acción (action)."

    if action == "search":
        query = parameters.get("query", "").strip()
        if not query:
            return "Error: Falta la búsqueda (query)."
        url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(query)
        launch_url(url)
        msg = f"Mapa abierto para '{query}'."
    elif action == "directions":
        origin = parameters.get("origin", "").strip()
        destination = parameters.get("destination", "").strip()
        if not origin or not destination:
            return "Error: Se requieren 'origin' y 'destination'."
        mode = parameters.get("mode", "car").lower().strip()
        mode_map = {"car": "driving", "auto": "driving", "walk": "walking", "caminando": "walking", "bike": "bicycling", "bicicleta": "bicycling"}
        travelmode = mode_map.get(mode, "driving")
        url = (
            "https://www.google.com/maps/dir/?api=1&"
            + urllib.parse.urlencode(
                {
                    "origin": origin,
                    "destination": destination,
                    "travelmode": travelmode,
                }
            )
        )
        launch_url(url)
        msg = f"Ruta abierta de '{origin}' a '{destination}'."
    else:
        return "Acción no soportada. Usa 'search' o 'directions'."

    if player:
        player.write_log(f"🗺️ {msg}")
    return msg
