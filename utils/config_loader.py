"""
Config Loader
=============
Cargador de configuración con soporte para múltiples fuentes.

Proporciona:
- Carga desde JSON, YAML, ENV
- Variables de entorno
- Valores por defecto
- Validación de schemas
- Hot reload opcional
"""

from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import os
import json
import threading
import copy


class ConfigSource(Enum):
    """Fuente de configuración."""
    FILE_JSON = "json"
    FILE_YAML = "yaml"
    FILE_ENV = "env"
    ENVIRONMENT = "environment"
    DEFAULT = "default"


@dataclass
class ConfigValue:
    """Valor de configuración con metadata."""
    value: Any
    source: ConfigSource
    key: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConfigSchema:
    """Schema de validación para configuración."""
    key: str
    value_type: type
    required: bool = False
    default: Any = None
    validator: Optional[Callable[[Any], bool]] = None
    description: str = ""


class ConfigLoader:
    """
    Cargador de configuración unificado.
    
    Uso:
        config = ConfigLoader()
        
        # Cargar desde archivos
        config.load_json('config.json')
        config.load_yaml('config.yaml')
        
        # Cargar desde env
        config.load_env('APP_')
        
        # Obtener con defaults
        value = config.get('database.host', default='localhost')
        
        # Validar schema
        config.validate_schema([
            ConfigSchema('port', int, required=True),
            ConfigSchema('debug', bool, default=False),
        ])
    """
    
    def __init__(self):
        self._config: Dict[str, ConfigValue] = {}
        self._lock = threading.RLock()
        self._schemas: List[ConfigSchema] = []
        self._file_paths: List[str] = []
        self._watchers: Dict[str, List[Callable]] = {}
    
    def load_json(self, path: str) -> None:
        """
        Cargar configuración desde JSON.
        
        Args:
            path: Ruta al archivo JSON
        """
        with self._lock:
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                self._merge_flat(data, ConfigSource.FILE_JSON)
                self._file_paths.append(path)
            except FileNotFoundError:
                pass
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in {path}: {e}")
    
    def load_yaml(self, path: str) -> None:
        """
        Cargar configuración desde YAML.
        
        Args:
            path: Ruta al archivo YAML
        """
        with self._lock:
            try:
                import yaml
                with open(path, 'r') as f:
                    data = yaml.safe_load(f)
                if data:
                    self._merge_flat(data, ConfigSource.FILE_YAML)
                self._file_paths.append(path)
            except ImportError:
                raise ImportError("PyYAML not installed. Run: pip install pyyaml")
            except FileNotFoundError:
                pass
    
    def load_env(self, prefix: str = "") -> None:
        """
        Cargar configuración desde variables de entorno.
        
        Args:
            prefix: Prefijo para filtrar variables (ej: 'APP_')
        """
        with self._lock:
            for key, value in os.environ.items():
                if prefix and not key.startswith(prefix):
                    continue
                
                config_key = key[len(prefix):].lower().replace('_', '.')
                
                parsed_value = self._parse_env_value(value)
                
                self._config[config_key] = ConfigValue(
                    value=parsed_value,
                    source=ConfigSource.ENVIRONMENT,
                    key=config_key
                )
    
    def load_dict(self, data: Dict[str, Any], source: ConfigSource = ConfigSource.DEFAULT) -> None:
        """
        Cargar configuración desde dict.
        
        Args:
            data: Diccionario de configuración
            source: Fuente de los datos
        """
        with self._lock:
            self._merge_flat(data, source)
    
    def get(
        self,
        key: str,
        default: Any = None,
        value_type: Optional[type] = None
    ) -> Any:
        """
        Obtener valor de configuración.
        
        Args:
            key: Clave (soporta path con puntos)
            default: Valor por defecto
            value_type: Tipo esperado para casting
        
        Returns:
            Valor de configuración o default
        """
        with self._lock:
            value = self._get_nested(key)
            
            if value is None:
                return default
            
            if value_type and not isinstance(value, value_type):
                try:
                    return value_type(value)
                except (ValueError, TypeError):
                    return default
            
            return value
    
    def set(
        self,
        key: str,
        value: Any,
        source: ConfigSource = ConfigSource.DEFAULT
    ) -> None:
        """
        Setear valor de configuración.
        
        Args:
            key: Clave
            value: Valor
            source: Fuente
        """
        with self._lock:
            old_value = self.get(key)
            
            self._config[key] = ConfigValue(
                value=copy.deepcopy(value),
                source=source,
                key=key
            )
            
            self._notify_watchers(key, old_value, value)
    
    def has(self, key: str) -> bool:
        """Verificar si existe clave."""
        with self._lock:
            return key in self._config
    
    def get_source(self, key: str) -> Optional[ConfigSource]:
        """Obtener fuente de una clave."""
        with self._lock:
            config_value = self._config.get(key)
            return config_value.source if config_value else None
    
    def get_all(self) -> Dict[str, Any]:
        """Obtener toda la configuración como dict."""
        with self._lock:
            return {k: v.value for k, v in self._config.items()}
    
    def clear(self) -> None:
        """Limpiar toda la configuración."""
        with self._lock:
            self._config.clear()
    
    def validate_schema(self, schemas: List[ConfigSchema]) -> List[str]:
        """
        Validar configuración contra schemas.
        
        Args:
            schemas: Lista de ConfigSchema a validar
        
        Returns:
            Lista de errores (vacía si todo OK)
        """
        errors = []
        
        for schema in schemas:
            value = self.get(schema.key)
            
            if value is None:
                if schema.required:
                    errors.append(f"Required key '{schema.key}' is missing")
                elif schema.default is not None:
                    self.set(schema.key, schema.default, ConfigSource.DEFAULT)
            else:
                if schema.validator and not schema.validator(value):
                    errors.append(f"Validation failed for '{schema.key}': {schema.description}")
                
                if schema.value_type and not isinstance(value, schema.value_type):
                    try:
                        casted = schema.value_type(value)
                        self.set(schema.key, casted, ConfigSource.DEFAULT)
                    except (ValueError, TypeError):
                        errors.append(f"Type mismatch for '{schema.key}': expected {schema.value_type.__name__}")
        
        return errors
    
    def watch(self, key: str, callback: Callable[[str, Any, Any], None]) -> None:
        """
        Observar cambios en una clave.
        
        Args:
            key: Clave a monitorear
            callback: Función llamada en cambio (key, old_value, new_value)
        """
        with self._lock:
            if key not in self._watchers:
                self._watchers[key] = []
            self._watchers[key].append(callback)
    
    def unwatch(self, key: str, callback: Callable) -> None:
        """Dejar de observar cambios."""
        with self._lock:
            if key in self._watchers:
                self._watchers[key] = [c for c in self._watchers[key] if c != callback]
    
    def reload(self) -> None:
        """Recargar archivos de configuración."""
        with self._lock:
            self._config.clear()
            
            for path in self._file_paths:
                if path.endswith('.json'):
                    self.load_json(path)
                elif path.endswith(('.yaml', '.yml')):
                    self.load_yaml(path)
    
    def _merge_flat(
        self,
        data: Dict[str, Any],
        source: ConfigSource
    ) -> None:
        """Merge diccionario plano a configuración."""
        for key, value in data.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    full_key = f"{key}.{sub_key}"
                    self._config[full_key] = ConfigValue(
                        value=copy.deepcopy(sub_value),
                        source=source,
                        key=full_key
                    )
            else:
                self._config[key] = ConfigValue(
                    value=copy.deepcopy(value),
                    source=source,
                    key=key
                )
    
    def _get_nested(self, key: str) -> Any:
        """Obtener valor anidado (soporta 'a.b.c')."""
        if key in self._config:
            return copy.deepcopy(self._config[key].value)
        
        keys = key.split('.')
        current = self._config
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        
        return copy.deepcopy(current)
    
    def _parse_env_value(self, value: str) -> Any:
        """Parsear valor de environment variable."""
        value = value.strip()
        
        if value.lower() in ('true', 'yes', '1', 'on'):
            return True
        if value.lower() in ('false', 'no', '0', 'off'):
            return False
        if value.lower() == 'null' or value.lower() == 'none' or value == '':
            return None
        
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            return value
    
    def _notify_watchers(self, key: str, old_value: Any, new_value: Any) -> None:
        """Notificar watchers de un cambio."""
        for watch_key, callbacks in self._watchers.items():
            if watch_key == key or (watch_key.endswith('.*') and key.startswith(watch_key[:-2])):
                for callback in callbacks:
                    try:
                        callback(key, old_value, new_value)
                    except Exception:
                        pass


def load_config(path: str) -> Dict[str, Any]:
    """Helper para cargar config desde archivo."""
    loader = ConfigLoader()
    
    if path.endswith('.json'):
        loader.load_json(path)
    elif path.endswith(('.yaml', '.yml')):
        loader.load_yaml(path)
    else:
        raise ValueError(f"Unsupported config format: {path}")
    
    return loader.get_all()
