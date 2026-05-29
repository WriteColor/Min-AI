# -*- coding: utf-8 -*-
"""goals.py — Advanced dynamic goals/tasks tracker with subtask checklists and persistence."""
import json
import uuid
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
GOALS_PATH = BASE_DIR / "config" / "goals.json"

def load_goals() -> list:
    if not GOALS_PATH.exists():
        return []
    try:
        return json.loads(GOALS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_goals(goals_list: list):
    try:
        GOALS_PATH.parent.mkdir(parents=True, exist_ok=True)
        GOALS_PATH.write_text(json.dumps(goals_list, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"[Goals] Error saving goals: {e}")

def goals(parameters: dict, player=None) -> str:
    """
    Gestiona los objetivos, metas y checklists de tareas pendientes de MIN.
    Acciones: list, add, update, add_subtask, toggle_subtask, delete
    """
    action = parameters.get("action", "list").lower()
    goals_list = load_goals()

    # ── LIST GOALS ────────────────────────────────────────────────────────
    if action == "list":
        if not goals_list:
            return "No tienes ningún objetivo registrado en la base de datos de MIN."
            
        status_filter = parameters.get("status", "all").lower() # all, pending, completed
        priority_filter = parameters.get("priority", "all").lower() # all, high, medium, low

        filtered = []
        for g in goals_list:
            # Filtro por estado
            if status_filter == "pending" and g.get("status") != "pending":
                continue
            if status_filter == "completed" and g.get("status") != "completed":
                continue
            # Filtro por prioridad
            if priority_filter != "all" and g.get("priority", "medium").lower() != priority_filter:
                continue
            filtered.append(g)

        if not filtered:
            return f"No se encontraron objetivos con los filtros aplicados (estado: {status_filter}, prioridad: {priority_filter})."

        lines = ["📋 OBJETIVOS Y TAREAS REGISTRADAS EN MIN:"]
        for g in filtered:
            # Calcular porcentaje completado de subtareas
            subtasks = g.get("subtasks", [])
            progress_str = ""
            if subtasks:
                done = sum(1 for s in subtasks if s.get("status") == "completed")
                pct = int((done / len(subtasks)) * 100)
                progress_str = f" [{done}/{len(subtasks)} sub-tareas - {pct}%]"

            status_icon = "✅" if g.get("status") == "completed" else "⏳"
            priority_icon = "🔥" if g.get("priority") == "high" else "⚡" if g.get("priority") == "medium" else "❄️"
            due_str = f" | Límite: {g['due_date']}" if g.get("due_date") else ""
            
            lines.append(f"{status_icon} ID: {g['id'][:6]} | {g['title']} ({priority_icon} {g.get('priority').upper()}){due_str}{progress_str}")
            if g.get("description"):
                lines.append(f"   Desc: {g['description']}")
                
            # Listar subtareas
            for idx, s in enumerate(subtasks):
                s_icon = "[x]" if s.get("status") == "completed" else "[ ]"
                lines.append(f"     {s_icon} Subtask {idx}: {s['title']}")

        return "\n".join(lines)

    # ── ADD GOAL ──────────────────────────────────────────────────────────
    elif action == "add":
        title = parameters.get("title", "").strip()
        if not title:
            # Fallback a parámetro genérico de texto
            title = parameters.get("goal", "").strip()
        if not title:
            return "Error: Se requiere especificar un título ('title') para crear el objetivo."

        new_goal = {
            "id": str(uuid.uuid4()),
            "title": title,
            "description": parameters.get("description", "").strip(),
            "priority": parameters.get("priority", "medium").lower(),
            "due_date": parameters.get("due_date", "").strip(),
            "status": "pending",
            "subtasks": [],
            "created_at": datetime.now().isoformat(),
            "completed_at": None
        }
        
        # Validar prioridades permitidas
        if new_goal["priority"] not in ("high", "medium", "low"):
            new_goal["priority"] = "medium"

        goals_list.append(new_goal)
        save_goals(goals_list)
        if player and hasattr(player, "broadcast"):
            player.broadcast({"type": "todos", "value": goals_list})
        return f"✅ Objetivo '{title}' registrado con éxito. ID: {new_goal['id'][:6]}."

    # ── UPDATE GOAL STATUS / PROPERTIES ──────────────────────────────────
    elif action == "update":
        goal_id = parameters.get("id", "").strip()
        if not goal_id:
            return "Error: Se requiere el 'id' del objetivo para poder actualizarlo."
            
        target = None
        for g in goals_list:
            if g["id"].startswith(goal_id) or g["id"] == goal_id:
                target = g
                break
                
        if not target:
            return f"Error: No se encontró ningún objetivo con el ID '{goal_id}'."

        # Actualizar propiedades si se pasaron
        if "title" in parameters:
            target["title"] = parameters["title"]
        if "description" in parameters:
            target["description"] = parameters["description"]
        if "priority" in parameters:
            p = parameters["priority"].lower()
            if p in ("high", "medium", "low"):
                target["priority"] = p
        if "due_date" in parameters:
            target["due_date"] = parameters["due_date"]
        if "status" in parameters:
            new_status = parameters["status"].lower()
            if new_status in ("pending", "completed"):
                target["status"] = new_status
                if new_status == "completed":
                    target["completed_at"] = datetime.now().isoformat()
                    # Completar todas las subtareas automáticamente
                    for s in target.get("subtasks", []):
                        s["status"] = "completed"
                else:
                    target["completed_at"] = None

        save_goals(goals_list)
        if player and hasattr(player, "broadcast"):
            player.broadcast({"type": "todos", "value": goals_list})
        return f"✅ Objetivo '{target['title']}' actualizado con éxito."

    # ── ADD SUBTASK ───────────────────────────────────────────────────────
    elif action == "add_subtask":
        goal_id = parameters.get("goal_id", "").strip()
        sub_title = parameters.get("title", "").strip()
        if not goal_id or not sub_title:
            return "Error: Se requiere el ID del objetivo ('goal_id') y el título de la subtarea ('title')."

        target = None
        for g in goals_list:
            if g["id"].startswith(goal_id) or g["id"] == goal_id:
                target = g
                break
                
        if not target:
            return f"Error: No se encontró ningún objetivo con el ID '{goal_id}'."

        subtask = {
            "title": sub_title,
            "status": "pending"
        }
        target["subtasks"].append(subtask)
        save_goals(goals_list)
        if player and hasattr(player, "broadcast"):
            player.broadcast({"type": "todos", "value": goals_list})
        return f"✅ Sub-tarea '{sub_title}' agregada al objetivo '{target['title']}'."

    # ── TOGGLE SUBTASK ────────────────────────────────────────────────────
    elif action == "toggle_subtask":
        goal_id = parameters.get("goal_id", "").strip()
        subtask_idx_param = parameters.get("subtask_index", None)
        subtask_title = parameters.get("title", "").strip()
        
        if not goal_id:
            return "Error: Se requiere el 'goal_id' del objetivo."

        target = None
        for g in goals_list:
            if g["id"].startswith(goal_id) or g["id"] == goal_id:
                target = g
                break
                
        if not target:
            return f"Error: No se encontró ningún objetivo con el ID '{goal_id}'."

        subtasks = target.get("subtasks", [])
        sub_match = None
        
        # Buscar por índice si se dio
        if subtask_idx_param is not None:
            try:
                idx = int(subtask_idx_param)
                if 0 <= idx < len(subtasks):
                    sub_match = subtasks[idx]
            except Exception:
                pass
                
        # Buscar por título si no se encontró por índice
        if not sub_match and subtask_title:
            for s in subtasks:
                if subtask_title.lower() in s["title"].lower():
                    sub_match = s
                    break

        if not sub_match:
            return "Error: No se pudo localizar la sub-tarea indicada por índice o título."

        # Alternar estado
        if sub_match["status"] == "completed":
            sub_match["status"] = "pending"
            target["status"] = "pending" # Si se desmarca una sub-tarea, el objetivo ya no está totalmente completado
        else:
            sub_match["status"] = "completed"
            # Si todas las sub-tareas están completas, completar el objetivo principal
            if all(s["status"] == "completed" for s in subtasks):
                target["status"] = "completed"
                target["completed_at"] = datetime.now().isoformat()

        save_goals(goals_list)
        if player and hasattr(player, "broadcast"):
            player.broadcast({"type": "todos", "value": goals_list})
        return f"✅ Estado de sub-tarea '{sub_match['title']}' alternado a '{sub_match['status']}'."

    # ── DELETE GOAL ───────────────────────────────────────────────────────
    elif action == "delete":
        goal_id = parameters.get("id", "").strip()
        if not goal_id:
            return "Error: Se requiere el 'id' del objetivo para eliminarlo."
            
        initial_len = len(goals_list)
        goals_list = [g for g in goals_list if not (g["id"].startswith(goal_id) or g["id"] == goal_id)]
        
        if len(goals_list) == initial_len:
            return f"No se encontró ningún objetivo con el ID '{goal_id}'."

        save_goals(goals_list)
        if player and hasattr(player, "broadcast"):
            player.broadcast({"type": "todos", "value": goals_list})
        return f"✅ Objetivo con ID '{goal_id[:6]}' eliminado de la base de datos."

    return f"Acción '{action}' no soportada por el rastreador de objetivos."
