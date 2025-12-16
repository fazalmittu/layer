"""
Configuration module for Layer.
Handles environment loading, API key validation, and app whitelist.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Key - required for authentication
API_KEY = os.getenv("MAC_API_KEY", "").strip()

if not API_KEY:
    print("ERROR: MAC_API_KEY not set. Please define it in your .env file.")
    sys.exit(1)

# Whitelisted applications
# Maps friendly key -> actual macOS application name
ALLOWED_APPS: dict[str, str] = {
    "spotify": "Spotify",
    "safari": "Safari",
    "chrome": "Google Chrome",
    "firefox": "Firefox",
    "vscode": "Visual Studio Code",
    "cursor": "Cursor",
    "terminal": "Terminal",
    "iterm": "iTerm",
    "notes": "Notes",
    "calendar": "Calendar",
    "mail": "Mail",
    "messages": "Messages",
    "slack": "Slack",
    "discord": "Discord",
    "finder": "Finder",
    "preview": "Preview",
    "textedit": "TextEdit",
}

# Server configuration (hardcoded for v0.1)
HOST = "0.0.0.0"
PORT = 8000

# AppleScript execution timeout in seconds
APPLESCRIPT_TIMEOUT = 10

# Safe directories for filesystem operations
# Only paths within these directories can be read/written
SAFE_DIRECTORIES = [
    "~/Desktop",
    "~/Documents",
    "~/Downloads",
]

