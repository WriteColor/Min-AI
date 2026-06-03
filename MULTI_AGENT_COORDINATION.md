# MULTI_AGENT_COORDINATION.md

# Sistema de Coordinación Multiagente para la Reingeniería de MIN

## Objetivo

Este documento define las reglas obligatorias de colaboración entre múltiples agentes de IA trabajando simultáneamente sobre el mismo repositorio.

Los agentes participantes son:

* OpenCode (MiniMax-M2.7)
* Claude Code Extension (MiniMax-M2.7)
* Gemini 3.5 Flash High (Antigravity)

Todos los agentes deben considerar este documento como la fuente oficial de coordinación del proyecto.

Ningún agente debe asumir el estado del proyecto basándose únicamente en el código presente en el repositorio.

El estado real del proyecto siempre estará definido por este documento.

---

# Principio Fundamental

Todos los agentes comparten un único objetivo:

Implementar la reingeniería completa del sistema de audio de MIN sin interferencias, duplicación de trabajo, conflictos arquitectónicos o sobrescritura accidental de cambios.

---

# Regla 1: Lectura Obligatoria

Antes de realizar cualquier acción, cada agente debe:

1. Leer completamente este documento.
2. Revisar el estado actual de todas las tareas.
3. Revisar las tareas en progreso.
4. Revisar los bloqueos reportados.
5. Revisar las recomendaciones dejadas por otros agentes.

Ningún agente debe comenzar a trabajar sin realizar esta revisión.

---

# Regla 2: Reserva de Trabajo

Antes de modificar cualquier archivo:

El agente debe registrar la tarea que tomará.

Debe indicar:

* Fecha y hora.
* Nombre del agente.
* Área del proyecto.
* Archivos involucrados.
* Estado inicial.

Formato:

## WORK CLAIM

Agent: Gemini
Task: Integración de Kokoro
Files:

* backend/audio/kokoro_engine.py
* backend/audio/tts_pipeline.py

Status: IN_PROGRESS

Timestamp: YYYY-MM-DD HH:MM

Mientras una tarea permanezca marcada como IN_PROGRESS, ningún otro agente podrá modificar esos mismos archivos.

---

# Regla 3: Estados Permitidos

Toda tarea debe encontrarse en uno de los siguientes estados:

PLANNING

El agente está analizando la implementación.

PENDING

Aún no se inició el trabajo.

IN_PROGRESS

Actualmente está siendo implementada.

BLOCKED

Existe algún impedimento.

REVIEW_REQUIRED

La implementación terminó pero requiere validación.

COMPLETED

La implementación fue terminada y validada.

---

# Regla 4: División de Responsabilidades

Para minimizar conflictos se establece inicialmente la siguiente distribución.

## OpenCode (MiniMax-M2.7)

Responsabilidades principales:

* Vosk
* Captura de micrófono
* Streaming de audio
* Buffers
* Decodificación UTF-8
* Hardware de entrada
* Diagnóstico de audio

No debe modificar:

* Kokoro
* Sistema TTS
* UI
* Configuración de proveedores

Sin coordinación previa.

---

## Claude Code (MiniMax-M2.7)

Responsabilidades principales:

* Kokoro-82M
* TTS Pipeline
* Cola de reproducción
* Segmentador de oraciones
* Streaming de voz
* Gestión de voces

No debe modificar:

* Captura de micrófono
* Vosk
* Configuración UI

Sin coordinación previa.

---

## Gemini 3.5 Flash High

Responsabilidades principales:

* Routing Gemini vs Multiproveedor
* Configuración global
* Selección de proveedores
* Gestión de modelos
* Integración entre módulos
* Refactorización arquitectónica
* Validación general

No debe modificar:

* Implementaciones internas de Vosk
* Implementaciones internas de Kokoro

Salvo necesidad crítica.

---

# Regla 5: Registro de Implementaciones

Cada agente debe documentar exactamente qué hizo.

Formato:

## IMPLEMENTATION LOG

Agent: Claude Code

Task:
Implementación de cola secuencial TTS

Files Modified:

* backend/audio/tts_queue.py
* backend/audio/kokoro_engine.py

Summary:

Se añadió una cola FIFO para evitar superposición de frases.

Status:

REVIEW_REQUIRED

Timestamp:

YYYY-MM-DD HH:MM

---

# Regla 6: Recomendaciones Cruzadas

Los agentes pueden dejar recomendaciones para otros agentes.

Formato:

## RECOMMENDATION

From:
OpenCode

To:
Claude Code

Message:

El buffer de entrada ahora entrega segmentos de 16000Hz estables.
Puede eliminar la conversión previa dentro de kokoro_engine.py.

Priority:

MEDIUM

Timestamp:

YYYY-MM-DD HH:MM

---

# Regla 7: Conflictos

Si un agente detecta que necesita modificar archivos reservados por otro agente:

NO debe modificar nada.

Debe registrar una solicitud.

Formato:

## CHANGE REQUEST

Agent:
Gemini

Target Agent:
Claude Code

Files:

* backend/audio/kokoro_engine.py

Reason:

Necesario para integrar selección dinámica de voz.

Status:

WAITING_APPROVAL

---

# Regla 8: Validación Cruzada

Cuando una tarea alcance REVIEW_REQUIRED:

Otro agente diferente debe revisar:

* código
* arquitectura
* errores potenciales
* compatibilidad

Solo entonces podrá marcarse como COMPLETED.

---

# Regla 9: Historial Permanente

Ningún registro debe eliminarse.

Los registros antiguos deben conservarse.

El documento funciona como memoria persistente compartida entre agentes.

---

# Regla 10: Prioridad Máxima

En caso de conflicto entre:

* Código existente
* Memoria de sesión
* Conversaciones previas
* Suposiciones del agente

Siempre prevalece lo registrado en este documento.

Este archivo representa la fuente oficial de coordinación del proyecto.

---

## WORK CLAIMS HISTORY

### WORK CLAIM 1

Agent: Gemini 3.5 Flash High (Antigravity)
Task: Routing Gemini vs Multiproveedor & Config defaults & Integration
Files:
* [core/config_manager.py](file:///c:/React-Nextjs-Projects/Jarvis%20AI/core/config_manager.py)
* [services/session/session_builder.py](file:///c:/React-Nextjs-Projects/Jarvis%20AI/services/session/session_builder.py)
* [main.py](file:///c:/React-Nextjs-Projects/Jarvis%20AI/main.py)
* [providers/base.py](file:///c:/React-Nextjs-Projects/Jarvis%20AI/providers/base.py)
* [services/ai/llm.py](file:///c:/React-Nextjs-Projects/Jarvis%20AI/services/ai/llm.py)
Status: COMPLETED
Timestamp: 2026-06-02 18:16

### WORK CLAIM 2

Agent: OpenCode
Task: Vosk Correction & Whisper Removal
Files:
* [services/audio/stt.py](file:///c:/React-Nextjs-Projects/Jarvis%20AI/services/audio/stt.py)
* [services/audio/service.py](file:///c:/React-Nextjs-Projects/Jarvis%20AI/services/audio/service.py)
* [services/audio/pipeline.py](file:///c:/React-Nextjs-Projects/Jarvis%20AI/services/audio/pipeline.py)
Status: COMPLETED
Timestamp: 2026-06-02 12:14

### WORK CLAIM 3

Agent: Claude Code
Task: Kokoro-82M TTS & Sentence Segmentation & Play Queue
Files:
* [services/audio/tts_service.py](file:///c:/React-Nextjs-Projects/Jarvis%20AI/services/audio/tts_service.py)
* [services/audio/tts.py](file:///c:/React-Nextjs-Projects/Jarvis%20AI/services/audio/tts.py)
Status: COMPLETED
Timestamp: 2026-06-02 18:18

---

## CHANGE REQUEST 1

Agent: Claude Code
Target Agent: Gemini 3.5 Flash High (Antigravity)
Files:
* [services/ai/llm.py](file:///c:/React-Nextjs-Projects/Jarvis%20AI/services/ai/llm.py)
Reason: Need to modify the streaming loop in LLMConsumer to send chunks/tokens to the TTS pipeline as they arrive, enabling sentence-by-sentence streaming voice generation.
Status: APPROVED


