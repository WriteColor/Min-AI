# 🟣 MIN — Asistente de Inteligencia Artificial

**MIN** es un asistente de IA avanzado con control total del sistema operativo Windows 11, interfaz gráfica moderna en Tauri + React, y comunicación en tiempo real mediante streaming de audio bidireccional con Google Gemini.

---

## ✨ Características Principales

### 🎙️ Asistente por Voz
- Streaming de audio bidireccional con **Google Gemini Live API**
- 8 voces TTS disponibles (Aoede, Kore, Leda, Zephyr, Charon, Puck, Fenrir, Orus)
- Detección automática de palabra clave para activación por voz
- Modo suspensión con Vosk para reconocimiento offline

### 🖥️ Control Total del Sistema
- Apertura y gestión de aplicaciones nativas de Windows
- Control multimedia avanzado (Spotify, YouTube, reproductores del sistema)
- Terminal segura con validación multinivel contra comandos destructivos
- Gestión de volumen del sistema, brillo y configuración de pantalla
- Control de ventanas (mover, redimensionar, minimizar, maximizar)

### 🌐 Navegador Web Inteligente
- Autodetección del navegador predeterminado del sistema
- Búsquedas web, YouTube, e interacción con páginas
- Caché de rutas de aplicaciones para acceso instantáneo

### 🔒 Seguridad Multinivel
| Capa | Componente | Protección |
|------|-----------|-----------|
| Nivel 1 | `core/prompt.txt` | Instrucciones que prohíben comandos destructivos |
| Nivel 2 | `terminal_agent.py` | 29 patrones regex + auditoría de seguridad |
| Nivel 3 | `self_edit.py` | Lista negra de archivos protegidos inmutables |

### 🎨 Interfaz Moderna
- **Tauri 2.x + Next.js 14 (App Router) + TypeScript** con Tailwind CSS v4
- Componentes shadcn-style con Radix UI primitives
- Orb 3D interactivo con Three.js que reacciona al estado del asistente
- Widgets auto-ocultables: Clima, Reloj, Música, Tareas, Favoritos
- Control bar minimalista con auto-hide en hover
- Settings dialog completo con 6 pestañas, enumeración de dispositivos de cámara, y dropdowns reales del sistema
- Sistema de archivos externo seguro con validación de rutas (path traversal protection)
- Configuración con fallback de 3 capas (Tauri → API → public/config)

### 🌤️ Clima y Geolocalización
- Geolocalización automática por IP o configuración manual
- Datos meteorológicos en tiempo real via Open-Meteo
- Widget de pronóstico de 5 días

### 🤖 Motor IA Dinámico
- Cambio automático entre modelos Gemini al alcanzar límites
- Fallback a OpenRouter para continuidad de servicio
- Soporte para visión (captura de pantalla) y análisis de imágenes

---

## 📁 Arquitectura del Proyecto

```
MIN/
├── main.py                 # Bootstrapper principal (3300 líneas)
├── ui.py                   # Servidor WebSocket (ws://127.0.0.1:8765)
├── MIN.bat                 # Launcher unificado (start/install/kill/status/dev)
├── install.py              # Instalador automático
├── core/
│   ├── prompt.txt          # System prompt con sección de seguridad
│   └── memory.json         # Memoria persistente del asistente
├── config/
│   ├── config.json       # Claves API (gitignored)
│   ├── app_registry.json   # Caché de rutas de aplicaciones
│   ├── favorites.json      # Sitios favoritos
│   └── rules.json          # Reglas de automatización
├── actions/
│   ├── terminal_agent.py   # Terminal segura con auditoría
│   ├── self_edit.py        # Auto-edición con archivos protegidos
│   ├── open_app.py         # Apertura de aplicaciones (sanitizado)
│   ├── browser_registry.py # Detección de navegadores
│   ├── weather.py          # Clima nativo (Open-Meteo)
│   ├── geolocation.py      # Geolocalización por IP
│   ├── media_control.py    # Control multimedia del sistema
│   ├── volume_control.py   # Control de volumen
│   └── ...                 # 20+ módulos de acciones
├── Min-UI/
│   ├── app/
│   │   ├── api/
│   │   │   ├── config/route.ts  # API de configs (GET/POST)
│   │   │   └── files/route.ts  # API de archivos externos (GET/POST/DELETE)
│   │   ├── page.tsx             # Componente principal
│   │   └── layout.tsx
│   ├── components/
│   │   ├── SettingsDialog.tsx  # 6 pestañas, dispositivos reales
│   │   ├── ControlBar.tsx       # File picker (input type="file")
│   │   ├── Chat.tsx            # Soporte multi-file upload
│   │   ├── Orb.tsx             # Esfera 3D interactiva
│   │   ├── SidebarDock.tsx     # Dock de widgets
│   │   ├── StatusDot.tsx       # Indicador de conexión
│   │   ├── ui/                  # Componentes shadcn-style
│   │   └── widgets/
│   │       ├── WeatherWidget.tsx
│   │       ├── MusicWidget.tsx  # Visualizador 12-bar
│   │       ├── ClockWidget.tsx
│   │       ├── TodoWidget.tsx   # Layout apilado
│   │       └── FavoritesWidget.tsx
│   ├── hooks/
│   │   ├── useWebSocket.ts     # Hook completo WS
│   │   ├── use-mobile.ts       # Viewport móvil
│   │   └── use-toast.ts       # Notificaciones toast
│   ├── lib/
│   │   ├── config-loader.ts   # 3 capas fallback
│   │   └── file-access.ts     # Validación de rutas
│   ├── types/
│   │   └── index.ts           # TypeScript (sin `any`)
│   └── src-tauri/
│       └── main.rs             # Comandos Rust (7 commands)
└── logs/
    └── security_audit.log   # Auditoría de seguridad
```

---

## 🚀 Instalación

### Requisitos
- **Python 3.11+** con pip
- **Node.js 18+** con pnpm
- **Rust** (para compilar Tauri)
- **Windows 11** (soporte nativo)

### Instalación Rápida
```batch
# Clonar el repositorio
git clone https://github.com/WriteColor/Min-AI.git
cd MIN

# Instalar todo automáticamente
MIN.bat install

# Iniciar MIN
MIN.bat
```

### Comandos del Launcher
```batch
MIN.bat              # Iniciar MIN (backend + UI)
MIN.bat install      # Instalación completa del entorno
MIN.bat kill         # Cerrar instancias de MIN (selectivo)
MIN.bat status       # Verificar estado de procesos y archivos
MIN.bat dev          # Modo desarrollo con hot-reload
MIN.bat help         # Mostrar ayuda
```

### Scripts NPM (Min-UI)
```bash
pnpm dev            # Desarrollo web (Next.js)
pnpm tauri:dev      # Desarrollo Tauri completo
pnpm tauri:build    # Build Tauri (requiere Cargo en PATH)
pnpm ui:dev         # Alias para dev
pnpm ui:build       # Alias para build
pnpm lint           # ESLint
```

---

## ⚙️ Configuración

La configuración se gestiona desde la UI (Settings → 5 pestañas) o editando `config/config.json`:

| Campo | Descripción |
|-------|-----------|
| `gemini_api_key` | Clave API de Google Gemini |
| `openrouter_api_key` | Clave API de OpenRouter (fallback) |
| `min_voice` | Voz TTS (Aoede, Charon, etc.) |
| `browser_preference` | `auto` / `chrome` / `firefox` / `edge` / `brave` |
| `mic_device` | Índice del dispositivo de micrófono |
| `speaker_device` | Nombre/índice del altavoz |
| `live_model` | Modelo Gemini para streaming de voz |
| `vision_model` | Modelo para análisis visual |
| `location_mode` | `system` (auto) o `manual` |

---

## 🛡️ Seguridad

MIN implementa **defensa en profundidad** con 3 capas independientes:

1. **Prompt-Level**: Instrucciones explícitas que prohíben comandos destructivos
2. **Terminal-Level**: 29 patrones regex que bloquean `rm -rf`, `format`, `diskpart`, `bcdedit`, etc.
3. **Self-Edit-Level**: Archivos críticos protegidos contra modificación

Cada comando ejecutado se registra en `logs/security_audit.log` para auditoría.

---

## 📝 Licencia

Proyecto privado. Todos los derechos reservados.
