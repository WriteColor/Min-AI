import urllib.request
import urllib.parse
import re
import traceback
from actions.web.browser_registry import launch_url

def web_navigation(parameters: dict, player=None) -> str:
    """
    Maneja la navegación web, en especial reproducir música en YouTube u otras páginas.
    """
    action = parameters.get("action", "").lower()
    query = parameters.get("query", "")

    if not action or not query:
        return "Error: Faltan parámetros ('action' o 'query')."

    try:
        if action == "play_youtube" or action == "youtube":
            # Realizar búsqueda silenciosa en YouTube
            search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
            try:
                req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
                html = urllib.request.urlopen(req).read().decode('utf-8')
                
                # Extraer el primer videoId de la respuesta JSON inyectada en el HTML
                video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
                
                # Filtrar IDs repetidos manteniendo el orden
                unique_ids = []
                for vid in video_ids:
                    if vid not in unique_ids:
                        unique_ids.append(vid)
                
                if unique_ids:
                    first_video_id = unique_ids[0]
                    video_url = f"https://www.youtube.com/watch?v={first_video_id}"
                    
                    # Abrir en el navegador por defecto
                    launch_url(video_url)
                    
                    if player and hasattr(player, "set_state"):
                        player.set_state("SUCCESS")
                        
                    return f"He reproducido '{query}' en YouTube automáticamente (Abriendo: {video_url})."
                else:
                    # Si falla el regex, abrimos al menos los resultados de búsqueda
                    launch_url(search_url)
                    return f"Abrí los resultados de búsqueda en YouTube para '{query}', pero no pude auto-reproducir el video."
            except Exception as e_req:
                launch_url(search_url)
                return f"Abrí YouTube con tu búsqueda '{query}'. Hubo un error extrayendo el enlace directo: {e_req}"

        elif action == "search":
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            launch_url(search_url)
            return f"He abierto una búsqueda en Google para '{query}'."

        else:
            return f"Error: Acción web '{action}' desconocida."

    except Exception as e:
        return f"Error al navegar: {str(e)}\n{traceback.format_exc()}"
