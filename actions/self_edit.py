# -*- coding: utf-8 -*-
"""
self_edit.py — Permite a MIN editar sus propios archivos de código fuente de forma segura.
Incluye validación estricta de sintaxis con py_compile y backups automáticos con rollbacks.
"""
import os
import shutil
import difflib
import py_compile
import tempfile
from pathlib import Path
from datetime import datetime
import re as _re

# Raíz del proyecto MIN
MIN_ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = MIN_ROOT / "backups"

# ── Archivos protegidos por seguridad multinivel ──────────────────────────────
PROTECTED_FILES = [
    r"core[/\\]prompt\.txt",
    r"actions[/\\]terminal_agent\.py",
    r"actions[/\\]self_edit\.py",
    r"config[/\\]api_keys\.json",
]

def _is_protected(file_path: str) -> bool:
    """Verifica si un archivo está en la lista de protección de seguridad multinivel."""
    normalized = file_path.replace("\\", "/")
    for pattern in PROTECTED_FILES:
        if _re.search(pattern, normalized):
            return True
    return False

def _ensure_backup_dir():
    BACKUP_DIR.mkdir(exist_ok=True)

def _make_backup(file_path: Path) -> str:
    """Crea una copia de seguridad del archivo antes de editarlo."""
    _ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    relative = file_path.relative_to(MIN_ROOT)
    safe_name = str(relative).replace(os.sep, "__").replace("/", "__")
    backup_name = f"{safe_name}.{timestamp}.bak"
    backup_path = BACKUP_DIR / backup_name
    shutil.copy2(file_path, backup_path)
    return str(backup_path)

def _resolve_path(file_ref: str) -> Path:
    """
    Resuelve una referencia de archivo relativa al proyecto MIN.
    Solo permite editar archivos dentro del directorio del proyecto.
    """
    p = Path(file_ref)
    if p.is_absolute():
        try:
            p.relative_to(MIN_ROOT)
            return p
        except ValueError:
            raise ValueError(
                f"Ruta fuera del proyecto MIN. Solo se pueden editar archivos dentro de: {MIN_ROOT}"
            )
    resolved = (MIN_ROOT / p).resolve()
    try:
        resolved.relative_to(MIN_ROOT)
    except ValueError:
        raise ValueError(f"Ruta resuelta fuera del proyecto: {resolved}")
    return resolved

def validate_syntax(code_content: str, file_name: str) -> tuple[bool, str]:
    """Compila el contenido del código usando py_compile para asegurar que no contenga errores de sintaxis."""
    if not file_name.endswith(".py"):
        return True, "" # Solo validar archivos de Python
    try:
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as temp_file:
            temp_file.write(code_content)
            temp_file_name = temp_file.name
        try:
            py_compile.compile(temp_file_name, doraise=True)
            return True, ""
        finally:
            if os.path.exists(temp_file_name):
                os.remove(temp_file_name)
    except py_compile.PyCompileError as e:
        return False, f"Fallo de compilación de sintaxis Python:\n{str(e)}"
    except Exception as e:
        return False, f"Excepción durante verificación de sintaxis: {str(e)}"

def self_edit(parameters: dict, player=None) -> str:
    """
    Auto-edición de código de MIN.
    Acciones: read_file, edit_file, append_file, create_file, list_backups, restore_backup
    Valida sintaxis en archivos .py antes de aplicar cambios para evitar crashes.
    """
    action = parameters.get("action", "").lower()
    file_ref = parameters.get("file", "")
    
    # ── READ ──────────────────────────────────────────────────────────────
    if action == "read_file":
        if not file_ref:
            return "Error: Se requiere 'file' para leer (ej: 'main.py', 'core/prompt.txt')."
        try:
            fp = _resolve_path(file_ref)
            if not fp.exists():
                return f"Error: El archivo '{file_ref}' no existe."
            content = fp.read_text(encoding="utf-8")
            lines = content.split("\n")
            if len(lines) > 200:
                numbered = "\n".join(f"{i+1}: {l}" for i, l in enumerate(lines[:200]))
                return (
                    f"Archivo '{file_ref}' ({len(lines)} líneas). Mostrando primeras 200:\n\n"
                    f"{numbered}\n\n... [{len(lines) - 200} líneas más]"
                )
            numbered = "\n".join(f"{i+1}: {l}" for i, l in enumerate(lines))
            return f"Archivo '{file_ref}' ({len(lines)} líneas):\n\n{numbered}"
        except Exception as e:
            return f"Error leyendo archivo: {e}"

    # ── EDIT (buscar y reemplazar) ────────────────────────────────────────
    elif action == "edit_file":
        if not file_ref:
            return "Error: Se requiere 'file'."
        if _is_protected(file_ref):
            return f"⛔ SEGURIDAD: El archivo '{file_ref}' está protegido por el sistema de seguridad multinivel y no puede ser modificado."
        target = parameters.get("target", "")
        replacement = parameters.get("replacement", "")
        if not target:
            return "Error: Se requiere 'target' (el texto exacto a buscar y reemplazar)."

        try:
            fp = _resolve_path(file_ref)
            if not fp.exists():
                return f"Error: El archivo '{file_ref}' no existe."

            content = fp.read_text(encoding="utf-8")
            
            if target not in content:
                return (
                    f"Error: No se encontró el texto 'target' en '{file_ref}'. "
                    f"Asegúrate de que sea exacto (incluyendo espacios e indentación)."
                )

            count = content.count(target)
            new_content = content.replace(target, replacement, 1)

            # Validar sintaxis antes de aplicar cambios
            is_valid, err_msg = validate_syntax(new_content, fp.name)
            if not is_valid:
                return f"Edición cancelada: {err_msg}"
            
            # Crear backup antes de editar
            backup_path = _make_backup(fp)
            fp.write_text(new_content, encoding="utf-8")

            # Generar diff
            old_lines = content.splitlines(keepends=True)
            new_lines = new_content.splitlines(keepends=True)
            diff = list(difflib.unified_diff(old_lines, new_lines, n=2))
            diff_str = "".join(diff[:30])
            if len(diff) > 30:
                diff_str += "\n... [diff truncado]"

            result = (
                f"✅ Archivo '{file_ref}' editado exitosamente.\n"
                f"Backup guardado en: {backup_path}\n"
                f"Ocurrencias encontradas: {count} (se reemplazó la primera)\n"
            )
            if diff_str:
                result += f"\nDiff:\n{diff_str}"
            return result

        except Exception as e:
            return f"Error editando archivo: {e}"

    # ── APPEND ────────────────────────────────────────────────────────────
    elif action == "append_file":
        if not file_ref:
            return "Error: Se requiere 'file'."
        if _is_protected(file_ref):
            return f"⛔ SEGURIDAD: El archivo '{file_ref}' está protegido por el sistema de seguridad multinivel y no puede ser modificado."
        content_to_add = parameters.get("content", "")
        if not content_to_add:
            return "Error: Se requiere 'content' (el texto a agregar al final del archivo)."

        try:
            fp = _resolve_path(file_ref)
            if not fp.exists():
                return f"Error: El archivo '{file_ref}' no existe."

            content = fp.read_text(encoding="utf-8")
            new_content = content + content_to_add

            # Validar sintaxis
            is_valid, err_msg = validate_syntax(new_content, fp.name)
            if not is_valid:
                return f"Adición cancelada: {err_msg}"

            backup_path = _make_backup(fp)
            fp.write_text(new_content, encoding="utf-8")

            return (
                f"✅ Contenido agregado al final de '{file_ref}'.\n"
                f"Backup: {backup_path}"
            )
        except Exception as e:
            return f"Error agregando contenido: {e}"

    # ── CREATE ────────────────────────────────────────────────────────────
    elif action == "create_file":
        if not file_ref:
            return "Error: Se requiere 'file' (ruta relativa al proyecto)."
        if _is_protected(file_ref):
            return f"⛔ SEGURIDAD: El archivo '{file_ref}' está protegido por el sistema de seguridad multinivel y no puede ser modificado."
        content_new = parameters.get("content", "")

        try:
            fp = _resolve_path(file_ref)
            
            # Validar sintaxis
            is_valid, err_msg = validate_syntax(content_new, fp.name)
            if not is_valid:
                return f"Creación cancelada: {err_msg}"

            if fp.exists():
                backup_path = _make_backup(fp)
                fp.write_text(content_new, encoding="utf-8")
                return (
                    f"✅ Archivo '{file_ref}' sobrescrito (backup: {backup_path})."
                )
            else:
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text(content_new, encoding="utf-8")
                return f"✅ Archivo '{file_ref}' creado exitosamente."
        except Exception as e:
            return f"Error creando archivo: {e}"

    # ── LIST BACKUPS ──────────────────────────────────────────────────────
    elif action == "list_backups":
        _ensure_backup_dir()
        backups = sorted(BACKUP_DIR.glob("*.bak"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not backups:
            return "No hay backups guardados."
        lines = [f"Backups disponibles ({len(backups)}):"]
        for b in backups[:20]:
            size_kb = b.stat().st_size / 1024
            lines.append(f"  - {b.name} ({size_kb:.1f} KB)")
        if len(backups) > 20:
            lines.append(f"  ... y {len(backups) - 20} más")
        return "\n".join(lines)

    # ── RESTORE BACKUP ────────────────────────────────────────────────────
    elif action == "restore_backup":
        backup_name = parameters.get("backup_name", "")
        if not backup_name:
            return "Error: Se requiere 'backup_name' (nombre del archivo .bak a restaurar)."

        _ensure_backup_dir()
        backup_file = BACKUP_DIR / backup_name
        if not backup_file.exists():
            return f"Error: Backup '{backup_name}' no encontrado."

        parts = backup_name.rsplit(".", 3)
        if len(parts) < 3:
            return "Error: Formato de nombre de backup no reconocido."
        
        original_rel = parts[0].replace("__", os.sep)
        original_path = MIN_ROOT / original_rel

        try:
            # Backup del estado actual antes de restaurar
            if original_path.exists():
                _make_backup(original_path)
            shutil.copy2(backup_file, original_path)
            return f"✅ Backup '{backup_name}' restaurado exitosamente a '{original_rel}'."
        except Exception as e:
            return f"Error restaurando backup: {e}"

    # ── LIST FILES ────────────────────────────────────────────────────────
    elif action == "list_files":
        directory = parameters.get("directory", ".")
        try:
            dp = _resolve_path(directory)
            if not dp.is_dir():
                return f"Error: '{directory}' no es un directorio."
            
            items = sorted(dp.iterdir())
            lines = [f"Contenido de '{directory}/' ({len(items)} items):"]
            for item in items:
                if item.name.startswith(".") and item.name not in [".gitignore"]:
                    continue
                if item.is_dir():
                    lines.append(f"  📁 {item.name}/")
                else:
                    size_kb = item.stat().st_size / 1024
                    lines.append(f"  📄 {item.name} ({size_kb:.1f} KB)")
            return "\n".join(lines)
        except Exception as e:
            return f"Error listando archivos: {e}"

    else:
        return (
            f"Acción '{action}' no reconocida. Acciones disponibles:\n"
            "- read_file: Leer un archivo del proyecto\n"
            "- edit_file: Buscar y reemplazar texto en un archivo\n"
            "- append_file: Agregar contenido al final de un archivo\n"
            "- create_file: Crear o sobrescribir un archivo\n"
            "- list_files: Listar archivos de un directorio\n"
            "- list_backups: Ver backups disponibles\n"
            "- restore_backup: Restaurar un backup anterior"
        )
