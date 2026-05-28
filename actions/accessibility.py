# -*- coding: utf-8 -*-
"""accessibility.py — Cognitive and motor accessibility controls for MIN."""
import os
import json
import time
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
ACC_CONFIG_PATH = CONFIG_DIR / "accessibility_config.json"
ROUTINES_PATH = CONFIG_DIR / "routines.json"
API_KEYS_PATH = CONFIG_DIR / "api_keys.json"

# Globals for motor tracking threads
_eye_tracking_active = False
_eye_tracking_thread = None
_micro_movement_active = False
_micro_movement_thread = None


def _load_api_key() -> str:
    if not API_KEYS_PATH.exists():
        return ""
    try:
        data = json.loads(API_KEYS_PATH.read_text(encoding="utf-8"))
        return data.get("gemini_api_key", "")
    except Exception:
        return ""


def _load_acc_config() -> dict:
    if not ACC_CONFIG_PATH.exists():
        return {
            "task_simplification_enabled": True,
            "emotional_regulation_enabled": True,
            "routine_gamification_enabled": True,
            "eye_tracking_enabled": False,
            "micro_movement_enabled": False,
            "visual_feedback_enabled": True,
            "high_contrast_mode": False,
            "auto_learn_routines": True,
            "speech_error_threshold": 0.5,
            "font_size_scale": 1.0
        }
    try:
        return json.loads(ACC_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_acc_config(cfg: dict) -> None:
    try:
        ACC_CONFIG_PATH.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
    except Exception as e:
        print(f"[ACC] Error saving config: {e}")


def _load_routines() -> list:
    if not ROUTINES_PATH.exists():
        default_routines = [
            {"name": "Revisar correo por la mañana", "completed": False, "streak": 0, "last_completed": "", "points": 10},
            {"name": "Planificar objetivos del día", "completed": False, "streak": 0, "last_completed": "", "points": 15},
            {"name": "Realizar ejercicio de respiración", "completed": False, "streak": 0, "last_completed": "", "points": 10}
        ]
        try:
            ROUTINES_PATH.write_text(json.dumps(default_routines, indent=4), encoding="utf-8")
            return default_routines
        except Exception:
            return default_routines
    try:
        return json.loads(ROUTINES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_routines(routines: list) -> None:
    try:
        ROUTINES_PATH.write_text(json.dumps(routines, indent=4), encoding="utf-8")
    except Exception as e:
        print(f"[ACC] Error saving routines: {e}")


def task_simplify(task_text: str) -> str:
    """Simplifica tareas complejas o textos largos."""
    task_text = str(task_text).strip()
    if not task_text:
        return "Por favor, proporciona el texto de la tarea que deseas simplificar."

    api_key = _load_api_key()
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = (
                "Eres MIN, un asistente de accesibilidad cognitiva. Tu objetivo es ayudar a personas que se "
                "abruman fácilmente. Divide y simplifica el siguiente texto o tarea en pasos secuenciales "
                "muy cortos, claros, directos y sin adornos. Responde en español.\n\n"
                f"Texto a simplificar:\n{task_text}"
            )
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"[ACC] Error calling Gemini for simplification: {e}")

    # Fallback si no hay conexión o falla la API
    sentences = [s.strip() for s in task_text.replace(".", "\n").split("\n") if s.strip()]
    if not sentences:
        return "No se pudo simplificar el texto."
    steps = [f"{i+1}. {sentence}" for i, sentence in enumerate(sentences)]
    return "Pasos simplificados de la tarea:\n" + "\n".join(steps)


def routine_gamify(parameters: dict) -> str:
    """Gestiona rutinas diarias gamificadas."""
    action = str(parameters.get("action", "list")).lower().strip()
    name = str(parameters.get("name", "")).strip()
    routines = _load_routines()
    today_str = time.strftime("%Y-%m-%d")

    if action == "add":
        if not name:
            return "Indica el nombre de la rutina a añadir."
        # Evitar duplicados
        if any(r["name"].lower() == name.lower() for r in routines):
            return f"La rutina '{name}' ya existe."
        routines.append({
            "name": name,
            "completed": False,
            "streak": 0,
            "last_completed": "",
            "points": 10
        })
        _save_routines(routines)
        return f"Rutina '{name}' añadida con éxito. Ganarás 10 puntos al completarla."

    elif action == "complete":
        if not name:
            return "Indica el nombre de la rutina que completaste."
        matched = None
        for r in routines:
            if name.lower() in r["name"].lower():
                matched = r
                break
        if not matched:
            return f"No se encontró ninguna rutina que coincida con '{name}'."

        if matched["last_completed"] == today_str:
            return f"La rutina '{matched['name']}' ya ha sido completada hoy."

        # Calcular racha (streak)
        last_comp = matched["last_completed"]
        streak = matched["streak"]
        if last_comp:
            try:
                # Comprobar si se completó ayer para mantener la racha
                from datetime import datetime, timedelta
                last_dt = datetime.strptime(last_comp, "%Y-%m-%d")
                yesterday = datetime.now() - timedelta(days=1)
                if last_dt.date() == yesterday.date():
                    streak += 1
                elif last_dt.date() < yesterday.date():
                    streak = 1
            except Exception:
                streak = 1
        else:
            streak = 1

        matched["completed"] = True
        matched["streak"] = streak
        matched["last_completed"] = today_str
        matched["points"] = matched.get("points", 10)

        # Otorgar puntos extra por racha
        bonus = streak * 2
        total_gained = matched["points"] + bonus

        _save_routines(routines)
        return (f"¡Excelente! Completaste '{matched['name']}'. Racha actual: {streak} días. "
                f"Obtienes {total_gained} puntos (incluye bonus de racha +{bonus}).")

    elif action == "progress":
        total = len(routines)
        if total == 0:
            return "No hay rutinas configuradas."
        completed_today = sum(1 for r in routines if r["last_completed"] == today_str)
        total_points = sum(r.get("points", 10) for r in routines if r["last_completed"] == today_str)
        pct = int((completed_today / total) * 100)
        return f"Progreso de hoy: {completed_today}/{total} ({pct}%). Puntos ganados hoy: {total_points}."

    else:  # list
        if not routines:
            return "No tienes rutinas configuradas."
        lines = []
        for r in routines:
            status = "✅ Completada" if r["last_completed"] == today_str else "❌ Pendiente"
            streak_info = f" (Racha: {r['streak']} días)" if r["streak"] > 0 else ""
            lines.append(f"- {r['name']}: {status}{streak_info}")
        return "Estado de tus rutinas diarias:\n" + "\n".join(lines)


def _eye_tracking_loop():
    global _eye_tracking_active
    try:
        import cv2
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("[ACC] No se pudo abrir la cámara web para eye tracking.")
            _eye_tracking_active = False
            return
        
        while _eye_tracking_active:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            # Simulamos que procesamos el frame para buscar los ojos.
            # En un entorno de producción, aquí se procesarían los landmarks oculares.
            time.sleep(0.2)
        cap.release()
    except Exception as e:
        print(f"[ACC] Error en el loop de seguimiento ocular: {e}")
        _eye_tracking_active = False


def eye_tracking(parameters: dict) -> str:
    """Controla el seguimiento ocular usando la webcam."""
    global _eye_tracking_active, _eye_tracking_thread
    action = str(parameters.get("action", "status")).lower().strip()

    if action == "start":
        if _eye_tracking_active:
            return "El seguimiento ocular ya está activo."
        try:
            import cv2
        except ImportError:
            return "OpenCV no está instalado en el sistema. Ejecuta 'pip install opencv-python'."

        _eye_tracking_active = True
        _eye_tracking_thread = threading.Thread(target=_eye_tracking_loop, daemon=True)
        _eye_tracking_thread.start()
        
        # Guardar en config
        cfg = _load_acc_config()
        cfg["eye_tracking_enabled"] = True
        _save_acc_config(cfg)
        return "Seguimiento ocular iniciado correctamente."

    elif action == "stop":
        if not _eye_tracking_active:
            return "El seguimiento ocular no está activo."
        _eye_tracking_active = False
        
        # Guardar en config
        cfg = _load_acc_config()
        cfg["eye_tracking_enabled"] = False
        _save_acc_config(cfg)
        return "Seguimiento ocular desactivado correctamente."

    else:
        status = "ACTIVO" if _eye_tracking_active else "INACTIVO"
        return f"Estado del seguimiento ocular: {status}."


def _micro_movement_loop():
    global _micro_movement_active
    try:
        import cv2
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("[ACC] No se pudo abrir la cámara web para micromovimientos.")
            _micro_movement_active = False
            return
        
        while _micro_movement_active:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            # Simular detección de micromovimientos de la cabeza
            time.sleep(0.2)
        cap.release()
    except Exception as e:
        print(f"[ACC] Error en el loop de micromovimientos: {e}")
        _micro_movement_active = False


def micro_movement(parameters: dict) -> str:
    """Controla la navegación por micromovimientos de cabeza."""
    global _micro_movement_active, _micro_movement_thread
    action = str(parameters.get("action", "status")).lower().strip()

    if action == "start":
        if _micro_movement_active:
            return "El control por micromovimientos ya está activo."
        try:
            import cv2
        except ImportError:
            return "OpenCV no está instalado en el sistema. Ejecuta 'pip install opencv-python'."

        _micro_movement_active = True
        _micro_movement_thread = threading.Thread(target=_micro_movement_loop, daemon=True)
        _micro_movement_thread.start()
        
        # Guardar en config
        cfg = _load_acc_config()
        cfg["micro_movement_enabled"] = True
        _save_acc_config(cfg)
        return "Control por micromovimientos iniciado."

    elif action == "stop":
        if not _micro_movement_active:
            return "El control por micromovimientos no está activo."
        _micro_movement_active = False
        
        # Guardar en config
        cfg = _load_acc_config()
        cfg["micro_movement_enabled"] = False
        _save_acc_config(cfg)
        return "Control por micromovimientos desactivado."

    else:
        status = "ACTIVO" if _micro_movement_active else "INACTIVO"
        return f"Estado del control por micromovimientos: {status}."


def accessibility(parameters: dict, player=None) -> str:
    """Punto de entrada principal para la herramienta de accesibilidad cognitiva y motora."""
    action = str(parameters.get("action", "")).lower().strip()
    cfg = _load_acc_config()

    if action == "task_simplify":
        text = parameters.get("text", "")
        return task_simplify(text)

    elif action == "emotional":
        stress_lvl = parameters.get("stress_level")
        if stress_lvl is None:
            stress_lvl = 0.5
        else:
            try:
                stress_lvl = float(stress_lvl)
            except ValueError:
                stress_lvl = 0.5

        if stress_lvl >= 0.7:
            msg = (
                "He detectado que tu nivel de estrés es alto. Te sugiero un ejercicio de respiración:\n"
                "1. Inhala por la nariz en 4 segundos.\n"
                "2. Mantén el aire 4 segundos.\n"
                "3. Exhala por la boca en 4 segundos.\n"
                "4. Espera 4 segundos con los pulmones vacíos.\n"
                "Tómate un respiro de 1 minuto. Estoy aquí contigo."
            )
        else:
            msg = "Tu nivel de estrés parece estar bajo control. Mantén un ritmo de trabajo saludable."
        
        if player and hasattr(player, "broadcast"):
            player.broadcast({
                "type": "accessibility_feedback",
                "action": "emotional",
                "stress_level": stress_lvl
            })
        return msg

    elif action == "routine":
        return routine_gamify(parameters)

    elif action == "eye_tracking":
        return eye_tracking(parameters)

    elif action == "micro_movement":
        return micro_movement(parameters)

    elif action == "speech_config":
        lvl = parameters.get("level")
        if lvl is not None:
            try:
                cfg["speech_error_threshold"] = float(lvl)
                _save_acc_config(cfg)
                if player and hasattr(player, "broadcast"):
                    player.broadcast({"type": "config_loaded", "value": json.dumps(cfg)})
                return f"Umbral del error de reconocimiento de voz ajustado a {lvl}."
            except ValueError:
                pass
        return "Indica un nivel numérico válido para ajustar la tolerancia de voz."

    elif action == "config":
        setting = parameters.get("setting")
        value = parameters.get("value")
        if setting:
            if value is not None:
                # Convertir a booleano o float si aplica
                val_str = str(value).lower()
                if val_str in ("true", "yes", "on"):
                    parsed_val = True
                elif val_str in ("false", "no", "off"):
                    parsed_val = False
                else:
                    try:
                        parsed_val = float(value)
                    except ValueError:
                        parsed_val = value
                
                cfg[setting] = parsed_val
                _save_acc_config(cfg)
                if player and hasattr(player, "broadcast"):
                    # Broadcast config update to frontend
                    try:
                        # Fetch full updated config and merge
                        cfg_path = CONFIG_DIR / "api_keys.json"
                        if cfg_path.exists():
                            full_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                            full_cfg["accessibility"] = cfg
                            player.broadcast({"type": "log", "value": f"config_loaded:{json.dumps(full_cfg)}"})
                    except Exception:
                        pass
                return f"Configuración de accesibilidad '{setting}' cambiada a {parsed_val}."
            else:
                return f"El valor de '{setting}' actual es {cfg.get(setting)}."
        return f"Configuración de accesibilidad actual:\n{json.dumps(cfg, indent=4)}"

    elif action == "feedback":
        if player and hasattr(player, "broadcast"):
            player.broadcast({"type": "accessibility_feedback", "value": "triggered"})
        return "Feedback de accesibilidad enviado a la interfaz."

    else:
        return (
            "Módulo de accesibilidad universal activo. Acciones soportadas:\n"
            "- task_simplify (text='...')\n"
            "- emotional (stress_level=0.0-1.0)\n"
            "- routine (action='add'/'complete'/'list'/'progress', name='...')\n"
            "- eye_tracking (action='start'/'stop')\n"
            "- micro_movement (action='start'/'stop')\n"
            "- speech_config (level=0.1-1.0)\n"
            "- config (setting='...', value='...')"
        )
