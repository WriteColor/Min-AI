# -*- coding: utf-8 -*-
"""install.py — MIN AI Unified Installer.

Handles:
  - System requirements verification
  - Virtual environment creation
  - Python dependency installation
  - Vosk speech model download
  - Initial configuration
  - Desktop shortcut creation
  - Health check of critical files
"""
import os
import sys
import subprocess
import shutil
import time
import json
import urllib.request
import zipfile


# ── Colores ───────────────────────────────────────────────────────────────────
os.system("")  # Activar ANSI en Windows
PURPLE = "\033[95m"
GREEN  = "\033[92m"
YELLOW = "\033[33m"
RED    = "\033[31m"
CYAN   = "\033[96m"
RESET  = "\033[0m"


def print_banner():
    print(f"{PURPLE}======================================================================={RESET}")
    print(f"{PURPLE}                                                                       {RESET}")
    print(f"{PURPLE}                ███╗   ███╗ ██╗ ███╗   ██╗                            {RESET}")
    print(f"{PURPLE}                ████╗ ████║ ██║ ████╗  ██║                            {RESET}")
    print(f"{PURPLE}                ██╔████╔██║ ██║ ██╔██╗ ██║                            {RESET}")
    print(f"{PURPLE}                ██║╚██╔╝██║ ██║ ██║╚██╗██║                            {RESET}")
    print(f"{PURPLE}                ██║ ╚═╝ ██║ ██║ ██║ ╚████║                            {RESET}")
    print(f"{PURPLE}                ╚═╝     ╚═╝ ╚═╝ ╚═╝  ╚═══╝                            {RESET}")
    print(f"{PURPLE}                                                                       {RESET}")
    print(f"{GREEN}                 SISTEMA DE INSTALACIÓN INTELIGENTE                   {RESET}")
    print(f"{PURPLE}======================================================================={RESET}")
    print()


def main():
    print_banner()
    print("Este asistente preparará a MIN para funcionar de forma óptima.")
    print()
    print(" [1] Comenzar instalación limpia (Recomendado)")
    print(" [2] Solo verificar estado de archivos")
    print(" [3] Salir")
    print()

    try:
        opt = input("Selecciona una opción (1-3): ").strip()
    except (KeyboardInterrupt, EOFError):
        opt = "3"

    if opt == "2":
        health_check()
        input("\nPresiona Enter para salir...")
        sys.exit(0)
    elif opt != "1":
        print("\nSaliendo del instalador...")
        time.sleep(1)
        sys.exit(0)

    # ══════════════════════════════════════════════════════════════════════════
    # FASE 1: Verificación de requisitos
    # ══════════════════════════════════════════════════════════════════════════
    os.system("cls" if os.name == "nt" else "clear")
    print_banner()
    print(f"{CYAN} [FASE 1/6] — Verificando requisitos del sistema...{RESET}")
    print()

    print(f"{GREEN}[OK] Python detectado: {sys.version.split()[0]}{RESET}")

    # Limpieza de residuos antiguos
    print(f"{YELLOW}[INFO] Limpiando archivos temporales y cachés...{RESET}")

    basura_dirs = ["build", "dist"]
    for folder in basura_dirs:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
            except Exception:
                pass

    archivos_basura = ["min.log", "MIN_Beta_Installer.exe"]
    for f in os.listdir("."):
        if f.endswith(".spec") or f in archivos_basura:
            try:
                os.remove(f)
            except Exception:
                pass

    # Limpiar archivos obsoletos de versiones anteriores
    obsoletos = [
        "inspect_bento_widgets.py",
        "download_vosk.py",
        "sitecustomize.py",
        "Iniciar MIN Beta.vbs",
        "Liberar_MIN.bat",
        "Instalar_MIN.bat",
    ]
    for f in obsoletos:
        if os.path.exists(f):
            try:
                os.remove(f)
                print(f"{YELLOW}[CLEAN] Archivo obsoleto eliminado: {f}{RESET}")
            except Exception:
                pass

    # Limpiar directorio launchers/ vacío
    if os.path.exists("launchers") and os.path.isdir("launchers"):
        try:
            shutil.rmtree("launchers")
            print(f"{YELLOW}[CLEAN] Directorio obsoleto eliminado: launchers/{RESET}")
        except Exception:
            pass

    print(f"{GREEN}[OK] Limpieza completada.{RESET}")
    time.sleep(1)

    # ══════════════════════════════════════════════════════════════════════════
    # FASE 2: Entorno Virtual
    # ══════════════════════════════════════════════════════════════════════════
    os.system("cls" if os.name == "nt" else "clear")
    print_banner()
    print(f"{CYAN} [FASE 2/6] — Configurando Entorno Virtual (.venv)...{RESET}")
    print()

    if not os.path.exists(".venv"):
        print(f"{YELLOW}[INFO] Creando entorno virtual de Python limpio...{RESET}")
        try:
            subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
            print(f"{GREEN}[OK] Entorno virtual creado exitosamente.{RESET}")
        except Exception as e:
            print(f"{RED}[ERROR] No se pudo crear el entorno virtual: {e}{RESET}")
            input("Presiona Enter para salir...")
            sys.exit(1)
    else:
        print(f"{GREEN}[OK] Entorno virtual existente detectado.{RESET}")

    time.sleep(1)

    # ══════════════════════════════════════════════════════════════════════════
    # FASE 3: Instalación de dependencias Python
    # ══════════════════════════════════════════════════════════════════════════
    os.system("cls" if os.name == "nt" else "clear")
    print_banner()
    print(f"{CYAN} [FASE 3/6] — Instalando dependencias de MIN...{RESET}")
    print()
    print("Esto puede tomar unos minutos dependiendo de tu conexión a Internet.")
    print()

    venv_python = os.path.join(".venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        venv_python = sys.executable  # Fallback

    try:
        subprocess.run([venv_python, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        subprocess.run([venv_python, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print(f"{GREEN}\n[OK] Todas las dependencias se instalaron correctamente.{RESET}")
    except Exception as e:
        print(f"{RED}\n[ERROR] Ocurrió un error al instalar dependencias: {e}{RESET}")
        input("Presiona Enter para salir...")
        sys.exit(1)

    time.sleep(1)

    # ══════════════════════════════════════════════════════════════════════════
    # FASE 4: Modelo Vosk de reconocimiento de voz
    # ══════════════════════════════════════════════════════════════════════════
    os.system("cls" if os.name == "nt" else "clear")
    print_banner()
    print(f"{CYAN} [FASE 4/6] — Verificando modelo de voz Vosk...{RESET}")
    print()

    vosk_target = os.path.join("config", "vosk_model")
    if os.path.exists(vosk_target) and os.listdir(vosk_target):
        print(f"{GREEN}[OK] Modelo Vosk ya instalado en {vosk_target}{RESET}")
    else:
        print(f"{YELLOW}[INFO] Descargando modelo Vosk en Español (≈39MB)...{RESET}")
        vosk_url = "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"
        zip_path = "vosk_model_download.zip"
        extract_path = os.path.join("config", "vosk-model-small-es-0.42")

        try:
            def _progress_hook(count, block_size, total_size):
                percent = min(100, int(count * block_size * 100 / total_size)) if total_size > 0 else 0
                bar = "█" * (percent // 2) + "░" * (50 - percent // 2)
                print(f"\r  [{bar}] {percent}%", end="", flush=True)

            urllib.request.urlretrieve(vosk_url, zip_path, reporthook=_progress_hook)
            print()  # newline after progress bar

            print(f"{YELLOW}[INFO] Extrayendo modelo...{RESET}")
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall("config")

            if os.path.exists(vosk_target):
                shutil.rmtree(vosk_target)
            os.rename(extract_path, vosk_target)

            os.remove(zip_path)
            print(f"{GREEN}[OK] Modelo Vosk instalado exitosamente.{RESET}")
        except Exception as e:
            print(f"\n{RED}[ERROR] No se pudo descargar el modelo Vosk: {e}{RESET}")
            print(f"{YELLOW}[INFO] MIN funcionará sin reconocimiento de voz offline.{RESET}")
            # Limpiar archivos parciales
            for cleanup in [zip_path, extract_path]:
                if os.path.exists(cleanup):
                    try:
                        if os.path.isdir(cleanup):
                            shutil.rmtree(cleanup)
                        else:
                            os.remove(cleanup)
                    except Exception:
                        pass

    time.sleep(1)

    # ══════════════════════════════════════════════════════════════════════════
    # FASE 5: Configuración inicial
    # ══════════════════════════════════════════════════════════════════════════
    os.system("cls" if os.name == "nt" else "clear")
    print_banner()
    print(f"{CYAN} [FASE 5/6] — Configuración Inicial...{RESET}")
    print()

    config_dir = os.path.join(".", "config")
    api_keys_path = os.path.join(config_dir, "api_keys.json")
    api_keys_template = os.path.join(config_dir, "api_keys.example.json")
    rules_path = os.path.join(config_dir, "rules.json")

    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
        print(f"{GREEN}[OK] Directorio config/ creado.{RESET}")

    if not os.path.exists(api_keys_path):
        if os.path.exists(api_keys_template):
            shutil.copy2(api_keys_template, api_keys_path)
            print(f"{GREEN}[OK] Archivo api_keys.json creado desde plantilla.{RESET}")
        else:
            default_config = {
                "gemini_api_key": "",
                "openrouter_api_key": "",
                "min_voice": "Aoede",
                "gpu_acceleration": True,
                "mic_device": 0,
                "speaker_device": "",
                "spotify_client_id": "",
                "spotify_client_secret": "",
                "spotify_redirect_uri": "http://127.0.0.1:8888/callback",
                "browser_preference": "auto",
                "browser_paths": {
                    "chrome": "", "brave": "", "edge": "",
                    "firefox": "", "opera": "", "opera_gx": "",
                    "vivaldi": "", "tor": ""
                },
                "location_mode": "system",
                "location_city": "",
                "location_lat": "",
                "location_lon": "",
                "timezone": "America/Tegucigalpa",
                "language": "es-ES",
                "live_model": "",
                "vision_model": "",
                "openrouter_default_model": "google/gemini-2.5-flash",
            }
            with open(api_keys_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4)
            print(f"{GREEN}[OK] Archivo api_keys.json creado con valores por defecto.{RESET}")
        print(f"{YELLOW}[INFO] Configura tus API Keys desde el panel de Configuración en la UI.{RESET}")
    else:
        # Migrate: remove deprecated fields from existing config
        try:
            with open(api_keys_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            deprecated = ["ui_mode", "min_theme", "os_system", "camera_index",
                          "spk_device", "chrome_google_profile", "chrome_exe_path",
                          "tmdb_api_key", "thinking_sound"]
            removed = [k for k in deprecated if k in cfg]
            for k in removed:
                del cfg[k]
            if removed:
                with open(api_keys_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=4)
                print(f"{YELLOW}[INFO] Campos obsoletos eliminados de api_keys.json: {', '.join(removed)}{RESET}")
        except Exception:
            pass
        print(f"{GREEN}[OK] Archivo api_keys.json existente detectado.{RESET}")

    if not os.path.exists(rules_path):
        with open(rules_path, "w", encoding="utf-8") as f:
            json.dump({"rules": []}, f, indent=4)
        print(f"{GREEN}[OK] Archivo rules.json creado.{RESET}")
    else:
        print(f"{GREEN}[OK] Archivo rules.json existente detectado.{RESET}")

    time.sleep(1)

    # ══════════════════════════════════════════════════════════════════════════
    # FASE 6: Acceso directo y verificación final
    # ══════════════════════════════════════════════════════════════════════════
    os.system("cls" if os.name == "nt" else "clear")
    print_banner()
    print(f"{CYAN} [FASE 6/6] — Accesos Directos y Verificación Final...{RESET}")
    print()

    # Desktop shortcut pointing to MIN.bat
    try:
        current_dir = os.getcwd()
        icon_path = os.path.join(current_dir, "assets", "min_icono.ico")
        target_bat = os.path.join(current_dir, "MIN.bat")

        if os.path.exists(target_bat):
            ps_cmd = (
                f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut("
                f"([System.Environment]::GetFolderPath('Desktop')+'\\MIN AI.lnk'));"
                f"$s.TargetPath='{target_bat}';"
                f"$s.WorkingDirectory='{current_dir}';"
                f"$s.IconLocation='{icon_path}';"
                f"$s.Description='Lanzador de MIN AI';"
                f"$s.Save()"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                check=True,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            )
            print(f"{GREEN}[OK] Acceso directo 'MIN AI' creado en el Escritorio.{RESET}")
        else:
            print(f"{YELLOW}[WARN] MIN.bat no encontrado, no se pudo crear acceso directo.{RESET}")
    except Exception as e:
        print(f"{YELLOW}[ADVERTENCIA] No se pudo crear el acceso directo: {e}{RESET}")

    print()

    # Health check
    health_check()

    time.sleep(1)

    # ══════════════════════════════════════════════════════════════════════════
    # Pantalla Final
    # ══════════════════════════════════════════════════════════════════════════
    print()
    print(f"{GREEN}======================================================================={RESET}")
    print(f"{GREEN}     ¡INSTALACIÓN Y CONFIGURACIÓN COMPLETADA CON ÉXITO!{RESET}")
    print(f"{GREEN}======================================================================={RESET}")
    print()
    print("MIN está listo para servirte.")
    print("Configura tus API Keys desde la interfaz de Configuración al iniciar.")
    print()
    print(" [1] Iniciar MIN ahora mismo")
    print(" [2] Salir")
    print()

    try:
        launch_opt = input("Selecciona una opción (1-2): ").strip()
    except (KeyboardInterrupt, EOFError):
        launch_opt = "2"

    if launch_opt == "1":
        print("Iniciando MIN...")
        try:
            bat_path = os.path.join(os.getcwd(), "MIN.bat")
            if os.path.exists(bat_path):
                os.startfile(bat_path)
            else:
                # Fallback — run directly
                py = os.path.join(".venv", "Scripts", "pythonw.exe")
                if not os.path.exists(py):
                    py = os.path.join(".venv", "Scripts", "python.exe")
                subprocess.Popen([py, "main.py"])
        except Exception as e:
            print(f"{RED}[ERROR] No se pudo iniciar MIN: {e}{RESET}")

    print(f"\nGracias por usar el instalador de MIN AI.")
    time.sleep(2)


def health_check():
    """Verify critical files and show status."""
    print(f"{CYAN}--- Verificación de Archivos Críticos ---{RESET}")

    checks = [
        ("main.py",              True),
        ("ui.py",                True),
        ("config/api_keys.json", True),
        ("config/vosk_model",    False),
        (".venv",                True),
        ("Min-UI/dist",       False),
        ("MIN.bat",              True),
        ("requirements.txt",     True),
        ("core/prompt.txt",      True),
    ]

    all_ok = True
    for path, critical in checks:
        exists = os.path.exists(path)
        if exists:
            print(f"  {GREEN}[✓] {path}{RESET}")
        elif critical:
            print(f"  {RED}[✗] {path} — FALTANTE (CRÍTICO){RESET}")
            all_ok = False
        else:
            print(f"  {YELLOW}[–] {path} — Opcional{RESET}")

    # Check API keys
    api_path = os.path.join("config", "api_keys.json")
    if os.path.exists(api_path):
        try:
            cfg = json.loads(open(api_path, encoding="utf-8").read())
            gemini = bool(cfg.get("gemini_api_key", "").strip())
            openrouter = bool(cfg.get("openrouter_api_key", "").strip())
            if gemini and openrouter:
                print(f"  {GREEN}[✓] API Keys configuradas{RESET}")
            else:
                missing = []
                if not gemini:
                    missing.append("Gemini")
                if not openrouter:
                    missing.append("OpenRouter")
                print(f"  {YELLOW}[–] API Keys faltantes: {', '.join(missing)}{RESET}")
        except Exception:
            print(f"  {YELLOW}[–] No se pudo leer api_keys.json{RESET}")

    if all_ok:
        print(f"\n  {GREEN}Estado general: ✓ Todo correcto{RESET}")
    else:
        print(f"\n  {RED}Estado general: ✗ Hay archivos críticos faltantes{RESET}")


if __name__ == "__main__":
    main()
