# MIN AI - Test Suite

## Descripción

Este directorio contiene todos los tests para verificar las funcionalidades del asistente MIN AI.

## Estructura

```
tests/
├── test_01_installed_apps.py      # Descubrir apps/juegos instalados
├── test_02_app_mute.py           # Silenciar aplicaciones
├── test_03_file_creation.py     # Crear archivos extensos
├── test_04_fractal_folders.py    # Estructuras de carpetas fractales
├── test_05_recycle_bin.py        # Eliminación a papelera
├── test_06_music_control.py      # Control de Spotify
├── test_07_web_search.py         # Búsqueda web sin navegador
├── test_08_song_creation.py      # Crear letras y canciones
├── test_09_personality.py        # Verificar personalidad
├── test_runner.py                # Ejecutor de tests
├── test_v2.py                    # Legacy: WebSocket
├── test_simple.py                # Legacy: Tests simples
├── test_filo.py                  # Legacy: Filosofía
├── test_one.py                   # Legacy: Uno
├── test_dificil.py               # Legacy: Difícil
├── test_ws_voice.py              # Legacy: Voz WebSocket
├── test_windows_service.py       # Legacy: Windows service
└── test_volume_fix.py            # Legacy: Fix volumen
```

## Uso

### Listar tests disponibles

```bash
python test_runner.py --list
```

### Ejecutar un test específico

```bash
python test_runner.py --run 01
```

### Ejecutar por categoría

```bash
python test_runner.py --category music
```

Categorías disponibles:
- `system` - Tests de sistema (apps instaladas, mute)
- `files` - Tests de archivos (creación, carpetas, papelera)
- `music` - Tests de música (Spotify, creación de canciones)
- `search` - Tests de búsqueda web
- `personality` - Tests de personalidad/conversacional

### Ejecutar todos los tests

```bash
python test_runner.py --all
```

## Tests Individuales

### Test 01: Aplicaciones/Juegos instalados
Descubre aplicaciones y juegos instalados en Windows.
- `get_installed_apps()` - Lista todas las apps
- `get_installed_games()` - Lista juegos

### Test 02: Mute de aplicaciones
Silencia aplicaciones específicas.
- `set_app_mute(app, mute_state)`
- `get_app_mute_state(app)`

### Test 03: Creación de archivos extensos
Crea múltiples tipos de archivos:
- **.txt** - Archivos de texto largos
- **.md** - Markdown con soporte LaTeX/KaTeX para fórmulas
- **.docx** - Documentos Word
- **.xlsx** - Spreadsheets Excel
- **.pptx** - Presentaciones PowerPoint

### Test 04: Estructuras de carpetas fractales
Genera estructuras de carpetas con patrones fractales:
- **Sierpinski** - Triángulo fractal
- **Fibonacci** - Árbol de Fibonacci
- **Mandelbrot** - Grid recursivo

### Test 05: Eliminación a papelera
Verifica que los archivos se eliminen a la papelera de reciclaje, no se borren permanentemente.

### Test 06: Control de música Spotify
Controla Spotify:
- `spotify_play()`, `spotify_pause()`
- `spotify_next()`, `spotify_previous()`
- `spotify_volume(level)`
- `spotify_current_song()`
- `spotify_search(query)`

### Test 07: Búsqueda web sin navegador
Búsquedas que retornan información resumida:
- `search_web(query)` - Búsqueda general
- `search_news(topic)` - Noticias
- `search_facts(query)` - Información factual
- Búsquedas con fechas específicas
- Búsquedas matemáticas

### Test 08: Creación de letras y canciones
Genera letras y canciones en español:
- `generate_song_lyrics(prompt)` - Crea letra
- `generate_song_from_lyrics(lyrics, ...)` - Genera canción
- `generate_song_simple(description, ...)` - Descripción directa

### Test 09: Verificación de personalidad
Evalúa que el asistente:
- ✓ Habla de forma natural (sin frases robóticas)
- ✓ Usa muletillas (eh, mmm, este, bueno)
- ✓ No usa frases estáticas repetitivas
- ✓ Respeta reglas de uso de herramientas
- ✓ Responde con longitud apropiada

## Tests Legacy

Los tests heredados (`test_v2.py`, `test_simple.py`, etc.) son tests anteriores que pueden servir como referencia pero no están integrados al test runner principal.

## Output

Los archivos generados por los tests se guardan en:

```
C:/React-Nextjs-Projects/Jarvis AI/tests_output/
├── fractal_test/           # Estructuras fractales
├── recycle_test/           # Archivos eliminados
├── music_test/             # Canciones generadas
└── (otros archivos de prueba)
```

## Notas

- Algunos tests requieren que MIN esté corriendo
- Los tests de música requieren Spotify instalado y conectado
- Los tests de canción requieren API de generación de música
- Los tests de web search requieren API keys configuradas
