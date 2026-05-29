# -*- coding: utf-8 -*-
"""desktop.py — Windows 11 Desktop HUD operations, wallpaper settings, and file diagnostics."""
import ctypes
import os
import urllib.request
from pathlib import Path
from actions.files.smart_file_organizer import smart_file_organizer

DESKTOP_PATH = Path(os.path.expanduser("~/Desktop")).resolve()

def set_wallpaper(image_path_str: str) -> tuple[bool, str]:
    """Cambia el fondo de pantalla de Windows usando la API nativa SystemParametersInfoW."""
    try:
        # Si es un enlace HTTP/HTTPS, descargar primero
        if image_path_str.startswith("http://") or image_path_str.startswith("https://"):
            temp_dir = Path(os.getenv("TEMP", "."))
            temp_path = temp_dir / "min_downloaded_wallpaper.jpg"
            req = urllib.request.Request(image_path_str, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                temp_path.write_bytes(response.read())
            image_path_str = str(temp_path.resolve())

        img_path = Path(image_path_str).resolve()
        if not img_path.exists():
            return False, f"El archivo de imagen no existe en la ruta: {image_path_str}"

        # 20 = SPI_SETDESKWALLPAPER
        # 3 = SPIF_UPDATEINIFILE | SPIF_SENDCHANGE (Actualiza el archivo y avisa a todas las ventanas del cambio)
        result = ctypes.windll.user32.SystemParametersInfoW(20, 0, str(img_path), 3)
        if result:
            return True, f"Fondo de pantalla cambiado exitosamente al archivo: {img_path.name}"
        else:
            return False, "Fallo al llamar a SystemParametersInfoW en el sistema operativo."
    except Exception as e:
        return False, f"Excepción al cambiar el fondo de pantalla: {str(e)}"

def desktop_control(parameters: dict, player=None) -> str:
    """
    Control avanzado del escritorio de Windows:
    - wallpaper / wallpaper_url: Cambiar fondo de pantalla
    - organize: Agrupar y mover íconos sueltos a carpetas por categoría
    - stats: Obtener un reporte de archivos en el escritorio
    """
    action = parameters.get("action", "stats").lower().strip()
    path_val = parameters.get("path", "").strip()
    url_val = parameters.get("url", "").strip()
    mode_val = parameters.get("mode", "type").lower().strip()

    if action in ("wallpaper", "wallpaper_url"):
        target_path = url_val if action == "wallpaper_url" else path_val
        if not target_path:
            return "Error: Se requiere especificar la ruta de la imagen ('path') o el enlace ('url')."
        
        if player:
            player.write_log(f"🖥️ Cambiando el fondo de pantalla del escritorio...")
            
        success, msg = set_wallpaper(target_path)
        if success:
            return f"✅ {msg}"
        return f"❌ Error: {msg}"

    elif action == "organize":
        if player:
            player.write_log(f"🖥️ Organizando archivos en el escritorio...")
        # Invocar al organizador inteligente apuntando al escritorio
        org_params = {
            "action": "organize",
            "directory": str(DESKTOP_PATH),
            "sort_by": mode_val
        }
        return smart_file_organizer(org_params, player)

    elif action == "stats" or action == "list":
        if not DESKTOP_PATH.exists():
            return "No se pudo localizar el directorio de escritorio en este equipo."
            
        items = list(DESKTOP_PATH.iterdir())
        files = [i for i in items if i.is_file()]
        dirs = [i for i in items if i.is_dir()]
        
        # Calcular tamaño acumulado de archivos
        total_size = sum(f.stat().st_size for f in files)
        total_size_mb = total_size / (1024 * 1024)
        
        file_list = []
        for f in files[:15]:
            fsize_kb = f.stat().st_size / 1024
            file_list.append(f"  📄 {f.name} ({fsize_kb:.1f} KB)")
            
        report_lines = [
            f"--- REPORT DE ESCRITORIO DE MIN ---",
            f"Ubicación: {DESKTOP_PATH}",
            f"Total elementos detectados: {len(items)}",
            f"Archivos sueltos: {len(files)} ({total_size_mb:.2f} MB en total)",
            f"Carpetas: {len(dirs)}",
            "Lista de archivos en el escritorio:"
        ]
        if file_list:
            report_lines.extend(file_list)
            if len(files) > 15:
                report_lines.append(f"  ... y {len(files)-15} archivos más.")
        else:
            report_lines.append("  (No hay archivos sueltos en el escritorio)")
            
        report = "\n".join(report_lines)
        if player:
            player.write_log(f"🖥️ Diagnóstico de escritorio generado.")
        return report

    else:
        return f"Acción de escritorio '{action}' no es compatible actualmente."
