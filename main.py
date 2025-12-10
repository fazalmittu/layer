"""
Layer - v0.1
A secure, minimal API for remote macOS automation.
"""

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from typing import Any

from config import API_KEY, ALLOWED_APPS, HOST, PORT
from schemas import (
    OpenAppRequest,
    CreateNoteRequest,
    SuccessResponse,
    AllowedApp,
)
from executor import open_application, create_note, ExecutionError


# =============================================================================
# App Initialization
# =============================================================================

app = FastAPI(
    title="Layer",
    description="A secure API for remote macOS automation",
    version="0.1.0",
)


# =============================================================================
# Custom Exception Handler for Consistent Response Format
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
# Authentication Dependency
# =============================================================================

def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")) -> str:
    """
    Validate the API key from request headers.
    Raises 401 if missing or invalid.
    """
    if x_api_key is None:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include 'X-API-Key' header."
        )
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key."
        )
    return x_api_key


# =============================================================================
# Helper Functions
# =============================================================================

def success_response(data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a standard success response envelope."""
    return {
        "status": "ok",
        "data": data or {}
    }


# =============================================================================
# Routes
# =============================================================================

@app.get("/ping")
async def ping() -> dict[str, Any]:
    """
    Health check endpoint.
    Does NOT require authentication.
    """
    return success_response({"message": "pong"})


@app.get("/allowed-apps")
async def allowed_apps(api_key: str = Header(None, alias="X-API-Key")) -> dict[str, Any]:
    """
    List all whitelisted applications that can be opened.
    Requires authentication.
    """
    verify_api_key(api_key)
    
    apps = [
        AllowedApp(key=key, mac_app_name=name).model_dump()
        for key, name in ALLOWED_APPS.items()
    ]
    
    return success_response({"allowed": apps})


@app.post("/open-app")
async def open_app(
    request: OpenAppRequest,
    api_key: str = Header(None, alias="X-API-Key")
) -> dict[str, Any]:
    """
    Open a whitelisted macOS application.
    Requires authentication.
    """
    verify_api_key(api_key)
    
    app_key = request.app.lower().strip()
    
    if app_key not in ALLOWED_APPS:
        raise HTTPException(
            status_code=404,
            detail=f"App '{request.app}' is not in the whitelist. Use /allowed-apps to see available apps."
        )
    
    mac_app_name = ALLOWED_APPS[app_key]
    
    try:
        message = open_application(mac_app_name)
        return success_response({"message": message, "app": mac_app_name})
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/create-note")
async def create_note_endpoint(
    request: CreateNoteRequest,
    api_key: str = Header(None, alias="X-API-Key")
) -> dict[str, Any]:
    """
    Create a new Apple Note with the given title and content.
    Requires authentication.
    """
    verify_api_key(api_key)
    
    if not request.title.strip():
        raise HTTPException(status_code=400, detail="Note title cannot be empty")
    
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Note content cannot be empty")
    
    try:
        message = create_note(request.title, request.content)
        return success_response({
            "message": message,
            "title": request.title
        })
    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    print(f"Starting Layer on http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)

