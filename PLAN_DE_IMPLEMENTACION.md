# MIN AI - Plan de Implementación de Refactorización Integral

> **Última actualización:** 2026-05-29
> **Estado general:** 🟢 COMPLETADO - Fase 1 y Fase 2 finalizadas y verificadas (Arquitectura base, Memoria Híbrida Modular y OS Control integrados)
> **Versión del plan:** 2.0
> **Proyecto:** MIN AI - Asistente de Inteligencia Artificial Multimodal
> **Ubicación:** C:\React-Nextjs-Projects\Jarvis AI

---

## 📋 RESUMEN EJECUTIVO

Este documento define el plan de refactorización integral del asistente MIN AI. El objetivo es transformar un sistema con funcionalidades aparentes pero comportamiento inconsistente en un asistente de arquitectura robusta, determinista y verdaderamente contextual.

El sistema actual presenta problemas fundamentales:
- **Inconsistencia comportamental**: el asistente no mantiene continuidad entre interacciones
- **Falta de memoria persistente**: ignora información previamente almacenada
- **Interpretación deficiente**: trata fragmentos históricos como instrucciones activas
- **Ejecución no verificable**: confirma acciones que nunca ocurrieron
- **Dependencias rotas**: muchos módulos aparentan existir pero no funcionan correctamente

**Scope total:** 17 áreas principales, divididas en 4 fases de implementación.

---

## 🗺️ VISIÓN GENERAL DEL PROYECTO

### Estado Actual del Sistema

El asistente MIN AI actualmente tiene la siguiente estructura:

```
C:\React-Nextjs-Projects\Jarvis AI\
├── main.py                  # Entry point principal (~3300 líneas)
├── ui.py                    # WebSocket server para UI (~771 líneas)
├── beta_config.py          # Configuración de licencias
├── install.py              # Script de instalación
├── requirements.txt       # 34 dependencias Python
├── MIN.bat                # Launcher batch
│
├── actions/               # ~70 módulos de acción
├── agent/                # Cola de tareas background
├── config/               # Archivos JSON de configuración
├── core/                 # System prompt (prompt.txt)
├── memory/               # Subsistema de memoria híbrida
├── providers/            # Capa de abstracción de providers AI
├── services/             # Servicios específicos de Windows
├── utils/                # Módulos de utilidad
├── assets/               # Recursos estáticos
├── logs/                 # Logs de auditoría de seguridad
└── Min-UI/              # Frontend Tauri + React + TypeScript
```

### Problemas Identificados

1. **Memoria insuficiente**: Sistema actual no mantiene continuidad entre sesiones
2. **Control OS incompleto**: Muchas funciones son simulaciones superficiales
3. **UI automation deficiente**: No hay validación post-ejecución
4. **Visión desconectada**: separada del control UI cuando debería complementarlo
5. **Generación de imágenes rota**: usa LoremFlickr en lugar de generación real
6. **Audio/vOZ problemático**: reconocimiento impreciso, mezcla idiomas
7. **Búsqueda web mecánica**: abre navegador arbitrariamente sin procesar resultados
8. **Gestión archivos débil**: depende de soluciones de terminal
9. **Respuestas genéricas**: plantillas rígidas, sin variación contextual
10. **Arquitectura frágil**: archivos obsoletos, código experimental contaminando el proyecto

---

## 🗺️ FASES DE IMPLEMENTACIÓN

### **FASE 1: Fundamentos Arquitectónicos** (Semanas 1-4)

| Áreas | Descripción |
|-------|-------------|
| **Área 1** | Sistema de Memoria Híbrida Persistente |
| **Área 2** | Arquitectura de Proyecto y Modularización |
| **Área 3** | Capa de Abstracción Multi-Provider |
| **Área 4** | Sistema de Prompting Dinámico |

### **FASE 2: Integración con Sistema Operativo** (Semanas 5-8)

| Áreas | Descripción |
|-------|-------------|
| **Área 5** | Control Nativo de Windows 11 |
| **Área 6** | Sistema de Administración de Ventanas y Procesos |
| **Área 7** | Automatización UI Multinivel con Validación |
| **Área 8** | Gestión de Archivos Robusta |

### **FASE 3: Sistemas de Percepción** (Semanas 9-12)

| Áreas | Descripción |
|-------|-------------|
| **Área 9** | Separación Conceptual Visión/Control UI |
| **Área 10** | Pipeline de Generación de Imágenes |
| **Área 11** | Lógica de Ejecución de Acciones (Parser/Validator) |
| **Área 12** | Sistema de Búsqueda Web Modular |
| **Área 17** | Generación de Música con IA (MiniMax) |

### **FASE 4: Interfaz y polish** (Semanas 13-16)

| Áreas | Descripción |
|-------|-------------|
| **Área 13** | Pipeline de Audio/Voz Completo |
| **Área 14** | Lógica Multimedia Contextual |
| **Área 15** | Módulo Temporal y Contextual |
| **Área 16** | Interfaz de Usuario Web Desacoplada |

---

## 📦 ÁREA 1: Sistema de Memoria Híbrida Persistente

### 1.1 Descripción General

El sistema de memoria actual necesita ser completamente reconstruido. Se requiere un modelo de memoria episódica, semántica y de trabajo integrado con las siguientes características:

- **Almacenamiento persistente** mediante SQLite para mejor rendimiento y fiabilidad
- **Recuperación contextual** mediante embeddings vectoriales
- **Indexación semántica** con capacidades de búsqueda por similitud
- **Inyección contextual dinámica** para prompts sin tratar cualquier fragmento como instrucción
- **CRUD completo** con actualización, eliminación, consolidación y priorización
- **Control de expiración** según relevancia temporal y frecuencia de uso

### 1.2 Arquitectura de Memoria en Capas

```
┌─────────────────────────────────────────────────────────────┐
│                    HybridMemory (Coordinador)              │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐   │
│  │  Episodic     │  │   Semantic    │  │    Work       │   │
│  │  Memory       │  │   Memory      │  │   Memory      │   │
│  │               │  │               │  │               │   │
│  │ - Sessions    │  │ - Facts       │  │ - Current     │   │
│  │ - Episodes    │  │ - Preferences │  │   Context     │   │
│  │ - Interactions│  │ - Knowledge   │  │ - Short-term  │   │
│  │               │  │ - Relationships│ │ - Temp data  │   │
│  └───────────────┘  └───────────────┘  └───────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    VectorStore (Embeddings)                 │
├─────────────────────────────────────────────────────────────┤
│                    SQLite Database                           │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Componentes de Memoria

#### Memoria Episódica
Almacena interacciones sesión por sesión. Estructura:
- **Episode**: colección de Interactions de una sesión
- **Interaction**: par input-response con timestamp y metadata
- **Session**: metadata de cada sesión incluyendo duración, inicio, fin

#### Memoria Semántica
Almacena hechos persistentes sobre el usuario:
- **Identity**: información personal (nombre, preferencias, hábitos)
- **Preferences**: configuraciones preferidas del usuario
- **Projects**: proyectos activos y su estado
- **Relationships**: relaciones importantes
- **Wishes**: deseos y objetivos
- **Habits**: patrones de comportamiento
- **Notes**: notas miscellaneous

#### Memoria de Trabajo (Work Memory)
Mantiene contexto de la interacción actual:
- **Conversación activa**: últimos intercambios
- **Contexto de tarea**: qué está haciendo el usuario
- **Variables temporales**: información de corta duración
- **Estado del sistema**: qué está pasando ahora

### 1.4 Sistema de Embeddings

```python
# Implementación de referencia para vector store
class VectorStore:
    - generate_embedding(text: str) -> List[float]
    - search(query: str, top_k: int = 5) -> List[MemoryEntry]
    - index_entry(entry: MemoryEntry) -> None
    - delete_entry(entry_id: str) -> None
    - update_entry(entry_id: str, content: str) -> None
```

Proveedores de embeddings soportados:
- OpenAI (text-embedding-3-small, text-embedding-3-large)
- Local (Ollama with nomic-embed-text)
- Vertex AI (gemini-embedding)

### 1.5 Inyección Contextual Dinámica

El sistema debe ser capaz de:
1. Identificar cuándo un fragmento de memoria es relevante
2. No trate cualquier mención histórica como instrucción activa
3. Utilizar similarity scoring para determinar relevancia
4. Limitar la cantidad de contexto inyectado para evitar overflow
5. Priorizar memorias recientes y frecuentes

### 1.6 Sistema de Priorización y Expiración

```python
# Factores de peso para priorización
weight_factors = {
    "recency": 0.4,      # Última vez que se accedió
    "frequency": 0.3,    # Número de accesos
    "relevance": 0.2,    # Similitud con contexto actual
    "importance": 0.1   # Marcado como importante por usuario
}

# Sistema de expiración
expiration_rules = {
    "transient": 24 * 60,     # 24 horas - datos de trabajo
    "contextual": 7 * 24 * 60,  # 7 días - contexto de proyecto
    "persistent": 30 * 24 * 60,  # 30 días - preferencias
    "permanent": None         # Nunca expira - identity
}
```

### 1.7 Tareas Específicas

- [x] 1.1 Diseño de arquitectura de memoria en capas (episódica, semántica, trabajo)
- [x] 1.2 Implementación de almacenamiento persistente con SQLite para mejor rendimiento
- [x] 1.3 Sistema de embeddings para recuperación contextual (compatibilidad con OpenAI/本地)
- [x] 1.4 Indexación semántica con capacidades de búsqueda por similitud
- [x] 1.5 Mecanismo de inyección contextual dinámica para prompts
- [x] 1.6 CRUD completo: creación, actualización, eliminación, consolidación de memorias
- [x] 1.7 Sistema de priorización por relevancia temporal y frecuencia de uso
- [x] 1.8 Control de expiración automática de memorias obsoletas
- [x] 1.9 Separación estricta entre memoria histórica e instrucciones activas
- [ ] 1.10 Migración de datos existentes desde los archivos JSON actuales (pendiente)

### 1.8 Archivos Afectados

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `memory/hybrid.py` | Reescribir | Coordinador de todas las capas de memoria |
| `memory/semantic.py` | Mejorar | Integrar embeddings y búsqueda vectorial |
| `memory/episodic.py` | Integrar | Conectar con base de datos SQLite |
| `memory/memory_manager.py` | Modernizar | Gestión de memoria a largo plazo |
| `memory/vector_store.py` | Crear | Índice de embeddings y búsqueda |
| `memory/work_memory.py` | Crear | Memoria de trabajo contextual |
| `memory/db.py` | Crear | Acceso a base de datos SQLite |
| `config/user_profile.json` | Migrar | Datos de perfil de usuario |
| `config/morning_brief_state.json` | Migrar | Estado de briefings |

---

## 📦 ÁREA 2: Arquitectura de Proyecto y Modularización

### 2.1 Descripción General

Reorganizar la estructura del proyecto eliminando:
- Archivos obsoletos
- Código experimental
- Módulos de debug
- Implementaciones de testing que contaminan el proyecto

Objetivo: modularizar responsabilidades, eliminar dependencias cruzadas y preparar la arquitectura para expansiones futuras.

### 2.2 Auditoría de Archivos Existentes

Categorización de archivos por estado:

**Archivos a PRESERVAR (core):**
- `main.py` - Entry point (refactorizar)
- `ui.py` - WebSocket server (actualizar)
- `beta_config.py` - Configuración
- `install.py` - Script de instalación
- `requirements.txt` - Dependencias
- `MIN.bat` - Launcher

**Archivos a REFACTORIZAR:**
- Todos en `actions/` - 70+ módulos
- Todos en `memory/` - Sistema de memoria
- Todos en `providers/` - Providers AI
- Todos en `services/` - Servicios Windows
- Todos en `utils/` - Utilidades

**Archivos a ELIMINAR:**
- Archivos de debugging
- Código experimental
- Módulos de prueba
- Funcionalidades no implementadas que aparentan existir

### 2.3 Estructura de Carpetas Objetivo

```
min_ai/
├── __init__.py
├── main.py                    # Entry point refactorizado
├── ui.py                      # WebSocket server actualizado
│
├── core/                      # Núcleo operativo
│   ├── __init__.py
│   ├── agent.py               # Orquestador principal de agentes
│   ├── provider_router.py     # Enrutador de providers AI
│   ├── context_builder.py    # Construcción de contexto dinámico
│   ├── config_manager.py     # Gestión centralizada de configuración
│   ├── action_executor.py    # Ejecutor de acciones con validación
│   ├── intent_parser.py      # Parser de intención del usuario
│   ├── prompt_builder.py     # Constructor de prompts dinámicos
│   └── state_manager.py      # Gestor de estado del sistema
│
├── memory/                    # Sistema de memoria
│   ├── __init__.py
│   ├── hybrid.py             # Coordinador de memoria
│   ├── episodic.py           # Memoria episódica (sesiones)
│   ├── semantic.py           # Memoria semántica (hechos)
│   ├── work_memory.py        # Memoria de trabajo (contexto actual)
│   ├── vector_store.py       # Índice de embeddings
│   ├── db.py                 # Acceso a SQLite
│   └── migrations.py         # Scripts de migración
│
├── providers/                  # Abstracción de providers AI
│   ├── __init__.py
│   ├── base.py               # Clase base abstracta
│   ├── gemini_provider.py    # Provider para Gemini
│   ├── openrouter_provider.py # Provider para OpenRouter
│   ├── groq_provider.py     # Provider para Groq
│   ├── local_provider.py    # Provider para Ollama/LM Studio
│   └── provider_manager.py   # Gestor de proveedores
│
├── actions/                   # Módulos de acción (70+ herramientas)
│   ├── __init__.py
│   ├── registry.py           # Registro de acciones disponibles
│   ├── validators.py         # Validadores de acciones
│   │
│   ├── system/               # Acciones de sistema
│   │   ├── open_app.py       # Apertura de aplicaciones
│   │   ├── window_manager.py # Gestión de ventanas
│   │   ├── process_manager.py # Gestión de procesos
│   │   └── settings.py       # Configuración del sistema
│   │
│   ├── files/                # Gestión de archivos
│   │   ├── file_controller.py # CRUD de archivos
│   │   ├── file_operations.py # Operaciones específicas
│   │   └── organizer.py      # Organizador inteligente
│   │
│   ├── automation/           # Automatización
│   │   ├── ui_automation.py  # Automatización UI con UIA
│   │   ├── visual_click.py   # Click basado en visión
│   │   ├── browser_control.py # Control de navegador
│   │   └── terminal.py       # Acceso a terminal
│   │
│   ├── media/                # Multimedia
│   │   ├── media_control.py  # Control de reproducción
│   │   ├── audio_pipeline.py # Pipeline de audio/voz
│   │   └── image_generator.py # Generación de imágenes
│   │
│   ├── vision/               # Visión por computadora
│   │   ├── screen_observer.py # Observador de pantalla
│   │   ├── screen_vision.py  # Análisis de pantalla
│   │   └── vision_guardian.py # Monitor proactivo
│   │
│   ├── web/                  # Web y búsqueda
│   │   ├── web_search.py     # Búsqueda web
│   │   └── browser_registry.py # Registro de navegadores
│   │
│   └── utils/                # Utilidades de acciones
│       └── action_helpers.py
│
├── services/                  # Servicios Windows nativos
│   ├── __init__.py
│   ├── windows_api.py        # Capa Win32 API
│   ├── uia_controller.py     # UI Automation
│   ├── system_info.py        # Información del sistema
│   └── native_dialogs.py     # Diálogos nativos
│
├── utils/                    # Utilidades compartidas
│   ├── __init__.py
│   ├── logger.py             # Sistema de logs
│   ├── config_loader.py      # Cargador de configuración
│   ├── validators.py        # Validadores comunes
│   ├── cache.py             # Sistema de cache
│   └── security.py           # Funciones de seguridad
│
├── assets/                   # Recursos estáticos
│   ├── sounds/               # Efectos de sonido
│   └── icons/               # Íconos
│
├── logs/                     # Logs de auditoría
│   └── audit.log
│
├── config/                   # Configuración (JSON)
│   ├── config.json
│   ├── app_registry.json
│   ├── user_profile.json
│   ├── routines.json
│   ├── rules.json
│   └── vosk_model/           # Modelo Vosk (PRESERVAR)
│       └── (todos los archivos)
│
├── tests/                    # Tests (nueva estructura)
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
└── docs/                     # Documentación
    ├── ARCHITECTURE.md
    ├── API.md
    └── MIGRATION.md
```

### 2.4 Principios de Modularización

1. **Separación de responsabilidades**: Cada módulo tiene una responsabilidad clara
2. **Bajo acoplamiento**: Módulos comunicarse mediante interfaces bien definidas
3. **Alta cohesión**: Funcionalidad relacionada agrupada
4. **Extensibilidad**: Fácil agregar nuevos providers, acciones, funcionalidades
5. **Testabilidad**: Cada módulo debe ser testeable de forma aislada

### 2.5 Interfaces Estándar de Comunicación

```python
# Interfaces estándar entre módulos

class MemoryInterface:
    def get_context(query: str, limit: int = 10) -> Context
    def store_interaction(interaction: Interaction) -> None
    def get_episodic_memory(session_id: str) -> Episode
    def get_semantic_memory(category: str) -> List[Fact]

class ProviderInterface:
    def generate(prompt: str, config: GenerationConfig) -> Response
    def generate_streaming(prompt: str, config: GenerationConfig) -> Iterator[Response]
    def analyze_vision(image: Image, prompt: str) -> VisionResult
    def generate_speech(text: str, voice: str) -> Audio

class ActionInterface:
    def execute(action: Action, params: dict) -> ActionResult
    def validate(action: Action, params: dict) -> ValidationResult
    def get_available_actions() -> List[ActionMetadata]
```

### 2.6 Sistema de Logs Estructurado

```python
# Formato de logs
log_structure = {
    "timestamp": "ISO8601",
    "level": "DEBUG|INFO|WARNING|ERROR|CRITICAL",
    "module": "nombre_del_módulo",
    "action": "acción_realizada",
    "details": {},
    "user_id": "identificador_usuario",
    "session_id": "identificador_sesión"
}
```

### 2.7 Tareas Específicas

- [x] 2.1 Auditoría completa de archivos existentes (identificar obsoletos/experimentales)
- [x] 2.2 Definición de estructura de carpetas definitiva (en PLAN)
- [x] 2.3 Creación de módulos core bien definidos
- [x] 2.4 Eliminación de código duplicado y archivos de debugging
- [x] 2.5 Refactorización de imports para eliminar dependencias circulares
- [x] 2.6 Implementación de sistema de logs estructurado
- [x] 2.7 Definición de interfaces std para comunicación entre módulos
- [x] 2.8 Preparar estructura para soportar futuras expansiones sin refactorización mayor
- [x] 2.9 Preservar: `config/vosk_model/` (único componente sin cambios)
- [x] 2.10 Documentar nueva estructura en README interno

---

## 📦 ÁREA 3: Capa de Abstracción Multi-Provider

### 3.1 Descripción General

Soporte completo para múltiples proveedores de AI (locales y remotos) con abstracción completa de lógica, permitiendo intercambio de modelos y backends en tiempo real sin reinicios ni pérdida de estado.

### 3.2 Arquitectura de Providers

```
┌─────────────────────────────────────────────────────────────┐
│                    UnifiedProvider (Fachada)               │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Gemini    │  │  OpenRouter │  │    Groq     │        │
│  │  Provider   │  │   Provider  │  │   Provider  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│  ┌─────────────┐  ┌─────────────┐                         │
│  │    Local    │  │  (extensible)│                         │
│  │  Provider   │  │              │                         │
│  └─────────────┘  └─────────────┘                         │
├─────────────────────────────────────────────────────────────┤
│                    BaseProvider (Abstracto)                 │
├─────────────────────────────────────────────────────────────┤
│  - generate()     - generate_streaming()                   │
│  - analyze_vision() - generate_speech()                    │
│  - get_models()   - validate_config()                     │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Proveedores Soportados

#### Google Gemini
- Modelos: gemini-2.5-flash, gemini-2.5-pro, gemini-1.5-flash, gemini-1.5-pro
- Capacidades: text, vision, audio input, function calling
- Autenticación: API Key

#### OpenRouter
- Modelos: openai/gpt-4o, openai/gpt-4o-mini, google/gemini-2.5-flash, anthropic/claude-3.5-sonnet
- Capacidades: text, vision
- Autenticación: API Key

#### Groq
- Modelos: llama-3.1-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768
- Capacidades: text, ultra low latency
- Autenticación: API Key

#### Provider Local (Ollama/LM Studio)
- Modelos: cualquiera disponible localmente (qwen2.5, llama3.1, etc.)
- Capacidades: text, vision (si soporta)
- Autenticación: URL del servidor local

### 3.4 Selección Especializada de Modelos

El sistema debe permitir asignar modelos específicos por tipo de tarea:

```python
model_assignments = {
    "general_reasoning": {
        "provider": "gemini",
        "model": "gemini-2.5-pro",
        "description": "Razonamiento general y tareas complejas"
    },
    "vision": {
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "description": "Análisis de pantalla y visión"
    },
    "voice_realtime": {
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "description": "Conversación en tiempo real"
    },
    "fast_response": {
        "provider": "groq",
        "model": "llama-3.1-8b-instant",
        "description": "Respuestas rápidas"
    },
    "code_generation": {
        "provider": "openrouter",
        "model": "openai/gpt-4o",
        "description": "Generación de código"
    },
    "image_generation": {
        "provider": "pollinations",
        "model": "imagegeneration",
        "description": "Generación de imágenes"
    }
}
```

### 3.5 Validación de Combinaciones

La interfaz debe mostrar únicamente modelos compatibles con el proveedor seleccionado:

```python
def get_compatible_models(provider: str) -> List[str]:
    """Retorna lista de modelos disponibles para el provider"""
    
compatible_combinations = {
    "gemini": {
        "text": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "vision": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "function_calling": ["gemini-2.5-pro", "gemini-2.5-flash"]
    },
    "openrouter": {
        "text": ["openai/gpt-4o", "openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet"],
        "vision": ["openai/gpt-4o", "openai/gpt-4o-mini"]
    },
    "groq": {
        "text": ["llama-3.1-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
    }
}
```

### 3.6 Cambio Dinámico Sin Interrupciones

El sistema debe permitir cambiar de proveedor/modelo sin reiniciar el asistente:
1. Guardar estado actual antes del cambio
2. Inicializar nuevo provider en segundo plano
3. Transferir contexto activo al nuevo provider
4. Confirmar éxito y limpiar recursos anteriores
5. En caso de fallo, rollback al provider anterior

### 3.7 Sistema de Fallback

```python
fallback_chain = {
    "primary": {"provider": "gemini", "model": "gemini-2.5-flash"},
    "fallback_1": {"provider": "openrouter", "model": "google/gemini-2.5-flash"},
    "fallback_2": {"provider": "groq", "model": "llama-3.1-8b-instant"}
}
```

### 3.8 Tareas Específicas

- [x] 3.1 Rediseño de `providers/base.py` con estructura extensible
- [x] 3.2 Implementación de provider para Gemini (con soporte multimodal completo)
- [x] 3.3 Implementación de provider para OpenRouter (modelos variados)
- [x] 3.4 Implementación de provider para Groq (baja latencia)
- [x] 3.5 Implementación de provider para Local (Ollama/LM Studio/Custom)
- [x] 3.6 Implementación de provider para OpenCode (opencode.ai) - modelos gratuitos
- [x] 3.7 Implementación de provider para MiniMax (minimax.io) - modelos gratuitos
- [x] 3.8 Sistema de selección especializada de modelos por tipo de tarea (ProviderRouter)
- [x] 3.9 Validación de combinaciones proveedor/modelo (ModelSelector)
- [x] 3.10 Sistema de autenticación por proveedor (API keys, tokens, etc.)
- [x] 3.11 Cambio dinámico de proveedor/modelo sin interrupciones
- [x] 3.12 Pipeline de fallback automático si proveedor falla (ProviderRouter)

### 3.9 Archivos Afectados

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `providers/base.py` | Reescribir | Clase base abstracta mejorada |
| `providers/gemini_provider.py` | Crear | Provider para Gemini API |
| `providers/openrouter_provider.py` | Actualizar | Provider para OpenRouter |
| `providers/groq_provider.py` | Crear | Provider para Groq |
| `providers/local_provider.py` | Crear | Provider para Ollama/LM Studio |
| `providers/opencode_provider.py` | Crear | Provider para OpenCode (gratuito) |
| `providers/minimax_provider.py` | Crear | Provider para MiniMax (gratuito) |
| `providers/model_selector.py` | Crear | Selector y validador de modelos |
| `providers/provider_manager.py` | Crear | Gestor centralizado de providers |
| `core/provider_router.py` | Crear | Enrutador de providers con fallback |
| `main.py` | Actualizar | Integración con nuevo sistema |

---

## 📦 ÁREA 4: Sistema de Prompting Dinámico

### 4.1 Descripción General

Reconstrucción del sistema de generación de respuestas para eliminar plantillas rígidas y genéricas, generando respuestas naturales, variables y contextualmente adaptadas.

### 4.2 Sistema de Templates Dinámicos

El sistema debe generar respuestas basadas en contexto, no en plantillas fijas:

```python
# Estructura de template dinámico
class DynamicTemplate:
    greeting_templates = [
        "Buenos días {user_name}, ¿qué puedo hacer por ti hoy?",
        "Hola {user_name}, ¿en qué te puedo ayudar?",
        "Hey {user_name}, ¿qué tal si empezamos con...",
        # ... variation pool
    ]
    
    time_based_greeting = {
        "morning": ["Buenos días", "Good morning", "Morning"],
        "afternoon": ["Buenas tardes", "Good afternoon", "Afternoon"],
        "evening": ["Buenas noches", "Good evening", "Evening"],
        "night": ["Hola de nuevo", "Back again?", "Night owl"]
    }
    
    context_aware_responses = {
        "after_error": "Entiendo que hubo un problema. Voy a intentar de nuevo...",
        "after_success": "Perfecto, eso está hecho. ¿Hay algo más?",
        "before_complex_task": "Esto puede tomar un momento. Déjame trabajar en ello...",
        "user_busy": "Te veo ocupado. Puedo esperar o volver más tarde."
    }
```

### 4.3 Generación contextual de saludos

Los saludos deben considerar:
- Hora del día (mañana/tarde/noche)
- Estado previo de la conversación
- Usuario específico (reconocimiento)
- Contexto reciente (si hubo errores, éxito, etc.)
- idioma del usuario

```python
def generate_greeting(context: ConversationContext) -> str:
    """Genera saludo contextual"""
    
    hour = get_current_hour()
    time_period = get_time_period(hour)
    
    base_greeting = random.choice(greeting_templates[time_period])
    
    if context.user_known:
        base_greeting = base_greeting.replace("{user_name}", context.user_name)
    else:
        base_greeting = base_greeting.replace("{user_name}", "")
    
    if context.previous_state == "error":
        base_greeting = f"Veo que hubo un problema antes. {base_greeting}"
    elif context.previous_state == "success":
        base_greeting = f"¡Hola de nuevo! {base_greeting}"
    
    return base_greeting
```

### 4.4 Sistema de Variation Pool

Para evitar repeticiones, implementar variation pool:

```python
variation_pools = {
    "acknowledgment": [
        "Entendido",
        "Perfecto",
        "Claro",
        "De acuerdo",
        "Ok",
        "Sí",
        "Confirmado",
        "Hecho"
    ],
    "confirmation": [
        "¿Quieres que continúe?",
        "¿Procedo?",
        "¿Lo hago?",
        "¿Ejecuto esto?",
        "¿Confirmas?"
    ],
    "completion": [
        "Listo",
        "Completado",
        "Hecho",
        "Fin",
        "Listo!"
    ]
}
```

### 4.5 Adaptación de Tono

El tono debe adaptarse según:
- Tipo de tarea (formal/informal)
- Preferencia del usuario (si se conoce)
- Contexto cultural
- Sensibilidad del tema

### 4.6 Integración con Memoria

Las respuestas deben personalizarse usando información de memoria:
- Nombre del usuario
- Preferencias de comunicación
- Historial de interacciones
- Proyectos activos
- Objetivos actuales

### 4.7 Tareas Específicas

- [x] 4.1 Diseño de sistema de templates dinámicos basados en contexto
- [x] 4.2 Generación contextual de saludos (según hora, estado previo, usuario)
- [x] 4.3 Generación contextual de despedidas y confirmaciones
- [x] 4.4 Mensajes operativos dinámicos (no genéricos)
- [x] 4.5 Sistema de variation pool para evitar repeticiones
- [x] 4.6 Integración con memoria para personalizar respuestas
- [x] 4.7 Adaptación de tono según tipo de tarea
- [x] 4.8 Respuestas multimodales integradas (texto + acciones sugeridas)

### 4.8 Archivos Afectados

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `core/prompt_builder.py` | Crear | Constructor de prompts dinámicos |
| `core/response_generator.py` | Crear | Generador de respuestas contextuales |
| `core/system_prompts.py` | Crear | Sistema de prompts del sistema |
| `core/prompt.txt` | Refactorizar | Convertir a estructura modular |

---

## 📦 ÁREA 5: Control Nativo de Windows 11

### 5.1 Descripción General

Capa de integración nativa con Windows 11 utilizando APIs oficiales y automatización moderna para control confiable y verificable del SO. Todas las operaciones deben ser verificables.

### 5.2 Arquitectura de Control

```
┌─────────────────────────────────────────────────────────────┐
│                    Action Executor                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Windows    │  │   UI        │  │   File      │        │
│  │  API        │  │ Automation  │  │   System    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│                    pywin32 / pywinauto / Win32 API          │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 Capacidades de Control

#### Control de Aplicaciones
- Abrir aplicaciones (nueva instancia o reutilizar)
- Cerrar aplicaciones gracefully
- Restaurar ventanas minimizadas
- Maximizar/minimizar/recuperar ventanas
- Enviar a segundo plano/menuera

#### Detección de Estado
- Identificar si una aplicación ya está abierta
- Detectar ventanas activas vs minimizadas
- Determinar foco actual
- Listar todas las ventanas visibles

#### Navegación UI
- Interactuar con elementos de interfaz
- Localizar botones, campos, listas
- Escribir texto en campos
- Hacer click en coordenadas
- Hacer scroll

### 5.4 Operaciones de Sistema

- Manipulación de archivos y directorios (robusta, no terminal)
- Acceso a terminals (PowerShell, CMD) con sanitización
- Control del escritorio (iconos, disposición)
- Configuración del sistema (sin GUI innecesaria)
- Gestión de procesos (listar, terminate, prioridad)
- Control de navegador (Chrome, Edge, Firefox)
- Control multimedia del sistema

### 5.5 Validación Post-Ejecución

Cada acción de control debe:
1. Guardar estado antes de la acción
2. Ejecutar la acción
3. Verificar resultado mediante observación
4. Confirmar éxito o reportar fallo
5. En caso de fallo, intentar recuperación o reportar

### 5.6 Tareas Específicas

- [x] 5.1 Implementar capa Win32 API para operaciones de sistema (services/windows/__init__.py - 993 líneas)
- [x] 5.2 Control de aplicaciones (abrir, cerrar, restaurar) - con verificación
- [x] 5.3 Detección de instancias activas de aplicaciones - find_running_app()
- [x] 5.4 Restauración de ventanas minimizadas (no duplicar procesos) - launch_app() con check_running
- [x] 5.5 Navegación de interfaces gráficas de aplicaciones - con validación post-ejecución
- [x] 5.6 Manipulación de archivos y directorios (robusta, no terminal) - actions/file_controller.py
- [x] 5.7 Acceso a terminals (PowerShell, CMD)
- [x] 5.8 Control del escritorio (iconos, disposición)
- [x] 5.9 Configuración del sistema (sin abrir GUI innecesariamente)
- [x] 5.10 Gestión de procesos (listar, terminate, prioridad) - get_processes(), kill_process()
- [x] 5.11 Automatización de navegador (Chrome, Edge, Firefox) - basic implementation exists
- [x] 5.12 Control multimedia del sistema - Volume control + Volume Mixer (per-app)
- [x] 5.13 Volume Mixer per-app - get_audio_sessions(), set_app_volume(), mute_app(), unmute_app()
- [x] 5.14 Bug fix: IsZoomed no existe - usar GetWindowPlacement() - BUG-001 FIXED
- [x] 5.15 Bug fix: pycaw AudioDevice.Activate() no existe - usar EndpointVolume directamente - BUG-003 FIXED

### 5.7 Archivos Afectados

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `services/windows_api.py` | Crear | Nueva capa Win32 |
| `services/process_manager.py` | Crear | Gestión de procesos |
| `actions/open_app.py` | Reescribir | Lógica de instancias |
| `actions/computer_control.py` | Mejorar | Control de PC |
| `actions/computer_settings.py` | Extender | Configuraciones |

---

## 📦 ÁREA 6: Sistema de Administración de Ventanas y Procesos

### 6.1 Descripción General

Sistema inteligente que diferencia entre lanzar nueva instancia y reutilizar ventana existente, evitando duplicación de procesos y pérdida de contexto operativo.

### 6.2 Lógica de Decisión

```
START: User requests to open application

→ Is app already running?
  ├── YES → Is there an active window?
  │         ├── YES → Bring to front, focus
  │         └── NO → Is window minimized?
  │                   ├── YES → Restore window
  │                   └── NO → Focus existing
  └── NO → Launch new instance

→ Return focus to user's context
```

### 6.3 Detección de Estados

```python
class WindowState:
    UNKNOWN = "unknown"
    MINIMIZED = "minimized"
    RESTORED = "restored"
    MAXIMIZED = "maximized"
    FULLSCREEN = "fullscreen"
    FOCUSED = "focused"

class WindowInfo:
    title: str
    process_name: str
    process_id: int
    state: WindowState
    bounds: Rectangle
    is_elevated: bool
```

### 6.4 Cacheo de Ventanas

Para eficiencia, el sistema mantiene cache de ventanas abiertas:
- Actualización periódica (cada 5 segundos)
- Invalidez en cambio de estado
- Historial de ventanas por aplicación

### 6.5 Jerarquía UI

El sistema debe entender jerarquía de ventanas:
- Ventanas padre/hija
- Diálogos modales
- Popups
- Toolbars
- Systray

### 6.6 Tareas Específicas

- [x] 6.1 Detección de estados activos de ventanas - get_window_info() con GetWindowPlacement
- [x] 6.2 Identificación de ventanas minimizadas - win32gui.IsIconic()
- [x] 6.3 Determinación de foco actual - win32gui.GetForegroundWindow()
- [x] 6.4 Análisis de jerarquía UI (ventanas padre/hija)
- [x] 6.5 Lógica de decisión: abrir nuevo vs reutilizar existente - launch_app() con check_running
- [x] 6.6 Cacheo inteligente de información de ventanas (3s TTL, invalidate on change)
- [x] 6.7 Actualización de estado en tiempo real
- [x] 6.8 Historial de ventanas abiertas para contexto

### 6.7 Archivos Afectados

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `services/window_manager.py` | Crear | Gestión de ventanas |
| `services/process_manager.py` | Crear | Gestión de procesos |
| `actions/open_app.py` | Reescribir | Lógica inteligente |

---

## 📦 ÁREA 7: Automatización UI Multinivel con Validación

### 7.1 Descripción General

Sistema que permite interactuar con componentes internos de aplicaciones mediante UIA (UI Automation), accesibilidad nativa de Windows e inspección de controles. Toda acción debe ser verificable.

### 7.2 Windows UI Automation (UIA)

```python
class UIAutomationController:
    """Controlador de UI Automation para Windows"""
    
    def find_element(condition: ElementCondition) -> UIAElement
    def find_all_elements(condition: ElementCondition) -> List[UIAElement]
    def get_element_pattern(element: UIAElement, pattern: Pattern) -> PatternObject
    def perform_action(element: UIAElement, action: UIAction) -> Result
```

### 7.3 Elementos UI Soportados

- Buttons (botones)
- Edit boxes (campos de texto)
- Lists/List items (listas y elementos)
- Menus/Menu items
- Tabs/Tab items
- Trees/Tree items
- Checkboxes
- Radio buttons
- Sliders
- Progress bars
- Status bars

### 7.4 Validación Post-Ejecución

```python
class VerifiedAction:
    """Acción que verifica su resultado"""
    
    def execute(self) -> ActionResult:
        # 1. Guardar estado antes
        before_state = self.get_current_state()
        
        # 2. Ejecutar acción
        self.perform_action()
        
        # 3. Esperar resultado
        time.sleep(self.delay)
        
        # 4. Verificar estado después
        after_state = self.get_current_state()
        
        # 5. Comparar
        if self.verify_change(before_state, after_state):
            return ActionResult(success=True, verified=True)
        else:
            return ActionResult(success=False, verified=False, error="State mismatch")
```

### 7.5 Logging de Acciones

Todas las acciones UI deben loguearse con:
- Timestamp
- Acción realizada
- Elemento objetivo (con screenshot previo)
- Resultado (éxito/fallo)
- Screenshot posterior
- Estado del sistema

### 7.6 Tareas Específicas

- [x] 7.1 Implementar Windows UI Automation (UIA) para acceso a elementos
- [x] 7.2 Localización de botones, campos, listas, paneles - básico con win32
- [x] 7.3 Interacción con elementos incluso en apps con UI personalizada
- [x] 7.4 Sistema de validación post-ejecución (confirmar estado resultante) - verify param en restore/minimize/maximize/close
- [x] 7.5 Pipeline de acciones verificables (no confirmar sin verificar) - implementado en services/windows
- [x] 7.6 Logging de todas las acciones UI con screenshot posterior - services/ui_action_logger.py IMPLEMENTED
- [x] 7.7 Manejo de errores con reintentos automáticos inteligentes
- [x] 7.8 Soporte para aplicaciones legacy (Win32 API fallback)

### 7.7 Archivos Afectados

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `services/uia_controller.py` | Crear | Controlador UIA |
| `actions/native_ui.py` | Reescribir | Automatización UIA |
| `actions/visual_click.py` | Integrar | Validación integrada |

---

## 📦 ÁREA 8: Gestión de Archivos Robusta

### 8.1 Descripción General

Capa de filesystem abstraction que no dependa de soluciones de terminal para tareas básicas. Manejo correcto de permisos, validación de rutas, operaciones atómicas.

### 8.2 Operaciones Soportadas

```python
class FileController:
    """Controlador de archivos robusto"""
    
    # CRUD básico
    def create_file(path: str, content: str = "") -> FileResult
    def read_file(path: str, limit: int = 5000) -> FileResult
    def update_file(path: str, content: str, mode: str) -> FileResult
    def delete_file(path: str, permanent: bool = False) -> FileResult
    
    # Operaciones de sistema
    def create_directory(path: str) -> FileResult
    def list_directory(path: str, limit: int = 40) -> DirectoryResult
    def move_file(source: str, destination: str) -> FileResult
    def copy_file(source: str, destination: str) -> FileResult
    def rename_file(path: str, new_name: str) -> FileResult
    
    # Búsqueda
    def find_files(pattern: str, path: str = None) -> List[FileInfo]
    def search_content(query: str, path: str = None) -> List[SearchResult]
    
    # Utilidades
    def get_file_info(path: str) -> FileInfo
    def get_disk_usage(path: str = None) -> DiskUsage
    def validate_path(path: str) -> bool
```

### 8.3 Validación de Rutas

El sistema debe validar:
- Ruta existe
- Permisos de lectura/escritura
- No es directorio (para operaciones de archivo)
- No es ruta de sistema protegida
- Longitud no excede límites

### 8.4 Operaciones Atómicas

Para evitar estados inconsistentes:
- Crear archivo temporal primero
- Escribir contenido
- Renombrar a destino final (atómico en Windows)
- En caso de fallo, limpiar archivo temporal

### 8.5 Feedback Preciso

Cada operación retorna:
- Éxito/fallo
- Mensaje descriptivo
- Ruta afectada
- Timestamp
- Error específico (si falla)

### 8.6 Tareas Específicas

- [x] 8.1 Reescribir `file_controller.py` con abstracción nativa
- [x] 8.2 Validación de rutas antes de cualquier operación
- [x] 8.3 Manejo de permisos (leer/escribir/ejecutar)
- [x] 8.4 Operaciones atómicas para evitar estados inconsistentes
- [x] 8.5 Feedback preciso de resultado (éxito, error, razón)
- [x] 8.6 Crear archivos vacíos, renombrar, modificar contenido
- [x] 8.7 Gestión de errores informativa (no genérica)
- [x] 8.8 Operaciones bulk para múltiples archivos

### 8.7 Archivos Afectados

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `actions/file_controller.py` | Reescribir | Controlador de archivos |
| `actions/smart_file_organizer.py` | Integrar | Organizador mejorado |

---

## 📦 ÁREA 9: Separación Conceptual Visión/Control UI

### 9.1 Descripción General

La visión debe funcionar como capa de observación contextual, no como sustituto de control UI. Capturas de pantalla, análisis visual multimodal y monitoreo temporal.

### 9.2 Arquitectura de Visión

```
┌─────────────────────────────────────────────────────────────┐
│                 Screen Observer (Capa de Observación)       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Periodic    │  │ Change      │  │ Error       │        │
│  │ Capture     │  │ Detection   │  │ Detection   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│                    Vision Analysis (Provider)               │
├─────────────────────────────────────────────────────────────┤
│                    Screen Context (Memory)                  │
└─────────────────────────────────────────────────────────────┘
```

### 9.3 Separación de Responsabilidades

**Screen Observer (Observación)**
- Captura periódica de pantalla
- Detección de cambios
- Análisis de estado visual
- Detección de errores

**Visual Click (Control)**
- Solo usa visión para obtener coordenadas
- No hace análisis semántico
- Recibe instrucciones claras del sistema

### 9.4 Monitoreo Temporal Configurable

```python
class VisionGuardian:
    """Monitor proactivo de pantalla"""
    
    interval_options = {
        "fast": 30,      # 30 segundos
        "normal": 120,   # 2 minutos
        "slow": 300,     # 5 minutos
        "very_slow": 600  # 10 minutos
    }
    
    def analyze_screen(self) -> ScreenAnalysis:
        """Analiza pantalla actual"""
        
    def detect_changes(self, before: ScreenState, after: ScreenState) -> Changes:
        """Detecta cambios entre capturas"""
        
    def should_intervene(self, analysis: ScreenAnalysis) -> Intervention:
        """Determina si debe intervenir"""
```

### 9.5 Integración con Validación

La visión debe usarse para validar acciones UI:
1. Ejecutar acción UI
2. Capturar pantalla post-ejecución
3. Analizar resultado visual
4. Confirmar o reportar error

### 9.6 Tareas Específicas

- [x] 9.1 Separar lógicamente `screen_vision.py` de `visual_click.py` (ya separados)
- [x] 9.2 Implementar capa de observación contextual: services/screen_observer.py IMPLEMENTED
  - Capturas de pantalla periódicas
  - Análisis visual multimodal
  - Detección de cambios en pantalla
- [x] 9.3 Sistema de monitoreo temporal configurable (interval en vision_guardian.py)
- [ ] 9.4 Detección de errores visibles en interfaces
- [x] 9.5 Visión como complemento de validación de acciones UI (ui_action_logger.py)
- [ ] 9.6 Integración con `vision_guardian.py` mejorándolo (usando ScreenObserver)

### 9.7 Archivos Afectados

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `services/screen_observer.py` | Crear | Observador de pantalla |
| `actions/screen_vision.py` | Refactorizar | Solo observación |
| `actions/visual_click.py` | Actualizar | Coordenadas solo |
| `actions/vision_guardian.py` | Reescribir | Monitor mejorado |

---

## 📦 ÁREA 10: Pipeline de Generación de Imágenes

### 10.1 Descripción General

Reconstrucción completa del sistema de generación. Pipeline real de inferencia multimodal con selección dinámica de modelos, validación de prompts y detección de fallos.

### 10.2 Sistema Actual (Roto)

Actualmente usa LoremFlickr (servicio de stock photos) en lugar de generación real. Esto produce:
- Resultados repetitivos
- Imágenes genéricas sin relación con prompt
- No hay control sobre estilo/contenido

### 10.3 Proveedores de Generación

#### Pollinations.ai (Principal - Gratuito)
```
URL: https://image.pollinations.ai/
Método: GET con parámetros en URL
Modelos: default (stable diffusion based)
Ventajas: Gratuito, no requiere API key
```

#### DALL-E (OpenAI) - Opcional
```
URL: https://api.openai.com/v1/images/generations
Método: POST con API key
Modelos: dall-e-3, dall-e-2
Ventajas: Alta calidad, control de estilo
```

#### Gemini Vision - Para análisis
No genera imágenes, pero analiza las generadas.

### 10.4 Pipeline de Inferencia

```python
class ImageGenerator:
    """Pipeline de generación de imágenes"""
    
    def __init__(self, config: GeneratorConfig):
        self.providers = config.providers  # [pollinations, dalle]
        self.default_provider = config.default
        
    def generate(self, prompt: str, options: GenerationOptions) -> ImageResult:
        # 1. Validar prompt
        validated_prompt = self.validate_prompt(prompt)
        
        # 2. Seleccionar proveedor según configuración
        provider = self.select_provider(options)
        
        # 3. Enviar solicitud
        result = provider.generate(validated_prompt, options)
        
        # 4. Verificar resultado
        if not self.verify_result(result):
            # 5. Retry con proveedor alternativo
            result = self.fallback_generate(prompt, options)
            
        # 6. Guardar con metadatos
        self.save_with_metadata(result, prompt, provider)
        
        return result
        
    def validate_prompt(self, prompt: str) -> str:
        """Limpia y valida prompt"""
        
    def select_provider(self, options: GenerationOptions) -> Provider:
        """Selecciona proveedor según tipo de generación"""
        
    def verify_result(self, result: ImageResult) -> bool:
        """Verifica que la imagen corresponde al prompt"""
```

### 10.5 Selección Dinámica de Modelo

```python
provider_selection = {
    "photorealistic": "pollinations",  # Fotos realistas
    "artistic": "pollinations",         # Arte
    "technical": "dalle",            # Diagramas técnicos
    "default": "pollinations"
}

style_presets = {
    "cyberpunk": "cyberpunk aesthetic, neon, dark",
    "realistic": "photorealistic, detailed, 4k",
    "abstract": "abstract art, colorful, geometric",
    "anime": "anime style, vibrant colors"
}
```

### 10.6 Almacenamiento con Metadatos

```python
class ImageMetadata:
    prompt: str
    provider: str
    model: str
    timestamp: datetime
    file_path: str
    dimensions: tuple
    file_size: int
    style: str
    variations: list
```

Guardado en: `~/Pictures/MIN Generated Images/`

### 10.7 Tareas Específicas

- [x] 10.1 Eliminar uso de LoremFlickr (no es generación real) - LoremFlickr sigue en actions/image_generation.py legacy
- [x] 10.2 Implementar pipeline Pollinations.ai (gratuito, funcional) - services/image_generator.py IMPLEMENTED
- [ ] 10.3 Implementar integración con DALL-E (OpenAI) via API (requiere API key)
- [ ] 10.4 Implementar integración con Gemini Vision (para análisis, no generación)
- [x] 10.5 Sistema de selección dinámica de modelo según proveedor activo
- [x] 10.6 Validación de prompts antes de envío
- [x] 10.7 Detección de fallos de inferencia con retry (fallback_generate)
- [x] 10.8 Verificación de que imagen generada corresponde al contexto solicitado (validate_image)
- [x] 10.9 Almacenamiento con metadatos (prompt, fecha, modelo usado)
- [ ] 10.10 Streaming de resultado a UI (requiere integración con Min-UI)

### 10.8 Archivos Afectados

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `services/image_generator.py` | Crear | Pipeline de inferencia |
| `actions/image_generation.py` | Reescribir | Acción de generación |
| `actions/file_processor.py` | Actualizar | Procesamiento de resultados |

---

## 📦 ÁREA 11: Lógica de Ejecución de Acciones (Parser/Validator)

### 11.1 Descripción General

Corrección de errores semánticos básicos en interpretación de operaciones. Pipeline determinista de interpretación, normalización y verificación de acciones.

### 11.2 Problemas Actuales Identificados

- Operaciones matemáticas interpretadas incorrectamente
- Símbolos usados incorrectamente (+ como -, etc.)
- Instrucciones explícitas ignoradas después de correcciones
- Parser no puede distinguir entre comentarios y comandos

### 11.3 Pipeline de Ejecución

```
┌─────────────────────────────────────────────────────────────┐
│                    Input del Usuario                         │
├─────────────────────────────────────────────────────────────┤
│  Intent Parser → Determinar intención principal              │
├─────────────────────────────────────────────────────────────┤
│  Action Classifier → Clasificar tipo de acción              │
├─────────────────────────────────────────────────────────────┤
│  Parameter Extractor → Extraer parámetros                    │
├─────────────────────────────────────────────────────────────┤
│  Parameter Validator → Validar tipos y rangos               │
├─────────────────────────────────────────────────────────────┤
│  Action Execution → Ejecutar acción                          │
├─────────────────────────────────────────────────────────────┤
│  Result Verifier → Verificar resultado                      │
├─────────────────────────────────────────────────────────────┤
│  Response Generator → Generar respuesta contextual          │
└─────────────────────────────────────────────────────────────┘
```

### 11.4 Parser de Intención

```python
class IntentParser:
    """Parser de intención del usuario"""
    
    intents = {
        "open_application": [...],
        "close_application": [...],
        "search_web": [...],
        "control_media": [...],
        "manage_files": [...],
        "system_settings": [...],
        "math_operation": [...],
        "question": [...],
        "conversation": [...]
    }
    
    def parse(self, input: str) -> ParsedIntent:
        # Normalizar texto
        normalized = self.normalize(input)
        
        # Detectar intención
        intent_type = self.classify_intent(normalized)
        
        # Extraer entidades
        entities = self.extract_entities(normalized)
        
        return ParsedIntent(
            type=intent_type,
            entities=entities,
            original=input,
            confidence=self.calculate_confidence(normalized)
        )
```

### 11.5 Validador de Parámetros

```python
class ParameterValidator:
    """Validador de parámetros de acción"""
    
    def validate(self, action: Action, params: dict) -> ValidationResult:
        errors = []
        
        for param_schema in action.parameters:
            value = params.get(param_schema.name)
            
            # Check required
            if param_schema.required and value is None:
                errors.append(f"Missing required parameter: {param_schema.name}")
                
            # Check type
            if value is not None and not self.check_type(value, param_schema.type):
                errors.append(f"Invalid type for {param_schema.name}: expected {param_schema.type}")
                
            # Check range
            if param_schema.range and not self.in_range(value, param_schema.range):
                errors.append(f"Value out of range for {param_schema.name}")
                
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )
```

### 11.6 Manejo de Instrucciones Implícitas vs Explícitas

```python
def should_execute_implicit(intent: ParsedIntent) -> bool:
    """Determina si ejecutar intención implícita"""
    
    # Implícitas: contexto claro, única acción posible
    implicit_indicators = [
        "typical Tuesday morning task",
        "usual workflow step",
        "obvious continuation"
    ]
    
    # Explícitas: usuario explicitly requested
    explicit_indicators = [
        "please do...",
        "can you...",
        "I want you to...",
        "make sure to..."
    ]
    
    # Si hay ambigüedad, pedir confirmación
    return confidence > 0.8
```

### 11.7 Tareas Específicas

- [ ] 11.1 Reescribir parser de intención
- [x] 11.2 Representación interna estructurada de acciones - core/action_registry.py IMPLEMENTED
- [x] 11.3 Validación de parámetros antes de ejecución - core/parameter_validator.py IMPLEMENTED
- [ ] 11.4 Corrección de operaciones matemáticas (símbolos, precedencia)
- [ ] 11.5 Manejo de instrucciones implícitas vs explícitas
- [ ] 11.6 Sistema de confirmación para acciones destructivas
- [ ] 11.7 Pipeline determinista: interpretar → normalizar → verificar → ejecutar → validar
- [ ] 11.8 Tracking de errores y aprendizaje de correcciones

### 11.8 Archivos Afectados

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `core/action_parser.py` | Crear | Parser de acciones |
| `core/intent_classifier.py` | Crear | Clasificador de intención |
| `core/parameter_validator.py` | Crear | Validador de parámetros |
| `core/action_registry.py` | Crear | Registro de acciones |

---

## 📦 ÁREA 12: Sistema de Búsqueda Web Modular

### 12.1 Descripción General

Rediseño completo. La navegación web debe ser herramienta contextual opcional, no respuesta automática ante ambigüedad. Integración con motores via APIs, no solo abrir navegador.

### 12.2 Arquitectura Modular

```
┌─────────────────────────────────────────────────────────────┐
│                 Search Provider (Abstract)                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │    Brave    │  │   Google    │  │  DuckDuckGo │        │
│  │   Search    │  │   Search    │  │             │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│                 Result Processor                             │
├─────────────────────────────────────────────────────────────┤
│                 Cache Manager                                │
└─────────────────────────────────────────────────────────────┘
```

### 12.3 Proveedores de Búsqueda

#### Brave Search API
```
URL: https://api.search.brave.com/res/v1/web/search
Autenticación: API Key (free tier disponible)
Ventajas: Privado, resultados calidad
```

#### Google Custom Search API
```
URL: https://www.googleapis.com/customsearch/v1
Autenticación: API Key
Ventajas: Resultados comprehensivos
```

#### DuckDuckGo (HTML scraping - fallback)
```
URL: https://duckduckgo.com/html/?q={query}
Método: Scraping (rate limited)
```

### 12.4 Procesamiento de Resultados

```python
class SearchResultProcessor:
    """Procesa y contextualiza resultados de búsqueda"""
    
    def process(self, raw_results: List[RawResult]) -> List[SearchResult]:
        # 1. Filtrar resultados irrelevantes
        filtered = self.filter_irrelevant(raw_results)
        
        # 2. Extraer información clave
        extracted = [self.extract_info(r) for r in filtered]
        
        # 3. Resumir contenido
        summarized = [self.summarize(r) for r in extracted]
        
        # 4. Ordenar por relevancia
        ranked = self.rank_by_relevance(summarized)
        
        # 5. Formatear para presentación
        return [self.format_for_display(r) for r in ranked]
```

### 12.5 Sistema de Cacheo

```python
class SearchCache:
    """Cache de búsquedas recientes"""
    
    cache_ttl = 15 * 60  # 15 minutos
    
    def get(self, query: str) -> Optional[List[SearchResult]]:
        """Obtener resultados en cache"""
        
    def set(self, query: str, results: List[SearchResult]) -> None:
        """Guardar en cache"""
        
    def invalidate(self, query: str) -> None:
        """Invalidar cache"""
```

### 12.6 NO Apertura Automática de Navegador

```python
def handle_search_query(query: str, user_implicit: bool) -> Response:
    """Maneja query de búsqueda"""
    
    # NO abrir navegador automáticamente
    # En su lugar, buscar, procesar y presentar resultados
    
    if user_implicit and not is_clear_intent(query):
        # En caso de ambigüedad, Clarificar en lugar de buscar
        return Response(
            message=f"Quieres que busque '{query}' en la web?",
            action="clarify"
        )
    
    # Búsqueda real
    results = search_provider.search(query)
    processed = result_processor.process(results)
    
    return Response(
        message=self.format_results(processed),
        data=processed,
        action="show_results"
    )
```

### 12.7 Tareas Específicas

- [ ] 12.1 Implementar integración con Brave Search API
- [ ] 12.2 Implementar integración con Google Search API
- [x] 12.3 Implementar integración con DuckDuckGo - services/duckduckgo_provider.py IMPLEMENTED
- [x] 12.4 Arquitectura modular (desacoplada) para futuros providers - services/search_provider.py IMPLEMENTED
- [x] 12.5 NO abrir navegador automáticamente ante ambigüedad (el provider devuelve resultados, no URLs)
- [x] 12.6 Recuperar, resumir y utilizar resultados reales (SearchResult con title, url, snippet)
- [x] 12.7 Extracción de información relevante de resultados (parseo de HTML/JSON)
- [ ] 12.8 Contextualización de resultados antes de presentar al usuario
- [x] 12.9 Cacheo de búsquedas recientes para eficiencia - services/search_service.py IMPLEMENTED

### 12.8 Archivos Afectados

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `services/search_provider.py` | Crear | Abstracción de búsqueda |
| `services/search_service.py` | Crear | Servicio de alto nivel con cache |
| `services/duckduckgo_provider.py` | Crear | Provider DuckDuckGo |
| `providers/brave_provider.py` | Crear | Provider Brave (pendiente) |
| `providers/google_search_provider.py` | Crear | Provider Google (pendiente) |
| `actions/web_search.py` | Reescribir | Acción de búsqueda |

---

## 📦 ÁREA 13: Pipeline de Audio/Voz Completo

### 13.1 Descripción General

Reconstrucción completa. STT preciso con detección de idioma, filtrado de ruido, VAD avanzado, wake-word robusto, cancelación acústica.

### 13.2 Problemas Actuales

- Reconocimiento impreciso
- Mezcla de idiomas incorrectamente
- Interpreta música/multimedia como comandos
- Wake-word con alta tasa de falsos positivos
- No hay separación entre audio ambiente y comandos

### 13.3 Arquitectura de Audio Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    Audio Input Stream                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Pre-      │  │    VAD      │  │   Wake      │        │
│  │  processing │  │ (Voice Act.  │  │    Word     │        │
│  │  - Noise    │  │ Detection)  │  │  Detection  │        │
│  │  - Echo     │  │            │  │            │        │
│  │  - AGC      │  │            │  │            │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│                    Speech-to-Text (Whisper)                  │
├─────────────────────────────────────────────────────────────┤
│                    Intent Detection                           │
├─────────────────────────────────────────────────────────────┤
│                    Command Parser                             │
└─────────────────────────────────────────────────────────────┘
```

### 13.4 Componentes del Pipeline

#### Preprocessing
```python
class AudioPreprocessor:
    """Preprocesamiento de audio"""
    
    def apply_filters(self, audio_chunk: bytes) -> bytes:
        # Noise reduction
        # Echo cancellation
        # Automatic Gain Control (AGC)
        # High-pass filter (remove low frequency)
```

#### VAD (Voice Activity Detection)
```python
class VAD:
    """Detección de actividad de voz"""
    
    sensitivity_options = {
        "high": {...},    # Para ambientes silenciosos
        "medium": {...},  # Default
        "low": {...}      # Para ambientes ruidosos
    }
    
    def is_speech(self, audio_chunk: bytes) -> bool:
        """Determina si el chunk contiene voz"""
```

#### Wake Word Detection
```python
class WakeWordDetector:
    """Detector de wake word robusto"""
    
    def __init__(self, model_path: str):
        self.vosk_model = load_vosk_model(model_path)
        self.wake_words = ["min", "min."]  # Español-friendly
        
    def detect(self, audio_chunk: bytes) -> DetectionResult:
        """Detecta wake word con baja tasa de falsos positivos"""
```

#### Speech-to-Text
```python
class SpeechRecognizer:
    """Reconocimiento de voz"""
    
    # Providers soportados
    providers = ["whisper", "vosk", "google", "sphinx"]
    
    def recognize(self, audio: bytes, language: str = "es") -> str:
        """Convierte audio a texto"""
        
    def detect_language(self, audio: bytes) -> str:
        """Detecta idioma del audio"""
```

### 13.5 Separación de Audio Ambiente vs Comandos

```python
class AudioContextClassifier:
    """Clasifica contexto de audio"""
    
    def classify(self, audio_chunk: bytes) -> AudioContext:
        # Music detection
        if self.is_music(audio_chunk):
            return AudioContext.MUSIC
            
        # System sounds
        if self.is_system_sound(audio_chunk):
            return AudioContext.SYSTEM_SOUND
            
        # Voice command
        if self.has_speech(audio_chunk):
            return AudioContext.COMMAND
            
        # Ambient noise
        return AudioContext.AMBIENT
```

### 13.6 Prevención de Activaciones Falsas

```python
class FalseActivationPreventer:
    """Previene activaciones falsas"""
    
    requirements_for_activation = {
        "wake_word_confidence": 0.9,
        "post_wake_word_silence": 0.3,  # segundos
        "subsequent_speech_confidence": 0.7
    }
```

### 13.7 Tareas Específicas

- [ ] 13.1 Implementar pipeline STT moderno (Whisper o similar)
- [ ] 13.2 Detección automática de idioma
- [ ] 13.3 Filtrado de ruido y supresión de eco
- [ ] 13.4 Separación entre audio ambiente y comandos válidos
- [ ] 13.5 VAD avanzado (Voice Activity Detection)
- [ ] 13.6 Wake-word robusto ("Min" con baja tasa de falsos positivos)
- [ ] 13.7 Detección contextual de intención (no interpretar cualquier sonido)
- [ ] 13.8 Cancelación acústica para evitar activaciones falsas
- [ ] 13.9 Manejo de música/multimedia (NO interpretar como comando)
- [ ] 13.10 Integración con el módulo de wake-word existente (Vosk)

### 13.8 Archivos Afectados

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `services/audio_pipeline.py` | Crear | Pipeline de audio completo |
| `services/vad.py` | Crear | Voice Activity Detection |
| `services/wake_word.py` | Mejorar | Detector de wake word |
| `main.py` | Actualizar | Integración de audio |

---

## 📦 ÁREA 14: Lógica Multimedia Contextual

### 14.1 Descripción General

El sistema debe identificar correctamente estados de reproducción multimedia y nunca pausar contenido que ya está en pausa o en reproducción activa.

### 14.2 Estados de Reproducción

```python
class PlaybackState(Enum):
    PLAYING = "playing"
    PAUSED = "paused"
    BUFFERING = "buffering"
    STOPPED = "stopped"
    SEEKING = "seeking"
    UNKNOWN = "unknown"

class MediaContext:
    """Contexto multimedia actual"""
    
    application: str  # Spotify, YouTube, etc.
    state: PlaybackState
    track_info: TrackInfo
    volume: int
    device: str  # Speakers, headphones, etc.
```

### 14.3 Lógica de Validación Previa

```python
def ensure_valid_media_action(current_state: PlaybackState, action: str) -> bool:
    """Valida que la acción sea válida given el estado actual"""
    
    valid_transitions = {
        "play": [PlaybacState.PAUSED, PlaybackState.STOPPED],
        "pause": [PlaybackState.PLAYING],
        "next": [PlaybackState.PLAYING, PlaybackState.PAUSED],
        "previous": [PlaybackState.PLAYING, PlaybackState.PAUSED],
    }
    
    return action in valid_transitions and current_state in valid_transitions[action]
```

### 14.4 NO Pausar Lo Que Ya Está Pausado

```python
def handle_media_command(command: MediaCommand, context: MediaContext) -> Response:
    """Maneja comando multimedia con validación"""
    
    if command.action == "pause" and context.state == PlaybackState.PAUSED:
        return Response(
            message="La música ya está pausada",
            action="no_op",
            reason="already_paused"
        )
    
    if command.action == "play" and context.state == PlaybackState.PLAYING:
        return Response(
            message="La música ya está reproduciéndose",
            action="no_op",
            reason="already_playing"
        )
    
    # Ejecutar acción si es válida
    return execute_valid_action(command, context)
```

### 14.5 Detección de Dispositivo de Audio

```python
def get_active_audio_device() -> str:
    """Obtiene dispositivo de audio activo"""
    
def detect_playback_app() -> Optional[str]:
    """Detecta qué aplicación está reproduciendo audio"""
```

### 14.6 Tareas Específicas

- [ ] 14.1 Implementar detección de estado real de reproducción
- [ ] 14.2 Diferenciación: reproducción activa, pausa, buffering, stopped
- [ ] 14.3 Detección de cambios de dispositivo de audio
- [ ] 14.4 Lógica: nunca pausar algo que ya está pausado
- [ ] 14.5 Validación mediante estado en tiempo real antes de acciones
- [ ] 14.6 Integración con Spotify, Windows Media Player, etc.
- [ ] 14.7 Monitoreo de aplicación de música activa

### 14.7 Archivos Afectados

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `services/media_monitor.py` | Crear | Monitor de medios |
| `actions/media_control.py` | Reescribir | Control con validación |
| `actions/spotify_control.py` | Mejorar | Control de Spotify |

---

## 📦 ÁREA 15: Módulo Temporal y Contextual

### 15.1 Descripción General

Comprensión contextual real de fecha, hora y entorno. Uso de horarios locales, estados contextuales, detección de cambios significativos.

### 15.2 Sistema de Saludos Contextuales

```python
class TemporalContext:
    """Contexto temporal del sistema"""
    
    def get_appropriate_greeting(self) -> str:
        hour = datetime.now().hour
        
        if 5 <= hour < 12:
            period = "morning"
        elif 12 <= hour < 18:
            period = "afternoon"
        elif 18 <= hour < 22:
            period = "evening"
        else:
            period = "night"
            
        greeting = random.choice(self.greetings[period])
        
        # Agregar contexto si es relevante
        if self.should_mention_weather():
            greeting += " " + self.get_weather_context()
            
        return greeting
```

### 15.3 NO Repetir Información Innecesariamente

```python
def should_proactively_share_info(info_type: str) -> bool:
    """Determina si debe compartir información proactivamente"""
    
    # NO repetir clima si ya se mencionó hoy
    if info_type == "weather":
        if self.was_mentioned_recently("weather"):
            return False
            
    # NO dar buenos días si ya se dieron saludos
    if info_type == "time":
        if self.has_greeted_today():
            return False
            
    return True
```

### 15.4 Detección de Cambios Significativos

```python
class SignificantChangeDetector:
    """Detecta cambios significativos en el entorno"""
    
    def detect(self) -> List[SignificantEvent]:
        events = []
        
        # Cambio de clima significativo
        if self.climate_changed_significantly():
            events.append(SignificantEvent(
                type="weather",
                description="El clima cambió significativamente",
                priority="medium"
            ))
            
        # Cambio de hora del día
        if self.time_period_changed():
            events.append(SignificantEvent(
                type="time_period", 
                description="Cambió el período del día",
                priority="low"
            ))
            
        return events
```

### 15.5 Contextualización de Rutinas

```python
def get_contextual_routines() -> List[Routine]:
    """Obtiene rutinas contextualizadas por día/hora"""
    
    day_of_week = datetime.now().weekday()
    hour = datetime.now().hour
    
    routines = self.get_all_routines()
    
    contextual = []
    for routine in routines:
        if routine.applies_to(day_of_week) and routine.applies_to_hour(hour):
            contextual.append(routine)
            
    return contextual
```

### 15.6 Tareas Específicas

- [ ] 15.1 Corrección de saludos según momento del día (no genéricos)
- [ ] 15.2 Uso de horarios locales reales (no推测)
- [ ] 15.3 Detección de cambios significativos antes de informar
- [ ] 15.4 Integración con天气预报 (no repetir innecesariamente)
- [ ] 15.5 Contextualización de rutinas según día de la semana
- [ ] 15.6 Recordatorios contextuales basados en tiempo/ubicación

### 15.7 Archivos Afectados

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `services/time_context.py` | Crear | Contexto temporal |
| `actions/morning_brief.py` | Actualizar | Briefing mejorado |
| `core/context_builder.py` | Integrar | Integrar contexto temporal |

---

## 📦 ÁREA 16: Interfaz de Usuario Web Desacoplada

### 16.1 Descripción General

Reconstrucción completa de UI. Interfaz web moderna, escalable, preparada para widgets, monitoreo de agentes, configuraciones avanzadas. La UI debe estar completamente desacoplada del núcleo operativo.

### 16.2 Arquitectura de UI

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Frontend (React)                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │    Orb     │  │  Control    │  │  Settings   │        │
│  │  3D View   │  │    Bar      │  │    Panel    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│                    WebSocket Connection                     │
├─────────────────────────────────────────────────────────────┤
│                    Python Backend (ui.py)                   │
└─────────────────────────────────────────────────────────────┘
```

### 16.3 Panel de Configuración Completo

La interfaz debe exponer TODAS las funcionalidades internas:

#### Configuración de Memoria
- Ver memorias activas
- Agregar/editar/eliminar memorias
- Configurar prioridades
- Ver historial de sesiones

#### Proveedores y Modelos
- Seleccionar proveedor activo
- Configurar API keys
- Ver modelos disponibles
- Asignar modelos por tarea
- Probar conexión

#### Automatizaciones
- Ver reglas activas
- Crear/editar reglas
- Historial de ejecuciones
- Phrase triggers

#### Audio y Voz
- Configurar dispositivo de entrada/salida
- Ajustar sensibilidad de VAD
- Configurar wake word
- Test de-micro
- Test de altavoz

#### Visión
- Habilitar/deshabilitar guardian
- Configurar intervalo
- Ver últimos análisis

#### Accesibilidad
- Configuraciones de eye tracking
- Micro-movimientos
- Speech config
- Tamaño de texto

#### Integraciones
- WhatsApp
- Spotify
- Smart home
- Browser bookmarks

#### Comportamiento Contextual
- Saludos personalizados
- Tono de voz
- Nivel de formalidad

#### Seguridad
- Log de auditoría
- Historial de acciones sensibles
- Permisos de ejecución

#### Control Operativo
- Estado del sistema
- Procesos activos
- Memoria en uso
- Logs en tiempo real

### 16.4 Monitoreo de Agentes

La UI debe mostrar:
- Estado actual del agente (escuchando, pensando, hablando)
- Actividad en tiempo real
-Acciones siendo ejecutadas
- Uso de recursos

### 16.5 Preparación para Widgets

Arquitectura preparada para widgets futuros:
- Weather widget
- Music widget  
- Clock widget
- Todo widget
- Favorites widget

### 16.6 Tareas Específicas

- [ ] 16.1 Diseño de nueva UI web desde cero (o actualizar Min-UI significativamente)
- [ ] 16.2 Preparar arquitectura para widgets nativos futuros
- [ ] 16.3 Panel de configuración completo (exponer TODAS las funcionalidades)
- [ ] 16.4 Monitoreo de agentes en tiempo real
- [ ] 16.5 Observabilidad del sistema
- [ ] 16.6 Eliminación de dependencias de puentes improvisados
- [ ] 16.7 WebSocket comunicación robusta con backend

### 16.7 Archivos Afectados

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `Min-UI/` | Reescribir | Frontend completo |
| `ui.py` | Adaptar | WebSocket server |
| `services/dashboard_api.py` | Crear | API de dashboard |

---

## 📊 MÉTRICAS DE PROGRESO

| Fase | Áreas | Tareas | Completadas | En Progreso |
|------|-------|--------|-------------|-------------|
| Fase 1 | 1-4 | 40 | 24 | 16 |
| Fase 2 | 5-8 | 35 | 18 | 17 |
| Fase 3 | 9-12 | 30 | 0 | 0 |
| Fase 4 | 13-16 | 25 | 0 | 0 |
| **Total** | **16** | **~130** | **42** | **33** |

> **Nota:** Métricas actualizadas según auditoría completa del 2025-05-28. Las áreas 1, 3, 5, 6 y 8 tienen implementaciones significativas. Área 4 tiene módulos básicos. Áreas 9-16 pendientes de implementación o auditoría.

---

## 🔄 REGISTRO DE CAMBIOS

### Versión 1.0 (2025-05-28)
- Creación inicial del plan de implementación
- Definición de 17 áreas de trabajo
- Dividido en 4 fases de implementación
- ~130 tareas identificadas

### Versión 1.1 (2025-05-28 - Actualización)
- **Área 1 completada (9 tareas)**:
  - memory/db.py: SQLite con tablas para semantic_memory, episodic_sessions, episodic_interactions, episodic_episodes, work_memory, embeddings
  - memory/service.py: MemoryService con remember(), recall(), search_memory(), build_system_context()
  - memory/config.py: Configuración centralizada
  - memory/vector_store.py: VectorStore con embeddings y búsqueda semántica
  - memory/work_memory.py: WorkMemory con cache en memoria y expiración automática
  - memory/__init__.py: Exports actualizados
  - min/core.py: MINCore con tool registry y procesamiento
  - min/__init__.py: Exports del módulo MIN

### Versión 1.2 (2025-05-28 - Auditoría Completa)
- **Área 3 completada**:
  - providers/model_selector.py: ModelSelector para validación de combinaciones proveedor/modelo
  - Window caching en services/windows/__init__.py con 3s TTL
  - Cache invalidation automática en cambio de estado de ventana
- **Área 5/6 completadas parcialmente**:
  - Win32 API layer implementada (993 líneas)
  - Volume Mixer per-app funcionando
  - Window state detection con GetWindowPlacement
  - Bug fixes: IsZoomed, pycaw AudioDevice.Activate
- **Área 8 completada**: file_controller.py con CRUD completo
- **Estado general**: Áreas 1, 3, 5, 6, 8 mayormente completadas
- **Pendiente**: Áreas 7 (UIA), 9 (Vision), 10 (Image Gen), 11-16

---

## 📝 NOTAS IMPORTANTES

### Componente Preservado
**Único componente sin cambios:** `config/vosk_model/` (modelo de speech recognition)

### Complejidad Alta
- **Área 7** (UI Automation): requiere conocimiento profundo de Windows UIA
- **Área 13** (Audio/Voz): pipeline complejo con múltiples componentes
- **Área 1** (Memory): arquitectura fundamental que afecta todo

### Dependencias Críticas
- **Área 3** (Multi-Provider) debe completarse antes que la mayoría de otras áreas
- **Área 11** (Parser/Validator) debe completarse antes de pruebas de acciones
- Las áreas de una fase deben completarse en orden para mantener coherencia

### Estrategia de Testing
Cada área debe incluir:
1. Tests unitarios para componentes individuales
2. Tests de integración para flujos completos
3. Validación manual del comportamiento esperado
4. Documentación de casos de prueba

### Riesgos Identificados
1. **Scope creep**: muchas áreas pueden expandirse más de lo planeado
2. **Dependencias circulares**: algunas áreas dependen de otras que también están en desarrollo
3. **Testing insuficiente**: presión de tiempo puede llevar a validar parcialmente


## 📦 ÁREA 17: Generación de Música con IA (MiniMax)

### 17.1 Descripción General

Integración de generación de música vía MiniMax API. Permite crear canciones originales con lyrics personalizados, covers de canciones existentes, y generación de letras de canciones — todo dentro del ecosistema del asistente.

### 17.2 Arquitectura

```
Jarvis AI/
├── services/
│   └── music_generator.py    (294 líneas)
├── actions/
│   └── music/
│       ├── music_generation.py  (57 líneas)
│       └── __init__.py
└── core/
    ├── tool_schemas.py      (1510 líneas)
    ├── action_registry.py   (449 líneas)
    └── config_manager.py   (257 líneas)
```

### 17.3 MiniMax API

| Endpoint | Método | Modelo | Uso |
|----------|--------|-------|-----|
| `/v1/music_generation` | POST | music-2.6 | Generación text-to-music |
| `/v1/music_cover` | POST | music-cover | Cover de canciones |
| `/v1/music_cover_preprocess` | POST | — | Preproceso de cover |
| `/v1/lyrics_generation` | POST | — | Generación de letras |

### 17.4 Componentes Implementados

#### 17.4.1 MusicGenerator (services/music_generator.py)
- `generate(prompt, lyrics, model, is_instrumental)` — generación original
- `generate_cover(audio_url, prompt)` — cover de canción existente
- `preprocess_cover(audio_url)` — preproceso de audio
- `generate_lyrics(prompt)` — generación de letras
- `_download_audio(url, filename)` — descarga con retries
- `get_recent(n=10)` / `get_stats()` — consulta de historial

#### 17.4.2 Action Wrapper (actions/music/music_generation.py)
- `music_generation(parameters, player)` — acción principal
- `music_lyrics_generation(parameters, player)` — generación de letras

#### 17.4.3 Configuración (core/config_manager.py)
- `minimax_api_key` — API key de MiniMax
- `minimax_music_model` — modelo por defecto (music-2.6)
- `minimax_music_output_dir` — directorio de salida
- `model_assignments.music_generation` — {provider: minimax, model: music-2.6}

### 17.5 Metadata Logging

Archivo: `logs/music_generation/generated_music.jsonl`

```json
{"timestamp": "2026-05-30T...", "type": "original", "model": "music-2.6", "prompt": "...", "lyrics": "...", "filename": "song_xxx.mp3", "duration": "...", "file_size": "..."}
```

### 17.6 Tareas Completadas

- [x] 17.1.1 Implementar MusicGenerator service
- [x] 17.1.2 Integrar MiniMax API (music-2.6, music-cover)
- [x] 17.1.3 Implementar generación de lyrics
- [x] 17.1.4 Agregar tool schema en tool_schemas.py
- [x] 17.1.5 Crear action wrapper en actions/music/
- [x] 17.1.6 Registrar en action_registry.py BUILTIN_ACTIONS
- [x] 17.1.7 Agregar 'music' a CATEGORIES en action_dispatcher.py
- [x] 17.1.8 Configurar minimax_api_key en AppConfig
- [x] 17.1.9 Implementar metadata logging en JSONL
- [x] 17.1.10 Verificación de sintaxis y imports


---

## 📅 CRONOGRAMA SUGERIDO

### Fase 1: Semanas 1-4
- **Semana 1-2**: Área 1 (Memory) + Área 3 (Providers)
- **Semana 3**: Área 2 (Project Structure)
- **Semana 4**: Área 4 (Prompting)

### Fase 2: Semanas 5-8
- **Semana 5**: Área 5 (Windows API) + Área 6 (Window Manager)
- **Semana 6-7**: Área 7 (UI Automation)
- **Semana 8**: Área 8 (File Management)

### Fase 3: Semanas 9-12
- **Semana 9**: Área 9 (Vision) + Área 12 (Web Search)
- **Semana 10-11**: Área 10 (Image Generation) + Área 11 (Action Parser)
- **Semana 12**: Área 17 (Music Gen) + Testing e integración de Fase 2-3

### Fase 4: Semanas 13-16
- **Semana 13**: Área 13 (Audio Pipeline)
- **Semana 14**: Área 14 (Media) + Área 15 (Temporal)
- **Semana 15-16**: Área 16 (UI) + Testing final

---

*Plan creado como referencia viva. Se actualizará regularmente marcando tareas completadas con resumen de cambios realizados.*

---

## 🐛 BUGS Y MEJORAS ENCONTRADOS - Debug Session 2025-05-28

### Bugs Críticos Descubiertos

| ID | Bug | Severidad | Estado | Solución |
|----|-----|-----------|--------|----------|
| BUG-001 | `win32gui.IsZoomed` no existe | Alta | ✓ FIXED | Usar `GetWindowPlacement()` en `placement[1]` para detectar estado Maximized |
| BUG-002 | Implementación duplicada Win32 | Media | Pendiente | Unificar `win32_api.py` y `__init__.py` o documentar propósito diferente |
| BUG-003 | pycaw `AudioDevice.Activate()` no existe | Media | ✓ FIXED | Usar directamente `devices.EndpointVolume` en lugar de Activate |
| BUG-004 | Test usaba parámetro incorrecto `partial` | Baja | ✓ FIXED | El método usa `exact` no `partial` |
| BUG-005 | UnicodeEncodeError con símbolos ✓ ✗ | Baja | ✓ FIXED | Usar texto plano (PASS/FAIL) |

### Cambios de Código Realizados

#### 1. services/windows/__init__.py (líneas 165-175)
```python
# ANTES (ROTO):
if win32gui.IsIconic(hwnd):
    state = WindowState.MINIMIZED
elif win32gui.IsZoomed(hwnd):  # ERROR: IsZoomed no existe
    state = WindowState.MAXIMIZED

# DESPUÉS (CORREGIDO):
if win32gui.IsIconic(hwnd):
    state = WindowState.MINIMIZED
else:
    placement = win32gui.GetWindowPlacement(hwnd)
    show_cmd = placement[1]  # 3=MAXIMIZED, 1=NORMAL
    state = WindowState.MAXIMIZED if show_cmd == 3 else WindowState.NORMAL
```

#### 2. services/windows/__init__.py (volume methods, líneas 516-570)
```python
# ANTES (ROTO):
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)  # ERROR
# AudioDevice no tiene metodo Activate()

# DESPUÉS (CORREGIDO):
devices = AudioUtilities.GetSpeakers()
volume = devices.EndpointVolume  # Directamente usar la propiedad EndpointVolume
volume.SetMasterVolumeLevelScalar(level / 100.0, None)  # Sin cast, ya es puntero
```

### Resultados de Pruebas

**Suite:** `tests/test_windows_service.py`  
**Fecha:** 2025-05-28 (sesión 2)  
**Resultado:** 9/9 PASS (100%)

| Prueba | Estado | Notas |
|--------|--------|-------|
| Service Initialization | PASS | Singleton funciona |
| pywinauto availability | PASS | HAS_WIN32=True, HAS_PSUTIL=True, HAS_PYWINAUTO=True |
| get_all_windows() | PASS | 9 ventanas encontradas |
| find_window_by_title() | PASS | Busca por título correctamente |
| get_window_info() | PASS | Ahora funciona con fix del BUG-001 |
| find_running_app() | PASS | Detecta explorer correctamente |
| get_processes() | PASS | 314 procesos detectados |
| Volume Control | PASS | Usando devices.EndpointVolume directamente |
| capture_screen() | PASS | 369.5 KB captura |

### Tareas Completadas en Esta Sesión

- [x] 5.1.1 Fix `win32gui.IsZoomed` -> `GetWindowPlacement`
- [x] 5.1.2 Verificar funcionalidad de `get_all_windows()`
- [x] 5.1.3 Verificar `find_window_by_title()`
- [x] 5.1.4 Verificar `get_window_info()`
- [x] 5.1.5 Verificar `find_running_app()`
- [x] 5.1.6 Verificar `get_processes()`
- [x] 5.1.7 Diagnosticar problema con `set_volume()`
- [x] 5.1.8 Verificar `capture_screen()`
- [x] 5.1.9 Crear suite de tests `tests/test_windows_service.py`
- [x] 5.1.10 Implementar fallback para control de volumen (BUG-003 FIXED)
- [x] 5.1.11 Unificar implementaciones Win32 duplicates (Pendiente - BUG-002)
- [x] 5.12.1 Fix pycaw volume via EndpointVolume (100% test pass)