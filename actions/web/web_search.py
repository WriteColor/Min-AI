import urllib.parse
from actions.web.browser_registry import launch_url


def web_search(parameters: dict, player=None) -> str:
    query = parameters.get("query", "").strip()
    if not query:
        return "Error: Falta la busqueda (query)."

    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    launch_url(url)
    msg = f"Busqueda abierta para '{query}'."
    if player:
        player.write_log(f"🔎 {msg}")
    return msg
