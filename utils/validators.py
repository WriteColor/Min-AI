"""
Validators
=========
Validadores comunes para parámetros y datos.

Proporciona:
- Validación de tipos
- Validación de rangos
- Validación de formatos
- Validación de longitud
- Validadores combinables
"""

from typing import Any, List, Optional, Callable, Union, Type
from dataclasses import dataclass, field
from enum import Enum
import re


@dataclass
class ValidationResult:
    """Resultado de una validación."""
    valid: bool
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class Validator:
    """Validador base."""
    
    def validate(self, value: Any) -> ValidationResult:
        raise NotImplementedError
    
    def __call__(self, value: Any) -> ValidationResult:
        return self.validate(value)


class TypeValidator(Validator):
    """Validador de tipo."""
    
    def __init__(self, expected_type: Type, allow_none: bool = False):
        self._expected_type = expected_type
        self._allow_none = allow_none
    
    def validate(self, value: Any) -> ValidationResult:
        if value is None:
            if self._allow_none:
                return ValidationResult(valid=True)
            return ValidationResult(valid=False, error="Value cannot be None")
        
        if not isinstance(value, self._expected_type):
            return ValidationResult(
                valid=False,
                error=f"Expected {self._expected_type.__name__}, got {type(value).__name__}"
            )
        
        return ValidationResult(valid=True)


class RangeValidator(Validator):
    """Validador de rango numérico."""
    
    def __init__(
        self,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        allow_none: bool = False
    ):
        self._min_value = min_value
        self._max_value = max_value
        self._allow_none = allow_none
    
    def validate(self, value: Any) -> ValidationResult:
        if value is None:
            if self._allow_none:
                return ValidationResult(valid=True)
            return ValidationResult(valid=False, error="Value cannot be None")
        
        if not isinstance(value, (int, float)):
            return ValidationResult(valid=False, error=f"Expected number, got {type(value).__name__}")
        
        if self._min_value is not None and value < self._min_value:
            return ValidationResult(valid=False, error=f"Value {value} below minimum {self._min_value}")
        
        if self._max_value is not None and value > self._max_value:
            return ValidationResult(valid=False, error=f"Value {value} above maximum {self._max_value}")
        
        return ValidationResult(valid=True)


class StringValidator(Validator):
    """Validador de strings."""
    
    def __init__(
        self,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
        allow_empty: bool = False,
        allow_none: bool = False
    ):
        self._min_length = min_length
        self._max_length = max_length
        self._pattern = re.compile(pattern) if pattern else None
        self._allow_empty = allow_empty
        self._allow_none = allow_none
    
    def validate(self, value: Any) -> ValidationResult:
        if value is None:
            if self._allow_none:
                return ValidationResult(valid=True)
            return ValidationResult(valid=False, error="Value cannot be None")
        
        if not isinstance(value, str):
            return ValidationResult(valid=False, error=f"Expected string, got {type(value).__name__}")
        
        if not value and not self._allow_empty:
            return ValidationResult(valid=False, error="String cannot be empty")
        
        if self._min_length is not None and len(value) < self._min_length:
            return ValidationResult(valid=False, error=f"String length {len(value)} below minimum {self._min_length}")
        
        if self._max_length is not None and len(value) > self._max_length:
            return ValidationResult(valid=False, error=f"String length {len(value)} above maximum {self._max_length}")
        
        if self._pattern and not self._pattern.match(value):
            return ValidationResult(valid=False, error=f"String does not match required pattern")
        
        return ValidationResult(valid=True)


class ListValidator(Validator):
    """Validador de listas."""
    
    def __init__(
        self,
        item_validator: Optional[Validator] = None,
        min_items: Optional[int] = None,
        max_items: Optional[int] = None,
        allow_none: bool = False
    ):
        self._item_validator = item_validator
        self._min_items = min_items
        self._max_items = max_items
        self._allow_none = allow_none
    
    def validate(self, value: Any) -> ValidationResult:
        if value is None:
            if self._allow_none:
                return ValidationResult(valid=True)
            return ValidationResult(valid=False, error="Value cannot be None")
        
        if not isinstance(value, list):
            return ValidationResult(valid=False, error=f"Expected list, got {type(value).__name__}")
        
        if self._min_items is not None and len(value) < self._min_items:
            return ValidationResult(valid=False, error=f"List length {len(value)} below minimum {self._min_items}")
        
        if self._max_items is not None and len(value) > self._max_items:
            return ValidationResult(valid=False, error=f"List length {len(value)} above maximum {self._max_items}")
        
        if self._item_validator:
            for i, item in enumerate(value):
                result = self._item_validator.validate(item)
                if not result.valid:
                    return ValidationResult(valid=False, error=f"Item {i}: {result.error}")
        
        return ValidationResult(valid=True)


class EnumValidator(Validator):
    """Validador de enum."""
    
    def __init__(self, enum_class: Type[Enum], allow_none: bool = False):
        self._enum_class = enum_class
        self._allow_none = allow_none
    
    def validate(self, value: Any) -> ValidationResult:
        if value is None:
            if self._allow_none:
                return ValidationResult(valid=True)
            return ValidationResult(valid=False, error="Value cannot be None")
        
        if not isinstance(value, self._enum_class):
            try:
                value = self._enum_class(value)
            except (ValueError, TypeError):
                valid_values = [e.value for e in self._enum_class]
                return ValidationResult(valid=False, error=f"Invalid value. Expected one of: {valid_values}")
        
        return ValidationResult(valid=True)


class ChoiceValidator(Validator):
    """Validador de opciones predefinidas."""
    
    def __init__(self, choices: List[Any], allow_none: bool = False):
        self._choices = choices
        self._allow_none = allow_none
    
    def validate(self, value: Any) -> ValidationResult:
        if value is None:
            if self._allow_none:
                return ValidationResult(valid=True)
            return ValidationResult(valid=False, error="Value cannot be None")
        
        if value not in self._choices:
            return ValidationResult(valid=False, error=f"Invalid choice. Expected one of: {self._choices}")
        
        return ValidationResult(valid=True)


class PathValidator(Validator):
    """Validador de paths."""
    
    def __init__(
        self,
        must_exist: bool = False,
        must_be_file: bool = False,
        must_be_dir: bool = False,
        allow_none: bool = False
    ):
        self._must_exist = must_exist
        self._must_be_file = must_be_file
        self._must_be_dir = must_be_dir
        self._allow_none = allow_none
    
    def validate(self, value: Any) -> ValidationResult:
        if value is None:
            if self._allow_none:
                return ValidationResult(valid=True)
            return ValidationResult(valid=False, error="Value cannot be None")
        
        if not isinstance(value, (str,)):
            return ValidationResult(valid=False, error=f"Expected path string, got {type(value).__name__}")
        
        import os
        path = value
        
        if self._must_exist and not os.path.exists(path):
            return ValidationResult(valid=False, error=f"Path does not exist: {path}")
        
        if self._must_be_file and os.path.exists(path) and not os.path.isfile(path):
            return ValidationResult(valid=False, error=f"Path is not a file: {path}")
        
        if self._must_be_dir and os.path.exists(path) and not os.path.isdir(path):
            return ValidationResult(valid=False, error=f"Path is not a directory: {path}")
        
        return ValidationResult(valid=True)


class CompositeValidator(Validator):
    """Validador combinable con AND/OR."""
    
    def __init__(self, validators: List[Validator], mode: str = "and"):
        self._validators = validators
        self._mode = mode
    
    def validate(self, value: Any) -> ValidationResult:
        if self._mode == "and":
            for validator in self._validators:
                result = validator.validate(value)
                if not result.valid:
                    return result
            return ValidationResult(valid=True)
        else:
            errors = []
            for validator in self._validators:
                result = validator.validate(value)
                if result.valid:
                    return ValidationResult(valid=True)
                errors.append(result.error)
            return ValidationResult(valid=False, error="; ".join(errors))


def validate_value(value: Any, validators: Union[Validator, List[Validator]]) -> ValidationResult:
    """
    Helper para validar un valor.
    
    Uso:
        result = validate_value(42, [TypeValidator(int), RangeValidator(min=0, max=100)])
        if not result.valid:
            print(result.error)
    """
    if isinstance(validators, Validator):
        validators = [validators]
    
    for validator in validators:
        result = validator.validate(value)
        if not result.valid:
            return result
    
    return ValidationResult(valid=True)
