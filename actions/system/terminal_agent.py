# -*- coding: utf-8 -*-
"""terminal_agent.py — Ejecución segura de comandos con validación multinivel."""
import subprocess
import os
import re
from datetime import datetime
from pathlib import Path

# ── Patrones peligrosos expandidos (29 patrones) ──────────────────────────────
DANGEROUS_PATTERNS = [
    r"rmdir\s+.*(/s|/q)",           # Recursive quiet directory deletion (CMD)
    r"del\s+.*(/f|/q|/s)",          # Force/quiet/recursive file deletion (CMD)
    r"rm\s+-r",                      # Recursive remove (Git Bash/WSL)
    r"rm\s+-f",                      # Force remove
    r"remove-item\s+.*(-recurse|-force)",  # PowerShell recursive/force deletion
    r"format\s+[a-z]:",              # Format disk partitions
    r"format-volume",                # PowerShell Format-Volume cmdlet
    r"diskpart",                     # Disk partition tool
    r"mkfs",                         # Linux partition formatting
    r"dd\s+if=",                     # Linux dd write block copy
    r"registry\s+delete",            # Delete registry keys
    r"reg\s+delete",                 # Registry deletion
    r"rd\s+.*(/s|/q)",              # Alternate directory deletion
    r"net\s+user\s+.*(/add|/delete)", # Modifying users
    r"bootsect",                     # Modifying boot files
    r"attrib\s+-r\s+-s\s+-h",       # Wiping system file attributes
    r"Invoke-Expression",            # PS arbitrary code execution
    r"\biex\b",                      # PS alias for Invoke-Expression
    r"Invoke-WebRequest.*\|.*iex",   # Download and execute
    r"Start-Process.*-Verb\s+RunAs", # PS privilege escalation
    r"\bschtasks\s+/create",         # Scheduled task creation
    r"\bwmic\s+.*delete",            # WMI object deletion
    r"\bcipher\s+/w",               # Secure wipe of free space
    r"\bbcdedit\b",                  # Boot configuration editor
    r"Set-ExecutionPolicy\s+Unrestricted",  # PS execution policy bypass
    r"\bnetsh\s+advfirewall.*off",   # Disable firewall
    r"\bpowershell\s+-e\s",          # Base64-encoded PS commands
    r"curl\s+.*\|\s*(ba)?sh",        # Download and pipe to shell
    r"wget\s+.*\|\s*(ba)?sh",        # Download and pipe to shell
]

# ── Directorios restringidos para working_directory ───────────────────────────
RESTRICTED_DIRS = [
    r"C:\Windows",
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    r"C:\$Recycle.Bin",
]


def _log_security_event(command: str, blocked: bool, reason: str = ""):
    """Registra eventos de seguridad en archivo de auditoría."""
    try:
        log_dir = Path(__file__).resolve().parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "security_audit.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "BLOCKED" if blocked else "EXECUTED"
        entry = f"[{timestamp}] [{status}] {command[:200]}"
        if reason:
            entry += f" | Reason: {reason}"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception:
        pass


def is_command_safe(command: str) -> tuple[bool, str]:
    """Valida que el comando no contenga operaciones destructivas peligrosas."""
    cmd_clean = command.strip()
    cmd_lower = cmd_clean.lower()

    # Check against dangerous regex patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd_lower, re.IGNORECASE):
            reason = f"Seguridad: Se bloqueó el comando porque contiene un patrón potencialmente destructivo ('{pattern}')."
            _log_security_event(cmd_clean, blocked=True, reason=pattern)
            return False, reason

    return True, ""


def _is_restricted_directory(working_dir: str | None) -> tuple[bool, str]:
    """Verifica si el directorio de trabajo está en una zona restringida."""
    if not working_dir:
        return False, ""
    wd = os.path.abspath(working_dir).rstrip("\\")
    for restricted in RESTRICTED_DIRS:
        if wd.lower().startswith(restricted.lower()):
            return True, f"Seguridad: No se permite ejecutar comandos en el directorio restringido '{restricted}'."
    return False, ""


def terminal_agent(parameters: dict, player=None) -> str:
    """
    Ejecuta comandos de forma segura en la terminal de Windows (PowerShell o CMD).
    Valida previamente que el comando no contenga operaciones destructivas.
    """
    command = parameters.get("command", "").strip()
    shell_type = parameters.get("shell", "powershell").lower()
    timeout_sec = int(parameters.get("timeout", 120))
    working_dir = parameters.get("working_directory", None)

    if not command:
        return "No se proporcionó ningún comando para ejecutar."

    # Validar seguridad del comando
    is_safe, error_msg = is_command_safe(command)
    if not is_safe:
        if player:
            player.write_log(f"⚠️ {error_msg}")
        return error_msg

    # Validar directorio de trabajo
    restricted, dir_msg = _is_restricted_directory(working_dir)
    if restricted:
        _log_security_event(command, blocked=True, reason=dir_msg)
        if player:
            player.write_log(f"⚠️ {dir_msg}")
        return dir_msg

    # Limitar timeout a un rango razonable
    timeout_sec = max(10, min(timeout_sec, 600))

    try:
        if shell_type == "cmd":
            cmd_args = ["cmd", "/c", command]
        else:
            # PowerShell por defecto — UTF-8 forzado para salida limpia
            cmd_args = [
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-Command",
                f"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; {command}"
            ]

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        if player:
            player.write_log(f"💻 Ejecutando comando terminal: {command[:80]}...")

        result = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=working_dir,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
            env=env,
        )

        output = result.stdout.strip()
        error = result.stderr.strip()

        # Log de auditoría para comando ejecutado exitosamente
        _log_security_event(command, blocked=False)

        if result.returncode == 0:
            if output:
                if len(output) > 3000:
                    output = output[:3000] + "\n...[Salida truncada]"
                return f"Comando ejecutado exitosamente:\n{output}"
            else:
                return "Comando ejecutado exitosamente (sin salida)."
        else:
            combined = ""
            if error:
                combined += f"STDERR:\n{error}\n"
            if output:
                combined += f"STDOUT:\n{output}"
            if not combined:
                combined = "(sin salida de error)"
            return f"El comando finalizó con código {result.returncode}:\n{combined}"

    except subprocess.TimeoutExpired:
        return f"Error: El comando excedió el timeout de {timeout_sec} segundos y fue terminado."
    except FileNotFoundError:
        return f"Error: No se encontró el ejecutable para shell '{shell_type}'."
    except Exception as e:
        return f"Excepción ejecutando terminal: {str(e)}"
