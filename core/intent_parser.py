"""
Intent Parser
=============
Parser de intención de usuario desde texto natural.

Proporciona:
- Extracción de intent desde mensajes
- Reconocimiento de entidades
- Clasificación de urgencia
- Detección de contexto conversacional
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re
import threading


class IntentCategory(Enum):
    """Categorías de intent."""
    ACTION = "action"
    QUESTION = "question"
    STATEMENT = "statement"
    COMMAND = "command"
    GREETING = "greeting"
    FAREWELL = "farewell"
    CONFIRMATION = "confirmation"
    CANCELLATION = "cancellation"
    UNKNOWN = "unknown"


class UrgencyLevel(Enum):
    """Nivel de urgencia."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class IntentEntity:
    """Entidad extraída del texto."""
    type: str
    value: Any
    confidence: float
    start_pos: int
    end_pos: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedIntent:
    """Intent parsed del mensaje."""
    original_text: str
    category: IntentCategory
    action: Optional[str]
    entities: List[IntentEntity]
    confidence: float
    urgency: UrgencyLevel
    parameters: Dict[str, Any]
    requires_confirmation: bool
    conversational_context: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)


class IntentPatterns:
    """Patrones para extracción de entities."""
    
    TIME_PATTERNS = [
        (r'\b(\d{1,2}):(\d{2})\b', 'time'),
        (r'\bat\s+(\d{1,2}):(\d{2})\b', 'time'),
        (r'\bin\s+(\d+)\s*(minutes?|hours?|seconds?)\b', 'duration'),
        (r'\bevery\s+(\d+)\s*(minutes?|hours?|days?)\b', 'recurrence'),
    ]
    
    NUMBER_PATTERNS = [
        (r'\b(\d+(?:\.\d+)?)\b', 'number'),
        (r'\b(one|two|three|four|five|six|seven|eight|nine|ten)\b', 'number_word'),
    ]
    
    FILE_PATTERNS = [
        (r'["\']([^"\']+)["\']', 'quoted_string'),
        (r'\b([A-Za-z]:\\[^\s]+)\b', 'windows_path'),
        (r'\b(/[^\s]+)\b', 'unix_path'),
        (r'\b(\w+\.\w{2,4})\b', 'filename'),
    ]
    
    WINDOW_TITLE_PATTERN = r'the\s+window\s+["\']([^"\']+)["\']'


class IntentParser:
    """
    Parser de intención de usuario.
    
    Uso:
        parser = IntentParser()
        
        # Parsear mensaje
        intent = parser.parse("Close the window 'Notepad'")
        
        # Acceder a resultados
        print(intent.action)  # 'close_window'
        print(intent.entities)  # [Entity('window_title', 'Notepad', ...)]
    """
    
    def __init__(self):
        self._action_keywords: Dict[str, List[str]] = {
            'open': ['open', 'launch', 'start', 'run', 'execute'],
            'close': ['close', 'quit', 'exit', 'terminate', 'kill'],
            'minimize': ['minimize', 'min'],
            'maximize': ['maximize', 'max', 'expand'],
            'restore': ['restore', 'resume', 'show'],
            'move': ['move', 'drag', 'relocate'],
            'resize': ['resize', 'scale', 'size'],
            'screenshot': ['screenshot', 'capture', 'screencap', 'screen'],
            'search': ['search', 'find', 'look for', 'google'],
            'create': ['create', 'make', 'new', 'add'],
            'delete': ['delete', 'remove', 'erase', 'trash'],
            'copy': ['copy', 'duplicate', 'clone'],
            'move_file': ['move', 'relocate', 'transfer'],
            'rename': ['rename', 'rename to', 'change name'],
        }
        self._intent_templates: Dict[str, str] = {}
        self._lock = threading.RLock()
        self._conversation_history: List[ParsedIntent] = []
        self._max_history: int = 50
    
    def register_template(self, pattern: str, action: str) -> None:
        """
        Registrar template de intent.
        
        Args:
            pattern: Patrón regex
            action: Nombre de acción asociada
        """
        with self._lock:
            self._intent_templates[pattern] = action
    
    def parse(self, text: str) -> ParsedIntent:
        """
        Parsear mensaje de usuario a intent.
        
        Args:
            text: Texto input del usuario
        
        Returns:
            ParsedIntent con toda la información extraída
        """
        original_text = text.strip()
        text_lower = original_text.lower()
        
        category = self._classify_category(text_lower)
        action = self._extract_action(text_lower)
        entities = self._extract_entities(original_text)
        confidence = self._calculate_confidence(category, action, entities)
        urgency = self._detect_urgency(text_lower)
        parameters = self._build_parameters(entities, text_lower)
        requires_confirmation = self._requires_confirmation(action, urgency)
        
        intent = ParsedIntent(
            original_text=original_text,
            category=category,
            action=action,
            entities=entities,
            confidence=confidence,
            urgency=urgency,
            parameters=parameters,
            requires_confirmation=requires_confirmation,
            conversational_context=self._get_conversational_context()
        )
        
        self._add_to_history(intent)
        return intent
    
    def parse_with_fallback(
        self,
        text: str,
        fallback_action: str = "general_query"
    ) -> ParsedIntent:
        """Parsear con fallback si confidence es baja."""
        intent = self.parse(text)
        if intent.confidence < 0.5 and intent.action is None:
            intent.action = fallback_action
            intent.parameters['query'] = text
        return intent
    
    def _classify_category(self, text: str) -> IntentCategory:
        """Clasificar categoría del mensaje."""
        if any(g in text for g in ['hi', 'hello', 'hey', 'good morning', 'good afternoon']):
            return IntentCategory.GREETING
        if any(g in text for g in ['bye', 'goodbye', 'see you', 'later']):
            return IntentCategory.FAREWELL
        if any(c in text for c in ['yes', 'yeah', 'yep', 'confirm', 'sure', 'do it']):
            return IntentCategory.CONFIRMATION
        if any(c in text for c in ['no', 'nope', 'cancel', 'stop', 'abort']):
            return IntentCategory.CANCELLATION
        if text.startswith(('open', 'close', 'start', 'stop', 'show', 'hide', 'find', 'search')):
            return IntentCategory.COMMAND
        if '?' in text:
            return IntentCategory.QUESTION
        if any(a in text for a in self._action_keywords.keys()):
            return IntentCategory.ACTION
        return IntentCategory.STATEMENT
    
    def _extract_action(self, text: str) -> Optional[str]:
        """Extraer acción del texto."""
        for action, keywords in self._action_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return action
        return None
    
    def _extract_entities(self, text: str) -> List[IntentEntity]:
        """Extraer entidades del texto."""
        entities = []
        
        for pattern, entity_type in IntentPatterns.TIME_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append(IntentEntity(
                    type=entity_type,
                    value=match.group(0),
                    confidence=0.9,
                    start_pos=match.start(),
                    end_pos=match.end()
                ))
        
        for pattern, entity_type in IntentPatterns.NUMBER_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append(IntentEntity(
                    type=entity_type,
                    value=match.group(1),
                    confidence=0.85,
                    start_pos=match.start(),
                    end_pos=match.end()
                ))
        
        for pattern, entity_type in IntentPatterns.FILE_PATTERNS:
            for match in re.finditer(pattern, text):
                entities.append(IntentEntity(
                    type=entity_type,
                    value=match.group(1),
                    confidence=0.8,
                    start_pos=match.start(),
                    end_pos=match.end()
                ))
        
        window_match = re.search(IntentPatterns.WINDOW_TITLE_PATTERN, text, re.IGNORECASE)
        if window_match:
            entities.append(IntentEntity(
                type='window_title',
                value=window_match.group(1),
                confidence=0.95,
                start_pos=window_match.start(),
                end_pos=window_match.end()
            ))
        
        return entities
    
    def _calculate_confidence(
        self,
        category: IntentCategory,
        action: Optional[str],
        entities: List[IntentEntity]
    ) -> float:
        """Calcular confidence del parseo."""
        confidence = 0.5
        
        if category in [IntentCategory.COMMAND, IntentCategory.ACTION]:
            confidence += 0.2
        
        if action:
            confidence += 0.15
        
        if entities:
            avg_confidence = sum(e.confidence for e in entities) / len(entities)
            confidence += avg_confidence * 0.15
        
        return min(confidence, 1.0)
    
    def _detect_urgency(self, text: str) -> UrgencyLevel:
        """Detectar nivel de urgencia."""
        critical_keywords = ['emergency', 'urgent', 'immediately', 'right now', 'asap']
        high_keywords = ['quickly', 'soon', 'important', 'priority']
        
        if any(k in text for k in critical_keywords):
            return UrgencyLevel.CRITICAL
        if any(k in text for k in high_keywords):
            return UrgencyLevel.HIGH
        if '?' in text:
            return UrgencyLevel.LOW
        return UrgencyLevel.NORMAL
    
    def _build_parameters(
        self,
        entities: List[IntentEntity],
        text: str
    ) -> Dict[str, Any]:
        """Construir parámetros desde entidades."""
        params = {}
        
        for entity in entities:
            if entity.type == 'quoted_string':
                params['target'] = entity.value
            elif entity.type == 'window_title':
                params['window_title'] = entity.value
            elif entity.type in ('number', 'number_word'):
                if 'number' not in params:
                    params['number'] = entity.value
            elif entity.type == 'filename':
                params['filename'] = entity.value
        
        return params
    
    def _requires_confirmation(self, action: Optional[str], urgency: UrgencyLevel) -> bool:
        """Determinar si requiere confirmación."""
        if urgency == UrgencyLevel.CRITICAL:
            return False
        if action in ['delete', 'close', 'terminate']:
            return True
        return False
    
    def _get_conversational_context(self) -> Dict[str, Any]:
        """Obtener contexto conversacional."""
        if not self._conversation_history:
            return {'turn_count': 0}
        
        last_intent = self._conversation_history[-1]
        return {
            'turn_count': len(self._conversation_history),
            'last_action': last_intent.action,
            'last_category': last_intent.category.value,
        }
    
    def _add_to_history(self, intent: ParsedIntent) -> None:
        """Agregar intent al historial conversacional."""
        with self._lock:
            self._conversation_history.append(intent)
            if len(self._conversation_history) > self._max_history:
                self._conversation_history.pop(0)
    
    def get_conversation_history(self, limit: int = 10) -> List[ParsedIntent]:
        """Obtener historial de conversación."""
        with self._lock:
            return self._conversation_history[-limit:]
    
    def clear_history(self) -> None:
        """Limpiar historial conversacional."""
        with self._lock:
            self._conversation_history.clear()
