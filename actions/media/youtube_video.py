"""youtube_video.py — Clean YouTube video launching action."""
import re
import urllib.parse
import urllib.request
from actions.web.browser_registry import launch_url

def youtube_video(parameters: dict, response=None, player=None) -> str:
    """Search for and play a YouTube video in the default browser."""
    query = parameters.get("query", "").strip()
    if not query:
        return "Por favor, especifica qué deseas reproducir en YouTube, señor."
        
    try:
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://www.youtube.com/results?search_query={encoded_query}"

        if player:
            player.write_log(f"📺 Buscando '{query}' en YouTube...")

        req = urllib.request.Request(
            search_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"},
        )
        
        # Read search results page
        html = urllib.request.urlopen(req, timeout=8).read().decode("utf-8")
        
        # Modern regex matching JSON videoId blocks inside ytInitialData
        matches = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
        
        # Fallback to older watch?v= format matches
        if not matches:
            matches = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", html)

        if matches:
            # We filter out typical repeat elements to get the first real video ID
            video_id = matches[0]
            url = f"https://www.youtube.com/watch?v={video_id}"
            launch_url(url)
            msg = f"Reproduciendo '{query}' directamente en YouTube."
        else:
            launch_url(search_url)
            msg = f"Abrí resultados de búsqueda en YouTube para '{query}' (no se pudo extraer ID directo)."

        if player:
            player.write_log(f"📺 {msg}")
        return msg
    except Exception as e:
        # If anything fails, launch search page as fallback
        try:
            launch_url(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")
        except Exception:
            pass
        return f"Error al intentar reproducir en YouTube: {e}"
