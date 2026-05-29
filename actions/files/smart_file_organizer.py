# -*- coding: utf-8 -*-
import os
import hashlib
import shutil
from pathlib import Path
from datetime import datetime

# Mapping of months in Spanish for date-based grouping
MONTHS_ES = {
    1: "01_Enero", 2: "02_Febrero", 3: "03_Marzo", 4: "04_Abril",
    5: "05_Mayo", 6: "06_Junio", 7: "07_Julio", 8: "08_Agosto",
    9: "09_Septiembre", 10: "10_Octubre", 11: "11_Noviembre", 12: "12_Diciembre"
}

def get_file_md5(file_path: Path) -> str:
    """Calcula el hash MD5 de un archivo para detectar duplicados reales."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return ""

def smart_file_organizer(parameters: dict, player=None) -> str:
    """
    Organiza archivos de forma inteligente por tipo, fecha, tamaño o reglas personalizadas.
    También detecta y gestiona archivos duplicados en un directorio.
    """
    action = parameters.get("action", "organize").lower()
    target_dir_str = parameters.get("directory", "")
    sort_by = parameters.get("sort_by", "type").lower() # Options: type, date, size
    custom_rules = parameters.get("custom_rules", None) # Optional dict mapping {Folder: [extensions]}
    delete_duplicates = parameters.get("delete_duplicates", False) # Clean up duplicates automatically

    if not target_dir_str:
        # Usar la carpeta de descargas del usuario por defecto
        target_dir_str = str(Path.home() / "Downloads")
        
    target_path = Path(target_dir_str).resolve()
    if not target_path.exists() or not target_path.is_dir():
        return f"Error: El directorio especificado '{target_dir_str}' no existe o no es válido."

    if action == "organize":
        moved_count = 0
        moved_details = []

        # ── 1. CLASIFICACIÓN POR TIPO/CATEGORÍA ──────────────────────────────────
        if sort_by == "type":
            # Categorías por defecto
            categories = {
                "Documentos": [".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".odt", ".csv", ".rtf"],
                "Imagenes": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff"],
                "Videos": [".mp4", ".mkv", ".avi", ".mov", ".flv", ".webm", ".wmv"],
                "Musica": [".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma"],
                "Instaladores": [".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm"],
                "Comprimidos": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"]
            }
            # Combinar con reglas de usuario
            if isinstance(custom_rules, dict):
                for cat, exts in custom_rules.items():
                    normalized_exts = [e.lower() if e.startswith(".") else f".{e.lower()}" for e in exts]
                    categories[cat] = normalized_exts

            for file in target_path.iterdir():
                # No organizar carpetas y saltar archivos ocultos
                if file.is_file() and not file.name.startswith("."):
                    ext = file.suffix.lower()
                    for cat, extensions in categories.items():
                        if ext in extensions:
                            cat_dir = target_path / cat
                            cat_dir.mkdir(exist_ok=True)
                            dest_file = cat_dir / file.name
                            
                            # Evitar colisión de nombres
                            if dest_file.exists():
                                dest_file = cat_dir / f"{file.stem}_{int(datetime.now().timestamp())}{file.suffix}"
                            
                            try:
                                shutil.move(str(file), str(dest_file))
                                moved_count += 1
                                moved_details.append(f"'{file.name}' -> '{cat}/'")
                                break
                            except Exception as e:
                                print(f"[Organizer] Error moving {file.name}: {e}")
                                break

        # ── 2. CLASIFICACIÓN POR FECHA (Año/Mes) ──────────────────────────────
        elif sort_by == "date":
            for file in target_path.iterdir():
                if file.is_file() and not file.name.startswith("."):
                    # Usar fecha de última modificación
                    mtime = datetime.fromtimestamp(file.stat().st_mtime)
                    year_dir = target_path / f"Año_{mtime.year}"
                    month_name = MONTHS_ES.get(mtime.month, f"{mtime.month:02d}_Mes")
                    month_dir = year_dir / month_name
                    
                    month_dir.mkdir(parents=True, exist_ok=True)
                    dest_file = month_dir / file.name
                    
                    if dest_file.exists():
                        dest_file = month_dir / f"{file.stem}_{int(datetime.now().timestamp())}{file.suffix}"
                        
                    try:
                        shutil.move(str(file), str(dest_file))
                        moved_count += 1
                        moved_details.append(f"'{file.name}' -> '{year_dir.name}/{month_name}/'")
                    except Exception as e:
                        print(f"[Organizer] Error moving {file.name}: {e}")

        # ── 3. CLASIFICACIÓN POR TAMAÑO ───────────────────────────────────────
        elif sort_by == "size":
            # Definir límites de tamaño en bytes
            # Gigantes: > 1 GB, Grandes: 100 MB - 1 GB, Medianos: 10 MB - 100 MB, Pequeños: < 10 MB
            size_categories = [
                ("Gigantes_mas_de_1GB", 1024 * 1024 * 1024),
                ("Grandes_100MB_a_1GB", 100 * 1024 * 1024),
                ("Medianos_10MB_a_100MB", 10 * 1024 * 1024),
                ("Pequenos_menos_de_10MB", 0)
            ]
            
            for file in target_path.iterdir():
                if file.is_file() and not file.name.startswith("."):
                    fsize = file.stat().st_size
                    folder_name = "Pequenos_menos_de_10MB"
                    for cat, min_size in size_categories:
                        if fsize >= min_size:
                            folder_name = cat
                            break
                            
                    cat_dir = target_path / folder_name
                    cat_dir.mkdir(exist_ok=True)
                    dest_file = cat_dir / file.name
                    
                    if dest_file.exists():
                        dest_file = cat_dir / f"{file.stem}_{int(datetime.now().timestamp())}{file.suffix}"
                        
                    try:
                        shutil.move(str(file), str(dest_file))
                        moved_count += 1
                        moved_details.append(f"'{file.name}' -> '{folder_name}/'")
                    except Exception as e:
                        print(f"[Organizer] Error moving {file.name}: {e}")

        else:
            return f"Error: Criterio de organización '{sort_by}' no soportado (usa 'type', 'date' o 'size')."

        if moved_count == 0:
            return f"No se encontraron archivos en '{target_path.name}' para organizar usando criterio '{sort_by}'."
            
        res = f"Organización completada en '{target_path.name}' por {sort_by}. Se movieron {moved_count} archivos:\n"
        res += "\n".join(moved_details[:15])
        if len(moved_details) > 15:
            res += f"\n... [y {len(moved_details)-15} archivos más]"
        return res

    elif action == "find_duplicates":
        # Buscar archivos duplicados usando hash MD5
        hashes = {}
        duplicates = []
        
        # Escaneo recursivo
        for root, dirs, files in os.walk(target_path):
            # Ignorar carpetas ocultas
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for file in files:
                if file.startswith("."):
                    continue
                file_path = Path(root) / file
                if file_path.is_file():
                    file_hash = get_file_md5(file_path)
                    if file_hash:
                        if file_hash in hashes:
                            duplicates.append((file_path, hashes[file_hash]))
                        else:
                            hashes[file_hash] = file_path
                            
        if not duplicates:
            return f"Análisis de duplicados completado en '{target_path.name}': No se encontraron archivos idénticos."
            
        if delete_duplicates:
            deleted_count = 0
            for dup_path, orig_path in duplicates:
                try:
                    dup_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"[Organizer] Error deleting duplicate {dup_path}: {e}")
            return f"Se detectaron {len(duplicates)} archivos duplicados reales en '{target_path.name}' y se eliminaron {deleted_count} de forma segura."

        res = f"Se detectaron {len(duplicates)} archivos duplicados reales en '{target_path.name}':\n"
        for dup, orig in duplicates[:10]:
            size_mb = dup.stat().st_size / (1024 * 1024)
            res += f"- Duplicado: '{dup.relative_to(target_path)}' ({size_mb:.2f} MB) es idéntico a '{orig.relative_to(target_path)}'\n"
            
        if len(duplicates) > 10:
            res += f"... [y {len(duplicates)-10} duplicados más encontrados]"
        res += "\n(Puedes añadir el parámetro 'delete_duplicates': true para eliminarlos automáticamente)."
        return res

    elif action == "disk_space":
        # Analizar el uso y espacio libre del disco
        try:
            total, used, free = shutil.disk_usage(str(target_path))
            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            free_gb = free / (1024**3)
            percent_used = (used / total) * 100
            
            return (
                f"Análisis de espacio de disco para la unidad de '{target_path.name}':\n"
                f"- Espacio Total: {total_gb:.2f} GB\n"
                f"- Espacio Usado: {used_gb:.2f} GB ({percent_used:.1f}%)\n"
                f"- Espacio Disponible: {free_gb:.2f} GB"
            )
        except Exception as e:
            return f"Error leyendo espacio de disco: {e}"

    else:
        return f"Acción '{action}' no reconocida por el organizador inteligente de archivos."
