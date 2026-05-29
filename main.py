import os
import json
import sys
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pywinauto")
from pathlib import Path

# Load config early to determine GPU acceleration settings
_gpu_enabled = False
try:
    if getattr(sys, "frozen", False):
        _base_dir = Path(sys.executable).parent
    else:
        _base_dir = Path(__file__).resolve().parent
    _cfg_path = _base_dir / "config" / "config.json"
    if _cfg_path.exists():
        _cfg = json.loads(_cfg_path.read_text(encoding="utf-8"))
        _gpu_enabled = _cfg.get("gpu_acceleration", False)
except Exception:
    pass

if _gpu_enabled:
    # GPU / High Performance Mode
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
        "--ignore-gpu-blocklist "
        "--enable-gpu-rasterization "
        "--enable-zero-copy "
        "--num-raster-threads=4 "
        "--js-flags=--max-old-space-size=1024"
    )
    os.environ["QSG_RHI_BACKEND"] = "d3d11"
    os.environ["QSG_INFO"] = "1"
    print("[MIN] GPU Acceleration is ENABLED. Offloading RAM rendering workload to GPU.")
else:
    # Balanced low-RAM mode
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
        "--enable-low-end-device-mode "
        "--renderer-process-limit=1 "
        "--js-flags=--max-old-space-size=64 "
        "--disable-gpu-shader-disk-cache "
        "--disable-dev-shm-usage "
        "--disable-extensions "
        "--disable-sync "
        "--mute-audio"
    )
    print("[MIN] Using Balanced Low RAM GPU-Composited mode for beautiful fluid rendering.")

import asyncio
from concurrent.futures import ThreadPoolExecutor
import re
import threading
import traceback

# ── Dedicated thread pool for tool execution — prevents starvation ────────────
_TOOL_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="min-tool")

try:
    from zoneinfo import ZoneInfo as _ZoneInfo
    _BA_TZ = _ZoneInfo("America/Tegucigalpa")  # Default timezone
except Exception:
    from datetime import timezone as _tz, timedelta as _td
    _BA_TZ = _tz(_td(hours=-5))


def _load_tz():
    """Load timezone from config.json config."""
    global _BA_TZ
    from core.config_manager import get_config
    try:
        tz_name = get_config().timezone
        if not tz_name:
            from datetime import datetime as _dt
            _BA_TZ = _dt.now().astimezone().tzinfo
            print(f"[TZ] Using system timezone: {_BA_TZ}")
            return
        try:
            _BA_TZ = _ZoneInfo(tz_name)
            print(f"[TZ] Timezone loaded: {tz_name}")
        except Exception as e:
            print(f"[TZ] Failed to load '{tz_name}': {e}")
            import zoneinfo as _zi
            available = _zi.available_timezones()
            tz_lower = tz_name.lower()
            for known in available:
                if known.lower() == tz_lower:
                    _BA_TZ = _ZoneInfo(known)
                    print(f"[TZ] Matched '{tz_name}' → '{known}'")
                    break
            else:
                parts = tz_name.replace("\\", "/").split("/")
                short = parts[-1].lower() if parts else ""
                for known in available:
                    if known.lower().endswith("/" + short):
                        _BA_TZ = _ZoneInfo(known)
                        print(f"[TZ] Partial match '{tz_name}' → '{known}'")
                        break
                else:
                    from datetime import datetime as _dt
                    _BA_TZ = _dt.now().astimezone().tzinfo
                    print(f"[TZ] Falling back to system timezone: {_BA_TZ}")
    except Exception as e:
        print(f"[TZ] Error reading config: {e}")

import numpy as np
import sounddevice as sd
from google import genai
from google.genai import types
from ui import MinUI

from memory.memory_manager import load_memory, update_memory, format_memory_for_prompt
from core.tool_schemas import TOOL_DECLARATIONS


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "config.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"
LOG_PATH        = BASE_DIR / "Min.log"

# ── Redirect output to log file ──────────────────────────────────────────────
try:
    import io as _io
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
        def fileno(self): raise _io.UnsupportedOperation("fileno")

    sys.stdout = _TeeStream(sys.stdout, _log_fh)
    sys.stderr = _TeeStream(sys.stderr, _log_fh)
except Exception:
    pass

# ── Suppress console windows from all child subprocesses ─────────────────────
if sys.platform == "win32":
    try:
        import ctypes as _ctypes
        if _ctypes.windll.kernel32.GetConsoleWindow() == 0:
            import subprocess as _sp
            _CREATE_NO_WINDOW = 0x08000000
            _orig_Popen = _sp.Popen
            class _NoCmdPopen(_orig_Popen):
                def __init__(self, *args, **kwargs):
                    kwargs["creationflags"] = kwargs.get("creationflags", 0) | _CREATE_NO_WINDOW
                    super().__init__(*args, **kwargs)
            _sp.Popen = _NoCmdPopen
            print("[MIN] subprocess.Popen patched: CREATE_NO_WINDOW active")
    except Exception as _e:
        print(f"[MIN] Could not patch subprocess: {_e}")

LIVE_MODEL          = "models/gemini-2.5-flash-native-audio-preview-12-2025"
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 256
PLAY_CHUNK_SIZE     = 480


def _get_api_key() -> str:
    from core.config_manager import get_config
    return get_config().gemini_api_key


def _get_live_model() -> str:
    from core.config_manager import get_config
    return get_config().live_model or LIVE_MODEL


def _get_llm_provider() -> str:
    from core.config_manager import get_config
    return get_config().llm_provider


def _get_min_voice() -> str:
    from core.config_manager import get_config
    return get_config().min_voice or "Aoede"


def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are MIN, Tony Stark's AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )

_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

def _clean_transcript(text: str) -> str:    
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    return text.strip()

def strip_markdown(text: str) -> str:
    """Removes standard markdown characters so that TTS doesn't read them aloud."""
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"#+\s+", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.strip()


# Load custom tools created by tool_creator
try:
    _custom_tools_path = BASE_DIR / "actions" / "custom_tools.json"
    if _custom_tools_path.exists():
        _custom_tools = json.loads(_custom_tools_path.read_text(encoding="utf-8"))
        if isinstance(_custom_tools, list):
            for _t in _custom_tools:
                if _t.get("name") not in [td["name"] for td in TOOL_DECLARATIONS]:
                    TOOL_DECLARATIONS.append(_t)
except Exception as _e:
    pass


class MinLive:
    def __init__(self, ui: MinUI):
        self.ui             = ui
        self.session        = None
        self.is_sleeping    = False
        self.vosk_recognizer = None
        try:
            import vosk
            if os.path.exists("config/vosk_model"):
                model = vosk.Model("config/vosk_model")
                self.vosk_recognizer = vosk.KaldiRecognizer(model, 16000)
                print("[MIN] Vosk model loaded successfully for wake-word.")
            else:
                print("[MIN] ⚠️ Vosk model not found at config/vosk_model. Wake-word disabled.")
        except Exception as ve:
            print(f"[MIN] Vosk initialization failed: {ve}")

        self.audio_in_queue = None
        self.out_queue      = None
        self.running        = True
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self._last_speak_time = 0.0
        self._stop_requested = asyncio.Event()

        self.ui.on_text_command = self._on_text_command
        self.ui.on_stop_command = self._on_stop_pressed
        self.ui.on_config_saved = self._apply_config
        self._turn_done_event: asyncio.Event | None = None
        self._api_1011_tool: str | None = None
        self._reconnect_event: asyncio.Event | None = None
        self._first_connect = True

        from core.action_dispatcher import ActionDispatcher
        self.dispatcher = ActionDispatcher(self.ui, self.speak, _TOOL_EXECUTOR)

    def _inject_text(self, text: str):
        """Thread-safe injection of a text message into the current live session."""
        if self._loop and self.session and not self._is_speaking:
            asyncio.run_coroutine_threadsafe(
                self.session.send_client_content(
                    turns={"parts": [{"text": text}]},
                    turn_complete=True
                ),
                self._loop
            )

    def _apply_config(self, cfg: dict):
        """Called from UI thread when user saves settings. Triggers session reconnect."""
        from core.config_manager import get_config_manager
        print("[MIN] ⚙️ Config actualizada — reconectando sesión...")
        self.ui.write_log("SYS: Aplicando nueva configuración...")
        
        get_config_manager().reload()

        # Reload vision guardian settings dynamically if it's active
        try:
            from actions.vision.vision_guardian import reload_state as reload_vision_guardian_state
            reload_vision_guardian_state()
        except Exception as e:
            print(f"[MIN] Error al recargar Vision Guardian: {e}")

        if self._reconnect_event and self._loop:
            self._loop.call_soon_threadsafe(self._reconnect_event.set)

    async def _watch_reconnect(self):
        """Task that triggers a graceful reconnect when config changes."""
        if self._reconnect_event:
            await self._reconnect_event.wait()
            raise RuntimeError("Config changed — reconnect requested")

    async def _stability_monitor(self):
        """Monitorea periódicamente el consumo de RAM y ejecuta GC. Si supera el umbral, reinicia."""
        import gc
        import psutil
        import os
        import sys
        import subprocess
        from core.config_manager import get_config

        while True:
            await asyncio.sleep(300)  # Cada 5 minutos
            gc.collect()
            try:
                cfg = get_config()
                max_mem = float(cfg.max_memory_mb or 500.0)

                proc = psutil.Process(os.getpid())
                mem_mb = proc.memory_info().rss / 1024 / 1024
                if mem_mb > max_mem:
                    print(f"[MIN] ⚠️ Uso de memoria ({mem_mb:.1f} MB) excedió el límite ({max_mem:.1f} MB). Reiniciando preventivamente...")
                    self.ui.write_log(f"SYS: Uso de memoria elevado ({mem_mb:.1f} MB). Reiniciando preventivamente...")
                    
                    main_py = str(Path(__file__).parent / "main.py")
                    subprocess.Popen([sys.executable, main_py], creationflags=0x00000008)
                    os._exit(0)
            except Exception as e:
                print(f"[MIN] Error en monitor de estabilidad: {e}")

    async def _speak_local(self, text: str):
        """TTS local robusto utilizando edge-tts. Previene hoarseness o cortes."""
        import edge_tts
        import tempfile
        from core.config_manager import get_config

        self.set_speaking(True)
        try:
            temp_path = os.path.join(tempfile.gettempdir(), f"min_local_tts_{os.getpid()}.mp3")
            
            clean_text = strip_markdown(text)
            
            cfg = get_config()
            rate = f"+{int((cfg.speech_rate or 1.0) * 15)}%" if cfg.speech_rate >= 1.0 else f"-{int((1.0 - cfg.speech_rate) * 15)}%"
            
            voices = {
                "Aoede": "es-US-PalomaNeural",
                "Kore": "es-MX-DaliaNeural",
                "Leda": "es-ES-ElviraNeural",
                "Zephyr": "es-US-AlonsoNeural",
                "Charon": "es-MX-JorgeNeural",
                "Puck": "es-ES-AlvaroNeural",
                "Fenrir": "es-AR-TomasNeural",
                "Orus": "es-CL-LorenzoNeural"
            }
            voice_code = voices.get(cfg.min_voice, "es-US-PalomaNeural")
            
            communicate = edge_tts.Communicate(clean_text, voice_code, rate=rate)
            await communicate.save(temp_path)
            
            def _play_and_wait():
                try:
                    import soundfile as sf
                    data, fs = sf.read(temp_path)
                    
                    rms_multiplier = 25
                    block_size = PLAY_CHUNK_SIZE
                    
                    with sd.OutputStream(
                        samplerate=fs,
                        channels=len(data.shape) if len(data.shape) > 1 else 1,
                        dtype="float32",
                        blocksize=block_size
                    ) as stream:
                        
                        idx = 0
                        while idx < len(data) and self._is_speaking and not self._stop_requested.is_set():
                            chunk = data[idx : idx + block_size]
                            
                            # Calular RMS para el orbe de la UI
                            try:
                                rms = float(np.sqrt(np.mean(chunk ** 2)))
                                self.ui.set_audio_level(min(1.0, rms * rms_multiplier))
                            except Exception:
                                pass
                                
                            stream.write(chunk.astype(np.float32))
                            idx += block_size
                except Exception as pe:
                    print(f"[MIN] local play error: {pe}")
                finally:
                    try:
                        os.remove(temp_path)
                    except:
                        pass
                        
            await asyncio.to_thread(_play_and_wait)
        except Exception as e:
            print(f"[MIN] TTS local error: {e}")
            
        self.set_speaking(False)

    async def _generic_llm_consumer(self, provider_name: str):
        """Consume comandos typed/transcribed locally, query LLM provider and speak output."""
        from core.config_manager import get_config
        from providers.base import get_provider_class, ProviderConfig
        import providers
        import json
        import traceback

        while True:
            text = await self._local_command_queue.get()
            if not text:
                continue

            self.ui.set_state("THINKING")
            cfg = get_config()

            # 1. Resolve prompt context using new database memory if available, fallback to memory manager
            mem_str = ""
            try:
                from memory.service import MemoryService
                memory_service = MemoryService()
                facts = memory_service.search_memory(text, top_k=5)
                if facts:
                    mem_str = "[LONG-TERM MEMORY & USER CONTEXT]\n"
                    for val, score in facts:
                        mem_str += f"- {val}\n"
                
                recent = memory_service.get_recent_context(max_interactions=5)
                if recent:
                    mem_str += f"\n[RECENT SESSION]\n{recent}\n"
            except Exception as me:
                print(f"[MIN] Failed to load memory service: {me}")
                try:
                    memory = load_memory()
                    mem_str = format_memory_for_prompt(memory)
                except Exception:
                    mem_str = ""

            sys_prompt = _load_system_prompt()
            
            # Mix time context
            from datetime import datetime
            _load_tz()
            now = datetime.now(_BA_TZ)
            time_str = now.strftime("%A, %d %B %Y — %I:%M:%S %p")
            tz_name = str(_BA_TZ)
            time_ctx = (
                f"[CURRENT DATE & TIME]\n"
                f"Right now it is: {time_str}\n"
                f"Timezone: {tz_name}\n\n"
            )
            
            full_prompt = f"{time_ctx}{mem_str}\n{sys_prompt}\n\nUser request: {text}"
            
            self.ui.clear_min_response()
            self.ui.stream_min_chunk("Pensando...")

            # 2. Execute LLM call using the provider registry
            provider_class = get_provider_class(provider_name)
            
            # Fallback for local_openai/local
            if not provider_class:
                if provider_name == "local_openai":
                    provider_class = get_provider_class("local")

            if not provider_class:
                self.ui.clear_min_response()
                self.ui.stream_min_chunk(f"Error: El proveedor '{provider_name}' no está registrado.")
                self.ui.set_state("LISTENING")
                continue
                
            # Build ProviderConfig
            api_key = ""
            base_url = None
            model = ""
            
            if provider_name == "local_openai":
                api_key = cfg.local_openai_api_key or "not-needed"
                base_url = cfg.local_openai_base_url
                model = cfg.local_openai_model or "mistral-7b-instruct"
            elif provider_name == "gemini":
                api_key = cfg.gemini_api_key
                model = cfg.active_model or "gemini-2.5-flash"
            elif provider_name == "openai":
                api_key = cfg.openai_api_key
                model = cfg.active_model or "gpt-4o"
            elif provider_name == "groq":
                api_key = cfg.groq_api_key if hasattr(cfg, "groq_api_key") else ""
                model = cfg.active_model or "llama-3.1-8b-instant"
            elif provider_name == "openrouter":
                api_key = cfg.openrouter_api_key
                model = cfg.openrouter_default_model or "google/gemini-2.5-flash"
            elif provider_name == "opencode":
                api_key = cfg.openrouter_api_key
                model = "meta-llama/llama-3.1-405b-instruct"
            
            prov_cfg = ProviderConfig(
                api_key=api_key,
                base_url=base_url,
                model=model,
                temperature=0.2,
                max_tokens=2048
            )
            
            try:
                # Instantiate and connect
                provider_inst = provider_class(prov_cfg)
                connected = await provider_inst.connect()
                if not connected:
                    raise RuntimeError("No se pudo conectar al proveedor.")
                
                self.ui.clear_min_response()
                
                full_resp = ""
                async for chunk in provider_inst.stream_text(full_prompt):
                    if chunk:
                        full_resp += chunk
                        self.ui.stream_min_chunk(chunk)
                
                # Log episodic interaction in database if available
                try:
                    from memory.service import MemoryService
                    MemoryService().log_user_message(text)
                    MemoryService().log_min_response(full_resp)
                except Exception:
                    pass
                
                # Speak response
                await self._speak_local(full_resp)
                
            except Exception as e:
                self.ui.clear_min_response()
                self.ui.stream_min_chunk(f"Error al conectar con {provider_name}: {e}")
                print(f"[MIN] Generic LLM error for {provider_name}: {e}")
                traceback.print_exc()
                
            self.ui.set_state("LISTENING")

    def _on_text_command(self, text: str):
        if not self._loop:
            return

        if text.startswith("[AUDIO_FILE]"):
            m = re.search(r'path=([^\s|]+)', text)
            if m:
                asyncio.run_coroutine_threadsafe(
                    self._process_audio_file(m.group(1)), self._loop
                )
            return

        if self._fire_phrase_triggers(text):
            return

        provider = _get_llm_provider()
        if provider != "gemini":
            self.ui.write_log(f"Tú ({provider.upper()}): {text}")
            self._loop.call_soon_threadsafe(self._local_command_queue.put_nowait, text)
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

    async def _process_audio_file(self, path: str):
        """Transcribe and analyze an audio file via Gemini (separate from realtime session)."""
        try:
            p = Path(path)
            if not p.exists():
                self.ui.write_log(f"❌ Archivo no encontrado: {path}")
                return

            self.ui.set_state("THINKING")
            client = genai.Client(api_key=_get_api_key())
            
            loop = asyncio.get_event_loop()
            
            def _analyze():
                audio_file = client.files.upload(file=p)
                prompt = (
                    "Transcribe este archivo de audio con total precisión. "
                    "Luego, analiza su contenido y proporciona una respuesta coherente."
                )
                response = client.models.generate_content(
                    model=_get_live_model(),
                    contents=[audio_file, prompt]
                )
                return response.text
                
            resp_text = await loop.run_in_executor(None, _analyze)
            self.ui.write_log(f"🔈 Análisis de archivo de audio completado.")
            self.ui.clear_min_response()
            self.ui.stream_min_chunk(resp_text)
            
            await self._speak_local(resp_text)
        except Exception as e:
            self.ui.write_log(f"❌ Error procesando audio: {e}")
            traceback.print_exc()
            
        self.ui.set_state("LISTENING")

    def _fire_phrase_triggers(self, user_text: str) -> bool:
        """
        Check phrase-based automations. Returns True if any trigger fired
        (caller should skip sending the text to Gemini in that case).
        """
        text_lower = user_text.lower()

        # ── Accessibility quick triggers ──────────────────────────────────────
        if any(p in text_lower for p in ["activar seguimiento ocular", "iniciar eye tracking",
                                          "activar control ocular", "encender seguimiento de ojos"]):
            try:
                from actions.system.accessibility import eye_tracking
                result = eye_tracking({"action": "start"})
                self.ui.write_log("⚡ " + result)
            except Exception as e:
                self.ui.write_log(f"[Phrase] Module not available: {e}")
            return True

        if any(p in text_lower for p in ["detener seguimiento ocular", "apagar eye tracking",
                                          "desactivar control ocular"]):
            try:
                from actions.system.accessibility import eye_tracking
                result = eye_tracking({"action": "stop"})
                self.ui.write_log("⚡ " + result)
            except Exception as e:
                self.ui.write_log(f"[Phrase] Module not available: {e}")
            return True

        if any(p in text_lower for p in ["activar detector de movimientos", "iniciar movimiento",
                                          "activar micromovimientos", "encender control por cabeza"]):
            try:
                from actions.system.accessibility import micro_movement
                result = micro_movement({"action": "start"})
                self.ui.write_log("⚡ " + result)
            except Exception as e:
                self.ui.write_log(f"[Phrase] Module not available: {e}")
            return True

        if any(p in text_lower for p in ["detener detector de movimientos", "apagar micromovimientos"]):
            try:
                from actions.system.accessibility import micro_movement
                result = micro_movement({"action": "stop"})
                self.ui.write_log("⚡ " + result)
            except Exception as e:
                self.ui.write_log(f"[Phrase] Module not available: {e}")
            return True

        if any(p in text_lower for p in ["simplifica", "simplificar", "dividir en pasos"]):
            for phrase in ["simplifica ", "simplificar ", "dividir en pasos "]:
                if phrase in text_lower:
                    task_text = user_text[len(phrase):].strip()
                    if task_text:
                        try:
                            from actions.system.accessibility import task_simplify
                            result = task_simplify(task_text)
                            self.ui.write_log("⚡ [Simplificado]\n" + result[:300])
                        except Exception as e:
                            self.ui.write_log(f"[Phrase] Module not available: {e}")
                        return True

        if "agregar rutina" in text_lower or "nueva rutina" in text_lower:
            for phrase in ["agregar rutina ", "nueva rutina "]:
                if phrase in text_lower:
                    routine_name = user_text[len(phrase):].strip()
                    if routine_name:
                        try:
                            from actions.system.accessibility import routine_gamify
                            result = routine_gamify({"action": "add", "name": routine_name})
                            self.ui.write_log("⚡ " + result)
                        except Exception as e:
                            self.ui.write_log(f"[Phrase] Module not available: {e}")
                        return True

        if "completar rutina" in text_lower or "terminar rutina" in text_lower:
            for phrase in ["completar rutina ", "terminar rutina "]:
                if phrase in text_lower:
                    routine_name = user_text[len(phrase):].strip()
                    if routine_name:
                        try:
                            from actions.system.accessibility import routine_gamify
                            result = routine_gamify({"action": "complete", "name": routine_name})
                            self.ui.write_log("⚡ " + result)
                        except Exception as e:
                            self.ui.write_log(f"[Phrase] Module not available: {e}")
                        return True

        if "mis rutinas" in text_lower or "ver rutinas" in text_lower or "listar rutinas" in text_lower:
            try:
                from actions.system.accessibility import routine_gamify
                result = routine_gamify({"action": "list"})
                self.ui.write_log("⚡ [Rutinas]\n" + result)
            except Exception as e:
                self.ui.write_log(f"[Phrase] Module not available: {e}")
            return True

        # ── User-defined phrase automations ───────────────────────────────────
        try:
            from actions.automation.rules_engine import check_phrase_triggers, _run_action as _rules_run_action
            triggered = check_phrase_triggers(user_text)
            if triggered:
                for rule in triggered:
                    action = rule.get("action", {})
                    name   = rule.get("name", "?")
                    self.ui.write_log(f"⚡ Automatización: {name}")
                    threading.Thread(
                        target=_rules_run_action, args=(action,), daemon=True
                    ).start()
                return True
        except Exception as e:
            print(f"[MIN] phrase trigger error: {e}")

        return False

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
            if not value:
                self._stop_requested.clear()

    def speak(self, text: str):
        """Dynamic text speaking function exposed to tools."""
        if not text:
            return
        print(f"[MIN] speak command: {text}")
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._speak_local(text), self._loop)

    def speak_error(self, tool_name: str, error: str):
        msg = f"Señor, ocurrió un error en la herramienta {tool_name}."
        self.speak(msg)

    def _on_stop_pressed(self):
        """Called when UI stop action is triggered by the user."""
        print("[MIN] 🛑 Stop requested by user.")
        self._stop_requested.set()
        self.set_speaking(False)
        self._drain_audio_queue()

    def _drain_audio_queue(self):
        if self.audio_in_queue:
            while not self.audio_in_queue.empty():
                try:
                    self.audio_in_queue.get_nowait()
                except Exception:
                    pass

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime

        memory     = load_memory()
        mem_str    = format_memory_for_prompt(memory)
        sys_prompt = _load_system_prompt()

        _load_tz()
        now      = datetime.now(_BA_TZ)
        time_str = now.strftime("%A, %d %B %Y — %I:%M:%S %p")
        utc_off  = now.strftime("%z")
        tz_name  = str(_BA_TZ)
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Timezone: {tz_name} (UTC{utc_off})\n"
            f"The current Unix timestamp is: {int(now.timestamp())}\n"
            f"Use this information to calculate exact times for reminders, scheduling, and answering time-related questions.\n\n"
        )

        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str)
        parts.append(sys_prompt)

        _voice_name = _get_min_voice()
        _speech_cfg = None
        try:
            _speech_cfg = types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=_voice_name
                    )
                )
            )
        except Exception:
            _speech_cfg = None

        cfg_kwargs: dict = dict(
            response_modalities=["AUDIO"],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
        )
        if _speech_cfg:
            cfg_kwargs["speech_config"] = _speech_cfg

        try:
            cfg_kwargs["output_audio_config"] = types.OutputAudioConfig(
                audio_encoding="LINEAR16",
                speaking_rate=1.15,
            )
        except Exception:
            pass

        try:
            cfg_kwargs["temperature"] = 0.2
        except Exception:
            pass

        _vad_applied = False
        try:
            cfg_kwargs["realtime_input_config"] = types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    start_of_speech_sensitivity="START_SENSITIVITY_HIGH",
                    end_of_speech_sensitivity="END_SENSITIVITY_HIGH",
                    prefix_padding_ms=60,
                    silence_duration_ms=350,
                )
            )
            _vad_applied = True
            print("[MIN] VAD config aplicado (typed)")
        except Exception:
            pass

        if not _vad_applied:
            try:
                cfg_kwargs["realtime_input_config"] = {
                    "automatic_activity_detection": {
                        "start_of_speech_sensitivity": "START_SENSITIVITY_HIGH",
                        "end_of_speech_sensitivity": "END_SENSITIVITY_HIGH",
                        "prefix_padding_ms": 100,
                        "silence_duration_ms": 500,
                    }
                }
                print("[MIN] VAD config aplicado (dict)")
            except Exception:
                print("[MIN] VAD config no aplicado")

        try:
            cfg_kwargs["context_window_compression"] = types.ContextWindowCompressionConfig(
                trigger_tokens=12000,
                sliding_window=types.SlidingWindow(target_tokens=6000),
            )
        except Exception:
            pass

        try:
            cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        except Exception:
            pass

        return types.LiveConnectConfig(**cfg_kwargs)

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        print(f"[MIN] 🔧 {name}  {args}")
        self.ui.set_state("THINKING")

        if name == "shutdown_min":
            self.ui.write_log("SYS: Apagando MIN...")
            try:
                self.ui.broadcast({"type": "ui_control", "action": "shutdown"})
                await asyncio.sleep(0.5)
            except Exception:
                pass
            self.running = False
            print("[MIN] Shutdown signal sent.")
            sys.exit(0)
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "Apagando MIN. ¡Hasta luego, señor!"}
            )

        if name == "save_memory":
            category = args.get("category", "notes")
            key      = args.get("key", "")
            value    = args.get("value", "")
            if key and value:
                update_memory({category: {key: {"value": value}}})
                print(f"[Memory] 💾 save_memory: {category}/{key} = {value}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "Memory saved."}
            )

        if name == "sleep_mode":
            self.is_sleeping = True
            self.ui.write_log("SYS: 💤 Entrando en suspensión local.")
            self.ui.set_state("MUTED")
            result = "Entrando en suspensión absoluta. Cortando transmisión a la nube hasta escuchar 'MIN'."

        elif name == "agent_task":
            try:
                from agent.task_queue import get_queue, TaskPriority
                priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
                priority = priority_map.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)
                task_id  = get_queue().submit(goal=args.get("goal", ""), priority=priority, speak=self.speak)
                result   = f"Task started (ID: {task_id})."
            except Exception as e:
                result = f"Error starting task: {e}"
        else:
            # Delegate tool execution entirely to ActionDispatcher
            result = await self.dispatcher.dispatch(name, args)

        # Record action for habit learning
        try:
            from actions.automation.user_profile import record_action
            if record_action:
                threading.Thread(target=lambda: record_action(name, args), daemon=True).start()
        except ImportError:
            pass

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[MIN] 📤 {name} → {str(result)[:80]}")
        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(media=msg)

    async def _listen_audio(self):
        print("[MIN] 🎤 Mic iniciado")
        loop = asyncio.get_event_loop()

        def callback(indata, frames, time_info, status):
            import time
            now = time.time()
            with self._speaking_lock:
                min_speaking = self._is_speaking
                if min_speaking:
                    self._last_speak_time = now

            provider = _get_llm_provider()

            if getattr(self, "is_sleeping", False):
                if getattr(self, "vosk_recognizer", None):
                    audio_data = indata.tobytes()
                    if self.vosk_recognizer.AcceptWaveform(audio_data):
                        res = json.loads(self.vosk_recognizer.Result())
                        text = res.get("text", "")
                        if "min" in text.lower():
                            self.is_sleeping = False
                            self.ui.set_state("LISTENING")
                            self.ui.write_log("SYS: 🟢 ¡Despierto!")
                            try:
                                import winsound
                                winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
                            except: pass
                return

            is_cooling_down = (now - getattr(self, "_last_speak_time", 0.0)) < 0.8
            if not min_speaking and not is_cooling_down and not self.ui.muted:
                try:
                    rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2))) / 32768.0
                    self.ui.set_audio_level(min(1.0, rms * 18))
                except Exception:
                    rms = 0.0
                
                audio_data = indata.tobytes()
                
                if provider != "gemini" and getattr(self, "vosk_recognizer", None):
                    if self.vosk_recognizer.AcceptWaveform(audio_data):
                        res = json.loads(self.vosk_recognizer.Result())
                        text = res.get("text", "").strip()
                        if text:
                            self.ui.write_log(f"Tú (Voz Local): {text}")
                            loop.call_soon_threadsafe(self._local_command_queue.put_nowait, text)
                elif provider == "gemini":
                    if rms < 0.003:
                        data = np.zeros_like(indata).tobytes()
                    else:
                        data = audio_data
                        
                    def _safe_put(q, item):
                        try:
                            q.put_nowait(item)
                        except Exception:
                            pass
                    loop.call_soon_threadsafe(
                        _safe_put, self.out_queue, {"data": data, "mime_type": "audio/pcm"}
                    )
            elif min_speaking:
                try:
                    rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2))) / 32768.0
                    self.ui.set_audio_level(min(1.0, rms * 15))
                except Exception:
                    pass

        try:
            with sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=callback,
            ):
                print("[MIN] 🎤 Mic stream open")
                while True:
                    await asyncio.sleep(0.01)
        except Exception as e:
            print(f"[MIN] ❌ Mic: {e}")
            raise

    async def _receive_audio(self):
        print("[MIN] 👂 Recv iniciado")
        out_buf, in_buf = [], []
        _first_chunk   = True
        _last_tool     = None

        try:
            while True:
                async for response in self.session.receive():

                    if response.data:
                        if not self._stop_requested.is_set():
                            self.audio_in_queue.put_nowait(response.data)

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            txt = _clean_transcript(sc.output_transcription.text)
                            if txt:
                                out_buf.append(txt)
                                if _first_chunk:
                                    self.ui.clear_min_response()
                                    _first_chunk = False
                                self.ui.stream_min_chunk(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = _clean_transcript(sc.input_transcription.text)
                            if txt:
                                in_buf.append(txt)

                        if sc.turn_complete:
                            self._stop_requested.clear()
                            if self._turn_done_event:
                                self._turn_done_event.set()
                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                self.ui.write_log(f"Tú: {full_in}")
                                self._fire_phrase_triggers(full_in)
                            in_buf = []
                            out_buf = []
                            _first_chunk = True

                    if response.tool_call:
                        self.ui.clear_min_response()
                        _first_chunk = True
                        fcs = response.tool_call.function_calls
                        for fc in fcs:
                            print(f"[MIN] 📞 {fc.name}")
                            _last_tool = fc.name
                        
                        if len(fcs) > 1:
                            tasks = [asyncio.create_task(self._execute_tool(fc)) for fc in fcs]
                            fn_responses = list(await asyncio.gather(*tasks))
                        else:
                            fn_responses = [await self._execute_tool(fcs[0])]
                        try:
                            await self.session.send_tool_response(
                                function_responses=fn_responses
                            )
                            _last_tool = None
                        except Exception as tool_err:
                            print(f"[MIN] ❌ send_tool_response failed: {tool_err}")
                            raise
        except Exception as e:
            msg  = str(e)
            code = getattr(e, "status_code", 0) or getattr(e, "code", 0) or 0
            if code == 1011 or "1011" in msg or "Internal error" in msg:
                tool_info = f" durante '{_last_tool}'" if _last_tool else ""
                print(f"[MIN] ⚡ API 1011{tool_info} — reconectando...")
                self._api_1011_tool = _last_tool
            else:
                print(f"[MIN] ❌ Recv: {e}")
                traceback.print_exc()
            raise

    async def _play_audio(self):
        print("[MIN] 🔊 Play iniciado")

        stream = sd.RawOutputStream(
            samplerate=RECEIVE_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=PLAY_CHUNK_SIZE,
        )
        stream.start()

        _jitter_buf: list[bytes] = []
        _JITTER_TARGET = 3
        prebuffering = True

        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        self.audio_in_queue.get(),
                        timeout=0.05
                    )
                except asyncio.TimeoutError:
                    if (
                        self._turn_done_event
                        and self._turn_done_event.is_set()
                        and self.audio_in_queue.empty()
                    ):
                        while _jitter_buf:
                            buffered = _jitter_buf.pop(0)
                            try:
                                play_data = np.frombuffer(buffered, dtype=np.int16)
                                rms = float(np.sqrt(np.mean(play_data.astype(np.float32) ** 2))) / 32768.0
                                self.ui.set_audio_level(min(1.0, rms * 25))
                            except Exception:
                                pass
                            await asyncio.to_thread(stream.write, buffered)
                        self.set_speaking(False)
                        self._turn_done_event.clear()
                        prebuffering = True
                    continue

                self.set_speaking(True)
                _jitter_buf.append(chunk)

                if prebuffering:
                    if len(_jitter_buf) >= _JITTER_TARGET:
                        prebuffering = False
                
                if not prebuffering:
                    buffered = _jitter_buf.pop(0)
                    try:
                        play_data = np.frombuffer(buffered, dtype=np.int16)
                        rms = float(np.sqrt(np.mean(play_data.astype(np.float32) ** 2))) / 32768.0
                        self.ui.set_audio_level(min(1.0, rms * 25))
                    except Exception:
                        pass
                    await asyncio.to_thread(stream.write, buffered)
        except Exception as e:
            print(f"[MIN] ❌ Play: {e}")
            raise
        finally:
            self.set_speaking(False)
            stream.stop()
            stream.close()

    async def run(self):
        self._local_command_queue = asyncio.Queue()

        client = genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"}
        )

        reconnect_delay   = 1.0
        consecutive_fails = 0

        while True:
            try:
                provider = _get_llm_provider()
                if provider != "gemini":
                    self._loop = asyncio.get_event_loop()
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue = asyncio.Queue(maxsize=5)
                    self._turn_done_event = asyncio.Event()
                    self._reconnect_event = asyncio.Event()

                    self.ui.set_state("LISTENING")
                    self.ui.write_log(f"SYS: MIN en línea (Modo {provider.upper()}).")
                    
                    async with asyncio.TaskGroup() as tg:
                        tg.create_task(self._listen_audio())
                        tg.create_task(self._play_audio())
                        tg.create_task(self._watch_reconnect())
                        tg.create_task(self._stability_monitor())
                        tg.create_task(self._generic_llm_consumer(provider))
                        
                        await self._reconnect_event.wait()
                    continue

                print("[MIN] 🔌 Conectando...")
                self.ui.set_state("THINKING")
                config = self._build_config()

                async with (
                    client.aio.live.connect(model=_get_live_model(), config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session          = session
                    self._loop            = asyncio.get_event_loop()
                    self.audio_in_queue   = asyncio.Queue()
                    self.out_queue        = asyncio.Queue(maxsize=5)
                    self._turn_done_event = asyncio.Event()
                    self._reconnect_event = asyncio.Event()

                    print("[MIN] ✅ Conectado.")
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("SYS: MIN en línea.")
                    reconnect_delay   = 1.0
                    consecutive_fails = 0
                    self._api_1011_tool = None

                    if self._first_connect:
                        self._first_connect = False
                        try:
                            from actions.vision.vision_guardian import start as _start_vision_guardian
                            _start_vision_guardian(
                                inject_fn=self._inject_text,
                                speaking_fn=lambda: self._is_speaking,
                            )
                        except Exception as _vge:
                            print(f"[MIN] VisionGuardian init error: {_vge}")
                        
                        _hour = __import__("datetime").datetime.now().hour
                        try:
                            from actions.automation.morning_brief import already_briefed_today
                            has_briefed = already_briefed_today()
                        except Exception:
                            has_briefed = False
                        
                        if 6 <= _hour < 12 and not has_briefed:
                            async def _auto_brief():
                                await asyncio.sleep(1)
                                await self.session.send_client_content(
                                    turns={"parts": [{"text": "[AUTO] Dame el informe matutino del día."}]},
                                    turn_complete=True
                                )
                            tg.create_task(_auto_brief())

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())
                    tg.create_task(self._watch_reconnect())
                    tg.create_task(self._stability_monitor())

            except Exception as e:
                exceptions = e.exceptions if isinstance(e, ExceptionGroup) else [e]

                is_handshake_timeout = False
                is_config_reconnect  = False
                for exc in exceptions:
                    msg = str(exc)
                    if "Config changed" in msg:
                        is_config_reconnect = True
                        consecutive_fails = 0
                    elif "timed out during opening handshake" in msg or (
                        isinstance(exc, TimeoutError) and "handshake" in msg
                    ):
                        is_handshake_timeout = True
                        print(f"[MIN] ⏱️ Timeout al conectar — reintentando en 1s...")
                    elif "1011" in msg or "Internal error" in msg:
                        tool_hint = self._api_1011_tool or ""
                        print(f"[MIN] ⚡ API 1011{tool_hint and ' durante '+tool_hint} — reconectando...")
                        consecutive_fails += 1
                        if consecutive_fails >= 4:
                            self.ui.write_log(
                                "SYS: ⚠️ Error 1011 repetido. Esperando para no saturar la API...\n"
                                "SYS: Si persiste más de 2 min, reiniciá MIN."
                            )
                        elif tool_hint:
                            self.ui.write_log(f"SYS: Error de servidor al ejecutar '{tool_hint}'. Reconectando...")
                        else:
                            self.ui.write_log("SYS: Error de servidor 1011. Reconectando...")
                    elif "1008" in msg or "policy violation" in msg.lower() or "not found for API version" in msg:
                        print(f"[MIN] ⚠️ Modelo no disponible en esta versión de API: {msg[:120]}")
                        self.ui.write_log("SYS: ⚠️ Modelo no disponible. Reintentando...")
                        consecutive_fails += 1
                    elif "1000" in msg or "going away" in msg.lower():
                        print(f"[MIN] 🔄 Sesión expirada — reconectando...")
                        consecutive_fails = 0
                    else:
                        print(f"[MIN] ⚠️ {exc}")
                        traceback.print_exc()
                        consecutive_fails += 1

                if is_config_reconnect:
                    self.set_speaking(False)
                    self.ui.set_state("THINKING")
                    await asyncio.sleep(0.5)
                    continue

                if is_handshake_timeout:
                    self.set_speaking(False)
                    self.ui.set_state("THINKING")
                    await asyncio.sleep(1.0)
                    continue

            self.set_speaking(False)
            self.ui.set_state("THINKING")

            if consecutive_fails > 1:
                max_delay = 90.0 if consecutive_fails >= 5 else 12.0
                reconnect_delay = min(reconnect_delay * 2, max_delay)
            elif consecutive_fails == 0:
                reconnect_delay = 1.0

            import random as _rnd
            jitter = _rnd.uniform(0, reconnect_delay * 0.25)
            total  = reconnect_delay + jitter
            print(f"[MIN] 🔄 Reconectando en {total:.1f}s...")
            await asyncio.sleep(total)


def main():
    # ── Single Instance Lock ──────────────────────────────────────────────────
    import ctypes
    global _single_instance_mutex
    _single_instance_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "MIN_AI_SINGLE_INSTANCE_MUTEX")
    if ctypes.windll.kernel32.GetLastError() == 183:
        print("[MIN] Ya hay una instancia en ejecución. Cerrando.")
        sys.exit(0)

    _load_tz()

    def _ensure_both_api_keys():
        from core.config_manager import get_config
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

        print("[MIN] ⚠️  Faltan las siguientes API keys: " + ", ".join(missing))
        print("[MIN] Configúralas desde el panel de Configuración en la interfaz Tauri.")
        print("[MIN] MIN iniciará igualmente, pero algunas funciones estarán limitadas.")

    _ensure_both_api_keys()

    ui = MinUI("face.png")

    # --- Global Hotkey Setup (INSERT key to wake/unmute MIN) ---
    try:
        def _setup_global_hotkey():
            import ctypes
            import ctypes.wintypes

            def on_hotkey_triggered():
                """Toggle mute state via global INSERT hotkey."""
                if getattr(ui, "muted", False):
                    ui.muted = False
                    ui.set_state("LISTENING")
                    ui.write_log("SYS: 🎤 Micrófono ACTIVADO vía atajo INS.")
                else:
                    ui.set_state("LISTENING")
                    ui.write_log("SYS: 🔔 MIN en foco vía atajo INS.")

            def hotkey_thread():
                user32 = ctypes.windll.user32
                try:
                    if not user32.RegisterHotKey(None, 99, 0x0000, 0x2D):
                        print("[HOTKEY] Error registering global Insert hotkey.")
                        return
                except Exception as e:
                    print(f"[HOTKEY] Exception registering global hotkey: {e}")
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

        _setup_global_hotkey()
        print("[MIN] Global INSERT hotkey registered successfully.")
    except Exception as e:
        print(f"[MIN] Global hotkey setup failed: {e}")

    def runner():
        ui.wait_for_api_key()
        min_live = MinLive(ui)
        try:
            asyncio.run(min_live.run())
        except KeyboardInterrupt:
            print("\n🔴 Apagando...")

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()


if __name__ == "__main__":
    main()