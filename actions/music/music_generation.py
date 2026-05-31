"""music_generation.py — Thin wrapper delegating to services/music_generator.py"""

from services.ai.music_generator import quick_generate, quick_cover, quick_lyrics


def music_generation(parameters: dict, player=None) -> str:
    prompt = (parameters.get("prompt") or parameters.get("query", "")).strip()
    if not prompt:
        prompt = "upbeat electronic music"

    lyrics = parameters.get("lyrics")
    model = parameters.get("model", "music-2.6")
    is_instrumental = parameters.get("is_instrumental", False)
    audio_url = parameters.get("audio_url")

    if player:
        player.write_log(f"Generando música para: '{prompt}'...")

    try:
        if audio_url and model == "music-cover":
            result = quick_cover(audio_url=audio_url, prompt=prompt, model=model)
        else:
            result = quick_generate(
                prompt,
                lyrics=lyrics,
                model=model,
                is_instrumental=is_instrumental,
            )

        if result.get("success"):
            path = result.get("path", "")
            url = result.get("url", "")
            msg = f"Música generada para '{prompt}' en: {path}"
            if player and hasattr(player, "broadcast"):
                try:
                    player.broadcast({
                        "type": "action_result",
                        "action": "music_generation",
                        "status": "success",
                        "music_url": url,
                        "local_path": path,
                    })
                except Exception:
                    pass
            return msg
        else:
            return f"Error: {result.get('error', 'unknown')}"
    except Exception as e:
        return f"Fallo: {e}"


def music_lyrics_generation(parameters: dict, player=None) -> str:
    prompt = (parameters.get("prompt") or parameters.get("query", "")).strip()
    if not prompt:
        return "Error: se requiere un prompt para generar letras"

    if player:
        player.write_log(f"Generando letras para: '{prompt}'...")

    try:
        result = quick_lyrics(prompt)
        if result.get("success"):
            lyrics = result.get("lyrics", "")
            return f"Letras generadas para '{prompt}':\n\n{lyrics}"
        else:
            return f"Error: {result.get('error', 'unknown')}"
    except Exception as e:
        return f"Fallo: {e}"
