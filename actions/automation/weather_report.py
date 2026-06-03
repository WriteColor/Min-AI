# -*- coding: utf-8 -*-
"""weather_report.py — Robust geolocated weather and timezone lookup client."""
from __future__ import annotations

import json
import os
import sys
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = BASE_DIR / "config" / "config.json"

_WEATHER_MAP = {
    0: ("Despejado", "☀️"),
    1: ("Mayormente despejado", "🌤️"),
    2: ("Parcialmente nublado", "⛅"),
    3: ("Nublado", "☁️"),
    45: ("Niebla", "🌫️"),
    48: ("Niebla con escarcha", "🌫️"),
    51: ("Llovizna ligera", "🌦️"),
    53: ("Llovizna", "🌦️"),
    55: ("Llovizna intensa", "🌧️"),
    56: ("Llovizna helada", "🌧️"),
    57: ("Llovizna helada intensa", "🌧️"),
    61: ("Lluvia ligera", "🌧️"),
    63: ("Lluvia", "🌧️"),
    65: ("Lluvia intensa", "🌧️"),
    66: ("Lluvia helada", "🌧️"),
    67: ("Lluvia helada intensa", "🌧️"),
    71: ("Nieve ligera", "❄️"),
    73: ("Nieve", "❄️"),
    75: ("Nieve intensa", "❄️"),
    77: ("Granos de nieve", "❄️"),
    80: ("Chubascos ligeros", "🌦️"),
    81: ("Chubascos", "🌧️"),
    82: ("Chubascos intensos", "⛈️"),
    85: ("Nieve ligera", "❄️"),
    86: ("Nieve intensa", "❄️"),
    95: ("Tormenta", "⛈️"),
    96: ("Tormenta con granizo", "⛈️"),
    99: ("Tormenta fuerte con granizo", "⛈️"),
}

def _load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_config_cache(city: str, lat: float, lon: float, tz_name: str) -> None:
    """Guarda en cache la geolocalización resuelta para evitar llamadas redundantes a APIs."""
    try:
        cfg = _load_config()
        cfg["location_city"] = city
        cfg["location_lat"] = str(lat)
        cfg["location_lon"] = str(lon)
        cfg["timezone"] = tz_name
        CONFIG_FILE.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
        
        # Broadcast configuration details to active WebSockets if available
        # Send loaded configurations back to Tauri frontend
        if "ui" in sys.modules:
            pass
            
        # Dynamically reload main._BA_TZ timezone info if main is running
        if "main" in sys.modules:
            try:
                main_mod = sys.modules["main"]
                main_mod._load_tz()
            except Exception as e:
                print(f"[TZ] Error reloading main timezone: {e}")
    except Exception as e:
        print(f"[Config] Error writing cached location: {e}")

def _wind_direction(deg: float | int | None) -> str:
    if deg is None:
        return ""
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = int((deg / 22.5) + 0.5) % 16
    return dirs[idx]

def _describe_weather(code: int | None) -> tuple[str, str]:
    if code is None:
        return "Desconocido", "❔"
    return _WEATHER_MAP.get(code, ("Desconocido", "❔"))

def _run_powershell(cmd: str) -> str:
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        return ""
    return ""

def _get_system_location() -> dict | None:
    """Intenta geolocalizar usando la API nativa de Windows (Location services)."""
    if sys.platform != "win32":
        return None
    ps_cmd = (
        "Add-Type -AssemblyName System.Device;"
        "$w = New-Object System.Device.Location.GeoCoordinateWatcher;"
        "$w.Start();"
        "for($i=0; $i -lt 15 -and $w.Status -ne 'Ready' -and $w.Status -ne 'NoData'; $i++){ Start-Sleep -Milliseconds 200 };"
        "if($w.Status -eq 'Ready'){ $c=$w.Position.Location; \"$($c.Latitude);$($c.Longitude)\" }"
    )
    output = _run_powershell(ps_cmd)
    if not output or ";" not in output:
        return None
    try:
        lat_str, lon_str = output.split(";", 1)
        return {"lat": float(lat_str), "lon": float(lon_str)}
    except Exception:
        return None

def _get_ip_location() -> dict | None:
    """
    Cadena de geolocalizadores IP con fallbacks automáticos para evitar rate-limits (HTTP 429).
    Intenta: ip-api.com -> ipinfo.io -> ipapi.co
    """
    # 1. Intentar con ip-api.com (Completamente gratuito, alto límite)
    try:
        req = urllib.request.Request("http://ip-api.com/json/", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("status") == "success":
                return {
                    "lat": float(data["lat"]),
                    "lon": float(data["lon"]),
                    "city": data.get("city"),
                    "region": data.get("regionName"),
                    "country": data.get("country"),
                    "timezone": data.get("timezone"),
                }
    except Exception as e:
        print(f"[Geo] ip-api.com failed: {e}")

    # 2. Intentar con ipinfo.io como primer fallback
    try:
        req = urllib.request.Request("https://ipinfo.io/json", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            if "loc" in data:
                lat_str, lon_str = data["loc"].split(",", 1)
                return {
                    "lat": float(lat_str),
                    "lon": float(lon_str),
                    "city": data.get("city"),
                    "region": data.get("region"),
                    "country": data.get("country"),
                    "timezone": data.get("timezone"),
                }
    except Exception as e:
        print(f"[Geo] ipinfo.io failed: {e}")

    # 3. Intentar con ipapi.co como último recurso (suele bloquear por exceso de uso)
    try:
        req = urllib.request.Request("https://ipapi.co/json/", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            if "latitude" in data and "longitude" in data:
                return {
                    "lat": float(data["latitude"]),
                    "lon": float(data["longitude"]),
                    "city": data.get("city"),
                    "region": data.get("region"),
                    "country": data.get("country_name"),
                    "timezone": data.get("timezone"),
                }
    except Exception as e:
        print(f"[Geo] ipapi.co failed: {e}")

    return None

def _location_from_config(cfg: dict) -> dict | None:
    mode = str(cfg.get("location_mode", "auto")).lower()
    if mode not in ("config", "manual", "auto", "system"):
        return None
    lat = cfg.get("location_lat")
    lon = cfg.get("location_lon")
    city = cfg.get("location_city")
    if lat and lon:
        try:
            return {"lat": float(lat), "lon": float(lon), "city": city, "timezone": cfg.get("timezone")}
        except Exception:
            return None
    if city:
        return {"city": str(city)}
    return None

def _geocode_city(city: str) -> dict | None:
    try:
        url = (
            "https://geocoding-api.open-meteo.com/v1/search?"
            + urllib.parse.urlencode({"name": city, "count": 1, "language": "es", "format": "json"})
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=8).read().decode("utf-8"))
        results = data.get("results") or []
        if not results:
            return None
        r = results[0]
        return {
            "lat": float(r.get("latitude")),
            "lon": float(r.get("longitude")),
            "city": r.get("name"),
            "region": r.get("admin1"),
            "country": r.get("country"),
            "timezone": r.get("timezone"),
        }
    except Exception:
        return None

def _fetch_weather(lat: float, lon: float, tz_name: str | None = None) -> dict:
    tz_param = tz_name if tz_name else "auto"
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        + urllib.parse.urlencode(
            {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,wind_direction_10m,is_day",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
                "timezone": tz_param,
            }
        )
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=8).read().decode("utf-8"))

def _format_location(loc: dict, fallback: str) -> str:
    parts = [loc.get("city"), loc.get("region"), loc.get("country")]
    place = ", ".join([p for p in parts if p])
    return place or fallback

def fetch_weather_data(parameters: dict | None = None) -> dict:
    params = parameters or {}
    city_param = str(params.get("city", "")).strip()
    cfg = _load_config()

    loc = None
    if city_param:
        loc = _geocode_city(city_param)
    
    # Si no se dio ciudad, buscar en cache local
    if not loc:
        loc = _location_from_config(cfg)
        if loc and "city" in loc and "lat" not in loc:
            loc = _geocode_city(loc["city"])
            
    # Si no hay cache, intentar geolocalizar por Windows Location
    if not loc:
        if str(cfg.get("location_mode", "auto")).lower() in ("system", "auto"):
            loc = _get_system_location()
            if loc:
                # Si obtuvimos coordenadas del sistema, usar reversa para saber la ciudad
                loc["city"] = cfg.get("location_city") or "Tu Ubicación"
                loc["timezone"] = cfg.get("timezone")
                
    # Si sigue sin localizar, geolocalizar por IP (carrusel de APIs)
    if not loc or "lat" not in loc or "lon" not in loc:
        loc = _get_ip_location()
        if loc and "lat" in loc and "lon" in loc:
            # Escribir en caché local del archivo de configuración para no requerir llamadas futuras
            _save_config_cache(loc["city"], loc["lat"], loc["lon"], loc["timezone"])

    if not loc or "lat" not in loc or "lon" not in loc:
        return {"error": "No pude determinar tu ubicación actual."}

    # Obtener el reporte climático de Open-Meteo
    try:
        data = _fetch_weather(loc["lat"], loc["lon"], loc.get("timezone"))
    except Exception as e:
        return {"error": f"Fallo al consultar Open-Meteo: {e}"}

    current = data.get("current", {})
    daily = data.get("daily", {})

    desc, emoji = _describe_weather(current.get("weather_code"))
    
    # ── CÁLCULO DE HORA LOCAL BASADO EN EL OFFSET UTC DE LA API ──────────────────
    # Esto soluciona los crashes causados por zoneinfo en Windows cuando falta tzdata.
    offset_sec = data.get("utc_offset_seconds")
    if offset_sec is not None:
        local_dt = datetime.now(timezone.utc) + timedelta(seconds=offset_sec)
        local_time = local_dt.strftime("%H:%M")
    else:
        # Fallback si no hay red o si falla el offset
        local_time = datetime.now().strftime("%H:%M")

    place = _format_location(loc, city_param or loc.get("city") or "tu zona")

    forecast = []
    dates = daily.get("time") or []
    maxs = daily.get("temperature_2m_max") or []
    mins = daily.get("temperature_2m_min") or []
    codes = daily.get("weather_code") or []
    for i in range(min(3, len(dates))):
        fdesc, femoji = _describe_weather(codes[i] if i < len(codes) else None)
        forecast.append(
            {
                "date": dates[i],
                "desc": fdesc,
                "emoji": femoji,
                "min": mins[i] if i < len(mins) else None,
                "max": maxs[i] if i < len(maxs) else None,
                "code": codes[i] if i < len(codes) else None,
            }
        )

    return {
        "place": place,
        "desc": desc,
        "emoji": emoji,
        "weather_code": current.get("weather_code"),
        "is_day": current.get("is_day"),
        "temp": current.get("temperature_2m"),
        "feel": current.get("apparent_temperature"),
        "humidity": current.get("relative_humidity_2m"),
        "precip": current.get("precipitation"),
        "wind": current.get("wind_speed_10m"),
        "wind_dir": _wind_direction(current.get("wind_direction_10m")),
        "local_time": local_time,
        "forecast": forecast,
    }

def weather_report(parameters: dict, player=None) -> str:
    data = fetch_weather_data(parameters)
    if data.get("error"):
        return f"Error: {data.get('error')} Configura manualmente 'location_city' en config/config.json."

    if player and hasattr(player, "show_weather_widget"):
        try:
            player.show_weather_widget()
        except Exception:
            pass

    # Broadcast actual weather info to Tauri socket dashboard
    if player and hasattr(player, "broadcast"):
        try:
            player.broadcast({
                "type": "weather",
                "data": data
            })
        except Exception:
            pass

    desc = data.get("desc")
    emoji = data.get("emoji")
    temp = data.get("temp")
    feel = data.get("feel")
    humidity = data.get("humidity")
    precip = data.get("precip")
    wind = data.get("wind")
    wind_dir = data.get("wind_dir")
    local_time = data.get("local_time")
    place = data.get("place")
    
    lines = [
        f"Clima actual en {place}: {desc} {emoji}",
        f"Temp: {temp}°C (sensación {feel}°C) | Humedad: {humidity}%",
        f"Viento: {wind} km/h {wind_dir} | Precipitación: {precip} mm",
        f"Hora local calculada: {local_time}",
    ]

    forecast = data.get("forecast", [])
    if forecast:
        forecast_lines = []
        for item in forecast:
            fdesc = item.get("desc")
            femoji = item.get("emoji")
            fmin = item.get("min")
            fmax = item.get("max")
            date = item.get("date")
            forecast_lines.append(f"{date}: {fdesc} {femoji} {fmin}°C/{fmax}°C")
        if forecast_lines:
            lines.append("Pronóstico: " + " | ".join(forecast_lines))

    report = "\n".join(lines)
    if player:
        player.write_log(f"🌤️ {report}")
    return report
