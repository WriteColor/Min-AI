# -*- coding: utf-8 -*-
"""
test_all_providers.py — Prueba todos los proveedores de IA configurados.
==========================================================================

Cada proveedor recibe el mismo prompt de prueba, su respuesta se guarda en un
log temporal separado, y luego se reproduce por TTS.

Uso:
    python test_all_providers.py

El log se guarda en: logs/test_providers_YYYYMMDD_HHMMSS/
"""

import asyncio
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
# BASE_DIR = tests/ → go up to project root
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs" / f"test_providers_{datetime.now().strftime('%Y%m%d_%H%MSS')}"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Ensure tests/ dir can import from project root
sys.path.insert(0, str(BASE_DIR))

# ── Prompt de prueba idéntico para todos ───────────────────────────────────
TEST_PROMPT = (
    "Responde ONLY with a single sentence in Spanish that introduces yourself, "
    "stating your model name, your provider name, and that you are working correctly. "
    "Example answer: 'Hola, soy GPT-4o de OpenAI y estoy funcionando correctamente.' "
    "Do NOT include any other text, brackets, or explanations. Just the sentence."
)

# ── Proveedores y modelos a probar ─────────────────────────────────────────
PROVIDERS = [
    {
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "api_key_field": "gemini_api_key",
    },
    {
        "provider": "openrouter",
        "model": "openai/gpt-4o-mini",
        "api_key_field": "openrouter_api_key",
    },
    {
        "provider": "minimax",
        "model": "MiniMax-M2.7",
        "api_key_field": "minimax_api_key",
    },
    {
        "provider": "ollama_cloud",
        "model": "nemotron-3-super:cloud",
        "api_key_field": "ollama_cloud_api_key",
    },
    {
        "provider": "nvidia_nim",
        "model": "qwen/qwen3-coder-480b-a35b-instruct",
        "api_key_field": "nvidia_nim_api_key",
    },
    {
        "provider": "compatible_local_openai",
        "model": "Qwen3_5-9B-UD-Q4_K_XL",
        "api_key_field": "compatible_local_openai_api_key",
        "base_url": "http://127.0.0.1:1337/v1",
        "use_local_provider": True,
    },
    # Groq - requiere API key (libre, obtener en console.groq.com)
    {
        "provider": "groq",
        "model": "groq/compound",
        "api_key_field": "groq_api_key",
    },
]


def load_config() -> dict:
    cfg_path = BASE_DIR / "config" / "config.json"
    if not cfg_path.exists():
        return {}
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_api_key(cfg: dict, field: str) -> str:
    return cfg.get(field, "")


def save_log(provider: str, model: str, prompt: str, response: str, error: str = None):
    """Guarda el log de una prueba."""
    log_file = LOG_DIR / f"{provider}__{model.replace('/', '_')}.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "ERROR" if error else "OK"
    content = f"""[{timestamp}] {provider.upper()} / {model} — {status}
═══════════════════════════════════════════════════════════

PROMPT ENVIADO:
{prompt}

RESPUESTA RECIBIDA:
{response}

ERROR (si existe):
{error or 'Ninguno'}

═══════════════════════════════════════════════════════════
"""
    log_file.write_text(content, encoding="utf-8")
    print(f"  |-- Log: {log_file.name}")


async def test_provider(provider_name: str, model: str, api_key: str,
                        base_url: str = None, prompt: str = TEST_PROMPT,
                        use_local: bool = False):
    """Prueba un proveedor individual."""
    print(f"\n{'='*60}")
    print(f"Probando: {provider_name} / {model}")
    print(f"{'='*60}")

    start = time.time()

    try:
        import providers  # Carga todos los providers y sus register_provider()
        from providers.base import ProviderConfig, get_provider_class

        # Obtener clase del provider desde el registry
        provider_key = "local" if use_local else provider_name
        provider_class = get_provider_class(provider_key)
        if not provider_class:
            raise RuntimeError(f"Provider '{provider_key}' no registrado en get_provider_class")

        # Construir config
        cfg = ProviderConfig(
            api_key=api_key,
            model=model,
        )
        if base_url:
            cfg.base_url = base_url

        # Instanciar provider
        prov = provider_class(cfg)

        # Conectar
        connected = await prov.connect()
        elapsed = time.time() - start

        if not connected:
            raise RuntimeError(f"No se pudo conectar a {provider_name}")

        print(f"  |-- Conectado en {elapsed:.1f}s")
        print(f"  |-- Enviando prompt...")

        # Enviar texto
        resp = await prov.send_text(prompt)
        elapsed = time.time() - start

        print(f"  |-- Respuesta recibida en {elapsed:.1f}s")
        print(f"  |-- Respuesta: {resp[:200]}{'...' if len(resp) > 200 else ''}")

        # Guardar log
        save_log(provider_name, model, prompt, resp)

        # Desconectar
        await prov.disconnect()

        return {"success": True, "response": resp, "elapsed": elapsed}

    except Exception as e:
        elapsed = time.time() - start
        error_msg = f"{type(e).__name__}: {e}"
        print(f"  |-- X ERROR: {error_msg}")
        traceback.print_exc()
        save_log(provider_name, model, prompt, "", error_msg)
        return {"success": False, "error": error_msg, "elapsed": elapsed}


def strip_think_tags(text: str) -> str:
    """
    Remove all <think>...</think> tags and their content iteratively.
    Handles nested tags by applying the regex repeatedly until no more tags are found,
    then removes orphaned word sequences between split think blocks.
    """
    # Pass 1: iteratively strip contiguous think blocks until stable
    prev = None
    result = text
    while prev != result:
        prev = result
        result = re.sub(r'<think>[\s\S]*?</think>', '', result).strip()

    # Pass 2: remove orphaned fragments left by non-nested but interleaved think blocks
    # e.g. "... <think> A...</think> text after first block <think> B...</think> ..."
    # After pass 1 these leave "text after first block" which is orphaned content
    # Pass 2: strip orphaned sentences that look like reasoning fragments after strip
    # e.g. "Interpretation: The user wants..." or "Analysis: ..."
    frag_pattern = re.sub(r'\s+', ' ', re.sub(r'\b[A-Z][a-z]{2,20}:\s*[A-Z]', 'X', result)).strip()
    if frag_pattern != result:
        result = frag_pattern

    # Pass 3: if result too short or too many colons, extract only clean complete sentences
    if len(result) < 10 or result.count(':') > 3:
        sentences = re.findall(r'[A-Z][^.!?\n]{10,300}[.!?]', result)
        if sentences:
            result = ' '.join(sentences)

    return result


def is_error_response(text: str) -> bool:
    """Check if response is an error message (not a valid model response)."""
    error_patterns = [
        "error:",
        "no se pudo",
        "connection error",
        "request timed out",
        "no tiene api key",
        "no está configurado",
        "not configured",
        "failed",
        "timed out",
    ]
    lower = text.lower()
    return any(lower.startswith(p) or p in lower for p in error_patterns)


def is_clean_response(text: str) -> bool:
    """
    Check if raw response (before think-stripping) is worth speaking.
    Reject: prompt-echo, deeply nested think content, near-empty, garbage.
    """
    if len(text) < 15:
        return False
    # Reject placeholder-echo responses
    if '[nombre del' in text or '[provider' in text.lower():
        return False

    # If think-stripping removes more than 60% of content, it is mostly think content
    clean = re.sub(r'<think>[\s\S]*?</think>', '', text).strip()
    if len(clean) < len(text) * 0.4:
        print(f"  +-- TTS: skipped (mostly think content, stripped {len(text) - len(clean)} chars)")
        return False

    # Reject if len(clean) < 60 and contains mostly prompt words only
    prompt_words = ['funcionando', 'correctamente', 'mensaje', 'prueba']
    content_words = sum(1 for w in prompt_words if w in clean.lower())
    if content_words >= 3 and len(clean) < 60:
        return False

    return True


async def speak_response(text: str, ui, response_text: str = None):
    """
    Reproduce el texto por TTS.
    - Strip <think>...</think> tags from response_text before speaking.
    - Only speak if the actual response is not an error message.
    """
    # Use actual response to decide if we should speak
    actual_response = (response_text or text).lower()

    # Don't speak error messages
    if is_error_response(actual_response):
        print(f"  +-- TTS: skipped error response")
        return

    # Use raw response (before think-stripping) to make quality decision
    raw = (response_text or text)
    if not is_clean_response(raw):
        print(f"  +-- TTS: skipped low-quality response")
        return

    # Strip thinking tags from the full text
    clean = strip_think_tags(text)

    if not clean:
        print(f"  +-- TTS: no clean text to speak")
        return

    try:
        from services.audio.tts_service import TTSService
        tts = TTSService(ui)
        tts._loop = asyncio.get_running_loop()
        tts.speak(clean)
        print(f"  +-- TTS: reproducido")
    except Exception as e:
        print(f"  +-- TTS error: {e}")


class FakeUI:
    """UI falsa para no depender de la ventana real."""
    def write_log(self, msg):
        print(f"    [LOG] {msg}")
    def broadcast(self, data):
        pass


async def main():
    print("=" * 60)
    print("MIN — PRUEBA DE TODOS LOS PROVEEDORES DE IA")
    print("=" * 60)
    print(f"Log directory: {LOG_DIR}")

    cfg = load_config()
    fake_ui = FakeUI()

    results = []
    for p in PROVIDERS:
        provider_name = p["provider"]
        model = p["model"]
        api_key = get_api_key(cfg, p["api_key_field"])
        base_url = p.get("base_url")

        # Verificar que hay API key (excepto local)
        if not api_key and provider_name not in ("compatible_local_openai", "local"):
            print(f"\n-- SKIP {provider_name}: no tiene API key configurada")
            results.append({
                "provider": provider_name,
                "model": model,
                "success": False,
                "error": "No API key configured"
            })
            continue

        result = await test_provider(
            provider_name, model, api_key, base_url,
            use_local=p.get("use_local_provider", False)
        )
        result["provider"] = provider_name
        result["model"] = model
        results.append(result)

        # TTS de la respuesta si tuvo éxito
        if result["success"]:
            await speak_response(
                f"Respuesta de {provider_name}: {result['response'][:500]}",
                fake_ui,
                response_text=result["response"]
            )

        # Pausa entre proveedores
        await asyncio.sleep(1)

    # ── Resumen ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("RESUMEN DE PRUEBAS")
    print("=" * 60)
    ok = [r for r in results if r["success"]]
    fail = [r for r in results if not r["success"]]
    print(f"Total: {len(results)} | OK: {len(ok)} | FAIL: {len(fail)}")
    for r in results:
        status = "[OK]" if r["success"] else "[FAIL]"
        elapsed = f"{r.get('elapsed', 0):.1f}s"
        err = f" - {r.get('error', '')}" if not r["success"] else ""
        print(f"  {status} {r['provider']}/{r['model']} ({elapsed}){err}")

    print(f"\nLogs guardados en: {LOG_DIR}")


if __name__ == "__main__":
    asyncio.run(main())