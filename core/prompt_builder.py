"""
core/prompt_builder.py — Dynamic Prompt Builder
================================================
Builds contextual prompts by combining system instructions, memory context,
user profile, and dynamic elements. Eliminates rigid templates in favor of
adaptive prompt generation.
"""

import random
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class PromptContext:
    """Context for building prompts."""
    user_name: str = ""
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    recent_interactions: List[str] = field(default_factory=list)
    current_task: str = ""
    active_projects: List[str] = field(default_factory=list)
    time_period: str = "morning"
    previous_state: str = ""
    conversation_history: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class PromptComponent:
    """A component of a prompt."""
    role: str  # "system", "user", "assistant"
    content: str
    priority: int = 0
    max_tokens: Optional[int] = None


class PromptBuilder:
    """
    Dynamic prompt builder that assembles prompts from modular components.
    
    Features:
    - Context-aware prompt generation
    - Modular component system
    - Dynamic greeting insertion
    - Memory integration
    - Variation pools to avoid repetition
    """
    
    def __init__(self):
        self._components: List[PromptComponent] = []
        self._system_prompt_base = ""
        self._variation_pools = self._init_variation_pools()
    
    def _init_variation_pools(self) -> Dict[str, List[str]]:
        """Initialize variation pools to avoid repetition."""
        return {
            "acknowledgment": [
                "Entendido", "Perfecto", "Claro", "De acuerdo",
                "Ok", "Sí", "Confirmado", "Hecho"
            ],
            "confirmation": [
                "Quieres que continúe?",
                "Procedo?",
                "Lo hago?",
                "Ejecuto esto?",
                "Confirmas?"
            ],
            "completion": [
                "Listo", "Completado", "Hecho", "Fin", "Listo!"
            ],
            "greeting_morning": [
                "Buenos dias",
                "Good morning",
                "Morning"
            ],
            "greeting_afternoon": [
                "Buenas tardes",
                "Good afternoon",
                "Afternoon"
            ],
            "greeting_evening": [
                "Buenas noches",
                "Good evening",
                "Evening"
            ],
            "greeting_night": [
                "Hola de nuevo",
                "Back again?",
                "Night owl"
            ],
            "before_complex_task": [
                "Esto puede tomar un momento.",
                "Voy a trabajar en ello.",
                "Un momento, por favor.",
                "Estoy procesando esto."
            ],
            "after_error": [
                "Entiendo que hubo un problema.",
                "Veo que hubo un error antes.",
                "Tuve dificultades con eso."
            ],
            "after_success": [
                "Perfecto, eso esta hecho.",
                "Listo! Todo funciono correctamente.",
                "Excelente, completada la tarea."
            ],
            "user_busy": [
                "Te veo ocupado.",
                "Puedo esperar o volver mas tarde.",
                "No hay apuro, estoy aqui."
            ]
        }
    
    def set_system_prompt(self, prompt: str):
        """Set the base system prompt."""
        self._system_prompt_base = prompt
    
    def add_component(
        self,
        content: str,
        role: str = "user",
        priority: int = 0,
        max_tokens: Optional[int] = None
    ):
        """Add a component to the prompt."""
        self._components.append(PromptComponent(
            role=role,
            content=content,
            priority=priority,
            max_tokens=max_tokens
        ))
    
    def add_context(self, context: PromptContext):
        """Add context information to the prompt."""
        context_parts = []
        
        if context.user_name:
            context_parts.append(f"User: {context.user_name}")
        
        if context.user_preferences:
            prefs = ", ".join([
                f"{k}={v}" for k, v in context.user_preferences.items()
            ])
            context_parts.append(f"Preferences: {prefs}")
        
        if context.active_projects:
            projects = ", ".join(context.active_projects)
            context_parts.append(f"Active projects: {projects}")
        
        if context.current_task:
            context_parts.append(f"Current task: {context.current_task}")
        
        if context.recent_interactions:
            recent = context.recent_interactions[-3:]
            context_parts.append(f"Recent: {' | '.join(recent)}")
        
        if context_parts:
            context_str = "\n".join(context_parts)
            self.add_component(f"[CONTEXT]\n{context_str}", role="system", priority=100)
    
    def add_memory_context(self, memories: List[Dict[str, Any]], max_items: int = 5):
        """Add memory context to the prompt."""
        if not memories:
            return
        
        items = memories[:max_items]
        memory_lines = []
        
        for mem in items:
            mem_type = mem.get("type", "unknown")
            content = mem.get("content", "")[:100]
            memory_lines.append(f"[{mem_type.upper()}] {content}")
        
        memory_str = "\n".join(memory_lines)
        self.add_component(f"[MEMORY]\n{memory_str}", role="system", priority=50)
    
    def add_conversation_history(
        self,
        history: List[Dict[str, str]],
        max_turns: int = 5
    ):
        """Add recent conversation history."""
        if not history:
            return
        
        turns = history[-max_turns:]
        conv_lines = []
        
        for turn in turns:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            conv_lines.append(f"{role.upper()}: {content}")
        
        conv_str = "\n".join(conv_lines)
        self.add_component(f"[CONVERSATION]\n{conv_str}", role="system", priority=30)
    
    def add_task_context(self, task: str, entities: Dict[str, Any]):
        """Add task-specific context."""
        task_lines = [f"Task: {task}"]
        
        if entities:
            for key, value in entities.items():
                task_lines.append(f"  {key}: {value}")
        
        task_str = "\n".join(task_lines)
        self.add_component(f"[TASK]\n{task_str}", role="user", priority=200)
    
    def build(self) -> List[Dict[str, str]]:
        """
        Build the final prompt message list.
        
        Returns:
            List of message dicts with 'role' and 'content' keys
        """
        sorted_components = sorted(
            self._components,
            key=lambda c: c.priority,
            reverse=True
        )
        
        messages = []
        for comp in sorted_components:
            messages.append({
                "role": comp.role,
                "content": comp.content
            })
        
        self._components.clear()
        return messages
    
    def build_single_prompt(
        self,
        user_input: str,
        context: Optional[PromptContext] = None,
        memory_context: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Build a single formatted prompt string.
        
        Args:
            user_input: The user's input text
            context: Optional context information
            memory_context: Optional memory entries
            
        Returns:
            Formatted prompt string
        """
        parts = []
        
        if self._system_prompt_base:
            parts.append(f"System: {self._system_prompt_base}")
        
        if context:
            if context.user_name:
                parts.append(f"User context: {context.user_name}")
            if context.active_projects:
                parts.append(f"Projects: {', '.join(context.active_projects)}")
        
        if memory_context:
            mem_lines = [f"- {m.get('content', '')[:80]}" for m in memory_context[:3]]
            parts.append(f"Relevant memories:\n" + "\n".join(mem_lines))
        
        parts.append(f"User: {user_input}")
        
        return "\n\n".join(parts)
    
    def get_random_variation(self, pool_name: str) -> str:
        """Get a random variation from a pool."""
        pool = self._variation_pools.get(pool_name, [])
        if not pool:
            return ""
        return random.choice(pool)
    
    def clear(self):
        """Clear all components."""
        self._components.clear()


class DynamicGreetingGenerator:
    """Generates context-aware greetings."""
    
    def __init__(self):
        self._greeting_templates = self._init_templates()
        self._last_greeting = ""
    
    def _init_templates(self) -> Dict[str, List[str]]:
        return {
            "morning": [
                "Buenos dias {name}, que puedo hacer por ti hoy?",
                "Hola {name}, buenos dias!",
                "Good morning {name}! En que te puedo ayudar?",
                "Buenos dias! Como amaneciste {name}?"
            ],
            "afternoon": [
                "Buenas tardes {name}, en que te puedo ayudar?",
                "Hola {name}, que tal la tarde?",
                "Hey {name}, como va tu dia?",
                "Buenas! Que necesitas?"
            ],
            "evening": [
                "Buenas noches {name}, como estuvo tu dia?",
                "Hola {name}, que tal esta noche?",
                "Buenas noches! En que te puedo ayudar?"
            ],
            "night": [
                "Hola de nuevo {name}, entrada tardia eh!",
                "Back again {name}? Noche de productividad?",
                "Night owl detected, {name}!"
            ]
        }
    
    def get_time_period(self) -> str:
        """Get current time period."""
        from datetime import datetime
        hour = datetime.now().hour
        
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"
    
    def generate(
        self,
        user_name: str = "",
        previous_state: str = "",
        time_period: Optional[str] = None
    ) -> str:
        """
        Generate a contextual greeting.
        
        Args:
            user_name: Name of the user
            previous_state: Previous conversation state (error, success, etc.)
            time_period: Optional override for time period
            
        Returns:
            Contextual greeting string
        """
        period = time_period or self.get_time_period()
        templates = self._greeting_templates.get(period, self._greeting_templates["morning"])
        
        greeting = random.choice(templates)
        
        if user_name:
            greeting = greeting.replace("{name}", user_name)
        else:
            greeting = greeting.replace("{name}", "")
        
        if previous_state == "error":
            greeting = f"Veo que hubo un problema antes. {greeting}"
        elif previous_state == "success":
            greeting = f"¡Hola de nuevo! {greeting}"
        
        self._last_greeting = greeting
        return greeting


def get_prompt_builder() -> PromptBuilder:
    """Get a new PromptBuilder instance."""
    return PromptBuilder()


def get_greeting_generator() -> DynamicGreetingGenerator:
    """Get a new DynamicGreetingGenerator instance."""
    return DynamicGreetingGenerator()