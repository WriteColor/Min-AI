# -*- coding: utf-8 -*-
"""git_control.py — Safe Git repository control client."""
import subprocess
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def _run_git_cmd(args: list[str]) -> tuple[int, str]:
    """Ejecuta un comando Git en el directorio base del proyecto y devuelve el código y la salida."""
    try:
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0" # Previene bloqueos por solicitud de credenciales
        
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=15,
            cwd=BASE_DIR,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        
        output = (result.stdout + "\n" + result.stderr).strip()
        return result.returncode, output
    except Exception as e:
        return -1, f"Error al ejecutar git: {str(e)}"

def git_control(parameters: dict, player=None) -> str:
    """
    Control de control de versiones Git para el repositorio local de MIN.
    Acciones: status | log | branch | add | commit | push | pull
    """
    action = parameters.get("action", "status").lower().strip()
    message = parameters.get("message", "MIN auto-commit").strip()
    files = parameters.get("files", ".").strip()

    # Sanitizar entrada de archivos para evitar inyección de comandos
    if ";" in files or "&" in files or "|" in files:
        return "Error: Caracteres inválidos detectados en los parámetros de archivos."

    if action == "status":
        code, out = _run_git_cmd(["status"])
        return f"Git Status (Código {code}):\n\n{out}"

    elif action == "log":
        code, out = _run_git_cmd(["log", "-n", "5", "--oneline"])
        return f"Últimos 5 commits:\n\n{out}"

    elif action == "branch":
        code, out = _run_git_cmd(["branch", "-a"])
        return f"Ramas del repositorio:\n\n{out}"

    elif action == "add":
        # Separar por espacios o comas
        file_list = [f.strip() for f in re.split(r'[,\s]+', files) if f.strip()]
        if not file_list:
            file_list = ["."]
        code, out = _run_git_cmd(["add"] + file_list)
        if code == 0:
            return f"✅ Archivos agregados al área de preparación (stage): {', '.join(file_list)}"
        return f"❌ Fallo al agregar archivos:\n{out}"

    elif action == "commit":
        if not message:
            return "Error: Se requiere un mensaje de commit ('message')."
        code, out = _run_git_cmd(["commit", "-m", message])
        if code == 0:
            return f"✅ Commit creado exitosamente con el mensaje: '{message}'."
        return f"⚠️ Commit no creado (tal vez no hay cambios en el stage):\n{out}"

    elif action == "push":
        if player:
            player.write_log("Subiendo cambios al servidor remoto (git push)...")
        code, out = _run_git_cmd(["push"])
        if code == 0:
            return "✅ Cambios subidos (pushed) al repositorio remoto exitosamente."
        return f"❌ Error al subir cambios:\n{out}"

    elif action == "pull":
        if player:
            player.write_log("Descargando cambios del servidor remoto (git pull)...")
        code, out = _run_git_cmd(["pull"])
        if code == 0:
            return "✅ Repositorio actualizado con éxito (pulled)."
        return f"❌ Error al descargar cambios:\n{out}"

    else:
        return f"Acción git '{action}' no es compatible con el controlador de repositorio."
