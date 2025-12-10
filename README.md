# Layer

A secure, minimal API layer for remote macOS automation. Turn your Mac into a programmable endpoint that can receive commands from remote users, AI agents, or automation systems.

## Features (v0.1)

- **Open Applications** - Launch whitelisted macOS apps remotely
- **Create Notes** - Create Apple Notes with title and content
- **API Key Authentication** - Secure all endpoints with a secret key
- **Consistent API** - All responses follow a predictable JSON envelope

## Prerequisites

- macOS (tested on Ventura and later)
- Python 3.11+
- Apple Notes app (for note creation)

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
# Copy the example env file
cp .env.example .env

# Generate a secure API key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Edit .env and paste your generated key
nano .env  # or use your preferred editor
```

Your `.env` should look like:
```
MAC_API_KEY=your-generated-secure-key-here
```

### 5. Grant Permissions

The first time you run commands that interact with Notes or other apps, macOS will prompt for permissions. Make sure to:

1. Allow Terminal (or your IDE) to control Notes in **System Preferences > Privacy & Security > Automation**
2. If prompted, allow accessibility permissions

## Running the Server

```bash
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

Or run directly:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

All authenticated endpoints require the `X-API-Key` header.

### Health Check

```bash
curl http://localhost:8000/ping
```

Response:
```json
{
  "status": "ok",
  "data": {"message": "pong"}
}
```

### List Allowed Apps

```bash
curl -H "X-API-Key: YOUR_KEY" http://localhost:8000/allowed-apps
```

Response:
```json
{
  "status": "ok",
  "data": {
    "allowed": [
      {"key": "spotify", "mac_app_name": "Spotify"},
      {"key": "safari", "mac_app_name": "Safari"},
      ...
    ]
  }
}
```

### Open an Application

```bash
curl -X POST http://localhost:8000/open-app \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"app": "spotify"}'
```

Response:
```json
{
  "status": "ok",
  "data": {
    "message": "Successfully opened Spotify",
    "app": "Spotify"
  }
}
```

### Create a Note

```bash
curl -X POST http://localhost:8000/create-note \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "My Note", "content": "Hello from the API!"}'
```

Response:
```json
{
  "status": "ok",
  "data": {
    "message": "Note 'My Note' created in iCloud account",
    "title": "My Note"
  }
}
```

## Error Responses

All errors follow the same format:

```json
{
  "status": "error",
  "message": "Human-readable error description",
  "detail": null
}
```

### Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Invalid request body |
| 401 | Missing or invalid API key |
| 404 | App not in whitelist |
| 500 | Execution error (app not installed, AppleScript failure, etc.) |

## Security Notes

⚠️ **Important Security Considerations:**

1. **Never expose port 8000 directly to the internet** without a secure tunnel
2. **Keep your API key secret** - treat it like a password
3. **Use HTTPS** when accessing remotely (via ngrok or Cloudflare Tunnel)
4. **Rotate your API key** if you suspect it's been compromised

### Remote Access (Optional)

For remote access, use a secure tunnel:

```bash
# Using ngrok (install from https://ngrok.com)
ngrok http 8000
```

This gives you a public HTTPS URL that tunnels to your local server.

## Extending the API

### Adding New Apps to Whitelist

Edit `config.py` and add entries to `ALLOWED_APPS`:

```python
ALLOWED_APPS = {
    "spotify": "Spotify",
    "myapp": "My Custom App",  # Add your app here
    ...
}
```

### Adding New Endpoints

1. Add request/response models to `schemas.py`
2. Add execution logic to `executor.py`
3. Add the route to `main.py`

## Troubleshooting

### "MAC_API_KEY not set" Error

Make sure you:
1. Created a `.env` file (copy from `.env.example`)
2. Set the `MAC_API_KEY` value in `.env`
3. Are running from the project directory

### Notes Permission Denied

macOS requires explicit permission for automation:

1. Open **System Preferences > Privacy & Security > Automation**
2. Find your terminal app (Terminal, iTerm, VS Code, etc.)
3. Enable the checkbox for **Notes**

### "Application not installed" Error

The app exists in the whitelist but isn't installed on your Mac. Either:
- Install the app
- Remove it from the whitelist in `config.py`

### AppleScript Timeout

If note creation times out:
1. Check if Notes app is responding
2. Ensure you have a valid Notes account (iCloud or local)
3. Try creating a note manually first

### iCloud Notes Not Working

If you don't use iCloud for Notes:
1. The API will automatically fall back to "On My Mac" account
2. If that fails, check **Notes > Preferences** to verify your accounts
