# Guia de Inicio Rapido — MIN AI

Esta guia te permite iniciar MIN en minutos.

---

## 1. Requisitos Previos

Antes de iniciar, asegurate de tener:

| Software | Version minima | Verificacion |
|----------|---------------|--------------|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| pnpm | 8+ | `pnpm --version` |
| Rust | 1.70+ | `rustc --version` |
| Windows | 11 | — |

---

## 2. Instalacion (Solo una vez)

```batch
cd "C:\React-Nextjs-Projects\Jarvis AI"
MIN.bat install
```

Esto instala:
- Entorno virtual Python (.venv)
- Dependencias Python (requirements.txt)
- Dependencias Node (pnpm install dentro de Min-UI)
- Registra atajos globales

---

## 3. Iniciar MIN — Opciones

### Opcion A: Launcher automatico (recomendado)

```batch
MIN.bat
```

Inicia **backend + frontend** con un solo comando.
El launcher abre una ventana y cierra automaticamente.

### Opcion B: Solo backend Python

```batch
.venv\Scripts\python.exe main.py
```

Inicia solo el servidor WebSocket en `ws://127.0.0.1:8765`.
No abre ventana de aplicacion.

### Opcion C: Frontend en navegador

```batch
cd Min-UI
pnpm dev
```

Abre la UI web en `http://localhost:3000`.
Necesita que el backend ya este corriendo.

### Opcion D: Desarrollo completo (Tauri)

```batch
cd Min-UI
pnpm tauri dev
```

Inicia Tauri en modo desarrollo con hot-reload.

---

## 4. Verificar que Esta Funcionando

### Backend activo

El backend esta corriendo cuando `logs/min.log` muestra:

```
[MIN] Connected!
SYS: MIN en linea.
[WS] Server running at ws://127.0.0.1:8765
```

### Verificar con el launcher

```batch
MIN.bat status
```

Muestra:
- Procesos Python activos
- Estado de archivos criticos
- Puerto WebSocket (8765)

---

## 5. Apagar MIN

### Cerrar todas las instancias

```batch
MIN.bat kill
```

Cierra selectivamente solo los procesos de MIN
(otros procesos Python no se ven afectados).

### Forzar cierre desde terminal

```batch
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *MIN*"
```

---

## 6. Configuracion

### Primera vez: Agregar API Keys

Edita `config/config.json`:

```json
{
  "gemini_api_key": "TU_API_KEY_DE_GOOGLE",
  "openrouter_api_key": "TU_API_KEY_DE_OPENROUTER",
  "min_voice": "Aoede",
  "live_model": "gemini-2.0-flash-exp",
  "vision_model": "gemini-1.5-flash"
}
```

### Obtener API Keys

- **Google Gemini**: https://aistudio.google.com/app/apikey
- **OpenRouter**: https://openrouter.ai/keys

### Configuracion desde la UI

Abre Settings en la aplicacion (icono de engranaje).
9 pestanas disponibles:
- Assistant (voz, modelo, idioma)
- Guardian (seguridad)
- Accessibility
- API Keys
- Location
- Local LLM
- Apps
- Profile
- System

---

## 7. Arquitectura de Conexion

```
┌─────────────────────────────────────────────────┐
│                   MIN UI (Tauri / Web)          │
│                   localhost:3000                 │
└─────────────────┬───────────────────────────────┘
                  │ WebSocket
                  │ ws://127.0.0.1:8765
                  ▼
┌─────────────────────────────────────────────────┐
│              Backend Python (main.py)           │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Gemini   │  │ Vosk     │  │ Guardian     │  │
│  │ Live API │  │ WakeWord │  │ Security     │  │
│  └──────────┘  └──────────┘  └──────────────┘  │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Actions  │  │ Web      │  │ System       │  │
│  │ Registry │  │ Browser  │  │ Control      │  │
│  └──────────┘  └──────────┘  └──────────────┘  │
└─────────────────────────────────────────────────┘
```

- **Backend**: `main.py` — servidor WebSocket, logica de IA, acciones
- **Frontend**: `Min-UI/` — React + Tauri, Orb 3D, widgets
- **Comunicacion**: WebSocket en puerto 8765

---

## 8. Estados del Orb (Interfaz Visual)

El Orb 3D cambia de color segun el estado:

| Estado | Color | Significado |
|--------|-------|-------------|
| LISTENING | Azul (#3B82F6) | Escuchando tu voz |
| THINKING | Purpura (#8B5CF6) | Procesando respuesta |
| SPEAKING | Cyan (#06B6D4) | Hablando respuesta |
| MUTED | Gris (#6B7280) | Silenciado |
| SUSPENDED | Amber (#F59E0B) | En espera |
| OFFLINE | Slate (#64748B) | Sin conexion |

---

## 9. Solucion de Problemas

### Error: "No se encontro Python"

```batch
MIN.bat install
```

Vuelve a ejecutar el instalador.

### Error: "ctypes.UUID no existe"

Este error ya fue corregido en el codigo.
Si persiste, asegurate de estar usando la version mas reciente.

### Error: "Module not found"

```batch
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Backend no responde en WebSocket

Verificar que el backend esta corriendo:

```batch
MIN.bat status
```

Ver logs:

```batch
Get-Content logs\min.log -Tail 20
```

### Verificar puertos en uso

```batch
netstat -an | findstr 8765
```

Si el puerto esta ocupado, cerrar procesos anteriores:

```batch
MIN.bat kill
```

---

## 10. Comandos del Launcher

| Comando | Accion |
|--------|--------|
| `MIN.bat` | Iniciar MIN completo |
| `MIN.bat install` | Instalar entorno |
| `MIN.bat kill` | Cerrar MIN |
| `MIN.bat status` | Ver estado |
| `MIN.bat dev` | Modo desarrollo |
| `MIN.bat help` | Mostrar ayuda |

---

## 11. Estructura de Archivos

```
MIN/
├── main.py              # Entry point backend
├── ui.py                # Servidor WebSocket
├── MIN.bat              # Launcher
├── config/
│   └── config.json      # API keys y configuracion
├── Min-UI/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/  # Orb, ControlBar, Chat, Settings...
│   │   └── hooks/
│   │       └── useWebSocket.ts
│   └── src-tauri/       # Backend Rust (Tauri)
├── actions/             # Modulos de acciones (20+)
├── core/                # Prompt, memoria
├── services/           # Windows API, audio, web
└── logs/
    └── min.log          # Log de ejecucion
```

---

## 12. Inicio Rapido Resumido

```batch
# 1. Instalar (solo una vez)
MIN.bat install

# 2. Agregar API keys en config/config.json

# 3. Iniciar
MIN.bat
```

Listo. MIN estara disponible en `http://localhost:3000` o en la aplicacion Tauri.
