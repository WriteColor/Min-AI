"""services/phrase_triggers.py — Quick phrase-based trigger checks"""

import threading


def fire_phrase_triggers(user_text: str, ui) -> bool:
    """
    Check phrase-based automations. Returns True if any trigger fired
    (caller should skip sending the text to Gemini in that case).
    """
    text_lower = user_text.lower()

    # ── Accessibility quick triggers ──────────────────────────────────────────
    if any(p in text_lower for p in ["activar seguimiento ocular", "iniciar eye tracking",
                                      "activar control ocular", "encender seguimiento de ojos"]):
        try:
            from actions.system.accessibility import eye_tracking
            result = eye_tracking({"action": "start"})
            ui.write_log("\u26a1 " + result)
        except Exception as e:
            ui.write_log(f"[Phrase] Module not available: {e}")
        return True

    if any(p in text_lower for p in ["detener seguimiento ocular", "apagar eye tracking",
                                      "desactivar control ocular"]):
        try:
            from actions.system.accessibility import eye_tracking
            result = eye_tracking({"action": "stop"})
            ui.write_log("\u26a1 " + result)
        except Exception as e:
            ui.write_log(f"[Phrase] Module not available: {e}")
        return True

    if any(p in text_lower for p in ["activar detector de movimientos", "iniciar movimiento",
                                      "activar micromovimientos", "encender control por cabeza"]):
        try:
            from actions.system.accessibility import micro_movement
            result = micro_movement({"action": "start"})
            ui.write_log("\u26a1 " + result)
        except Exception as e:
            ui.write_log(f"[Phrase] Module not available: {e}")
        return True

    if any(p in text_lower for p in ["detener detector de movimientos", "apagar micromovimientos"]):
        try:
            from actions.system.accessibility import micro_movement
            result = micro_movement({"action": "stop"})
            ui.write_log("\u26a1 " + result)
        except Exception as e:
            ui.write_log(f"[Phrase] Module not available: {e}")
        return True

    if any(p in text_lower for p in ["simplifica", "simplificar", "dividir en pasos"]):
        for phrase in ["simplifica ", "simplificar ", "dividir en pasos "]:
            if phrase in text_lower:
                task_text = user_text[len(phrase):].strip()
                if task_text:
                    try:
                        from actions.system.accessibility import task_simplify
                        result = task_simplify(task_text)
                        ui.write_log("\u26a1 [Simplificado]\n" + result[:300])
                    except Exception as e:
                        ui.write_log(f"[Phrase] Module not available: {e}")
                    return True

    if "agregar rutina" in text_lower or "nueva rutina" in text_lower:
        for phrase in ["agregar rutina ", "nueva rutina "]:
            if phrase in text_lower:
                routine_name = user_text[len(phrase):].strip()
                if routine_name:
                    try:
                        from actions.system.accessibility import routine_gamify
                        result = routine_gamify({"action": "add", "name": routine_name})
                        ui.write_log("\u26a1 " + result)
                    except Exception as e:
                        ui.write_log(f"[Phrase] Module not available: {e}")
                    return True

    if "completar rutina" in text_lower or "terminar rutina" in text_lower:
        for phrase in ["completar rutina ", "terminar rutina "]:
            if phrase in text_lower:
                routine_name = user_text[len(phrase):].strip()
                if routine_name:
                    try:
                        from actions.system.accessibility import routine_gamify
                        result = routine_gamify({"action": "complete", "name": routine_name})
                        ui.write_log("\u26a1 " + result)
                    except Exception as e:
                        ui.write_log(f"[Phrase] Module not available: {e}")
                    return True

    if "mis rutinas" in text_lower or "ver rutinas" in text_lower or "listar rutinas" in text_lower:
        try:
            from actions.system.accessibility import routine_gamify
            result = routine_gamify({"action": "list"})
            ui.write_log("\u26a1 [Rutinas]\n" + result)
        except Exception as e:
            ui.write_log(f"[Phrase] Module not available: {e}")
        return True

    # ── User-defined phrase automations ───────────────────────────────────────
    try:
        from actions.automation.rules_engine import check_phrase_triggers, _run_action as _rules_run_action
        triggered = check_phrase_triggers(user_text)
        if triggered:
            for rule in triggered:
                action = rule.get("action", {})
                name   = rule.get("name", "?")
                ui.write_log(f"\u26a1 Automatizaci\u00f3n: {name}")
                threading.Thread(
                    target=_rules_run_action, args=(action,), daemon=True
                ).start()
            return True
    except Exception as e:
        print(f"[MIN] phrase trigger error: {e}")

    return False
