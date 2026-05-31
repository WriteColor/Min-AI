# JARVIS AI - Actions Reference

> **Last updated:** 2025-05-31

---

## Action System Overview

Actions are Python functions that JARVIS calls to perform tasks. They are declared in `TOOL_DECLARATIONS` for AI tool calling and registered in `action_registry.py`.

All actions follow the signature:
```python
def action_name(parameters: dict, player=None) -> str:
    """Description."""
    # Implementation
    return "Result message"
```

---

## System Actions (`actions/system/`)

### open_app

```python
def open_app(app_name: str, player=None) -> str
```

**Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `app_name` | string | Application name or path |

**Example:** `"Open Spotify"`

---

### computer_control

```python
def computer_control(action: str, player=None) -> str
```

**Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `action` | string | "screenshot", "lock", "sleep", "shutdown" |

**Example:** `"Take a screenshot"`

---

### computer_settings

```python
def computer_settings(action: str, value: str = None, player=None) -> str
```

**Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `action` | string | "volume", "brightness", "dark_mode" |
| `value` | string | Target value (e.g., "50", "on", "off") |

**Example:** `"Set volume to 80"`

---

### terminal_agent

```python
def terminal_agent(command: str, player=None) -> str
```

**Security:** 29 regex patterns block destructive commands.

**Example:** `"List files in current directory"`

---

### sleep_mode

```python
def sleep_mode(minutes: int = 30, player=None) -> str
```

**Example:** `"Sleep for 30 minutes"`

---

### shutdown_min

```python
def shutdown_min(minutes: int = 60, player=None) -> str
```

**Example:** `"Shutdown in 60 minutes"`

---

### native_ui

```python
def native_ui(action: str, player=None) -> str
```

**Actions:** click, double_click, right_click, hover, type_text

**Example:** `"Click the start button"`

---

### system_monitor

```python
def system_monitor(player=None) -> str
```

**Returns:** CPU, RAM, GPU usage stats

---

## Automation Actions (`actions/automation/`)

### weather_report

```python
def weather_report(location: str = None, player=None) -> str
```

**Example:** `"Weather in Buenos Aires"`

---

### reminder

```python
def reminder(message: str, minutes: int, player=None) -> str
```

**Example:** `"Remind me in 30 minutes to check email"`

---

### scheduler

```python
def scheduler(action: str, task: str = None, time_str: str = None, player=None) -> str
```

**Actions:** list, add, remove, show

**Example:** `"Schedule meeting at 3pm"`

---

### gmail_control

```python
def gmail_control(action: str, query: str = None, player=None) -> str
```

**Actions:** search_emails, send_email, mark_read, delete_email

**Example:** `"Search emails from Juan"`

---

### whatsapp

```python
def whatsapp(action: str, contact: str = None, message: str = None, player=None) -> str
```

**Actions:** send, read_recent

---

### goals

```python
def goals(action: str, goal: str = None, player=None) -> str
```

**Actions:** add, complete, list, progress

---

### morning_brief

```python
def morning_brief(player=None) -> str
```

Returns weather, calendar, tasks, news summary.

---

### rules_engine

```python
def rules_engine(action: str, rule_text: str = None, player=None) -> str
```

**Actions:** add_rule, list_rules, remove_rule

**Example:** `"When I say good morning, tell me the weather"`

---

### google_drive

```python
def google_drive(action: str, file_name: str = None, player=None) -> str
```

**Actions:** list_files, upload_file, download_file

---

## Vision Actions (`actions/vision/`)

### screen_vision

```python
def screen_vision(question: str, player=None) -> str
```

**Multi-provider:** Uses Gemini/GPT-4V/Pollinations for screen analysis.

**Example:** `"What is displayed on screen?"`

---

### visual_click

```python
def visual_click(target: str, player=None) -> str
```

AI-powered click at screen coordinates.

**Example:** `"Click the X button"`

---

### image_generation

```python
def image_generation(description: str, player=None) -> str
```

**Provider:** Pollinations.ai (free)

**Example:** `"Generate image of a sunset over mountains"`

---

### vision_guardian

```python
def vision_guardian(action: str, player=None) -> str
```

**Actions:** enable, disable, status

Proactive screen monitoring.

---

## Media Actions (`actions/media/`)

### spotify_control

```python
def spotify_control(action: str, query: str = None, player=None) -> str
```

**Actions:** play, pause, next, previous, volume, search

**Example:** `"Play some jazz music"`

---

### youtube_video

```python
def youtube_video(action: str, query: str = None, player=None) -> str
```

**Actions:** search, play, pause, get_current

---

### media_control

```python
def media_control(action: str, player=None) -> str
```

**Actions:** play, pause, next, previous, volume_up, volume_down

---

## Web Actions (`actions/web/`)

### web_search

```python
def web_search(query: str, player=None) -> str
```

**Provider:** DuckDuckGo

**Example:** `"Search for Python tutorials"`

---

### browser_control

```python
def browser_control(action: str, url: str = None, tab: int = None, player=None) -> str
```

**Actions:** open, close, navigate, get_url, list_tabs

---

### web_navigation

```python
def web_navigation(action: str, query: str = None, player=None) -> str
```

**Actions:** youtube_search, google_search, go_back, go_forward, refresh

---

## File Actions (`actions/files/`)

### file_controller

```python
def file_controller(operation: str, path: str = None, content: str = None, player=None) -> str
```

**Operations:** read, write, append, delete, list, search, create_folder

**Example:** `"Read the file notes.txt"`

---

### smart_file_organizer

```python
def smart_file_organizer(directory: str = None, player=None) -> str
```

Auto-organizes files by type.

---

## Memory Actions (`actions/automation/`)

### knowledge_base

```python
def knowledge_base(action: str, query: str = None, memory_type: str = None, player=None) -> str
```

**Actions:** save, search, list_categories, get_recent

**Example:** `"Remember that my birthday is June 15"`

---

### save_memory

```python
def save_memory(category: str, key: str, value: str, player=None) -> str
```

**Example:** `"Save my favorite color is blue"`

---

## Utility Actions (`actions/utils/`)

### openrouter_agent

```python
def openrouter_agent(prompt: str, player=None) -> str
```

Direct OpenRouter query for custom tasks.

---

## Music Actions (`actions/music/`)

### music_control

```python
def music_control(action: str, description: str = None, player=None) -> str
```

**Actions:** generate, stop

**Example:** `"Generate relaxing piano music"`

---

## Tool Declaration Schema

Each tool in `TOOL_DECLARATIONS`:

```json
{
  "name": "action_name",
  "description": "What the action does",
  "parameters": {
    "type": "object",
    "properties": {
      "param_name": {
        "type": "string",
        "description": "Parameter description"
      }
    },
    "required": ["param_name"]
  }
}
```

---

## Parameter Validation

Before execution, `ParameterValidator` checks:
- Required parameters present
- Type matches (string, integer, boolean)
- Enum values valid
- String length within limits

---

## Action Result Format

All actions return a string. Success/error distinguished by prefix:
- Success: `"Opened Spotify successfully"`
- Error: `"Failed: Application not found"`

---

## Adding Custom Actions

1. Create file in appropriate `actions/` subdirectory
2. Define function with `parameters` dict and `player` argument
3. Add tool declaration to `core/tool_schemas.py`
4. Register in `core/action_registry.py`

---

## Security

| Action | Protection |
|--------|------------|
| `terminal_agent` | 29 regex patterns block rm, del, format, shutdown, etc. |
| `self_edit` | Protected file list + backup + syntax validation |
| `file_controller` | Restricted to project directory |
| `shutdown_min` | Confirmation required for < 5 minutes |
