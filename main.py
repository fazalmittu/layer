"""
Layer
A secure, minimal API for remote macOS automation.
"""

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from typing import Any

from config import API_KEY, ALLOWED_APPS, HOST, PORT
from schemas import (
    OpenAppRequest,
    CreateNoteRequest,
    SetClipboardRequest,
    OpenURLRequest,
    RunShortcutRequest,
    NotifyRequest,
    SpeakRequest,
    VolumeRequest,
    ListFilesRequest,
    ReadFileRequest,
    WriteFileRequest,
    AllowedApp,
)
from executor import (
    ExecutionError,
    # Apps
    open_application,
    # Notes
    create_note,
    # Clipboard
    get_clipboard,
    set_clipboard,
    # Screenshot
    take_screenshot,
    # URL
    open_url,
    # Shortcuts
    run_shortcut,
    # Notifications
    send_notification,
    # Speech
    speak_text,
    # System
    get_volume,
    set_volume,
    get_dark_mode,
    toggle_dark_mode,
    sleep_system,
    lock_screen,
    # Filesystem
    list_files,
    read_file,
    write_file,
    list_downloads,
)


# =============================================================================
# App Initialization
# =============================================================================

app = FastAPI(
    title="Layer",
    description="A secure API for remote macOS automation",
)


# =============================================================================
# Custom Exception Handler
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Wrap all HTTP exceptions in the standard error envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "detail": None,
        }
    )


# =============================================================================
# Authentication
# =============================================================================

def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")) -> str:
    """Validate the API key from request headers."""
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="Missing API key. Include 'X-API-Key' header.")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    return x_api_key


# =============================================================================
# Helpers
# =============================================================================

def success_response(data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a standard success response envelope."""
    return {"status": "ok", "data": data or {}}


def require_auth(api_key: str | None) -> None:
    """Verify API key, raise if invalid."""
    verify_api_key(api_key)


# =============================================================================
# Health Check
# =============================================================================

@app.get("/ping")
async def ping() -> dict[str, Any]:
    """Health check endpoint. No auth required."""
    return success_response({"message": "pong"})


# =============================================================================
# Application Control
# =============================================================================

@app.get("/allowed-apps")
async def allowed_apps(api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """List all whitelisted applications."""
    require_auth(api_key)
    apps = [AllowedApp(key=key, mac_app_name=name).model_dump() for key, name in ALLOWED_APPS.items()]
    return success_response({"allowed": apps})


@app.post("/open-app")
async def open_app_endpoint(request: OpenAppRequest, api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """Open a whitelisted macOS application."""
    require_auth(api_key)
    
    app_key = request.app.lower().strip()
    if app_key not in ALLOWED_APPS:
        raise HTTPException(status_code=404, detail=f"App '{request.app}' is not in the whitelist.")
    
    try:
        message = open_application(ALLOWED_APPS[app_key])
        return success_response({"message": message, "app": ALLOWED_APPS[app_key]})
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Notes
# =============================================================================

@app.post("/create-note")
async def create_note_endpoint(request: CreateNoteRequest, api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """Create a new Apple Note."""
    require_auth(api_key)
    
    if not request.title.strip():
        raise HTTPException(status_code=400, detail="Note title cannot be empty")
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Note content cannot be empty")
    
    try:
        message = create_note(request.title, request.content)
        return success_response({"message": message, "title": request.title})
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Clipboard
# =============================================================================

@app.get("/clipboard")
async def get_clipboard_endpoint(api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """Get current clipboard text content."""
    require_auth(api_key)
    try:
        text = get_clipboard()
        return success_response({"text": text})
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clipboard")
async def set_clipboard_endpoint(request: SetClipboardRequest, api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """Set clipboard text content."""
    require_auth(api_key)
    try:
        message = set_clipboard(request.text)
        return success_response({"message": message})
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Screenshot
# =============================================================================

@app.get("/screenshot")
async def screenshot_endpoint(api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """Take a screenshot and return as base64 PNG."""
    require_auth(api_key)
    try:
        b64_data = take_screenshot()
        return success_response({"image": b64_data, "format": "png", "encoding": "base64"})
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# URL
# =============================================================================

@app.post("/open-url")
async def open_url_endpoint(request: OpenURLRequest, api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """Open a URL in the default browser."""
    require_auth(api_key)
    try:
        message = open_url(request.url)
        return success_response({"message": message, "url": request.url})
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Shortcuts
# =============================================================================

@app.post("/run-shortcut")
async def run_shortcut_endpoint(request: RunShortcutRequest, api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """Run a Shortcuts.app shortcut."""
    require_auth(api_key)
    try:
        output = run_shortcut(request.name, request.input)
        return success_response({"message": f"Shortcut '{request.name}' executed", "output": output})
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Notifications
# =============================================================================

@app.post("/notify")
async def notify_endpoint(request: NotifyRequest, api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """Send a macOS notification."""
    require_auth(api_key)
    try:
        message = send_notification(request.title, request.message, request.subtitle, request.sound)
        return success_response({"message": message})
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Text-to-Speech
# =============================================================================

@app.post("/speak")
async def speak_endpoint(request: SpeakRequest, api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """Speak text using macOS text-to-speech."""
    require_auth(api_key)
    try:
        message = speak_text(request.text, request.voice, request.rate)
        return success_response({"message": message})
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# System Controls
# =============================================================================

@app.get("/volume")
async def get_volume_endpoint(api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """Get current volume settings."""
    require_auth(api_key)
    try:
        vol = get_volume()
        return success_response(vol)
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/volume")
async def set_volume_endpoint(request: VolumeRequest, api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """Set system volume."""
    require_auth(api_key)
    try:
        message = set_volume(request.level, request.mute)
        return success_response({"message": message})
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dark-mode")
async def get_dark_mode_endpoint(api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """Get current dark mode status."""
    require_auth(api_key)
    try:
        enabled = get_dark_mode()
        return success_response({"enabled": enabled})
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/dark-mode")
async def toggle_dark_mode_endpoint(api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """Toggle dark mode."""
    require_auth(api_key)
    try:
        message = toggle_dark_mode()
        return success_response({"message": message})
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sleep")
async def sleep_endpoint(api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """Put the system to sleep."""
    require_auth(api_key)
    try:
        message = sleep_system()
        return success_response({"message": message})
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/lock")
async def lock_endpoint(api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """Lock the screen."""
    require_auth(api_key)
    try:
        message = lock_screen()
        return success_response({"message": message})
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Filesystem
# =============================================================================

@app.post("/files/list")
async def list_files_endpoint(request: ListFilesRequest, api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """List files in a directory (safe directories only)."""
    require_auth(api_key)
    try:
        files = list_files(request.path, request.show_hidden)
        return success_response({"path": request.path, "files": files})
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/files/read")
async def read_file_endpoint(request: ReadFileRequest, api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """Read a text file (safe directories only)."""
    require_auth(api_key)
    try:
        content = read_file(request.path, request.max_size)
        return success_response({"path": request.path, "content": content})
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/files/write")
async def write_file_endpoint(request: WriteFileRequest, api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """Write to a file (safe directories only)."""
    require_auth(api_key)
    try:
        message = write_file(request.path, request.content, request.append)
        return success_response({"message": message, "path": request.path})
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/downloads")
async def list_downloads_endpoint(api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """List files in Downloads folder."""
    require_auth(api_key)
    try:
        files = list_downloads()
        return success_response({"files": files})
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    print(f"Starting Layer on http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)
