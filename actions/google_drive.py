# -*- coding: utf-8 -*-
"""google_drive.py — Dual Google Drive API client & Local Sync folder fallback."""
import os
import shutil
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = BASE_DIR / "config" / "credentials.json"
TOKEN_FILE = BASE_DIR / "config" / "token.json"
LOCAL_DRIVE_DIR = Path(os.path.expanduser("~/Pictures/MIN Drive")).resolve()

SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.readonly']

def _get_drive_service():
    if not GOOGLE_LIBS_AVAILABLE or not CREDENTIALS_FILE.exists():
        return None
    
    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception:
            pass

    try:
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
                creds = flow.run_local_server(port=0)
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"[Drive] Google Auth failed: {e}")
        return None

def google_drive(parameters: dict, player=None) -> str:
    """
    Control de almacenamiento Google Drive.
    Acciones: upload | list | download
    Sincroniza automáticamente de manera local en 'Pictures/MIN Drive' si las credenciales API de Google no están presentes.
    """
    action = parameters.get("action", "list").lower().strip()
    file_path_str = parameters.get("file_path", "").strip()
    file_id = parameters.get("file_id", "").strip()
    query = parameters.get("query", "").strip()

    service = _get_drive_service()
    
    # ── ACCIÓN: UPLOAD ────────────────────────────────────────────────────
    if action == "upload":
        if not file_path_str:
            return "Error: Se requiere la ruta del archivo local ('file_path') para subir a Drive."
        
        src_path = Path(file_path_str).resolve()
        if not src_path.exists() or not src_path.is_file():
            return f"Error: El archivo local '{file_path_str}' no existe."

        if service:
            try:
                file_metadata = {'name': src_path.name}
                media = MediaFileUpload(str(src_path), resumable=True)
                file_uploaded = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                return f"✅ Archivo '{src_path.name}' subido exitosamente a Google Drive. ID: {file_uploaded.get('id')}"
            except Exception as e:
                print(f"[Drive] Google Drive upload error: {e}")

        # Fallback local
        try:
            LOCAL_DRIVE_DIR.mkdir(parents=True, exist_ok=True)
            dest_file = LOCAL_DRIVE_DIR / src_path.name
            shutil.copy2(src_path, dest_file)
            return f"✅ Sincronizado localmente en carpeta Drive simulada: {dest_file}"
        except Exception as e:
            return f"Error al copiar archivo a Drive local: {e}"

    # ── ACCIÓN: LIST ──────────────────────────────────────────────────────
    elif action == "list":
        if service:
            try:
                q = "trashed = false"
                if query:
                    q += f" and name contains '{query}'"
                results = service.files().list(
                    pageSize=10, fields="nextPageToken, files(id, name)", q=q
                ).execute()
                items = results.get('files', [])
                if not items:
                    return "No se encontraron archivos en Google Drive."
                
                lines = ["☁️ ARCHIVOS EN GOOGLE DRIVE:"]
                for item in items:
                    lines.append(f"• Name: {item['name']} | ID: {item['id']}")
                return "\n".join(lines)
            except Exception as e:
                print(f"[Drive] Google Drive list error: {e}")

        # Fallback local
        if not LOCAL_DRIVE_DIR.exists():
            return "No se encontraron archivos cargados. Crea la carpeta de sincronización local en 'Pictures/MIN Drive'."
            
        items = list(LOCAL_DRIVE_DIR.iterdir())
        if not items:
            return "No hay archivos en tu carpeta sincronizada de Drive local."
            
        lines = [f"📁 ARCHIVOS EN DRIVE LOCAL (Carpeta: {LOCAL_DRIVE_DIR.name}):"]
        for f in items[:15]:
            if f.is_file():
                size_kb = f.stat().st_size / 1024
                lines.append(f"• {f.name} ({size_kb:.1f} KB)")
        return "\n".join(lines)

    # ── ACCIÓN: DOWNLOAD ──────────────────────────────────────────────────
    elif action == "download":
        if not file_id and not file_path_str:
            return "Error: Se requiere 'file_id' o 'file_name' ('file_path') para descargar del almacenamiento."

        dest_dir = Path(os.path.expanduser("~/Downloads")).resolve()
        
        if service and file_id:
            try:
                import io
                from googleapiclient.http import MediaIoBaseDownload
                
                # Obtener metadatos para saber el nombre
                metadata = service.files().get(fileId=file_id).execute()
                filename = metadata.get('name', 'downloaded_file')
                dest_file = dest_dir / filename
                
                request = service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                
                dest_file.write_bytes(fh.getvalue())
                return f"✅ Archivo '{filename}' descargado exitosamente de Google Drive a tu carpeta de descargas: {dest_file}"
            except Exception as e:
                print(f"[Drive] Google Drive download error: {e}")

        # Fallback local
        try:
            filename = file_path_str or (file_id + ".file" if file_id else "")
            src_file = LOCAL_DRIVE_DIR / filename
            if not src_file.exists():
                # Intentar buscar por coincidencia parcial de nombre
                matched = None
                if LOCAL_DRIVE_DIR.exists():
                    for f in LOCAL_DRIVE_DIR.iterdir():
                        if filename.lower() in f.name.lower():
                            matched = f
                            break
                if matched:
                    src_file = matched
                else:
                    return f"Error: No se encontró ningún archivo matching '{filename}' en el almacenamiento local de Drive."

            dest_file = dest_dir / src_file.name
            shutil.copy2(src_file, dest_file)
            return f"✅ Descargado de Drive local a tu carpeta de descargas: {dest_file}"
        except Exception as e:
            return f"Error al procesar descarga de Drive local: {e}"

    else:
        return f"Acción de Drive '{action}' no es soportada."
