"""
Layer
A secure, minimal API for remote macOS automation.
"""

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse, FileResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Any
from pathlib import Path

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
    PomodoroStartRequest,
)
from pomodoro import pomodoro_manager
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
    # Window Layout
    set_window_layout,
)
from workflow_engine import workflow_engine, WorkflowError


# =============================================================================
# App Initialization
# =============================================================================

app = FastAPI(
    title="Layer",
    description="A secure API for remote macOS automation",
)

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


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
# UI / Frontend
# =============================================================================

@app.get("/")
async def serve_ui():
    """Serve the workflow editor UI."""
    index_path = Path(__file__).parent / "static" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return JSONResponse({"message": "UI not found. Check static/index.html"}, status_code=404)


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
# Pomodoro Timer
# =============================================================================

async def on_work_session_complete():
    """Called when a work session ends."""
    try:
        send_notification(
            "Pomodoro Complete!",
            "Time for a break. Step away from the screen.",
            subtitle=f"Session #{pomodoro_manager.state.sessions_completed}",
            sound=True
        )
        speak_text("Pomodoro complete. Time for a break.", rate=200)
    except Exception:
        pass  # Don't fail the timer if notification fails


async def on_break_complete():
    """Called when a break ends."""
    try:
        send_notification(
            "Break Over!",
            "Ready to focus? Starting next work session.",
            sound=True
        )
        speak_text("Break over. Let's get back to work.", rate=200)
    except Exception:
        pass


# Set up callbacks
pomodoro_manager.set_callbacks(on_work_session_complete, on_break_complete)


@app.post("/pomodoro/start")
async def pomodoro_start(
    request: PomodoroStartRequest,
    api_key: str = Header(None, alias="X-API-Key")
) -> dict[str, Any]:
    """
    Start a pomodoro work session.
    
    Optionally enables focus mode (mutes volume).
    After work_duration minutes, notifies and starts break.
    After break_duration minutes, notifies and starts next work session.
    """
    require_auth(api_key)
    
    if pomodoro_manager.is_active:
        raise HTTPException(status_code=400, detail="Pomodoro already active. Stop it first.")
    
    original_volume = None
    
    # Enable focus mode if requested (just mute - dark mode requires accessibility permissions)
    if request.focus_mode:
        try:
            vol_info = get_volume()
            original_volume = vol_info.get("level", 50)
            set_volume(mute=True)
        except ExecutionError:
            pass  # Continue even if mute fails
    
    # Start the pomodoro
    result = await pomodoro_manager.start(
        work_duration=request.work_duration,
        break_duration=request.break_duration,
        focus_mode=request.focus_mode,
        original_volume=original_volume,
    )
    
    # Send start notification
    try:
        send_notification(
            "Pomodoro Started",
            f"{request.work_duration} minute work session. Focus!",
            sound=True
        )
    except ExecutionError:
        pass
    
    return success_response(result)


@app.get("/pomodoro/status")
async def pomodoro_status(api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """Get current pomodoro timer status."""
    require_auth(api_key)
    return success_response(pomodoro_manager.get_status())


@app.post("/pomodoro/stop")
async def pomodoro_stop(api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """
    Stop the current pomodoro session.
    
    Restores original volume if focus mode was enabled.
    """
    require_auth(api_key)
    
    if not pomodoro_manager.is_active:
        raise HTTPException(status_code=400, detail="No active pomodoro to stop.")
    
    result = await pomodoro_manager.stop()
    
    # Restore original volume
    if result.get("original_volume") is not None:
        try:
            set_volume(mute=False)
            set_volume(level=result["original_volume"])
        except ExecutionError:
            pass
    
    try:
        send_notification(
            "Pomodoro Stopped",
            f"Completed {result.get('sessions_completed', 0)} session(s).",
            sound=False
        )
    except ExecutionError:
        pass
    
    return success_response({
        "stopped": True,
        "sessions_completed": result.get("sessions_completed", 0),
    })


@app.post("/pomodoro/skip")
async def pomodoro_skip(api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """
    Skip to the next phase.
    
    If in work session: counts as complete, starts break.
    If in break: starts next work session.
    """
    require_auth(api_key)
    
    if not pomodoro_manager.is_active:
        raise HTTPException(status_code=400, detail="No active pomodoro to skip.")
    
    result = await pomodoro_manager.skip()
    
    phase = result.get("session_type", "work")
    try:
        send_notification(
            "Phase Skipped",
            f"Now in {phase} mode.",
            sound=True
        )
    except ExecutionError:
        pass
    
    return success_response(result)


# =============================================================================
# Workflows
# =============================================================================

# Helper functions for workflow actions that need to match expected signatures
def _workflow_open_app(app: str) -> str:
    """Open app for workflow - validates against whitelist."""
    app_key = app.lower().strip()
    if app_key not in ALLOWED_APPS:
        raise ExecutionError(f"App '{app}' is not in the whitelist")
    return open_application(ALLOWED_APPS[app_key])


def _workflow_notify(title: str, message: str, subtitle: str = None, sound: bool = True) -> str:
    return send_notification(title, message, subtitle, sound)


def _workflow_speak(text: str, voice: str = None, rate: int = None) -> str:
    return speak_text(text, voice, rate)


def _workflow_screenshot() -> dict:
    return {"image": take_screenshot(), "format": "png"}


def _workflow_clipboard_get() -> dict:
    return {"text": get_clipboard()}


def _workflow_clipboard_set(text: str) -> str:
    return set_clipboard(text)


def _workflow_create_note(title: str, content: str) -> str:
    return create_note(title, content)


def _workflow_open_url(url: str) -> str:
    return open_url(url)


def _workflow_volume(level: int = None, mute: bool = None) -> str:
    return set_volume(level, mute)


def _workflow_run_shortcut(name: str, input: str = None) -> dict:
    return {"output": run_shortcut(name, input)}


def _workflow_sleep() -> str:
    return sleep_system()


def _workflow_lock() -> str:
    return lock_screen()


def _workflow_window_layout(layout: str, app: str = None) -> str:
    return set_window_layout(layout, app)


def _workflow_pomodoro_start(work_duration: int = 25, break_duration: int = 5, focus_mode: bool = False) -> dict:
    """Synchronous wrapper for pomodoro start."""
    import asyncio
    
    # Get or create event loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Handle focus mode
    original_volume = None
    if focus_mode:
        try:
            vol_info = get_volume()
            original_volume = vol_info.get("level", 50)
            set_volume(mute=True)
        except ExecutionError:
            pass
    
    # Create a coroutine and run it
    async def start():
        return await pomodoro_manager.start(
            work_duration=int(work_duration) if isinstance(work_duration, str) else work_duration,
            break_duration=int(break_duration) if isinstance(break_duration, str) else break_duration,
            focus_mode=focus_mode,
            original_volume=original_volume,
        )
    
    # Run in existing loop or create new one
    if loop.is_running():
        future = asyncio.ensure_future(start())
        # Can't await in sync context with running loop, so just return status
        return pomodoro_manager.get_status()
    else:
        return loop.run_until_complete(start())


def _workflow_pomodoro_stop() -> dict:
    """Synchronous wrapper for pomodoro stop."""
    import asyncio
    
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def stop():
        return await pomodoro_manager.stop()
    
    if loop.is_running():
        return {"stopped": True, "sessions_completed": pomodoro_manager.state.sessions_completed}
    else:
        return loop.run_until_complete(stop())


def _workflow_pomodoro_status() -> dict:
    return pomodoro_manager.get_status()


# Register all actions with the workflow engine
workflow_engine.register_actions({
    "open-app": _workflow_open_app,
    "notify": _workflow_notify,
    "speak": _workflow_speak,
    "screenshot": _workflow_screenshot,
    "clipboard-get": _workflow_clipboard_get,
    "clipboard-set": _workflow_clipboard_set,
    "create-note": _workflow_create_note,
    "open-url": _workflow_open_url,
    "volume": _workflow_volume,
    "run-shortcut": _workflow_run_shortcut,
    "sleep": _workflow_sleep,
    "lock": _workflow_lock,
    "window-layout": _workflow_window_layout,
    "pomodoro-start": _workflow_pomodoro_start,
    "pomodoro-stop": _workflow_pomodoro_stop,
    "pomodoro-status": _workflow_pomodoro_status,
})


@app.get("/workflows")
async def list_workflows(api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """List all defined workflows."""
    require_auth(api_key)
    try:
        workflows = workflow_engine.list_workflows()
        return success_response({"workflows": workflows})
    except WorkflowError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workflows/{name}")
async def get_workflow(name: str, api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """Get a specific workflow definition."""
    require_auth(api_key)
    workflow = workflow_engine.get_workflow(name)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow '{name}' not found")
    return success_response(workflow)


@app.put("/workflows/{name}")
async def create_or_update_workflow(
    name: str,
    request: Request,
    api_key: str = Header(None, alias="X-API-Key")
) -> dict[str, Any]:
    """Create or update a workflow."""
    require_auth(api_key)
    try:
        body = await request.json()
        workflow = workflow_engine.create_workflow(name, body)
        return success_response(workflow)
    except WorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/workflows/{name}")
async def delete_workflow(name: str, api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """Delete a workflow."""
    require_auth(api_key)
    deleted = workflow_engine.delete_workflow(name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Workflow '{name}' not found")
    return success_response({"deleted": name})


@app.post("/run/{name}")
async def run_workflow(
    name: str,
    request: Request,
    api_key: str = Header(None, alias="X-API-Key")
) -> dict[str, Any]:
    """
    Execute a workflow by name.
    
    Optional JSON body can provide runtime inputs for the workflow.
    """
    require_auth(api_key)
    
    # Parse optional inputs from body
    inputs = None
    try:
        body = await request.body()
        if body:
            inputs = await request.json()
    except Exception:
        pass
    
    try:
        result = workflow_engine.run(name, inputs)
        return success_response(result)
    except WorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    print(f"Starting Layer on http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)
