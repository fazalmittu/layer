"""
Pydantic models for request/response schemas.
All responses follow a consistent envelope format.
"""

from typing import Any
from pydantic import BaseModel, Field


# =============================================================================
# Request Models
# =============================================================================

class OpenAppRequest(BaseModel):
    """Request body for opening an application."""
    app: str = Field(..., description="App key from whitelist (e.g., 'spotify', 'vscode')")


class CreateNoteRequest(BaseModel):
    """Request body for creating a new Apple Note."""
    title: str = Field(..., description="Note title")
    content: str = Field(..., description="Note body content")


# =============================================================================
# Response Models
# =============================================================================

class SuccessResponse(BaseModel):
    """Standard success response envelope."""
    status: str = "ok"
    data: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Standard error response envelope."""
    status: str = "error"
    message: str
    detail: dict[str, Any] | None = None


class AllowedApp(BaseModel):
    """Single app entry in the whitelist."""
    key: str
    mac_app_name: str


class AllowedAppsData(BaseModel):
    """Data payload for /allowed-apps endpoint."""
    allowed: list[AllowedApp]

