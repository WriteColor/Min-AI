# -*- coding: utf-8 -*-
"""google_calendar.py — Dual Google Calendar API client & Local Calendar database fallback."""
import json
import os
from pathlib import Path
from datetime import datetime

# Google OAuth imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google.auth.exceptions import UserAccessTokenError
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CREDENTIALS_FILE = BASE_DIR / "config" / "credentials.json"
TOKEN_FILE = BASE_DIR / "config" / "token.json"
LOCAL_CALENDAR_FILE = BASE_DIR / "config" / "local_calendar.json"

SCOPES = ['https://www.googleapis.com/auth/calendar']

def _get_google_service():
    """Obtiene el cliente del servicio de Google Calendar v3."""
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
        
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        print(f"[Calendar] Google Auth failed: {e}")
        return None

def _load_local_events() -> list:
    if not LOCAL_CALENDAR_FILE.exists():
        return []
    try:
        return json.loads(LOCAL_CALENDAR_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def _save_local_events(events: list):
    try:
        LOCAL_CALENDAR_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOCAL_CALENDAR_FILE.write_text(json.dumps(events, indent=4, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"[Calendar] Error saving local events: {e}")

def google_calendar(parameters: dict, player=None) -> str:
    """
    Gestión integral del calendario.
    Intenta sincronizar con Google Calendar v3 (mediante config/credentials.json).
    Si no está configurado, administra automáticamente un calendario local en config/local_calendar.json.
    Acciones: list | add | delete
    """
    action = parameters.get("action", "list").lower().strip()
    summary = parameters.get("title", "").strip() or parameters.get("summary", "").strip()
    start_time_str = parameters.get("start", "").strip() or parameters.get("date", "").strip()
    end_time_str = parameters.get("end", "").strip()
    event_id = parameters.get("event_id", "").strip()

    service = _get_google_service()

    # ── ACCIÓN: LIST ──────────────────────────────────────────────────────
    if action == "list":
        if service:
            try:
                now_iso = datetime.utcnow().isoformat() + 'Z'
                events_result = service.events().list(
                    calendarId='primary', timeMin=now_iso,
                    maxResults=10, singleEvents=True,
                    orderBy='startTime'
                ).execute()
                events = events_result.get('items', [])
                
                if not events:
                    return "No tienes próximos eventos programados en Google Calendar."
                
                lines = ["📅 PRÓXIMOS EVENTOS (Google Calendar):"]
                for event in events:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    lines.append(f"• ID: {event['id'][:8]} | {event.get('summary', 'Sin título')} — Inicio: {start}")
                return "\n".join(lines)
            except Exception as e:
                print(f"[Calendar] Error listing Google Calendar: {e}")
        
        # Fallback a calendario local
        events = _load_local_events()
        # Filtrar pasados y ordenar
        future_events = [e for e in events if e.get("start", "") >= datetime.now().isoformat()]
        future_events = sorted(future_events, key=lambda x: x.get("start", ""))
        
        if not future_events:
            return "No tienes eventos pendientes en tu calendario (Local)."
            
        lines = ["📅 PRÓXIMOS EVENTOS (Calendario Local):"]
        for idx, event in enumerate(future_events[:10]):
            lines.append(f"• Index: {idx} | {event.get('summary', 'Sin título')} — Inicio: {event.get('start')}")
        return "\n".join(lines)

    # ── ACCIÓN: ADD (Crear evento) ────────────────────────────────────────
    elif action == "add":
        if not summary or not start_time_str:
            return "Error: Se requieren el título ('title') y la fecha/hora de inicio ('start')."

        # Intentar parsear fecha a ISO
        try:
            # Ejemplo: "2026-05-30 15:00" o "2026-05-30"
            if len(start_time_str) == 10: # Solo fecha
                start_iso = f"{start_time_str}T09:00:00"
                end_iso = f"{start_time_str}T10:00:00"
            else:
                start_iso = start_time_str.replace(" ", "T")
                end_iso = end_time_str.replace(" ", "T") if end_time_str else ""
                
            if not end_iso:
                # Duración por defecto de 1 hora
                dt = datetime.fromisoformat(start_iso)
                end_iso = (dt.replace(hour=dt.hour + 1)).isoformat()
        except Exception:
            # Si falla, usar formato plano
            start_iso = start_time_str
            end_iso = end_time_str or start_time_str

        if service:
            try:
                event_body = {
                    'summary': summary,
                    'start': {'dateTime': start_iso, 'timeZone': 'UTC'},
                    'end': {'dateTime': end_iso, 'timeZone': 'UTC'},
                }
                event = service.events().insert(calendarId='primary', body=event_body).execute()
                return f"✅ Evento '{summary}' creado exitosamente en Google Calendar. ID: {event.get('id')}"
            except Exception as e:
                print(f"[Calendar] Error inserting in Google Calendar: {e}")

        # Fallback a local
        events = _load_local_events()
        new_event = {
            "summary": summary,
            "start": start_iso,
            "end": end_iso,
            "created_at": datetime.now().isoformat()
        }
        events.append(new_event)
        _save_local_events(events)
        return f"✅ Evento '{summary}' creado exitosamente en tu calendario local (inicio: {start_iso})."

    # ── ACCIÓN: DELETE (Eliminar evento) ──────────────────────────────────
    elif action == "delete":
        if service and event_id:
            try:
                service.events().delete(calendarId='primary', eventId=event_id).execute()
                return f"✅ Evento con ID '{event_id}' eliminado de Google Calendar."
            except Exception as e:
                print(f"[Calendar] Error deleting from Google Calendar: {e}")

        # Eliminar localmente
        events = _load_local_events()
        initial_len = len(events)
        
        # Filtrar por título coincidente si no hay ID
        if event_id:
            events = [e for e in events if e.get("id") != event_id]
        elif summary:
            events = [e for e in events if summary.lower() not in e.get("summary", "").lower()]
            
        if len(events) == initial_len:
            return "No se encontró ningún evento que coincida para eliminar."
            
        _save_local_events(events)
        return "✅ Evento eliminado exitosamente de tu calendario local."

    else:
        return f"Acción de calendario '{action}' no es soportada."
