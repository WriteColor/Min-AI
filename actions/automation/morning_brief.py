# -*- coding: utf-8 -*-
"""morning_brief.py — Advanced morning brief report compiling weather, pending goals, and hardware diagnostics."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from actions.automation.weather_report import fetch_weather_data
from actions.automation.goals import load_goals
import psutil

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = BASE_DIR / "config" / "morning_brief_state.json"

def _today_str() -> str:
    return datetime.now().date().isoformat()

def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

def morning_brief(parameters: dict, player=None) -> str:
    """
    Genera un reporte matutino completo para el usuario:
    Clima detallado, recordatorio de metas y tareas pendientes, y estado del hardware.
    """
    now = datetime.now()
    
    # 1. GREETING AND TIME
    brief_lines = [
        f"☀️ BUENOS DÍAS, SEÑOR. Hoy es {now.strftime('%d de %B de %Y')} y son las {now.strftime('%H:%M')}."
    ]

    # Trigger weather widget on UI if PyQt6
    if player and hasattr(player, "show_weather_widget"):
        try:
            player.show_weather_widget()
        except Exception:
            pass

    # 2. DETAILED WEATHER
    wdata = fetch_weather_data(parameters or {})
    if wdata.get("error"):
        brief_lines.append("⚠️ El servicio de clima no está disponible temporalmente.")
    else:
        place = wdata.get("place") or "tu zona"
        desc = wdata.get("desc") or "clima"
        emoji = wdata.get("emoji") or "🌤️"
        temp = wdata.get("temp")
        feel = wdata.get("feel")
        humidity = wdata.get("humidity")
        wind = wdata.get("wind")
        
        weather_str = f"🌤️ Clima en {place}: {desc} {emoji} con una temperatura de {temp}°C (sensación térmica de {feel}°C)."
        if humidity is not None and wind is not None:
            weather_str += f" Humedad del {humidity}% y vientos de {wind} km/h."
        brief_lines.append(weather_str)

    # 3. PENDING GOALS & CHECKS
    goals_list = load_goals()
    pending_goals = [g for g in goals_list if g.get("status") == "pending"]
    
    if pending_goals:
        brief_lines.append(f"📋 TAREAS PENDIENTES: Tienes {len(pending_goals)} objetivos activos en tu lista.")
        
        # Sort pending by high priority first
        high_prio = [g for g in pending_goals if g.get("priority") == "high"]
        other_prio = [g for g in pending_goals if g.get("priority") != "high"]
        
        prio_to_report = (high_prio + other_prio)[:3] # Report top 3
        for g in prio_to_report:
            prio_label = "🔥 ALTA" if g.get("priority") == "high" else "⚡ MEDIA" if g.get("priority") == "medium" else "❄️ BAJA"
            due_label = f" (Vence: {g['due_date']})" if g.get("due_date") else ""
            brief_lines.append(f"  - {g['title']} [Prioridad: {prio_label}]{due_label}")
    else:
        brief_lines.append("📋 TAREAS PENDIENTES: No tienes objetivos pendientes por completar hoy.")

    # 4. HARDWARE STATUS & DIAGNOSTICS WARNINGS
    try:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        
        warnings = []
        if cpu > 80:
            warnings.append(f"Uso de CPU muy alto ({cpu}%)")
        if ram > 85:
            warnings.append(f"Uso de RAM crítico ({ram}%)")
            
        diag_str = f"💻 Estado del Sistema: CPU al {cpu}% y RAM al {ram}%."
        if warnings:
            diag_str += " ⚠️ Advertencia: " + ", ".join(warnings) + "."
        brief_lines.append(diag_str)
    except Exception:
        pass

    # Save state
    mark_briefed()

    report = "\n".join(brief_lines)
    if player:
        player.write_log(f"🌅 {report}")
    return report

def already_briefed_today() -> bool:
    state = _load_state()
    return state.get("last_date") == _today_str()

def mark_briefed() -> None:
    _save_state({"last_date": _today_str()})
