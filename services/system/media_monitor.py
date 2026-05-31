import psutil
try:
    import win32gui
    import win32process
except ImportError:
    pass

def get_active_media():
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
