"""ui.py — MIN WebSocket UI Server for Tauri frontend."""
from __future__ import annotations
import sys
import os
import json
import psutil
import threading
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta


FAVORITES_PATH = Path(__file__).parent / "config" / "favorites.json"


def load_favorites() -> list:
    if not FAVORITES_PATH.exists():
        default_favs = [
            {"title": "Noticias", "url": "https://news.google.com"},
            {"title": "TradingView", "url": "https://www.tradingview.com"},
            {"title": "GitHub", "url": "https://github.com"},
        ]
        save_favorites(default_favs)
        return default_favs
    try:
        return json.loads(FAVORITES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_favorites(favs_list: list):
    try:
        FAVORITES_PATH.parent.mkdir(parents=True, exist_ok=True)
        FAVORITES_PATH.write_text(
            json.dumps(favs_list, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as e:
        print(f"[Favorites] Error saving favorites: {e}")


class MockRootTauri:
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


class MinUI:
    def __init__(self, face_path=""):
        self.muted = False
        self.current_file = ""

        self.on_text_command = None
        self.on_stop_command = None
        self.on_config_saved = None

        self.min_response_buffer = ""

        self._clients: set = set()
        self._ws_loop = None
        self.root = MockRootTauri(self)
        print("[MIN] Running in Headless WebSocket mode for Tauri.")

        # Run startup shortcut setup in background thread
        threading.Thread(target=self.ensure_startup_shortcut, daemon=True).start()

    def wait_for_api_key(self):
        pass

    def write_log(self, text: str):
        # Dedup: no reenviar si el último log es idéntico
        if hasattr(self, '_last_log') and self._last_log == text:
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

            # Enviar el chunk como log unificado (no palabra por palabra)
            self.broadcast({"type": "log", "value": "MIN: " + text})

    def show_weather_widget(self):
        try:
            from actions.weather_report import fetch_weather_data

            data = fetch_weather_data({})
            if not data.get("error"):
                self.broadcast({"type": "weather", "data": data})
        except Exception:
            pass

    async def _run_ws_server(self):
        import websockets
        import json
        import asyncio
        import logging
        
        class HandshakeFilter(logging.Filter):
            def filter(self, record):
                if record.msg in ("opening handshake failed", "connection handler failed"):
                    return False
                if record.exc_info and record.exc_info[0]:
                    exc_name = record.exc_info[0].__name__
                    if exc_name in ("InvalidMessage", "EOFError", "InvalidHandshake", "ConnectionClosed", "ConnectionClosedError", "ConnectionClosedOK"):
                        return False
                msg_str = str(record.msg)
                if "handshake" in msg_str or "HTTP request" in msg_str or "connection closed" in msg_str:
                    return False
                return True

        logging.getLogger("websockets.server").addFilter(HandshakeFilter())
        logging.getLogger("websockets.protocol").addFilter(HandshakeFilter())
        logging.getLogger("websockets").setLevel(logging.CRITICAL)

        def get_active_media():
            import psutil

            try:
                import win32gui
                import win32process
            except ImportError:
                return {"app": "Ninguno", "title": "Sin reproducción", "artist": ""}

            try:
                pids_by_name = {}
                for proc in psutil.process_iter(["pid", "name"]):
                    try:
                        name = proc.info["name"]
                        if name:
                            name_lower = name.lower()
                            if name_lower not in pids_by_name:
                                pids_by_name[name_lower] = []
                            pids_by_name[name_lower].append(proc.info["pid"])
                    except Exception:
                        pass

                visible_windows = []

                def enum_windows_callback(hwnd, extra):
                    if win32gui.IsWindowVisible(hwnd):
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        title = win32gui.GetWindowText(hwnd)
                        if title:
                            visible_windows.append((title, pid, hwnd))
                    return True

                win32gui.EnumWindows(enum_windows_callback, None)

                # 1. Spotify
                spotify_pids = pids_by_name.get("spotify.exe", [])
                if spotify_pids:
                    for title, pid, hwnd in visible_windows:
                        if pid in spotify_pids:
                            if title not in [
                                "Spotify",
                                "Spotify Premium",
                                "Spotify Free",
                                "Spotify Partner Store",
                                "Spotify helper",
                                "SpotifyOverlay",
                            ]:
                                if " - " in title:
                                    parts = title.split(" - ", 1)
                                    return {
                                        "app": "Spotify",
                                        "artist": parts[0],
                                        "title": parts[1],
                                    }
                                return {"app": "Spotify", "artist": "", "title": title}
                    for title, pid, hwnd in visible_windows:
                        if pid in spotify_pids and title in [
                            "Spotify",
                            "Spotify Premium",
                            "Spotify Free",
                        ]:
                            return {
                                "app": "Spotify",
                                "artist": "Pausado",
                                "title": "Spotify",
                            }

                # 2. VLC
                vlc_pids = pids_by_name.get("vlc.exe", [])
                if vlc_pids:
                    for title, pid, hwnd in visible_windows:
                        if pid in vlc_pids:
                            if " - VLC media player" in title:
                                clean_title = title.replace(
                                    " - VLC media player", ""
                                )
                                if " - " in clean_title:
                                    parts = clean_title.split(" - ", 1)
                                    return {
                                        "app": "VLC Media Player",
                                        "artist": parts[0],
                                        "title": parts[1],
                                    }
                                return {
                                    "app": "VLC Media Player",
                                    "artist": "",
                                    "title": clean_title,
                                }

                # 3. Web Browsers
                browser_process_names = [
                    "chrome.exe",
                    "brave.exe",
                    "firefox.exe",
                    "msedge.exe",
                    "opera.exe",
                ]
                for browser_name in browser_process_names:
                    browser_pids = pids_by_name.get(browser_name, [])
                    if browser_pids:
                        for title, pid, hwnd in visible_windows:
                            if pid in browser_pids:
                                if " - YouTube" in title:
                                    clean_title = title.split(" - YouTube")[0]
                                    artist = "YouTube"
                                    if " - " in clean_title:
                                        parts = clean_title.split(" - ", 1)
                                        artist = parts[0]
                                        clean_title = parts[1]
                                    return {
                                        "app": browser_name.replace(".exe", "").capitalize(),
                                        "artist": artist,
                                        "title": clean_title,
                                    }
                                elif "Netflix" in title:
                                    return {
                                        "app": "Netflix",
                                        "artist": "Netflix",
                                        "title": title.split(" - ")[0],
                                    }
                                elif "SoundCloud" in title:
                                    return {
                                        "app": "SoundCloud",
                                        "artist": "SoundCloud",
                                        "title": title.split(" - ")[0],
                                    }

                # 4. Modern Windows Media Player
                wmp_pids = pids_by_name.get(
                    "microsoft.media.player.exe", []
                ) or pids_by_name.get("wmplayer.exe", [])
                if wmp_pids:
                    for title, pid, hwnd in visible_windows:
                        if pid in wmp_pids:
                            if title and title not in [
                                "Media Player",
                                "Reproductor de multimedia",
                            ]:
                                if " - " in title:
                                    parts = title.split(" - ", 1)
                                    return {
                                        "app": "Windows Media Player",
                                        "artist": parts[0],
                                        "title": parts[1],
                                    }
                                return {
                                    "app": "Windows Media Player",
                                    "artist": "",
                                    "title": title,
                                }

                return {"app": "Ninguno", "title": "Sin reproducción", "artist": ""}
            except Exception:
                return {"app": "Ninguno", "title": "Sin reproducción", "artist": ""}

        async def handler(websocket):
            print(f"[WS] Client connected from {websocket.remote_address}")
            self._clients.add(websocket)
            try:
                # Send current state upon connection
                await websocket.send(
                    json.dumps(
                        {
                            "type": "state",
                            "value": "MUTED" if self.muted else "LISTENING",
                        }
                    )
                )

                # Send loaded config to Tauri client
                try:
                    cfg_path = Path(__file__).parent / "config" / "config.json"
                    if cfg_path.exists():
                        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                        
                        # Load accessibility config
                        acc_path = Path(__file__).parent / "config" / "accessibility_config.json"
                        if acc_path.exists():
                            try:
                                cfg["accessibility"] = json.loads(acc_path.read_text(encoding="utf-8"))
                            except Exception as _ae:
                                print(f"[WS] Error loading accessibility: {_ae}")
                        
                        # Load vision guardian state
                        vg_path = Path(__file__).parent / "config" / "vision_guardian_state.json"
                        if vg_path.exists():
                            try:
                                cfg["vision_guardian"] = json.loads(vg_path.read_text(encoding="utf-8"))
                            except Exception as _ve:
                                print(f"[WS] Error loading vision_guardian: {_ve}")
                        
                        # Load user profile
                        up_path = Path(__file__).parent / "config" / "user_profile.json"
                        if up_path.exists():
                            try:
                                cfg["user_profile"] = json.loads(up_path.read_text(encoding="utf-8"))
                            except Exception as _upe:
                                print(f"[WS] Error loading user_profile: {_upe}")

                        # Load app registry
                        ar_path = Path(__file__).parent / "config" / "app_registry.json"
                        if ar_path.exists():
                            try:
                                cfg["app_registry"] = json.loads(ar_path.read_text(encoding="utf-8"))
                            except Exception as _are:
                                print(f"[WS] Error loading app_registry: {_are}")

                        cfg_text = json.dumps(cfg)
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "log",
                                    "value": f"config_loaded:{cfg_text}",
                                }
                            )
                        )
                except Exception as e:
                    print(f"[WS] Error loading initial config: {e}")

                # Send initial weather if available
                try:
                    from actions.weather_report import fetch_weather_data

                    data = fetch_weather_data({})
                    if not data.get("error"):
                        await websocket.send(
                            json.dumps({"type": "weather", "data": data})
                        )
                except Exception:
                    pass

                # Send initial todos
                try:
                    from actions.goals import load_goals

                    await websocket.send(
                        json.dumps({"type": "todos", "value": load_goals()})
                    )
                except Exception as e:
                    print(f"[WS] Error loading initial goals: {e}")

                # Send initial favorites
                try:
                    await websocket.send(
                        json.dumps({"type": "favorites", "value": load_favorites()})
                    )
                except Exception as e:
                    print(f"[WS] Error loading initial favorites: {e}")

                # Read messages
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type")
                        if msg_type == "command":
                            val = data.get("value", "")
                            if self.on_text_command:
                                self.on_text_command(val)
                        elif msg_type == "toggle_mute":
                            self.muted = not self.muted
                            self.broadcast(
                                {
                                    "type": "state",
                                    "value": "MUTED" if self.muted else "LISTENING",
                                }
                            )
                        elif msg_type == "media_control":
                            action = data.get("action", "")
                            try:
                                from actions.media_control import media_control

                                res = media_control({"action": action})
                                self.write_log(f"SYS: Control de Medios: {res}")
                            except Exception as e:
                                print(f"[WS] Media control error: {e}")
                        elif msg_type == "save_config":
                            config_data = data.get("config", {})
                            try:
                                cfg_dir = Path(__file__).parent / "config"
                                
                                # 1. Extract and save accessibility_config
                                if "accessibility" in config_data:
                                    accessibility_data = config_data.pop("accessibility")
                                    acc_path = cfg_dir / "accessibility_config.json"
                                    acc_path.write_text(json.dumps(accessibility_data, indent=4), encoding="utf-8")
                                    print("[WS] Accessibility config saved.")

                                # 2. Extract and save vision_guardian
                                if "vision_guardian" in config_data:
                                    vision_guardian_data = config_data.pop("vision_guardian")
                                    vg_path = cfg_dir / "vision_guardian_state.json"
                                    vg_path.write_text(json.dumps(vision_guardian_data, indent=4), encoding="utf-8")
                                    print("[WS] Vision guardian state saved.")

                                # 3. Extract and save user_profile
                                if "user_profile" in config_data:
                                    user_profile_data = config_data.pop("user_profile")
                                    up_path = cfg_dir / "user_profile.json"
                                    up_path.write_text(json.dumps(user_profile_data, indent=4), encoding="utf-8")
                                    print("[WS] User profile saved.")

                                # 4. Extract and save app_registry
                                if "app_registry" in config_data:
                                    app_registry_data = config_data.pop("app_registry")
                                    ar_path = cfg_dir / "app_registry.json"
                                    ar_path.write_text(json.dumps(app_registry_data, indent=4), encoding="utf-8")
                                    print("[WS] App registry saved.")

                                # 5. Save the rest in config.json
                                cfg_path = cfg_dir / "config.json"
                                if cfg_path.exists():
                                    cfg = json.loads(
                                        cfg_path.read_text(encoding="utf-8")
                                    )
                                    cfg.update(config_data)
                                    cfg_path.write_text(
                                        json.dumps(cfg, indent=4), encoding="utf-8"
                                    )
                                    print(
                                        f"[WS] Config saved successfully to {cfg_path}"
                                    )
                            except Exception as e:
                                print(f"[WS] Error saving config files: {e}")

                            if self.on_config_saved:
                                self.on_config_saved(config_data)
                        elif msg_type == "set_file":
                            path_val = data.get("value", "").strip()
                            self.current_file = path_val
                            self.write_log(f"SYS: Archivo cargado en el kernel: {self.current_file}")
                        elif msg_type == "get_todos":
                            from actions.goals import load_goals

                            await websocket.send(
                                json.dumps({"type": "todos", "value": load_goals()})
                            )
                        elif msg_type == "add_todo":
                            from actions.goals import load_goals, save_goals
                            import uuid

                            title = data.get("title", "").strip()
                            priority = data.get("priority", "medium").lower()
                            if title:
                                gls = load_goals()
                                gls.append(
                                    {
                                        "id": str(uuid.uuid4()),
                                        "title": title,
                                        "description": data.get(
                                            "description", ""
                                        ).strip(),
                                        "priority": priority
                                        if priority in ("high", "medium", "low")
                                        else "medium",
                                        "due_date": data.get("due_date", "").strip(),
                                        "status": "pending",
                                        "subtasks": [],
                                        "created_at": datetime.now().isoformat(),
                                        "completed_at": None,
                                    }
                                )
                                save_goals(gls)
                                self.broadcast({"type": "todos", "value": gls})
                        elif msg_type == "toggle_todo":
                            from actions.goals import load_goals, save_goals

                            todo_id = data.get("id", "")
                            gls = load_goals()
                            for g in gls:
                                if g["id"] == todo_id:
                                    g["status"] = (
                                        "completed"
                                        if g["status"] == "pending"
                                        else "pending"
                                    )
                                    if g["status"] == "completed":
                                        g[
                                            "completed_at"
                                        ] = datetime.now().isoformat()
                                        for s in g.get("subtasks", []):
                                            s["status"] = "completed"
                                    else:
                                        g["completed_at"] = None
                                    break
                            save_goals(gls)
                            self.broadcast({"type": "todos", "value": gls})
                        elif msg_type == "delete_todo":
                            from actions.goals import load_goals, save_goals

                            todo_id = data.get("id", "")
                            gls = load_goals()
                            gls = [g for g in gls if g["id"] != todo_id]
                            save_goals(gls)
                            self.broadcast({"type": "todos", "value": gls})
                        elif msg_type == "get_favorites":
                            await websocket.send(
                                json.dumps(
                                    {"type": "favorites", "value": load_favorites()}
                                )
                            )
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
                                import webbrowser

                                webbrowser.open(url)
                        elif msg_type == "list_audio_devices":
                            # Listar dispositivos de audio (micrófono y speakers) disponibles
                            devices = {"microphones": [], "speakers": []}
                            try:
                                import pyaudio
                                pa = pyaudio.PyAudio()
                                for i in range(pa.get_device_count()):
                                    info = pa.get_device_info_by_index(i)
                                    dev_entry = {
                                        "index": i,
                                        "name": info.get("name", f"Device {i}"),
                                        "channels_in": info.get("maxInputChannels", 0),
                                        "channels_out": info.get("maxOutputChannels", 0),
                                    }
                                    if info.get("maxInputChannels", 0) > 0:
                                        devices["microphones"].append(dev_entry)
                                    if info.get("maxOutputChannels", 0) > 0:
                                        devices["speakers"].append(dev_entry)
                                pa.terminate()
                            except Exception as e:
                                print(f"[WS] Error listing audio devices: {e}")
                            await websocket.send(json.dumps({"type": "audio_devices", "data": devices}))
                        elif msg_type == "list_models":
                            # Listar modelos disponibles de Gemini y OpenRouter
                            models = {"gemini": [], "openrouter": []}
                            cfg_path = Path(__file__).parent / "config" / "config.json"
                            try:
                                cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
                            except Exception:
                                cfg = {}
                            # Gemini models
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
                                    print(f"[WS] Error listing Gemini models: {e}")
                            # OpenRouter models
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
                                    print(f"[WS] Error listing OpenRouter models: {e}")
                            await websocket.send(json.dumps({"type": "models_list", "data": models}))
                        elif msg_type == "agent_status":
                            # Devolver estado de la instancia del agente
                            import os
                            status_info = {
                                "pid": os.getpid(),
                                "uptime_seconds": 0,
                                "memory_mb": 0,
                                "python_version": sys.version,
                            }
                            try:
                                proc = psutil.Process(os.getpid())
                                status_info["memory_mb"] = round(proc.memory_info().rss / 1024 / 1024, 1)
                                status_info["uptime_seconds"] = round((datetime.now() - datetime.fromtimestamp(proc.create_time())).total_seconds())
                            except Exception:
                                pass
                            await websocket.send(json.dumps({"type": "agent_status", "data": status_info}))
                        elif msg_type == "agent_kill":
                            # Kill forzado de la instancia del agente
                            self.broadcast({"type": "log", "value": "SYS: Apagando instancia de MIN..."})
                            self.broadcast({"type": "ui_control", "action": "shutdown"})
                            import os
                            os._exit(0)
                        elif msg_type == "agent_restart":
                            # Reinicio completo: lanza nuevo proceso y termina este
                            self.broadcast({"type": "log", "value": "SYS: Reiniciando MIN..."})
                            try:
                                import subprocess
                                main_py = str(Path(__file__).parent / "main.py")
                                subprocess.Popen([sys.executable, main_py], creationflags=0x00000008)  # DETACHED_PROCESS
                            except Exception as e:
                                print(f"[WS] Error restarting: {e}")
                            import os
                            os._exit(0)
                        elif msg_type == "list_browsers":
                            # Listar navegadores detectados
                            try:
                                from actions.browser_registry import detect_installed_browsers, resolve_browser_path
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
                                print(f"[WS] Error listing browsers: {e}")
                    except Exception as e:
                        print(f"[WS] Error parsing client message: {e}")
            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                self._clients.remove(websocket)
                print("[WS] Client disconnected")

        async def media_tracker():
            last_media = None
            while True:
                try:
                    if self._clients:
                        media = get_active_media()
                        if media != last_media:
                            last_media = media
                            self.broadcast(
                                {
                                    "type": "media",
                                    "app": media["app"],
                                    "title": media["title"],
                                    "artist": media["artist"],
                                }
                            )
                except Exception as e:
                    print(f"[WS Media] Error in tracker loop: {e}")
                await asyncio.sleep(2.0)

        # Run tracker in background
        asyncio.create_task(media_tracker())

        async with websockets.serve(handler, "127.0.0.1", 8765):
            print("[WS] Server running at ws://127.0.0.1:8765")
            await asyncio.Future()

    def broadcast(self, data: dict):
        if not self._clients:
            return
        msg = json.dumps(data)

        async def do_send():
            websockets_list = list(self._clients)
            if websockets_list:
                await asyncio.gather(
                    *[c.send(msg) for c in websockets_list], return_exceptions=True
                )

        if self._ws_loop:
            asyncio.run_coroutine_threadsafe(do_send(), self._ws_loop)

    def ensure_startup_shortcut(self):
        try:
            import subprocess

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
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            print("[STARTUP] Startup shortcut ensured successfully.")
        except Exception as e:
            print(f"[STARTUP] Error ensuring startup shortcut: {e}")

