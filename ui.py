"""
ui.py — MIN WebSocket UI Server
===============================
Clean WebSocket server for Tauri frontend communication.
Handles all UI events, config, media tracking, and client connections.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import psutil
import sys
import threading
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path

import websockets

# ── Constants ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
FAVORITES_PATH = CONFIG_DIR / "favorites.json"

# ── Favorites Helpers ───────────────────────────────────────────────────────
def load_favorites() -> list:
    if not FAVORITES_PATH.exists():
        return []
    try:
        return json.loads(FAVORITES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_favorites(favs_list: list):
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        FAVORITES_PATH.write_text(
            json.dumps(favs_list, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception as e:
        print(f"[Favorites] Error: {e}")

# ── Mock Tauri Root ─────────────────────────────────────────────────────────
class MockRootTauri:
    """Fake root for Tkinter-like mainloop compatibility."""
    def __init__(self, ui):
        self.ui = ui

    def mainloop(self):
        self.ui._ws_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.ui._ws_loop)
        try:
            self.ui._ws_loop.run_until_complete(self.ui._run_ws_server())
        except KeyboardInterrupt:
            pass
        finally:
            self.ui._ws_loop.close()

    def after(self, ms: int, func):
        t = threading.Timer(ms / 1000.0, func)
        t.daemon = True
        t.start()

# ── WebSocket Log Filter ───────────────────────────────────────────────────
class _WSLogFilter(logging.Filter):
    def filter(self, record):
        msgs = (
            "opening handshake failed",
            "connection handler failed",
            "handshake",
            "HTTP request",
            "connection closed",
        )
        msg_str = str(record.msg)
        if any(m in msg_str for m in msgs):
            return False
        if record.exc_info and record.exc_info[0]:
            from websockets.exceptions import (
                InvalidMessage, EOFError, InvalidHandshake,
                ConnectionClosed, ConnectionClosedError, ConnectionClosedOK
            )
            if record.exc_info[0] in (
                InvalidMessage, EOFError, InvalidHandshake,
                ConnectionClosed, ConnectionClosedError, ConnectionClosedOK
            ):
                return False
        return True

# ── MinUI ────────────────────────────────────────────────────────────────────
class MinUI:
    def __init__(self, face_path=""):
        self.muted = False
        self.current_file = ""

        # Callbacks (set by main.py)
        self.on_text_command = None
        self.on_stop_command = None
        self.on_config_saved = None

        # Response buffer
        self.min_response_buffer = ""

        # Connected WebSocket clients
        self._clients: set = set()
        self._ws_loop = None

        # Gesture thread handle
        self._gesture_thread = None

        self.root = MockRootTauri(self)
        print("[MIN] Running in Headless WebSocket mode for Tauri.")

        threading.Thread(target=self.ensure_startup_shortcut, daemon=True).start()

    # ── Basic UI Methods ─────────────────────────────────────────────────

    def wait_for_api_key(self):
        pass

    def write_log(self, text: str):
        if hasattr(self, "_last_log") and self._last_log == text:
            return
        self._last_log = text
        print(text)
        self.broadcast({"type": "log", "value": text})

    def set_state(self, state: str):
        self.broadcast({"type": "state", "value": state})
        if state == "MUTED":
            self.muted = True
        elif state in ("LISTENING", "SPEAKING", "THINKING"):
            if self.muted:
                self.muted = False

    def set_audio_level(self, level: float):
        self.broadcast({"type": "volume", "value": level})

    def clear_min_response(self):
        self.min_response_buffer = ""
        self.broadcast({"type": "log", "value": "MIN: [Clear]"})

    def stream_min_chunk(self, chunk: str):
        text = chunk.replace("MIN:", "").strip()
        if text:
            if self.min_response_buffer:
                self.min_response_buffer += " " + text
            else:
                self.min_response_buffer = text
            self.broadcast({"type": "log", "value": "MIN: " + text})

    def show_weather_widget(self):
        try:
            from actions.automation.weather_report import fetch_weather_data
            data = fetch_weather_data({})
            if not data.get("error"):
                self.broadcast({"type": "weather", "data": data})
        except Exception:
            pass

    # ── WebSocket Server ─────────────────────────────────────────────────

    async def _run_ws_server(self):
        # Suppress noisy websockets logs
        ws_logger = logging.getLogger("websockets")
        ws_logger.addFilter(_WSLogFilter())
        ws_logger.setLevel(logging.CRITICAL)

        from services.system.media_monitor import get_active_media

        async def handler(websocket):
            addr = websocket.remote_address
            print(f"[WS] Client connected from {addr}")
            self._clients.add(websocket)

            try:
                # Send current state
                await websocket.send(json.dumps({
                    "type": "state",
                    "value": "MUTED" if self.muted else "LISTENING"
                }))

                # Send full config to new client
                await self._send_config(websocket)

                # Send weather
                await self._send_weather(websocket)

                # Send todos
                await self._send_todos(websocket)

                # Send favorites
                await websocket.send(json.dumps({
                    "type": "favorites",
                    "value": load_favorites()
                }))

                # Message loop
                async for message in websocket:
                    await self._handle_message(websocket, message)

            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                self._clients.discard(websocket)
                print(f"[WS] Client disconnected: {addr}")

        async def media_tracker():
            last_media = None
            while True:
                try:
                    if self._clients:
                        media = get_active_media()
                        if media != last_media:
                            last_media = media
                            self.broadcast({
                                "type": "media",
                                "app": media["app"],
                                "title": media["title"],
                                "artist": media["artist"],
                            })
                except Exception as e:
                    print(f"[WS Media] Tracker error: {e}")
                await asyncio.sleep(2.0)

        asyncio.create_task(media_tracker())

        print("[WS] Server running at ws://127.0.0.1:8765")
        async with websockets.serve(handler, "127.0.0.1", 8765):
            await asyncio.Future()

    async def _send_config(self, websocket):
        """Send full config to newly connected client."""
        try:
            cfg_path = CONFIG_DIR / "config.json"
            if cfg_path.exists():
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

                # Merge sub-configs into cfg dict
                sub_configs = [
                    ("accessibility", "accessibility_config.json"),
                    ("vision_guardian", "vision_guardian_state.json"),
                    ("user_profile", "user_profile.json"),
                    ("app_registry", "app_registry.json"),
                ]
                for key, filename in sub_configs:
                    path = CONFIG_DIR / filename
                    if path.exists():
                        try:
                            cfg[key] = json.loads(path.read_text(encoding="utf-8"))
                        except Exception:
                            pass

                await websocket.send(json.dumps({
                    "type": "log",
                    "value": f"config_loaded:{json.dumps(cfg)}"
                }))
        except Exception as e:
            print(f"[WS] Config send error: {e}")

    async def _send_weather(self, websocket):
        """Send weather data to newly connected client."""
        try:
            from actions.automation.weather_report import fetch_weather_data
            data = fetch_weather_data({})
            if not data.get("error"):
                await websocket.send(json.dumps({"type": "weather", "data": data}))
        except Exception:
            pass

    async def _send_todos(self, websocket):
        """Send todos to newly connected client."""
        try:
            from actions.automation.goals import load_goals
            await websocket.send(json.dumps({"type": "todos", "value": load_goals()}))
        except Exception as e:
            print(f"[WS] Todos send error: {e}")

    async def _handle_message(self, websocket, message):
        """Handle incoming WebSocket message from Tauri client."""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "")

            if msg_type == "command":
                val = data.get("value", "")
                if self.on_text_command:
                    self.on_text_command(val)

            elif msg_type == "toggle_mute":
                self.muted = not self.muted
                self.broadcast({
                    "type": "state",
                    "value": "MUTED" if self.muted else "LISTENING"
                })

            elif msg_type == "toggle_camera_gestures":
                self._toggle_camera_gestures()

            elif msg_type == "media_control":
                action = data.get("action", "")
                try:
                    from actions.media.media_control import media_control
                    res = media_control({"action": action})
                    self.write_log(f"SYS: Control de Medios: {res}")
                except Exception as e:
                    print(f"[WS] Media control error: {e}")

            elif msg_type == "save_config":
                await self._handle_save_config(data.get("config", {}))

            elif msg_type == "set_file":
                path_val = data.get("value", "").strip()
                self.current_file = path_val
                self.write_log(f"SYS: Archivo cargado: {self.current_file}")

            elif msg_type == "get_todos":
                from actions.automation.goals import load_goals
                await websocket.send(json.dumps({
                    "type": "todos",
                    "value": load_goals()
                }))

            elif msg_type == "add_todo":
                await self._handle_add_todo(data)

            elif msg_type == "toggle_todo":
                await self._handle_toggle_todo(data)

            elif msg_type == "delete_todo":
                await self._handle_delete_todo(data)

            elif msg_type == "get_favorites":
                await websocket.send(json.dumps({
                    "type": "favorites",
                    "value": load_favorites()
                }))

            elif msg_type == "add_favorite":
                title = data.get("title", "").strip()
                url = data.get("url", "").strip()
                if title and url:
                    favs = load_favorites()
                    favs.append({"title": title, "url": url})
                    save_favorites(favs)
                    self.broadcast({"type": "favorites", "value": favs})

            elif msg_type == "delete_favorite":
                url = data.get("url", "")
                favs = load_favorites()
                favs = [f for f in favs if f["url"] != url]
                save_favorites(favs)
                self.broadcast({"type": "favorites", "value": favs})

            elif msg_type == "open_url":
                url = data.get("url", "")
                if url:
                    webbrowser.open(url)

            elif msg_type == "list_audio_devices":
                await self._handle_list_audio_devices(websocket)

            elif msg_type == "list_models":
                await self._handle_list_models(websocket)

            elif msg_type == "agent_status":
                await self._handle_agent_status(websocket)

            elif msg_type == "agent_kill":
                self.stop_gesture_thread()
                self.broadcast({"type": "log", "value": "SYS: Apagando MIN..."})
                self.broadcast({"type": "ui_control", "action": "shutdown"})
                os._exit(0)

            elif msg_type == "agent_restart":
                self.stop_gesture_thread()
                self.broadcast({"type": "log", "value": "SYS: Reiniciando MIN..."})
                try:
                    main_py = str(BASE_DIR / "main.py")
                    subprocess.Popen(
                        [sys.executable, main_py],
                        creationflags=0x00000008
                    )
                except Exception as e:
                    print(f"[WS] Restart error: {e}")
                os._exit(0)

            elif msg_type == "list_browsers":
                await self._handle_list_browsers(websocket)

        except Exception as e:
            print(f"[WS] Message handling error: {e}")

    async def _handle_save_config(self, config_data: dict):
        """Save config and sub-configs from UI."""
        try:
            # Extract and save sub-configs
            sub_configs = [
                ("accessibility", "accessibility_config.json"),
                ("vision_guardian", "vision_guardian_state.json"),
                ("user_profile", "user_profile.json"),
                ("app_registry", "app_registry.json"),
            ]
            for key, filename in sub_configs:
                if key in config_data:
                    path = CONFIG_DIR / filename
                    path.write_text(
                        json.dumps(config_data.pop(key), indent=4),
                        encoding="utf-8"
                    )

            # Save remaining config
            cfg_path = CONFIG_DIR / "config.json"
            if cfg_path.exists():
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                cfg.update(config_data)
                cfg_path.write_text(json.dumps(cfg, indent=4), encoding="utf-8")

            if self.on_config_saved:
                self.on_config_saved(config_data)

        except Exception as e:
            print(f"[WS] Config save error: {e}")

    async def _handle_add_todo(self, data: dict):
        from actions.automation.goals import load_goals, save_goals
        title = data.get("title", "").strip()
        priority = data.get("priority", "medium").lower()
        if title:
            gls = load_goals()
            gls.append({
                "id": str(uuid.uuid4()),
                "title": title,
                "description": data.get("description", "").strip(),
                "priority": priority if priority in ("high", "medium", "low") else "medium",
                "due_date": data.get("due_date", "").strip(),
                "status": "pending",
                "subtasks": [],
                "created_at": datetime.now().isoformat(),
                "completed_at": None,
            })
            save_goals(gls)
            self.broadcast({"type": "todos", "value": gls})

    async def _handle_toggle_todo(self, data: dict):
        from actions.automation.goals import load_goals, save_goals
        todo_id = data.get("id", "")
        gls = load_goals()
        for g in gls:
            if g["id"] == todo_id:
                g["status"] = "completed" if g["status"] == "pending" else "pending"
                if g["status"] == "completed":
                    g["completed_at"] = datetime.now().isoformat()
                    for s in g.get("subtasks", []):
                        s["status"] = "completed"
                else:
                    g["completed_at"] = None
                break
        save_goals(gls)
        self.broadcast({"type": "todos", "value": gls})

    async def _handle_delete_todo(self, data: dict):
        from actions.automation.goals import load_goals, save_goals
        todo_id = data.get("id", "")
        gls = load_goals()
        gls = [g for g in gls if g["id"] != todo_id]
        save_goals(gls)
        self.broadcast({"type": "todos", "value": gls})

    async def _handle_list_audio_devices(self, websocket):
        devices = {"microphones": [], "speakers": []}
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                dev = {
                    "index": i,
                    "name": info.get("name", f"Device {i}"),
                    "channels_in": info.get("maxInputChannels", 0),
                    "channels_out": info.get("maxOutputChannels", 0),
                }
                if dev["channels_in"] > 0:
                    devices["microphones"].append(dev)
                if dev["channels_out"] > 0:
                    devices["speakers"].append(dev)
            pa.terminate()
        except Exception as e:
            print(f"[WS] Audio devices error: {e}")
        await websocket.send(json.dumps({"type": "audio_devices", "data": devices}))

    async def _handle_list_models(self, websocket):
        models = {"gemini": [], "openrouter": []}
        cfg_path = CONFIG_DIR / "config.json"
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
        except Exception:
            cfg = {}

        # Gemini
        gemini_key = cfg.get("gemini_api_key", "")
        if gemini_key:
            try:
                import urllib.request
                req = urllib.request.Request(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}",
                    headers={"User-Agent": "MIN/2.0"}
                )
                resp = urllib.request.urlopen(req, timeout=10)
                data_resp = json.loads(resp.read().decode("utf-8"))
                for m in data_resp.get("models", []):
                    models["gemini"].append({
                        "id": m.get("name", ""),
                        "name": m.get("displayName", m.get("name", "")),
                        "description": m.get("description", ""),
                    })
            except Exception as e:
                print(f"[WS] Gemini models error: {e}")

        # OpenRouter
        or_key = cfg.get("openrouter_api_key", "")
        if or_key:
            try:
                import urllib.request
                req = urllib.request.Request(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {or_key}", "User-Agent": "MIN/2.0"}
                )
                resp = urllib.request.urlopen(req, timeout=10)
                data_resp = json.loads(resp.read().decode("utf-8"))
                for m in data_resp.get("data", []):
                    models["openrouter"].append({
                        "id": m.get("id", ""),
                        "name": m.get("name", m.get("id", "")),
                        "context_length": m.get("context_length", 0),
                    })
            except Exception as e:
                print(f"[WS] OpenRouter models error: {e}")

        await websocket.send(json.dumps({"type": "models_list", "data": models}))

    async def _handle_agent_status(self, websocket):
        status = {
            "pid": os.getpid(),
            "uptime_seconds": 0,
            "memory_mb": 0,
            "python_version": sys.version,
        }
        try:
            proc = psutil.Process(os.getpid())
            status["memory_mb"] = round(proc.memory_info().rss / 1024 / 1024, 1)
            status["uptime_seconds"] = round(
                (datetime.now() - datetime.fromtimestamp(proc.create_time())).total_seconds()
            )
        except Exception:
            pass
        await websocket.send(json.dumps({"type": "agent_status", "data": status}))

    async def _handle_list_browsers(self, websocket):
        try:
            from actions.web.browser_registry import detect_installed_browsers, resolve_browser_path
            detected = detect_installed_browsers()
            current_key, current_path = resolve_browser_path()
            await websocket.send(json.dumps({
                "type": "browsers_list",
                "data": {
                    "installed": {k: v for k, v in detected.items()},
                    "current": current_key,
                    "current_path": current_path or "",
                }
            }))
        except Exception as e:
            print(f"[WS] Browsers list error: {e}")

    # ── Broadcast ────────────────────────────────────────────────────────────

    def broadcast(self, data: dict):
        if not self._clients:
            return
        msg = json.dumps(data)
        async def do_send():
            if list(self._clients):
                await asyncio.gather(
                    *[c.send(msg) for c in self._clients],
                    return_exceptions=True
                )
        if self._ws_loop:
            asyncio.run_coroutine_threadsafe(do_send(), self._ws_loop)

    # ── Startup Shortcut ───────────────────────────────────────────────────

    def ensure_startup_shortcut(self):
        try:
            appdata = os.getenv("APPDATA")
            if not appdata:
                return
            startup_dir = os.path.join(
                appdata,
                "Microsoft",
                "Windows",
                "Start Menu",
                "Programs",
                "Startup",
            )
            shortcut_path = os.path.join(startup_dir, "MIN AI.lnk")
            current_dir = os.path.abspath(os.path.dirname(__file__))
            target_bat = os.path.join(current_dir, "MIN.bat")
            icon_path = os.path.join(current_dir, "assets", "min_icono.ico")

            if not os.path.exists(target_bat):
                return

            ps_cmd = (
                f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{shortcut_path}');"
                f"$s.TargetPath='{target_bat}';"
                f"$s.WorkingDirectory='{current_dir}';"
                f"$s.IconLocation='{icon_path}';"
                f"$s.Description='Lanzador Automatico de MIN AI';"
                f"$s.Save()"
            )
            import subprocess
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            print("[STARTUP] Shortcut ensured.")
        except Exception as e:
            print(f"[STARTUP] Error: {e}")

    # ── Camera Gestures ───────────────────────────────────────────────────

    def _toggle_camera_gestures(self):
        if not hasattr(self, "_gesture_thread") or self._gesture_thread is None:
            try:
                from services.vision.gesture_controller import GestureController
                cfg_path = CONFIG_DIR / "config.json"
                cam_idx = 0
                if cfg_path.exists():
                    try:
                        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                        cam_idx = cfg.get("camera_index", 0)
                    except Exception:
                        pass
                self._gesture_thread = GestureController(self, camera_index=cam_idx)
                self._gesture_thread.start()
                self.write_log("SYS: Control gestual iniciado.")
            except Exception as e:
                self.write_log(f"SYS: Error gesture control: {e}")
        else:
            self.stop_gesture_thread()

    def stop_gesture_thread(self):
        if hasattr(self, "_gesture_thread") and self._gesture_thread is not None:
            self._gesture_thread.stop()
            self._gesture_thread = None
            self.write_log("SYS: Control gestual detenido.")
