import json
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
API_FILE = BASE_DIR / "config" / "config.json"

def _get_api_key() -> str:
    if not API_FILE.exists():
        return ""
    try:
        data = json.loads(API_FILE.read_text(encoding="utf-8"))
        return data.get("openrouter_api_key", "")
    except Exception:
        return ""

def _get_default_model() -> str:
    if not API_FILE.exists():
        return "google/gemini-2.5-flash:free"
    try:
        data = json.loads(API_FILE.read_text(encoding="utf-8"))
        return data.get("openrouter_default_model", "google/gemini-2.5-flash:free")
    except Exception:
        return "google/gemini-2.5-flash:free"

def openrouter_agent(query: str, model: str = "google/gemini-2.5-flash:free") -> str:
    """
    Delega una tarea de texto compleja a OpenRouter usando el modelo especificado.
    """
    api_key = _get_api_key()
    if not api_key:
        return (
            "No se encontró una clave de OpenRouter en la configuración. "
            "Por favor, añade 'openrouter_api_key' en config/config.json."
        )

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/min-beta", #The Repo is not avaible right now, but we can use this as a placeholder for the referer header
        "X-Title": "MIN AI Assistant",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model or _get_default_model(),
        "max_tokens": 1500,
        "messages": [
            {"role": "system", "content": "Eres un Agente Especialista delegado por MIN. Responde de forma clara y directa en español."},
            {"role": "user", "content": query}
        ]
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            if "choices" in response_data and len(response_data["choices"]) > 0:
                return response_data["choices"][0]["message"]["content"]
            else:
                return "Error: Respuesta inesperada de OpenRouter."
    except urllib.error.HTTPError as e:
        error_info = e.read().decode("utf-8")
        return f"Error de OpenRouter (HTTP {e.code}): {error_info}"
    except Exception as e:
        return f"Error al conectar con OpenRouter: {str(e)}"
