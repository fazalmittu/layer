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


class SetClipboardRequest(BaseModel):
    """Request body for setting clipboard content."""
    text: str = Field(..., description="Text to copy to clipboard")


class OpenURLRequest(BaseModel):
    """Request body for opening a URL."""
    url: str = Field(..., description="URL to open in default browser")


class RunShortcutRequest(BaseModel):
    """Request body for running a Shortcut."""
    name: str = Field(..., description="Name of the Shortcut to run")
    input: str | None = Field(None, description="Optional input text for the Shortcut")


class NotifyRequest(BaseModel):
    """Request body for sending a notification."""
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification body text")
    subtitle: str | None = Field(None, description="Optional subtitle")
    sound: bool = Field(True, description="Play notification sound")


class SpeakRequest(BaseModel):
    """Request body for text-to-speech."""
    text: str = Field(..., description="Text to speak")
    voice: str | None = Field(None, description="Voice name (e.g., 'Samantha', 'Alex')")
    rate: int | None = Field(None, description="Speech rate (words per minute, default ~175)")


class VolumeRequest(BaseModel):
    """Request body for setting volume."""
    level: int | None = Field(None, ge=0, le=100, description="Volume level 0-100")
    mute: bool | None = Field(None, description="Mute/unmute (overrides level if set)")


class BrightnessRequest(BaseModel):
    """Request body for setting brightness."""
    level: float = Field(..., ge=0, le=1, description="Brightness level 0.0-1.0")


class ListFilesRequest(BaseModel):
    """Request body for listing files."""
    path: str = Field(..., description="Directory path to list")
    show_hidden: bool = Field(False, description="Include hidden files")


class ReadFileRequest(BaseModel):
    """Request body for reading a file."""
    path: str = Field(..., description="File path to read")
    max_size: int = Field(1048576, description="Max file size in bytes (default 1MB)")


class WriteFileRequest(BaseModel):
    """Request body for writing a file."""
    path: str = Field(..., description="File path to write")
    content: str = Field(..., description="Content to write")
    append: bool = Field(False, description="Append to file instead of overwrite")


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
