"""
main.py — MIN AI Assistant Core
===============================
A fresh, modular implementation of the MIN AI assistant.
Full access to all tools in actions/, config/, memory/, core/, services/, providers/.
"""

from __future__ import annotations

import asyncio
import ctypes
import json
import os
import sys
import threading
import traceback
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore", category=UserWarning, module="pywinauto")

# ── Constants ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "logs" / "min.log"
CONFIG_PATH = BASE_DIR / "config" / "config.json"

CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 256
PLAY_CHUNK_SIZE = 480

TOOL_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="min-tool")

# ── Logging Setup ────────────────────────────────────────────────────────────
def _setup_logging():
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        _log_fh = open(LOG_PATH, "w", encoding="utf-8", buffering=1)
        class _TeeStream:
            def __init__(self, *streams):
                self._streams = [s for s in streams if s is not None]
            def write(self, data):
                for s in self._streams:
                    try: s.write(data)
                    except Exception: pass
            def flush(self):
                for s in self._streams:
                    try: s.flush()
                    except Exception: pass
            @property
            def encoding(self): return "utf-8"
            def fileno(self): raise IOError("fileno")
        sys.stdout = _TeeStream(sys.stdout, _log_fh)
        sys.stderr = _TeeStream(sys.stderr, _log_fh)
    except Exception as e:
        print(f"[MIN] Logging setup failed: {e}")

_setup_logging()

# ── Subprocess Window Suppression ───────────────────────────────────────────
if sys.platform == "win32":
    try:
        CREATE_NO_WINDOW = 0x08000000
        import subprocess as _sp
        _orig_popen = _sp.Popen
        class _NoCmdPopen(_orig_popen):
            def __init__(self, *args, **kwargs):
                kwargs["creationflags"] = kwargs.get("creationflags", 0) | CREATE_NO_WINDOW
                super().__init__(*args, **kwargs)
        _sp.Popen = _NoCmdPopen
    except Exception as e:
        print(f"[MIN] Could not patch subprocess: {e}")

# ── Imports ─────────────────────────────────────────────────────────────────
from services._core.helpers import strip_markdown
from services.audio.tts_service import TTSService
from services.audio.service import AudioService
from services.ai.llm import LLMConsumer
from services.system.stability_monitor import StabilityMonitor
from services._core.phrase_triggers import fire_phrase_triggers

from core.config_manager import get_config, get_config_manager
from core.tool_schemas import TOOL_DECLARATIONS
from core.action_dispatcher import ActionDispatcher

from memory.memory_manager import load_memory, update_memory, format_memory_for_prompt

from ui import MinUI

# ── Load Custom Tools ────────────────────────────────────────────────────────
try:
    _custom_tools_path = BASE_DIR / "actions" / "custom_tools.json"
    if _custom_tools_path.exists():
        _custom_tools = json.loads(_custom_tools_path.read_text(encoding="utf-8"))
        if isinstance(_custom_tools, list):
            for _t in _custom_tools:
                if _t.get("name") not in [td["name"] for td in TOOL_DECLARATIONS]:
                    TOOL_DECLARATIONS.append(_t)
except Exception as _e:
    print(f"[MIN] Custom tools load error: {_e}")

# ── Provider Configuration ───────────────────────────────────────────────────
def _get_api_key() -> str:
    return get_config().gemini_api_key

def _get_llm_provider() -> str:
    return get_config().llm_provider

def _get_live_model() -> str:
    return get_config().live_model or "models/gemini-2.5-flash-native-audio-preview-12-2025"

def _get_min_voice() -> str:
    return get_config().min_voice or "Aoede"


class MINAssistant:
    """
    Core assistant class that orchestrates all services.
    Clean separation: Audio <-> LLM <-> Tools <-> UI
    """

    def __init__(self, ui: MinUI):
        self.ui = ui
        self.session = None
        self.is_sleeping = False
        self.running = True
        self._loop = None

        # Wake word recognizer (Vosk)
        self.vosk_recognizer = self._init_vosk()

        # Audio queues
        self.audio_in_queue = None
        self.out_queue = None
        self._turn_done_event = None
        self._stop_requested = asyncio.Event()
        self._reconnect_event = None
        self._first_connect = True

        # Services
        self.tts = TTSService(ui)
        self.audio = AudioService(
            ui,
            self.tts,
            get_llm_provider=_get_llm_provider,
            get_api_key=_get_api_key,
            get_live_model=_get_live_model,
            vosk_recognizer=self.vosk_recognizer,
            local_command_queue=asyncio.Queue()
        )
        self.audio.set_execute_tool_func(self._execute_tool)

        self._llm_command_queue = asyncio.Queue()
        self.llm = LLMConsumer(ui, self.tts, self._llm_command_queue)
        self.monitor = StabilityMonitor(ui)

        # Tool dispatcher
        self.dispatcher = ActionDispatcher(self.ui, self.tts.speak, TOOL_EXECUTOR)

        # Wire UI callbacks
        self.ui.on_text_command = self._on_text_command
        self.ui.on_stop_command = self._on_stop_pressed
        self.ui.on_config_saved = self._apply_config

        print("[MIN] Assistant initialized successfully")

    def _init_vosk(self, force=False):
        """Initialize Vosk wake-word recognizer if model exists."""
        if _get_llm_provider() == "gemini" and not force:
            print("[MIN] Gemini provider active at startup, skipping Vosk initialization")
            return None
        try:
            import os
            import vosk
            from services.audio.stt import _MODEL_CACHE
            model_path = BASE_DIR / "config" / "vosk_model"
            if model_path.exists():
                abs_path = os.path.abspath(str(model_path))
                if abs_path not in _MODEL_CACHE:
                    _MODEL_CACHE[abs_path] = vosk.Model(str(model_path))
                model = _MODEL_CACHE[abs_path]
                recognizer = vosk.KaldiRecognizer(model, 16000)
                print("[MIN] Vosk wake-word model loaded")
                return recognizer
            else:
                print("[MIN] Vosk model not found at config/vosk_model")
        except Exception as ve:
            print(f"[MIN] Vosk init failed: {ve}")
        return None

    def _apply_config(self, cfg: dict):
        """Called when user saves settings from UI."""
        print("[MIN] Config updated, reloading...")
        get_config_manager().reload()

        try:
            from actions.vision.vision_guardian import reload_state as reload_vision
            reload_vision()
        except Exception as e:
            print(f"[MIN] Vision reload error: {e}")

        if self._reconnect_event and self._loop:
            self._loop.call_soon_threadsafe(self._reconnect_event.set)

    def _on_stop_pressed(self):
        """Handle user stop action."""
        print("[MIN] Stop requested")
        self._stop_requested.set()
        self.tts.set_speaking(False)
        self.audio._drain_audio_queue()

    def _on_text_command(self, text: str):
        """Route text commands from UI to appropriate handler."""
        if not self._loop:
            return

        if getattr(self.audio, "is_sleeping", False):
            wake_keywords = ["despierta", "despiértate", "despiertate", "wake", "wake up", "min", "jarvis"]
            if any(kw in text.lower() for kw in wake_keywords):
                self.is_sleeping = False
                self.audio.is_sleeping = False
                if _get_llm_provider() == "gemini":
                    self.vosk_recognizer = None
                    self.audio.vosk_recognizer = None
                    from services.audio.stt import _MODEL_CACHE
                    _MODEL_CACHE.clear()
                    import gc
                    gc.collect()
                    print("[MIN] Vosk model unloaded and memory freed after text wake-word detection")
                self.ui.set_state("LISTENING")
                self.ui.write_log("SYS: 🟠 ¡Despierto!")
                try:
                    import winsound
                    winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
                except Exception:
                    pass
            return

        # Handle audio file input
        if text.startswith("[AUDIO_FILE]"):
            import re
            m = re.search(r'path=([^\s|]+)', text)
            if m:
                asyncio.run_coroutine_threadsafe(
                    self.audio.process_audio_file(m.group(1), _get_api_key(), _get_live_model()),
                    self._loop
                )
            return

        # Phrase triggers (rules engine)
        if fire_phrase_triggers(text, self.ui):
            return

        # Route based on provider
        provider = _get_llm_provider()
        if provider != "gemini":
            self.ui.write_log(f"Tú ({provider.upper()}): {text}")
            self._loop.call_soon_threadsafe(self._llm_command_queue.put_nowait, text)
        else:
            if not self.session:
                return
            asyncio.run_coroutine_threadsafe(
                self.session.send_client_content(
                    turns={"parts": [{"text": text}]},
                    turn_complete=True
                ),
                self._loop
            )

    async def _execute_tool(self, fc) -> dict:
        """Execute a tool call and return the response."""
        name = fc.name
        args = dict(fc.args or {})

        print(f"[MIN] [EXEC] {name}  {args}")
        self.ui.set_state("THINKING")

        # Built-in tools
        if name == "shutdown_min":
            self.ui.write_log("SYS: Apagando MIN...")
            try:
                self.ui.broadcast({"type": "ui_control", "action": "shutdown"})
                await asyncio.sleep(0.5)
            except Exception:
                pass
            self.running = False
            return {"result": "Apagando MIN. Hasta luego!"}

        if name == "sleep_mode":
            self.is_sleeping = True
            self.audio.is_sleeping = True
            if _get_llm_provider() == "gemini":
                self.vosk_recognizer = self._init_vosk(force=True)
                self.audio.vosk_recognizer = self.vosk_recognizer
            self.ui.write_log("SYS: Modo suspension activado")
            self.ui.set_state("MUTED")
            return {"result": "Entrando en suspension. Di 'MIN' para despertar."}

        if name == "save_memory":
            category = args.get("category", "notes")
            key = args.get("key", "")
            value = args.get("value", "")
            if key and value:
                update_memory({category: {key: {"value": value}}})
            self.ui.set_state("LISTENING")
            return {"result": "Memoria guardada."}

        # Dispatch to action modules
        result = await self.dispatcher.dispatch(name, args)

        # Record action in user profile
        try:
            from actions.automation.user_profile import record_action
            if record_action:
                threading.Thread(
                    target=lambda: record_action(name, args),
                    daemon=True
                ).start()
        except ImportError:
            pass

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[MIN] [DONE] {name}")
        return {"result": result}

    async def _watch_reconnect(self):
        """Wait for reconnect signal."""
        if self._reconnect_event:
            await self._reconnect_event.wait()
            raise RuntimeError("Config changed — reconnect")

    def _inject_text(self, text: str):
        """Thread-safe text injection into live session."""
        if self._loop and self.session and not self.tts.is_speaking:
            asyncio.run_coroutine_threadsafe(
                self.session.send_client_content(
                    turns={"parts": [{"text": text}]},
                    turn_complete=True
                ),
                self._loop
            )

    async def run(self):
        """Main event loop — handles reconnection and session management."""
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"}
        )

        reconnect_delay = 1.0
        consecutive_fails = 0

        while self.running:
            try:
                provider = _get_llm_provider()

                # Enforce dynamic resource routing: load Vosk/Kokoro on non-Gemini, unload completely on Gemini
                if provider == "gemini":
                    if self.vosk_recognizer is not None:
                        print("[MIN] Gemini provider active, unloading Vosk wake-word recognizer...")
                        self.vosk_recognizer = None
                        self.audio.vosk_recognizer = None
                    if hasattr(self.audio, "audio_pipeline"):
                        print("[MIN] Gemini provider active, destroying AudioPipeline local engines...")
                        delattr(self.audio, "audio_pipeline")
                    from services.audio.tts import KokoroEngine
                    KokoroEngine().unload()
                    from services.audio.stt import _MODEL_CACHE
                    _MODEL_CACHE.clear()
                    import gc
                    gc.collect()
                else:
                    if self.vosk_recognizer is None:
                        print("[MIN] Non-Gemini provider active, initializing Vosk wake-word recognizer...")
                        self.vosk_recognizer = self._init_vosk()
                        self.audio.vosk_recognizer = self.vosk_recognizer

                # ── Non-Gemini providers (OpenRouter, etc.) ──────────────
                if provider != "gemini":
                    self._loop = asyncio.get_event_loop()
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue = asyncio.Queue(maxsize=5)
                    self._turn_done_event = asyncio.Event()
                    self._reconnect_event = asyncio.Event()
                    self.session = None

                    self.audio.assign_session(
                        self.session, self._loop, self.out_queue,
                        self.audio_in_queue, self._turn_done_event,
                        self._stop_requested
                    )

                    self.ui.set_state("LISTENING")
                    self.ui.write_log(f"SYS: MIN en linea (Modo {provider.upper()})")

                    async with asyncio.TaskGroup() as tg:
                        tg.create_task(self.audio.listen_audio())
                        tg.create_task(self.audio.play_audio())
                        tg.create_task(self._watch_reconnect())
                        tg.create_task(self.monitor.run())
                        tg.create_task(self.llm.run(provider))
                        await self._reconnect_event.wait()
                    continue

                # ── Gemini Live Session ──────────────────────────────────
                print("[MIN] Connecting to Gemini...")
                self.ui.set_state("THINKING")

                from services.session.session_builder import SessionBuilder
                config = SessionBuilder.build_config()

                async with (
                    client.aio.live.connect(
                        model=_get_live_model(),
                        config=config
                    ) as session,
                    asyncio.TaskGroup() as tg
                ):
                    self.session = session
                    self._loop = asyncio.get_event_loop()
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue = asyncio.Queue(maxsize=5)
                    self._turn_done_event = asyncio.Event()
                    self._reconnect_event = asyncio.Event()

                    self.audio.assign_session(
                        session, self._loop, self.out_queue,
                        self.audio_in_queue, self._turn_done_event,
                        self._stop_requested
                    )

                    print("[MIN] Connected!")
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("SYS: MIN en linea.")
                    reconnect_delay = 1.0
                    consecutive_fails = 0

                    # First-time setup
                    if self._first_connect:
                        self._first_connect = False
                        self._start_vision_guardian()
                        self._auto_morning_brief()

                    # Start all audio/session tasks
                    tg.create_task(self.audio.send_realtime())
                    tg.create_task(self.audio.listen_audio())
                    tg.create_task(self.audio.receive_audio())
                    tg.create_task(self.audio.play_audio())
                    tg.create_task(self._watch_reconnect())
                    tg.create_task(self.monitor.run())

            except Exception as e:
                self._handle_connection_error(e, consecutive_fails)
                consecutive_fails += 1

            # Exponential backoff for reconnection
            self.tts.set_speaking(False)
            self.ui.set_state("THINKING")

            if consecutive_fails > 1:
                max_delay = 90.0 if consecutive_fails >= 5 else 12.0
                reconnect_delay = min(reconnect_delay * 2, max_delay)
            elif consecutive_fails == 0:
                reconnect_delay = 1.0

            jitter = (reconnect_delay * 0.25) if consecutive_fails > 0 else 0
            total_delay = reconnect_delay + jitter
            print(f"[MIN] Reconnecting in {total_delay:.1f}s...")
            await asyncio.sleep(total_delay)

    def _handle_connection_error(self, e, consecutive_fails):
        """Handle various connection errors with appropriate responses."""
        import random

        exceptions = e.exceptions if isinstance(e, ExceptionGroup) else [e]

        is_handshake_timeout = False
        is_config_reconnect = False

        for exc in exceptions:
            msg = str(exc)

            if "Config changed" in msg:
                is_config_reconnect = True
            elif "timed out during opening handshake" in msg or (
                isinstance(exc, TimeoutError) and "handshake" in msg
            ):
                is_handshake_timeout = True
                print(f"[MIN] Timeout: retrying in 1s...")
            elif "1011" in msg or "Internal error" in msg:
                print(f"[MIN] API 1011 error: {msg[:100]}")
                if consecutive_fails >= 4:
                    self.ui.write_log(
                        "SYS: Error 1011 repetido. Esperando para no saturar la API..."
                    )
            elif "1008" in msg or "policy violation" in msg.lower():
                print(f"[MIN] Policy violation: {msg[:120]}")
            elif "1000" in msg or "going away" in msg.lower():
                print(f"[MIN] Session expired")
            else:
                print(f"[MIN] Error: {exc}")
                traceback.print_exc()

        if is_config_reconnect:
            self.tts.set_speaking(False)
            self.ui.set_state("THINKING")

        if is_handshake_timeout:
            self.tts.set_speaking(False)
            self.ui.set_state("THINKING")

    def _start_vision_guardian(self):
        """Start the vision guardian for proactive screen monitoring."""
        try:
            from actions.vision.vision_guardian import start as start_vision
            start_vision(
                inject_fn=self._inject_text,
                speaking_fn=lambda: self.tts.is_speaking,
            )
        except Exception as e:
            print(f"[MIN] VisionGuardian init error: {e}")

    def _auto_morning_brief(self):
        """Auto-generate morning brief if configured and not already done today."""
        hour = datetime.now().hour
        if not (6 <= hour < 12):
            return

        try:
            from actions.automation.morning_brief import already_briefed_today
            if already_briefed_today():
                return
        except Exception:
            return

        async def _do_brief():
            await asyncio.sleep(1)
            if self.session:
                await self.session.send_client_content(
                    turns={"parts": [{"text": "[AUTO] Dame el informe matutino del dia."}]},
                    turn_complete=True
                )

        asyncio.create_task(_do_brief())


def main():
    """Application entry point with single-instance lock and hotkey setup."""

    # ── Single Instance Lock ──────────────────────────────────────────────
    _single_instance_mutex = ctypes.windll.kernel32.CreateMutexW(
        None, False, "MIN_AI_SINGLE_INSTANCE_MUTEX"
    )
    if ctypes.windll.kernel32.GetLastError() == 183:
        print("[MIN] Ya hay una instancia en ejecucion. Cerrando.")
        sys.exit(0)

    # ── API Key Check ─────────────────────────────────────────────────────
    def _check_api_keys():
        cfg = get_config()
        gemini = cfg.gemini_api_key.strip()
        openrouter = cfg.openrouter_api_key.strip()

        if gemini and openrouter:
            print("[MIN] API keys detectadas correctamente.")
            return

        missing = []
        if not gemini:
            missing.append("Gemini API Key")
        if not openrouter:
            missing.append("OpenRouter API Key")

        print(f"[MIN] Faltan las siguientes API keys: {', '.join(missing)}")
        print("[MIN] Configuralas desde el panel de Configuracion.")

    _check_api_keys()

    # ── UI Initialization ─────────────────────────────────────────────────
    ui = MinUI("face.png")

    # ── Global Hotkey (INSERT key) ────────────────────────────────────────
    def _setup_global_hotkey():
        def on_hotkey_triggered():
            if ui.muted:
                ui.muted = False
                ui.set_state("LISTENING")
                ui.write_log("SYS: Microfono ACTIVADO via atajo INS.")
            else:
                ui.set_state("LISTENING")
                ui.write_log("SYS: MIN en foco via atajo INS.")

        def hotkey_thread():
            user32 = ctypes.windll.user32
            try:
                if not user32.RegisterHotKey(None, 99, 0x0000, 0x2D):
                    print("[HOTKEY] Error registering Insert hotkey.")
                    return
            except Exception as e:
                print(f"[HOTKEY] Exception: {e}")
                return

            try:
                msg = ctypes.wintypes.MSG()
                while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                    if msg.message == 0x0312:
                        if msg.wParam == 99:
                            threading.Thread(target=on_hotkey_triggered, daemon=True).start()
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
            finally:
                user32.UnregisterHotKey(None, 99)

        threading.Thread(target=hotkey_thread, daemon=True).start()
        print("[MIN] Global INSERT hotkey registered.")

    _setup_global_hotkey()

    # ── Start Assistant ───────────────────────────────────────────────────
    def runner():
        ui.wait_for_api_key()
        assistant = MINAssistant(ui)
        try:
            asyncio.run(assistant.run())
        except KeyboardInterrupt:
            print("\n[MIN] Apagando...")

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()


if __name__ == "__main__":
    main()
