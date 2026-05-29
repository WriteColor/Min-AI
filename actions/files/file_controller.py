# -*- coding: utf-8 -*-
"""file_controller.py — Advanced file controller with comprehensive CRUD operations and safe deletions."""
import os
import shutil
import re
from pathlib import Path
from datetime import datetime

# Try to import send2trash, if not available fall back to standard remove/rmdir
try:
    from send2trash import send2trash
except ImportError:
    send2trash = None

def _resolve_shortcut(shortcut: str) -> Path:
    """Resuelve alias estándar a sus correspondientes directorios absolutos del usuario."""
    s = shortcut.lower().strip()
    home = Path.home()
    if s in ("desktop", "escritorio"):
        return home / "Desktop"
    elif s in ("downloads", "descargas"):
        return home / "Downloads"
    elif s in ("documents", "documentos"):
        return home / "Documents"
    elif s in ("pictures", "imagenes", "imágenes"):
        return home / "Pictures"
    elif s in ("music", "musica", "música"):
        return home / "Music"
    elif s in ("home", "usuario"):
        return home
    return Path(shortcut).resolve()

def file_controller(parameters: dict, player=None) -> str:
    """
    Control avanzado del sistema de archivos.
    Acciones: list | create_file | create_folder | delete | move | copy | rename | read | write | edit | find | disk_usage
    """
    action = parameters.get("action", "").lower().strip()
    path_str = parameters.get("path", "").strip()
    dest_str = parameters.get("destination", "").strip()
    new_name = parameters.get("new_name", "").strip()
    content = parameters.get("content", "")
    search_name = parameters.get("name", "").strip()
    extension = parameters.get("extension", "").strip()
    old_text = parameters.get("old_text", "")
    new_text = parameters.get("new_text", "")
    edit_mode = parameters.get("mode", "replace").lower().strip() # replace, append, prepend, overwrite

    if not action:
        return "Error: Se requiere especificar la acción ('action')."

    # --- 1. RESOLVER RUTA PRINCIPAL ---
    target_path = None
    if path_str:
        try:
            target_path = _resolve_shortcut(path_str)
        except Exception as e:
            return f"Error al resolver la ruta '{path_str}': {e}"
    else:
        # Por defecto usar el directorio del usuario
        target_path = Path.home()

    # --- ACCIONES ---

    # ── LIST ──────────────────────────────────────────────────────────────
    if action == "list":
        if not target_path.exists() or not target_path.is_dir():
            return f"Error: La ruta '{target_path}' no existe o no es un directorio."
        try:
            lines = [f"📁 Contenido del directorio '{target_path.name}':"]
            items = sorted(target_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            for item in items[:40]: # Limitar a 40 elementos en consola
                if item.name.startswith("."):
                    continue
                if item.is_dir():
                    lines.append(f"  📁 {item.name}/")
                else:
                    size_kb = item.stat().st_size / 1024
                    lines.append(f"  📄 {item.name} ({size_kb:.1f} KB)")
            if len(items) > 40:
                lines.append(f"  ... y {len(items)-40} elementos más.")
            return "\n".join(lines)
        except Exception as e:
            return f"Error al listar archivos: {e}"

    # ── CREATE FILE ───────────────────────────────────────────────────────
    elif action == "create_file":
        if not path_str:
            return "Error: Se requiere 'path' indicando dónde crear el archivo (incluyendo nombre y extensión)."
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")
            return f"✅ Archivo creado exitosamente en: {target_path}"
        except Exception as e:
            return f"Error al crear archivo: {e}"

    # ── CREATE FOLDER ─────────────────────────────────────────────────────
    elif action == "create_folder":
        if not path_str:
            return "Error: Se requiere 'path' indicando el nombre de la carpeta a crear."
        try:
            target_path.mkdir(parents=True, exist_ok=True)
            return f"✅ Carpeta creada exitosamente en: {target_path}"
        except Exception as e:
            return f"Error al crear carpeta: {e}"

    # ── DELETE (Seguro, a papelera de reciclaje) ──────────────────────────
    elif action == "delete":
        if not path_str or not target_path.exists():
            return f"Error: El archivo o carpeta '{path_str}' no existe."
        try:
            if send2trash:
                send2trash(str(target_path))
                return f"✅ '{target_path.name}' movido a la papelera de reciclaje de Windows."
            else:
                # Fallback destructivo si no está instalado send2trash
                if target_path.is_dir():
                    shutil.rmtree(target_path)
                else:
                    target_path.unlink()
                return f"⚠️ '{target_path.name}' eliminado permanentemente (send2trash no disponible)."
        except Exception as e:
            return f"Error al eliminar: {e}"

    # ── MOVE ──────────────────────────────────────────────────────────────
    elif action == "move":
        if not path_str or not dest_str:
            return "Error: Se requieren 'path' (origen) y 'destination' (destino) para mover."
        try:
            dest_path = _resolve_shortcut(dest_str)
            if dest_path.is_dir():
                dest_file = dest_path / target_path.name
            else:
                dest_file = dest_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                
            shutil.move(str(target_path), str(dest_file))
            return f"✅ Movido '{target_path.name}' exitosamente a: {dest_file}"
        except Exception as e:
            return f"Error al mover: {e}"

    # ── COPY ──────────────────────────────────────────────────────────────
    elif action == "copy":
        if not path_str or not dest_str:
            return "Error: Se requieren 'path' (origen) y 'destination' (destino) para copiar."
        try:
            dest_path = _resolve_shortcut(dest_str)
            if dest_path.is_dir():
                dest_file = dest_path / target_path.name
            else:
                dest_file = dest_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                
            if target_path.is_dir():
                shutil.copytree(str(target_path), str(dest_file))
            else:
                shutil.copy2(str(target_path), str(dest_file))
            return f"✅ Copiado '{target_path.name}' exitosamente a: {dest_file}"
        except Exception as e:
            return f"Error al copiar: {e}"

    # ── RENAME ────────────────────────────────────────────────────────────
    elif action == "rename":
        if not path_str or not new_name:
            return "Error: Se requieren 'path' (archivo actual) y 'new_name' (nuevo nombre)."
        try:
            new_path = target_path.parent / new_name
            target_path.rename(new_path)
            return f"✅ Renombrado '{target_path.name}' a '{new_name}' exitosamente."
        except Exception as e:
            return f"Error al renombrar: {e}"

    # ── READ ──────────────────────────────────────────────────────────────
    elif action == "read":
        if not target_path.exists() or not target_path.is_file():
            return f"Error: El archivo '{target_path}' no existe o no es un archivo válido."
        try:
            txt = target_path.read_text(encoding="utf-8", errors="replace")
            # Truncar salida larga para evitar desbordar el contexto de la IA
            if len(txt) > 5000:
                txt = txt[:5000] + "\n... [Contenido truncado]"
            return f"Contenido de '{target_path.name}':\n\n{txt}"
        except Exception as e:
            return f"Error al leer archivo: {e}"

    # ── WRITE ─────────────────────────────────────────────────────────────
    elif action == "write":
        if not path_str:
            return "Error: Se requiere 'path' para escribir en el archivo."
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")
            return f"✅ Contenido escrito en '{target_path.name}' con éxito."
        except Exception as e:
            return f"Error al escribir: {e}"

    # ── EDIT (Buscar y reemplazar / Modificar) ────────────────────────────
    elif action == "edit":
        if not target_path.exists() or not target_path.is_file():
            return f"Error: El archivo '{target_path}' no existe o no es válido."
        try:
            orig = target_path.read_text(encoding="utf-8", errors="replace")
            if edit_mode == "replace":
                if not old_text:
                    return "Error: Para editar en modo 'replace' se requiere especificar 'old_text'."
                if old_text not in orig:
                    return f"Error: No se encontró el texto exacto a reemplazar ('old_text') en {target_path.name}."
                new_content = orig.replace(old_text, new_text, 1)
            elif edit_mode == "append":
                new_content = orig + new_text
            elif edit_mode == "prepend":
                new_content = new_text + orig
            elif edit_mode == "overwrite":
                new_content = new_text
            else:
                return f"Modo de edición '{edit_mode}' no soportado."
                
            target_path.write_text(new_content, encoding="utf-8")
            return f"✅ Archivo '{target_path.name}' editado exitosamente en modo '{edit_mode}'."
        except Exception as e:
            return f"Error al editar archivo: {e}"

    # ── FIND (Búsqueda recursiva por patrón/extensión) ─────────────────────
    elif action == "find":
        # Búsqueda en carpetas del usuario
        lines = [f"🔍 Resultados de búsqueda en '{target_path.name}' matching name='{search_name}', ext='{extension}':"]
        found_count = 0
        try:
            # os.walk para escaneo recursivo rápido
            for root, dirs, files in os.walk(target_path):
                # Saltar carpetas ocultas
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for f in files:
                    if f.startswith("."):
                        continue
                    
                    match_name = not search_name or search_name.lower() in f.lower()
                    match_ext = not extension or f.lower().endswith(extension.lower())
                    
                    if match_name and match_ext:
                        full_p = Path(root) / f
                        size_kb = full_p.stat().st_size / 1024
                        lines.append(f"  - '{full_p.relative_to(target_path)}' ({size_kb:.1f} KB)")
                        found_count += 1
                        if found_count >= 30: # Límite de resultados
                            lines.append("  ... [Demasiados resultados, truncando lista]")
                            break
                if found_count >= 30:
                    break
            if found_count == 0:
                return f"No se encontró ningún archivo que coincida con la búsqueda en '{target_path.name}'."
            return "\n".join(lines)
        except Exception as e:
            return f"Error en búsqueda: {e}"

    # ── DISK USAGE ────────────────────────────────────────────────────────
    elif action == "disk_usage":
        try:
            total, used, free = shutil.disk_usage(str(target_path))
            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            free_gb = free / (1024**3)
            pct = (used / total) * 100
            return (
                f"Análisis de disco para '{target_path.anchor}':\n"
                f"- Espacio Total: {total_gb:.2f} GB\n"
                f"- Espacio Usado: {used_gb:.2f} GB ({pct:.1f}%)\n"
                f"- Espacio Disponible: {free_gb:.2f} GB"
            )
        except Exception as e:
            return f"Error al leer espacio del disco: {e}"

    else:
        return f"Acción de archivos '{action}' no es compatible por el controlador de archivos."
