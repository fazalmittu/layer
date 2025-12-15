# Layer

A secure, minimal API layer for remote macOS automation. Turn your Mac into a programmable endpoint that can receive commands from remote users, AI agents, or automation systems.

## Features

- **Application Control** - Open whitelisted macOS apps
- **Notes** - Create Apple Notes
- **Clipboard** - Read/write system clipboard
- **Screenshots** - Capture screen as base64 PNG
- **Notifications** - Send macOS notifications
- **Text-to-Speech** - Speak text aloud
- **System Controls** - Volume, sleep, lock
- **Shortcuts** - Run Shortcuts.app workflows
- **Filesystem** - Read/write files in safe directories
- **Pomodoro Timer** - Built-in focus timer with notifications
- **Window Layout** - Arrange windows (requires Rectangle app)
- **Custom Workflows** - Define your own multi-step automations in YAML
- **API Key Authentication** - Secure all endpoints

## Prerequisites

- macOS (Ventura or later)
- Python 3.11+

### Optional: Rectangle (for Window Layout)

The `window-layout` action requires [Rectangle](https://rectangleapp.com/) to be installed.

```bash
# Install via Homebrew
brew install --cask rectangle
```

After installing, you'll need to grant Rectangle accessibility permissions:
1. Open **System Preferences > Privacy & Security > Accessibility**
2. Enable Rectangle in the list

If Rectangle is not installed, any workflow using `window-layout` will fail with a helpful error message.

## Setup

### 1. Clone and Navigate

```bash
cd layer
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Generate a secure API key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Create .env file with your key
echo "MAC_API_KEY=your-generated-key-here" > .env
```

### 5. Grant Permissions

The first time you run commands, macOS will prompt for permissions:

1. Allow Terminal (or your IDE) to control apps in **System Preferences > Privacy & Security > Automation**
2. If prompted, allow accessibility permissions

## Running the Server

```bash
source venv/bin/activate
python main.py
```

The API will be available at `http://localhost:8000`

---

## Custom Workflows

The killer feature of Layer is **custom workflows**. Define multi-step automations in `workflows.yaml` and call them via a single API endpoint.

### Example: workflows.yaml

```yaml
workflows:
  morning-routine:
    description: "Start your morning with apps and a greeting"
    inputs:
      - name: greeting
        default: "Good morning!"
    steps:
      - action: open-app
        params:
          app: slack
      - action: open-app
        params:
          app: vscode
      - action: notify
        params:
          title: "Morning Routine"
          message: "{{ input.greeting }}"

  focus-session:
    description: "Start a focus session"
    inputs:
      - name: duration
        default: 25
    steps:
      - action: volume
        params:
          mute: true
      - action: pomodoro-start
        params:
          work_duration: "{{ input.duration }}"
      - action: notify
        params:
          title: "Focus Started"
          message: "{{ input.duration }} minutes"

  coding-layout:
    description: "Set up split windows for coding"
    steps:
      - action: open-app
        params:
          app: vscode
      - action: window-layout
        params:
          layout: left-half
      - action: open-app
        params:
          app: terminal
      - action: window-layout
        params:
          layout: right-half
```

### Running a Workflow

```bash
# Run with default inputs
curl -X POST http://localhost:8000/run/morning-routine \
  -H "X-API-Key: YOUR_KEY"

# Run with custom inputs
curl -X POST http://localhost:8000/run/focus-session \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"duration": 45}'
```

### Variable Substitution

Use `{{ }}` syntax to reference:

| Variable | Description |
|----------|-------------|
| `{{ input.name }}` | Runtime input passed when calling the workflow |
| `{{ steps[0].field }}` | Output from a previous step |
| `{{ timestamp }}` | Current timestamp (YYYY-MM-DD HH:MM:SS) |
| `{{ date }}` | Current date (YYYY-MM-DD) |
| `{{ time }}` | Current time (HH:MM:SS) |

### Conditional Execution

Add `if` to skip steps based on conditions:

```yaml
steps:
  - action: clipboard-get
  - action: notify
    if: "steps[0].text != ''"
    params:
      title: "Clipboard has content"
      message: "{{ steps[0].text }}"
```

Supported operators: `==`, `!=`, `>`, `<`, `>=`, `<=`

### Available Actions

| Action | Description |
|--------|-------------|
| `open-app` | Open a whitelisted application |
| `notify` | Send a macOS notification |
| `speak` | Text-to-speech |
| `screenshot` | Capture screen |
| `clipboard-get` | Get clipboard text |
| `clipboard-set` | Set clipboard text |
| `create-note` | Create an Apple Note |
| `open-url` | Open URL in browser |
| `volume` | Set volume level or mute |
| `run-shortcut` | Run a Shortcuts.app shortcut |
| `sleep` | Put system to sleep |
| `lock` | Lock the screen |
| `window-layout` | Arrange windows (requires Rectangle) |
| `pomodoro-start` | Start a pomodoro timer |
| `pomodoro-stop` | Stop the pomodoro timer |
| `pomodoro-status` | Get pomodoro status |

### Window Layouts (Rectangle)

Available layout options for `window-layout`:

- `left-half`, `right-half`, `top-half`, `bottom-half`
- `top-left`, `top-right`, `bottom-left`, `bottom-right`
- `first-third`, `center-third`, `last-third`
- `first-two-thirds`, `last-two-thirds`
- `maximize`, `almost-maximize`, `center`, `restore`
- `smaller`, `larger`

---

## API Endpoints

All endpoints (except `/ping`) require the `X-API-Key` header.

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/ping` | Health check (no auth required) |
| **Apps** | | |
| `GET` | `/allowed-apps` | List whitelisted applications |
| `POST` | `/open-app` | Open a whitelisted application |
| **Notes** | | |
| `POST` | `/create-note` | Create a new Apple Note |
| **Clipboard** | | |
| `GET` | `/clipboard` | Get clipboard text content |
| `POST` | `/clipboard` | Set clipboard text content |
| **Screenshot** | | |
| `GET` | `/screenshot` | Capture screen as base64 PNG |
| **Browser** | | |
| `POST` | `/open-url` | Open URL in default browser |
| **Shortcuts** | | |
| `POST` | `/run-shortcut` | Run a Shortcuts.app shortcut |
| **Notifications** | | |
| `POST` | `/notify` | Send a macOS notification |
| **Speech** | | |
| `POST` | `/speak` | Text-to-speech output |
| **System** | | |
| `GET` | `/volume` | Get volume level and mute status |
| `POST` | `/volume` | Set volume level or mute/unmute |
| `POST` | `/sleep` | Put system to sleep |
| `POST` | `/lock` | Lock the screen |
| **Filesystem** | | |
| `POST` | `/files/list` | List files in a directory |
| `POST` | `/files/read` | Read a text file |
| `POST` | `/files/write` | Write to a file |
| `GET` | `/downloads` | List Downloads folder |
| **Pomodoro** | | |
| `POST` | `/pomodoro/start` | Start a pomodoro timer |
| `GET` | `/pomodoro/status` | Get current timer status |
| `POST` | `/pomodoro/stop` | Stop the timer |
| `POST` | `/pomodoro/skip` | Skip to next phase |
| **Workflows** | | |
| `GET` | `/workflows` | List all workflows |
| `GET` | `/workflows/{name}` | Get workflow definition |
| `PUT` | `/workflows/{name}` | Create/update a workflow |
| `DELETE` | `/workflows/{name}` | Delete a workflow |
| `POST` | `/run/{name}` | Execute a workflow |

---

## Examples

### Run a Workflow

```bash
curl -X POST http://localhost:8000/run/morning-routine \
  -H "X-API-Key: YOUR_KEY"
```

Response:
```json
{
  "status": "ok",
  "data": {
    "workflow": "morning-routine",
    "steps_executed": 4,
    "steps_skipped": 0,
    "results": [
      {"step": 0, "action": "open-app", "status": "ok"},
      {"step": 1, "action": "open-app", "status": "ok"},
      {"step": 2, "action": "notify", "status": "ok"},
      {"step": 3, "action": "speak", "status": "ok"}
    ],
    "duration_ms": 1234
  }
}
```

### Create a Workflow via API

```bash
curl -X PUT http://localhost:8000/workflows/my-workflow \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "My custom workflow",
    "steps": [
      {"action": "notify", "params": {"title": "Hello", "message": "World"}}
    ]
  }'
```

### Start a Pomodoro

```bash
curl -X POST http://localhost:8000/pomodoro/start \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"work_duration": 25, "break_duration": 5, "focus_mode": true}'
```

---

## Error Responses

All errors follow the same format:

```json
{
  "status": "error",
  "message": "Human-readable error description",
  "detail": null
}
```

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Invalid request or workflow error |
| 401 | Missing or invalid API key |
| 404 | Resource not found |
| 500 | Execution error |

---

## Security Notes

⚠️ **Important:**

1. **Never expose port 8000 directly to the internet** without a secure tunnel
2. **Keep your API key secret** - treat it like a password
3. **Use HTTPS** when accessing remotely (via ngrok or Cloudflare Tunnel)

### Remote Access (Optional)

```bash
# Using ngrok
ngrok http 8000
```

---

## Troubleshooting

### "MAC_API_KEY not set" Error

Make sure you created a `.env` file with your API key.

### Notes Permission Denied

1. Open **System Preferences > Privacy & Security > Automation**
2. Enable your terminal app for **Notes**

### Window Layout Not Working

1. Install Rectangle: `brew install --cask rectangle`
2. Grant accessibility permissions to Rectangle
3. Make sure Rectangle is running

### AppleScript Timeout

1. Check if the target app is responding
2. Try the action manually first
3. Restart the app if needed
