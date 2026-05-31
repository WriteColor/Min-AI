import urllib.parse
from actions.web.browser_registry import launch_url
from services.providers.search_service import get_search_service


def web_search(parameters: dict, player=None) -> str:
    query = parameters.get("query", "").strip()
    if not query:
        return "Error: Falta la busqueda (query)."

    # Provide search summary to AI
    search_service = get_search_service()
    summary = search_service.search_and_summarize(query, max_results=3)

    msg = f"Resultados obtenidos para '{query}'."
    if player:
        player.write_log(f"🔎 {msg}")
        
    return summary
