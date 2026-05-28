"""
core/response_generator.py — Contextual Response Generator
========================================================
Generates natural, varied responses based on context and memory.
Eliminates generic templates in favor of adaptive response generation.
"""

import random
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ResponseContext:
    """Context for generating responses."""
    task_type: str = ""
    task_success: bool = True
    user_name: str = ""
    conversation_turn: int = 0
    language: str = "es"
    tone: str = "neutral"


class ResponseGenerator:
    """
    Generates contextual responses with variation.
    
    Features:
    - Variation pools to avoid repetition
    - Context-aware tone adaptation
    - Task-specific response patterns
    - Integration with memory for personalization
    """
    
    def __init__(self):
        self._variation_pools = self._init_variation_pools()
        self._tone_modifiers = self._init_tone_modifiers()
    
    def _init_variation_pools(self) -> Dict[str, List[str]]:
        """Initialize response variation pools."""
        return {
            "acknowledgment": [
                "Entendido", "Perfecto", "Claro", "De acuerdo",
                "Ok", "Si", "Confirmado", "Hecho", "Vale"
            ],
            "confirmation": [
                "Quieres que continue?",
                "Procedo?",
                "Lo hago?",
                "Ejecuto esto?",
                "Confirmas que es lo que necesitas?"
            ],
            "completion": [
                "Listo!", "Completado!", "Hecho!", "Fin.", "Listo.",
                "Todo listo!", "Listo! Que sigue?"
            ],
            "error_soft": [
                "Hmm, eso no salio como esperaba.",
                "Tuve un problema con eso.",
                "No pude completar la accion.",
                "Algo salio mal."
            ],
            "error_sympathetic": [
                "Entiendo la frustracion. Voy a intentarlo de otra manera.",
                "No te preocupes, podemos intentarlo de nuevo.",
                "Tuve dificultades. Dame un momento para revisar."
            ],
            "asking_clarification": [
                "Podrias darme mas detalles?",
                "Quiero estar seguro de entender bien.",
                "Necesito un poco mas de informacion.",
                "Puedo pedirte que seas mas especifico?"
            ],
            "positive_reinforcement": [
                "Gran idea!",
                "Me gusta esa direccion.",
                "Excelente eleccion!",
                "Perfecto, eso tiene sentido."
            ],
            "waiting": [
                "Un momento...",
                "Procesando...",
                "Dame un segundo...",
                "Trabajando en ello..."
            ],
            "thinking": [
                "Déjame pensar...",
                "Voy a analizar esto...",
                "Un momento, estoy razonando..."
            ]
        }
    
    def _init_tone_modifiers(self) -> Dict[str, Callable[[str], str]]:
        """Initialize tone modification functions."""
        return {
            "formal": lambda s: f"Con todo respeto, {s}",
            "casual": lambda s: f"Hey! {s}",
            "friendly": lambda s: f"{s} :)",
            "brief": lambda s: s.split(".")[0] + "."
        }
    
    def get_random_variation(self, pool_name: str) -> str:
        """Get a random variation from a pool."""
        pool = self._variation_pools.get(pool_name, [])
        if not pool:
            return ""
        return random.choice(pool)
    
    def generate_completion(
        self,
        context: Optional[ResponseContext] = None,
        custom_message: str = ""
    ) -> str:
        """
        Generate a task completion response.
        
        Args:
            context: Response context
            custom_message: Optional custom completion message
            
        Returns:
            Completion response string
        """
        if custom_message:
            base = custom_message
        else:
            base = self.get_random_variation("completion")
        
        if context and context.task_type:
            base = f"{base} ({context.task_type})"
        
        return base
    
    def generate_error(
        self,
        error_message: str = "",
        context: Optional[ResponseContext] = None,
        recovery_suggestion: str = ""
    ) -> str:
        """
        Generate an error response.
        
        Args:
            error_message: The error that occurred
            context: Response context
            recovery_suggestion: Optional suggestion for recovery
            
        Returns:
            Error response string
        """
        base = self.get_random_variation("error_soft")
        
        if error_message:
            base = f"{base} {error_message}"
        
        if recovery_suggestion:
            base = f"{base} {recovery_suggestion}"
        elif context and context.task_type:
            base = f"{base} Puedo intentar con {context.task_type} de otra manera?"
        
        return base
    
    def generate_confirmation(
        self,
        action: str,
        context: Optional[ResponseContext] = None
    ) -> str:
        """
        Generate a confirmation request.
        
        Args:
            action: The action to confirm
            context: Response context
            
        Returns:
            Confirmation request string
        """
        confirmation = self.get_random_variation("confirmation")
        return f"{action}? {confirmation}"
    
    def generate_waiting(
        self,
        context: Optional[ResponseContext] = None
    ) -> str:
        """Generate a waiting/processing response."""
        return self.get_random_variation("waiting")
    
    def generate_thinking(self) -> str:
        """Generate a thinking response."""
        return self.get_random_variation("thinking")
    
    def generate_clarification(
        self,
        topic: str,
        context: Optional[ResponseContext] = None
    ) -> str:
        """Generate a clarification request."""
        base = self.get_random_variation("asking_clarification")
        if topic:
            return f"Sobre {topic}, {base.lower()}"
        return base
    
    def generate_greeting(
        self,
        user_name: str = "",
        context: Optional[ResponseContext] = None
    ) -> str:
        """
        Generate a contextual greeting.
        
        Args:
            user_name: User's name
            context: Response context
            
        Returns:
            Greeting string
        """
        from core.prompt_builder import get_greeting_generator
        
        generator = get_greeting_generator()
        
        if context:
            return generator.generate(
                user_name=user_name,
                previous_state="success" if context.conversation_turn > 0 else ""
            )
        
        return generator.generate(user_name=user_name)
    
    def generate_farewell(
        self,
        user_name: str = "",
        context: Optional[ResponseContext] = None
    ) -> str:
        """
        Generate a farewell response.
        
        Args:
            user_name: User's name
            context: Response context
            
        Returns:
            Farewell string
        """
        hour = datetime.now().hour
        
        if 21 <= hour or hour < 5:
            farewells = ["Hasta mañana!", "Buenas noches!", "Que descanses!"]
        elif 17 <= hour < 21:
            farewells = ["Hasta luego!", "Buenas noches!", "Hasta pronto!"]
        elif 12 <= hour < 17:
            farewells = ["Hasta luego!", "Hasta pronto!", "Nos vemos!"]
        else:
            farewells = ["Hasta luego!", "Buena tarde!", "Hasta pronto!"]
        
        farewell = random.choice(farewells)
        
        if user_name:
            farewell = f"{farewell} {user_name}"
        
        return farewell
    
    def generate_suggestion(
        self,
        suggestion: str,
        context: Optional[ResponseContext] = None
    ) -> str:
        """
        Generate a suggestion response.
        
        Args:
            suggestion: The suggestion to make
            context: Response context
            
        Returns:
            Suggestion string
        """
        prefixes = [
            "Podrias probar",
            "Te recomiendo",
            "Que tal si",
            "Podria sugerirte",
            "Que tal"
        ]
        
        prefix = random.choice(prefixes)
        return f"{prefix}: {suggestion}"


def get_response_generator() -> ResponseGenerator:
    """Get a new ResponseGenerator instance."""
    return ResponseGenerator()