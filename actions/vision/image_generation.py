"""image_generation.py — Thin wrapper delegating to services/image_generator.py"""

from services.ai.image_generator import quick_generate


def image_generation(parameters: dict, player=None) -> str:
    prompt = (parameters.get("prompt") or parameters.get("query", "")).strip()
    if not prompt:
        prompt = "futuristic tech"

    count = parameters.get("count", 1)
    aspect_ratio = parameters.get("aspect_ratio")
    model = parameters.get("model")
    style = parameters.get("style")

    if player:
        player.write_log(f"Generando imagen para: '{prompt}'...")

    results = []
    for i in range(min(count, 4)):
        try:
            result = quick_generate(
                prompt,
                style=style,
                model=model,
                aspect_ratio=aspect_ratio,
            )

            if result.get("success"):
                path = result.get("path", "")
                url = result.get("url", "")
                msg = f"Imagen generada para '{prompt}' en: {path}"
                results.append(msg)

                if player and hasattr(player, "broadcast"):
                    try:
                        player.broadcast({
                            "type": "action_result",
                            "action": "image_generation",
                            "status": "success",
                            "image_url": url,
                            "local_path": path,
                            "seed": result.get("seed"),
                        })
                    except Exception:
                        pass
            else:
                results.append(f"Error: {result.get('error', 'unknown')}")
        except Exception as e:
            results.append(f"Fallo: {e}")

    return "\n".join(results)
