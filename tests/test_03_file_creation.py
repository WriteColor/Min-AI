"""
Test 03: Creación de archivos extensos
==========================
Prueba creación de: txt, markdown (LaTeX/KaTeX), Word, Excel, PowerPoint
"""

import asyncio
import json
import sys
import os
from pathlib import Path
sys.path.insert(0, ".")

from actions.files.file_controller import create_text_file, create_markdown_file
from actions.office.word_actions import create_word_doc
from actions.office.excel_actions import create_excel_doc
from actions.office.powerpoint_actions import create_pptx_doc


TEST_DIR = Path("C:/React-Nextjs-Projects/Jarvis AI/tests_output")
TEST_DIR.mkdir(exist_ok=True)


async def create_long_text():
    """Crea archivo de texto extenso con múltiples secciones."""
    print("\n[1] Creando archivo de texto extenso...")

    content = """
ACTA DE REUNIÓN - PROYECTO JARVIS AI
=====================================

Fecha: 30 de Mayo de 2026
Hora: 10:00 AM
Lugar: Sala de Juntas Virtual

ASISTENTES
----------
- Juan Pérez - Director de Proyecto
- María García - Lead Developer
- Carlos López - QA Engineer
- Ana Martínez - UX Designer

AGENDA
------
1. Revisión de avances del sprint actual
2. Discusión de obstáculos técnicos
3. Planificación del próximo sprint
4. Asignación de recursos
5. Revisión de timeline

DESARROLLO DE LA REUNIÓN
------------------------

1. AVANCES DEL SPRINT ACTUAL

El equipo presentó los siguientes logros:
- Implementación del módulo de reconocimiento de voz (95% completado)
- Integración con APIs de terceros (Spotify, WhatsApp) - Completado
- Mejora del sistema de prompts (en desarrollo)
- Optimización de latencia en respuestas (30% más rápido)
- Implementación de sistema de recycle bin (completado)

Métricas del sprint:
- Historias de usuario completadas: 12/15
- Bugs corregidos: 23
- Code coverage: 78%
- Tiempo promedio de respuesta: 1.2 segundos

2. OBSTÁCULOS TÉCNICOS

Se discutieron los siguientes problemas:

a) Problema de latencia en OpenRouter
   - Causa: Configuración incorrecta del path de API
   - Solución: Corregido en commit #452
   - Status: RESUELTO

b) Duplicación de voz en respuestas TTS
   - Causa: Múltiples llamadas a speak() sin mutex
   - Solución: Implementar flag de turno completado
   - Status: EN PROGRESO

c) Timeouts en respuestas largas
   - Causa: Cliente desconecta antes de recibir respuesta
   - Solución: Implementar streaming de respuesta
   - Status: ANALIZANDO

3. PLANIFICACIÓN DEL PRÓXIMO SPRINT

Historias de usuario planeadas:
- HU-101: Sistema de notificaciones push
- HU-102: Integración con calendario externo
- HU-103: Dashboard de estadísticas de uso
- HU-104: Sistema de plugins/extensions
- HU-105: Mejora de reconocimiento de comandos

Estimación de esfuerzo: 34 puntos de historia
Capacidad del equipo: 28 puntos de historia
Decisión: Priorizar HU-101, HU-102, HU-103

4. ASIGNACIÓN DE RECURSOS

- Juan Pérez: 40 horas/semana (disponible)
- María García: 40 horas/semana (disponible)
- Carlos López: 32 horas/semana (vacaciones del 5-12 Junio)
- Ana Martínez: 40 horas/semana (disponible)

5. REVISIÓN DE TIMELINE

Fase 1 (Core): Completada ✓
Fase 2 (Integraciones): 85% - Esperada: 15 Junio 2026
Fase 3 (UI/UX): 60% - Esperada: 30 Junio 2026
Fase 4 (Testing): 40% - Esperada: 15 Julio 2026
Lanzamiento v1.0: 1 Agosto 2026

ACUERDOS
--------
1. Reunión diaria sync: 9:00 AM (30 min)
2. Demo de sprint: Viernes 5 Junio 2026, 3:00 PM
3. Code review obligatorio antes de merge
4. Actualización de documentación técnica semanal

PRÓXIMA REUNIÓN
---------------
Fecha: 6 de Junio de 2026
Hora: 10:00 AM
Tema: Review de HU-101 (Sistema de notificaciones)

FIRMAS
------
____________________    ____________________
Juan Pérez             María García
Director de Proyecto   Lead Developer

____________________    ____________________
Carlos López           Ana Martínez
QA Engineer            UX Designer
"""

    result = await create_text_file(
        str(TEST_DIR / "acta_reunion_v3.txt"),
        content
    )
    print(f"    → {'✓' if result.get('success') else '✗'} {result.get('message', '')}")
    return result.get('success')


async def create_markdown_with_latex():
    """Crea archivo markdown con formato LaTeX/KaTeX para matemáticas."""
    print("\n[2] Creando markdown con fórmulas matemáticas (LaTeX/KaTeX)...")

    content = """# Manual de Física Cuántica
## Capítulo 1: Fundamentos Matemáticos

---

## 1.1 Ecuaciones Diferenciales Parciales

La ecuación de Schrödinger dependiente del tiempo es:

$$
i\\hbar\\frac{\\partial}{\\partial t}\\Psi(\\mathbf{r},t) = \\hat{H}\\Psi(\\mathbf{r},t)
$$

donde:
- $i$ es la unidad imaginaria
- $\\hbar$ es la constante de Planck reducida
- $\\Psi(\\mathbf{r},t)$ es la función de onda
- $\\hat{H}$ es el operador Hamiltoniano

### Forma Expandida

Para una partícula libre en 3D:

$$
\\left[-\\frac{\\hbar^2}{2m}\\nabla^2 + V(\\mathbf{r})\\right]\\Psi = i\\hbar\\frac{\\partial\\Psi}{\\partial t}
$$

---

## 1.2 Álgebra Lineal y Espacios de Hilbert

### Producto Interno

El producto interno entre dos estados $|\\psi\\rangle$ y $|\\phi\\rangle$ se define como:

$$
\\langle\\psi|\\phi\\rangle = \\int_{-\\infty}^{\\infty}\\psi^*(x)\\phi(x)\\,dx
$$

### Operadores Unitarios

Un operador $\\hat{U}$ es unitario si:

$$
\\hat{U}^\\dagger\\hat{U} = \\hat{U}\\hat{U}^\\dagger = \\hat{I}
$$

### Teorema de Eigenvalores

Para un observable representado por un operador Hermitiano $\\hat{A}$:

$$
\\hat{A}|a_n\\rangle = a_n|a_n\\rangle
$$

donde $a_n$ son los eigenvalores reales.

---

## 1.3 Transformadas de Fourier

La transformada de Fourier de una función $\\Psi(x)$:

$$
\\tilde{\\Psi}(k) = \\frac{1}{\\sqrt{2\\pi}}\\int_{-\\infty}^{\\infty} \\Psi(x)e^{-ikx}\\,dx
$$

Y la transformada inversa:

$$
\\Psi(x) = \\frac{1}{\\sqrt{2\\pi}}\\int_{-\\infty}^{\\infty} \\tilde{\\Psi}(k)e^{ikx}\\,dk
$$

---

## 1.4 Integrales de Camino de Feynman

La amplitud de probabilidad entre dos puntos es:

$$
\\langle x_f,t_f|x_i,t_i\\rangle = \\int \\mathcal{D}[x(t)]\\,e^{\\frac{i}{\\hbar}S[x(t)]}
$$

donde $S[x(t)]$ es la acción:

$$
S = \\int_{t_i}^{t_f} L(x,\\dot{x},t)\\,dt = \\int_{t_i}^{t_f}\\left[\\frac{1}{2}m\\dot{x}^2 - V(x)\\right]dt
$$

---

## 1.5 Matrices de Pauli

Para描述 espín 1/2, usamos las matrices de Pauli:

$$
\\sigma_x = \\begin{pmatrix} 0 & 1 \\\\ 1 & 0 \\end{pmatrix},
\\quad
\\sigma_y = \\begin{pmatrix} 0 & -i \\\\ i & 0 \\end{pmatrix},
\\quad
\\sigma_z = \\begin{pmatrix} 1 & 0 \\\\ 0 & -1 \\end{pmatrix}
$$

El operador de espín total:

$$
\\vec{\\sigma} \\cdot \\vec{B} = \\begin{pmatrix} B_z & B_x - iB_y \\\\ B_x + iB_y & -B_z \\end{pmatrix}
$$

---

## 1.6 Distribuciones de Probabilidad

### Distribución de Maxwell-Boltzmann

$$
P(v)\\,dv = 4\\pi\\left(\\frac{m}{2\\pi k_B T}\\right)^{3/2} v^2 e^{-\\frac{mv^2}{2k_B T}}\\,dv
$$

### Distribución de Bose-Einstein

$$
n_i = \\frac{g_i}{e^{(\\epsilon_i - \\mu)/k_B T} - 1}
$$

### Distribución de Fermi-Dirac

$$
f(\\epsilon) = \\frac{1}{e^{(\\epsilon - \\epsilon_F)/k_B T} + 1}
$$

---

## Resumen de Constantes

| Constante | Símbolo | Valor |
|-----------|----------|-------|
| Velocidad de la luz | $c$ | $2.998 \\times 10^8$ m/s |
| Constante de Planck | $h$ | $6.626 \\times 10^{-34}$ J·s |
| Constante de Planck reducida | $\\hbar$ | $1.055 \\times 10^{-34}$ J·s |
| Número de Avogadro | $N_A$ | $6.022 \\times 10^{23}$ mol$^{-1}$ |
| Constante de Boltzmann | $k_B$ | $1.381 \\times 10^{-23}$ J/K |
| Carga del electrón | $e$ | $1.602 \\times 10^{-19}$ C |
| Masa del electrón | $m_e$ | $9.109 \\times 10^{-31}$ kg |

---

*Documento generado para pruebas de renderizado LaTeX/KaTeX*
"""

    result = await create_markdown_file(
        str(TEST_DIR / "manual_fisica_cuantica.md"),
        content
    )
    print(f"    → {'✓' if result.get('success') else '✗'} {result.get('message', '')}")
    return result.get('success')


async def create_word_doc():
    """Crea documento Word extenso."""
    print("\n[3] Creando documento Word...")

    content = """{
    "title": "Informe Técnico del Proyecto JARVIS AI",
    "sections": [
        {
            "heading": "Resumen Ejecutivo",
            "content": "Este documento presenta el estado actual del proyecto JARVIS AI, incluyendo avances técnicos, obstáculos encontrados y roadmap futuro. El proyecto ha logrado hitos significativos en el desarrollo de un asistente de voz inteligente con capacidades avanzadas de procesamiento de lenguaje natural."
        },
        {
            "heading": "Arquitectura del Sistema",
            "content": "El sistema está construido sobre una arquitectura modular que incluye: Módulo de Voz (VOSK para wake word y reconocimiento), Motor LLM (Gemini API con fallback a OpenRouter), Sistema de Herramientas (tool_call para acciones delegadas), Interfaz de Audio (TTS/STT bidireccional), y Persistencia de Memoria (SQLite para historial)."
        },
        {
            "heading": "Módulo de Procesamiento de Voz",
            "content": "El sistema de voz utiliza VOSK para reconocimiento de wake word y transcripción en tiempo real. El TTS (text-to-speech) soporta múltiples motores y permite personalización de voz. Se implementó un sistema VAD (voice activity detection) para detectar cuando el usuario deja de hablar."
        },
        {
            "heading": "Integración de APIs",
            "content": "El asistente integra múltiples APIs: Spotify para control de música, WhatsApp para mensajería, OpenRouter para razonamiento complejo, y servicios de navegación web. Cada integración requiere manejo de errores robusto y retry logic."
        },
        {
            "heading": "Análisis de Rendimiento",
            "content": "Las métricas actuales muestran: Latencia promedio de respuesta: 1.2 segundos, Accuracy de reconocimiento: 94%, Uptime del sistema: 99.2%, Tiempo medio entre fallos: 48 horas."
        },
        {
            "heading": "Seguridad y Privacidad",
            "content": "Se implementan las siguientes medidas: Encriptación de datos en tránsito (TLS), Almacenamiento seguro de API keys, Rate limiting para prevenir abuso, Logs de auditoría para acciones sensibles."
        },
        {
            "heading": "Roadmap Q3 2026",
            "content": "Los objetivos para el próximo quarter incluyen: Soporte para más idiomas además de español, Integración con Home Assistant para smart home, Sistema de aprendizaje por feedback del usuario, Plugin system para extensiones de terceros."
        }
    ]
}"""

    try:
        result = await create_word_doc(
            str(TEST_DIR / "informe_tecnico.docx"),
            json.loads(content)
        )
        print(f"    → {'✓' if result.get('success') else '✗'} {result.get('message', '')}")
        return result.get('success')
    except Exception as e:
        print(f"    → ✗ Error: {e}")
        return False


async def create_excel_doc():
    """Crea spreadsheet Excel con múltiples hojas."""
    print("\n[4] Creando spreadsheet Excel...")

    data = {
        "Hoja1 - Métricas": [
            {"Métrica": "Usuarios Activos", "Valor": 1523, "Cambio": "+12%"},
            {"Métrica": "Respuestas/Día", "Valor": 45200, "Cambio": "+8%"},
            {"Métrica": "Tiempo Promedio (s)", "Valor": 1.2, "Cambio": "-15%"},
            {"Métrica": "Satisfacción (1-5)", "Valor": 4.7, "Cambio": "+3%"},
        ],
        "Hoja2 - Presupuesto": [
            {"Categoría": "Infraestructura", "Asignado": 50000, "Gastado": 32500},
            {"Categoría": "Personal", "Asignado": 150000, "Gastado": 145000},
            {"Categoría": "APIs", "Asignado": 25000, "Gastado": 18750},
            {"Categoría": "Marketing", "Asignado": 30000, "Gastado": 12000},
        ],
        "Hoja3 - Sprint": [
            {"Historia": "HU-101 Notificaciones", "Estado": "Completado", "Puntos": 5},
            {"Historia": "HU-102 Calendario", "Estado": "En Progreso", "Puntos": 8},
            {"Historia": "HU-103 Dashboard", "Estado": "En Progreso", "Puntos": 5},
            {"Historia": "HU-104 Plugins", "Estado": "Pendiente", "Puntos": 13},
            {"Historia": "HU-105 Mejora TTS", "Estado": "Completado", "Puntos": 3},
        ]
    }

    try:
        result = await create_excel_doc(
            str(TEST_DIR / "metrics_sprint.xlsx"),
            data
        )
        print(f"    → {'✓' if result.get('success') else '✗'} {result.get('message', '')}")
        return result.get('success')
    except Exception as e:
        print(f"    → ✗ Error: {e}")
        return False


async def create_pptx_doc():
    """Crea presentación PowerPoint."""
    print("\n[5] Creando presentación PowerPoint...")

    slides = [
        {
            "title": "Proyecto JARVIS AI - Estado Actual",
            "content": [
                "Arquitectura modular desplegada",
                "Integraciones con Spotify, WhatsApp, OpenRouter activas",
                "Rendimiento: 1.2s latencia promedio",
                "Siguiente: Expansión de capacidades"
            ],
            "layout": "title_and_content"
        },
        {
            "title": "Métricas de Uso",
            "content": [
                "1,523 usuarios activos mensuales",
                "45,200+ respuestas generadas",
                "94% accuracy de reconocimiento",
                "4.7/5 satisfacción del usuario"
            ],
            "layout": "title_and_content"
        },
        {
            "title": "Roadmap Q3 2026",
            "content": [
                "Mes 1: Soporte multi-idioma",
                "Mes 2: Integración Home Assistant",
                "Mes 3: Sistema de plugins",
                "Mes 4: Launch v2.0"
            ],
            "layout": "title_and_content"
        },
        {
            "title": "Integración de APIs",
            "content": [
                "Spotify: Control de música ✓",
                "WhatsApp: Mensajería ✓",
                "OpenRouter: Razonamiento ✓",
                "Web Search: Exploración ✓"
            ],
            "layout": "title_and_content"
        }
    ]

    try:
        result = await create_pptx_doc(
            str(TEST_DIR / "presentacion_estado.pptx"),
            slides
        )
        print(f"    → {'✓' if result.get('success') else '✗'} {result.get('message', '')}")
        return result.get('success')
    except Exception as e:
        print(f"    → ✗ Error: {e}")
        return False


async def main():
    print("=" * 60)
    print("TEST 03: Creación de archivos extensos")
    print("=" * 60)

    results = []
    results.append(await create_long_text())
    results.append(await create_markdown_with_latex())
    results.append(await create_word_doc())
    results.append(await create_excel_doc())
    results.append(await create_pptx_doc())

    print("\n" + "=" * 60)
    print(f"RESULTADO: {sum(results)}/{len(results)} archivos creados")
    print(f"Ubicación: {TEST_DIR}")
    print("=" * 60)

    return all(results)


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
