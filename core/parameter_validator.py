"""
Parameter Validator
=================
Validador de parámetros para acciones del sistema.

Asegura que los parámetros pasados a las acciones son válidos
antes de ejecutarlas, previniendo errores por tipo incorrecto,
valores fuera de rango, o parámetros faltantes.
"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import inspect


class ValidationError(Exception):
    """Error de validación con detalles."""
    
    def __init__(self, param_name: str, error_type: str, message: str):
        self.param_name = param_name
        self.error_type = error_type
        self.message = message
        super().__init__(f"[{param_name}] {error_type}: {message}")


class ValidationType(Enum):
    """Tipos de validación disponibles."""
    REQUIRED = "required"
    TYPE = "type"
    RANGE = "range"
    MIN = "min"
    MAX = "max"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    IN = "in"
    NOT_IN = "not_in"
    PATTERN = "pattern"
    CUSTOM = "custom"


@dataclass
class ParameterSchema:
    """Esquema de un parámetro de acción."""
    name: str
    param_type: type
    required: bool = False
    default: Any = None
    description: str = ""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    allowed_values: Optional[List[Any]] = None
    forbidden_values: Optional[List[Any]] = None
    pattern: Optional[str] = None
    custom_validator: Optional[Callable[[Any], bool]] = None


@dataclass
class ValidationResult:
    """Resultado de una validación."""
    valid: bool
    errors: List[ValidationError]
    
    @property
    def error_messages(self) -> List[str]:
        return [str(e) for e in self.errors]
    
    def __bool__(self) -> bool:
        return self.valid


class ParameterValidator:
    """
    Validador de parámetros para acciones.
    
    Uso:
        validator = ParameterValidator()
        
        # Definir esquema
        schema = {
            'window_handle': ParameterSchema(
                name='window_handle',
                param_type=int,
                required=True,
                description='HWND de la ventana'
            ),
            'verify': ParameterSchema(
                name='verify',
                param_type=bool,
                required=False,
                default=True
            )
        }
        
        # Validar
        result = validator.validate(schema, {'window_handle': 12345, 'verify': True})
        if not result.valid:
            print(result.error_messages)
    """
    
    TYPE_MAP = {
        'str': str, 'int': int, 'float': float, 'bool': bool,
        'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
        'None': type(None), 'any': Any
    }
    
    def __init__(self):
        self._schemas: Dict[str, Dict[str, ParameterSchema]] = {}
    
    def register_schema(self, action_name: str, schema: Dict[str, ParameterSchema]) -> None:
        """Registrar esquema de validación para una acción."""
        self._schemas[action_name] = schema
    
    def get_schema(self, action_name: str) -> Optional[Dict[str, ParameterSchema]]:
        """Obtener esquema registrado para una acción."""
        return self._schemas.get(action_name)
    
    def validate(
        self,
        schema: Dict[str, ParameterSchema],
        params: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validar parámetros contra esquema.
        
        Args:
            schema: Diccionario de ParameterSchema
            params: Parámetros a validar
            
        Returns:
            ValidationResult con éxito/errores
        """
        errors = []
        
        for param_name, param_schema in schema.items():
            value = params.get(param_name)
            
            # Check required
            if param_schema.required and value is None:
                errors.append(ValidationError(
                    param_name=param_name,
                    error_type="REQUIRED",
                    message="Parameter is required but was not provided"
                ))
                continue
            
            # Skip further validation if None and not required
            if value is None:
                continue
            
            # Check type
            expected_type = param_schema.param_type
            if expected_type != Any and not isinstance(value, expected_type):
                # Try type coercion for some types
                if expected_type == int and isinstance(value, (str, float)):
                    try:
                        value = int(float(value))
                        params[param_name] = value
                    except (ValueError, TypeError):
                        pass
                
                if not isinstance(value, expected_type):
                    errors.append(ValidationError(
                        param_name=param_name,
                        error_type="TYPE",
                        message=f"Expected {expected_type.__name__}, got {type(value).__name__}"
                    ))
                    continue
            
            # Check range (for numeric types)
            if isinstance(value, (int, float)):
                if param_schema.min_value is not None and value < param_schema.min_value:
                    errors.append(ValidationError(
                        param_name=param_name,
                        error_type="RANGE",
                        message=f"Value {value} is less than minimum {param_schema.min_value}"
                    ))
                
                if param_schema.max_value is not None and value > param_schema.max_value:
                    errors.append(ValidationError(
                        param_name=param_name,
                        error_type="RANGE",
                        message=f"Value {value} is greater than maximum {param_schema.max_value}"
                    ))
            
            # Check length (for sequences)
            if isinstance(value, (str, list, tuple)):
                if param_schema.min_length is not None and len(value) < param_schema.min_length:
                    errors.append(ValidationError(
                        param_name=param_name,
                        error_type="LENGTH",
                        message=f"Length {len(value)} is less than minimum {param_schema.min_length}"
                    ))
                
                if param_schema.max_length is not None and len(value) > param_schema.max_length:
                    errors.append(ValidationError(
                        param_name=param_name,
                        error_type="LENGTH",
                        message=f"Length {len(value)} exceeds maximum {param_schema.max_length}"
                    ))
            
            # Check allowed values
            if param_schema.allowed_values is not None:
                if value not in param_schema.allowed_values:
                    errors.append(ValidationError(
                        param_name=param_name,
                        error_type="ALLOWED_VALUES",
                        message=f"Value '{value}' is not in allowed values: {param_schema.allowed_values}"
                    ))
            
            # Check forbidden values
            if param_schema.forbidden_values is not None:
                if value in param_schema.forbidden_values:
                    errors.append(ValidationError(
                        param_name=param_name,
                        error_type="FORBIDDEN_VALUES",
                        message=f"Value '{value}' is in forbidden values: {param_schema.forbidden_values}"
                    ))
            
            # Check pattern
            if param_schema.pattern is not None and isinstance(value, str):
                import re
                if not re.match(param_schema.pattern, value):
                    errors.append(ValidationError(
                        param_name=param_name,
                        error_type="PATTERN",
                        message=f"Value '{value}' does not match pattern {param_schema.pattern}"
                    ))
            
            # Custom validator
            if param_schema.custom_validator is not None:
                try:
                    if not param_schema.custom_validator(value):
                        errors.append(ValidationError(
                            param_name=param_name,
                            error_type="CUSTOM",
                            message="Custom validation failed"
                        ))
                except Exception as e:
                    errors.append(ValidationError(
                        param_name=param_name,
                        error_type="CUSTOM",
                        message=f"Custom validator raised exception: {e}"
                    ))
        
        return ValidationResult(valid=len(errors) == 0, errors=errors)


# Common schemas for built-in actions
COMMON_SCHEMAS = {
    'restore_window': {
        'hwnd': ParameterSchema(
            name='hwnd',
            param_type=int,
            required=True,
            description='Window handle (HWND)'
        ),
        'verify': ParameterSchema(
            name='verify',
            param_type=bool,
            required=False,
            default=True,
            description='Verify the action succeeded'
        ),
        'log_action': ParameterSchema(
            name='log_action',
            param_type=bool,
            required=False,
            default=False,
            description='Log with screenshots'
        )
    },
    'minimize_window': {
        'hwnd': ParameterSchema(
            name='hwnd',
            param_type=int,
            required=True,
            description='Window handle (HWND)'
        ),
        'verify': ParameterSchema(
            name='verify',
            param_type=bool,
            required=False,
            default=True
        ),
        'log_action': ParameterSchema(
            name='log_action',
            param_type=bool,
            required=False,
            default=False
        )
    },
    'maximize_window': {
        'hwnd': ParameterSchema(
            name='hwnd',
            param_type=int,
            required=True,
            description='Window handle (HWND)'
        ),
        'verify': ParameterSchema(
            name='verify',
            param_type=bool,
            required=False,
            default=True
        ),
        'log_action': ParameterSchema(
            name='log_action',
            param_type=bool,
            required=False,
            default=False
        )
    },
    'close_window': {
        'hwnd': ParameterSchema(
            name='hwnd',
            param_type=int,
            required=True,
            description='Window handle (HWND)'
        ),
        'verify': ParameterSchema(
            name='verify',
            param_type=bool,
            required=False,
            default=True
        ),
        'log_action': ParameterSchema(
            name='log_action',
            param_type=bool,
            required=False,
            default=False
        )
    },
    'open_app': {
        'app_name': ParameterSchema(
            name='app_name',
            param_type=str,
            required=True,
            min_length=1,
            description='Name of application to open'
        ),
        'check_running': ParameterSchema(
            name='check_running',
            param_type=bool,
            required=False,
            default=True,
            description='Check if app is already running'
        )
    },
    'generate_image': {
        'prompt': ParameterSchema(
            name='prompt',
            param_type=str,
            required=True,
            min_length=1,
            max_length=500,
            description='Image generation prompt'
        ),
        'style': ParameterSchema(
            name='style',
            param_type=str,
            required=False,
            allowed_values=['cyberpunk', 'realistic', 'anime', 'abstract', 'oil_painting', 'watercolor', None],
            description='Style preset'
        ),
        'width': ParameterSchema(
            name='width',
            param_type=int,
            required=False,
            default=1024,
            min_value=256,
            max_value=2048,
            description='Image width'
        ),
        'height': ParameterSchema(
            name='height',
            param_type=int,
            required=False,
            default=1024,
            min_value=256,
            max_value=2048,
            description='Image height'
        )
    }
}


# Singleton
_validator_instance: Optional[ParameterValidator] = None


def get_validator() -> ParameterValidator:
    """Get singleton validator with common schemas registered."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = ParameterValidator()
        # Register common schemas
        for action_name, schema in COMMON_SCHEMAS.items():
            _validator_instance.register_schema(action_name, schema)
    return _validator_instance
