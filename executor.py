"""
Command execution module.
Handles AppleScript execution, shell commands, input sanitization, and timeouts.
"""

import subprocess
import base64
import os
import tempfile
from pathlib import Path
from config import APPLESCRIPT_TIMEOUT, SAFE_DIRECTORIES


class ExecutionError(Exception):
    """Raised when command execution fails."""
    pass


# =============================================================================
# AppleScript Utilities
# =============================================================================

def sanitize_applescript_string(text: str, handle_newlines: bool = False) -> str:
    """
    Escape special characters for safe AppleScript string inclusion.
    """
    text = text.replace("\\", "\\\\")
    text = text.replace('"', '\\"')
    text = text.replace("\t", "    ")
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    
    if handle_newlines:
        text = text.replace("\n", "{{NEWLINE}}")
    
    return text


def build_applescript_string_with_newlines(text: str) -> str:
    """
    Build an AppleScript string expression that handles newlines properly.
    """
    sanitized = sanitize_applescript_string(text, handle_newlines=True)
    parts = sanitized.split("{{NEWLINE}}")
    
    if len(parts) == 1:
        return f'"{parts[0]}"'
    
    quoted_parts = [f'"{part}"' for part in parts]
    return " & linefeed & ".join(quoted_parts)


def run_applescript(script: str, timeout: int = APPLESCRIPT_TIMEOUT) -> str:
    """Execute an AppleScript and return the output."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or "Unknown AppleScript error"
            raise ExecutionError(error_msg)
            
        return result.stdout.strip()
        
    except subprocess.TimeoutExpired:
        raise ExecutionError(f"AppleScript execution timed out after {timeout} seconds")
    except FileNotFoundError:
        raise ExecutionError("osascript not found - are you running on macOS?")


def run_shell(args: list[str], timeout: int = 30) -> str:
    """Execute a shell command and return the output."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or f"Command failed with code {result.returncode}"
            raise ExecutionError(error_msg)
            
        return result.stdout.strip()
        
    except subprocess.TimeoutExpired:
        raise ExecutionError(f"Command timed out after {timeout} seconds")
    except FileNotFoundError:
        raise ExecutionError(f"Command not found: {args[0]}")


# =============================================================================
# Application Control
# =============================================================================

def open_application(app_name: str) -> str:
    """Open a macOS application."""
    try:
        result = subprocess.run(
            ["open", "-a", app_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            if "Unable to find application" in error_msg or result.returncode == 1:
                raise ExecutionError(f"Application '{app_name}' is not installed on this machine")
            raise ExecutionError(error_msg or f"Failed to open {app_name}")
            
        return f"Successfully opened {app_name}"
        
    except FileNotFoundError:
        raise ExecutionError("'open' command not found - are you running on macOS?")


# =============================================================================
# Notes
# =============================================================================

def get_notes_accounts() -> list[str]:
    """Get list of available Notes accounts."""
    script = 'tell application "Notes" to get name of every account'
    output = run_applescript(script)
    
    if not output:
        return []
    
    accounts = [a.strip() for a in output.split(",")]
    return accounts


def create_note(title: str, content: str) -> str:
    """Create a new Apple Note."""
    safe_title = sanitize_applescript_string(title.replace("\n", " ").replace("\r", " "))
    content_expr = build_applescript_string_with_newlines(content)
    
    try:
        accounts = get_notes_accounts()
    except ExecutionError as e:
        raise ExecutionError(f"Failed to access Notes app: {e}")
    
    if not accounts:
        raise ExecutionError("No Notes accounts found on this machine")
    
    target_account = None
    for preferred in ["iCloud", "On My Mac"]:
        if preferred in accounts:
            target_account = preferred
            break
    
    if target_account is None:
        target_account = accounts[0]
    
    script = f'''
tell application "Notes"
    set noteBody to {content_expr}
    tell account "{target_account}"
        tell folder "Notes"
            make new note at end with properties {{name:"{safe_title}", body:noteBody}}
        end tell
    end tell
end tell
'''
    
    try:
        run_applescript(script)
        return f"Note '{title}' created in {target_account} account"
    except ExecutionError as e:
        error_str = str(e)
        if "folder" in error_str.lower() and "Notes" in error_str:
            raise ExecutionError(f"Notes folder not found in account '{target_account}'")
        raise


# =============================================================================
# Clipboard
# =============================================================================

def get_clipboard() -> str:
    """Get current clipboard text content."""
    script = 'get the clipboard as text'
    try:
        return run_applescript(script)
    except ExecutionError:
        return ""


def set_clipboard(text: str) -> str:
    """Set clipboard text content."""
    safe_text = sanitize_applescript_string(text)
    script = f'set the clipboard to "{safe_text}"'
    run_applescript(script)
    return "Clipboard updated"


# =============================================================================
# Screenshot
# =============================================================================

def take_screenshot() -> str:
    """Take a screenshot and return as base64 string."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        subprocess.run(
            ["screencapture", "-x", tmp_path],
            capture_output=True,
            timeout=10
        )
        
        with open(tmp_path, "rb") as f:
            data = f.read()
        
        return base64.b64encode(data).decode("utf-8")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# =============================================================================
# URL
# =============================================================================

def open_url(url: str) -> str:
    """Open a URL in the default browser."""
    result = subprocess.run(
        ["open", url],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise ExecutionError(f"Failed to open URL: {result.stderr.strip()}")
    
    return f"Opened {url}"


# =============================================================================
# Shortcuts
# =============================================================================

def run_shortcut(name: str, input_text: str | None = None) -> str:
    """Run a Shortcuts.app shortcut."""
    args = ["shortcuts", "run", name]
    
    if input_text:
        args.extend(["-i", input_text])
    
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            error = result.stderr.strip()
            if "couldn't find" in error.lower() or "no such shortcut" in error.lower():
                raise ExecutionError(f"Shortcut '{name}' not found")
            raise ExecutionError(error or f"Shortcut '{name}' failed")
        
        return result.stdout.strip() or f"Shortcut '{name}' executed"
    except subprocess.TimeoutExpired:
        raise ExecutionError(f"Shortcut '{name}' timed out after 60 seconds")


# =============================================================================
# Notifications
# =============================================================================

def send_notification(title: str, message: str, subtitle: str | None = None, sound: bool = True) -> str:
    """Send a macOS notification."""
    safe_title = sanitize_applescript_string(title)
    safe_message = sanitize_applescript_string(message)
    
    script = f'display notification "{safe_message}" with title "{safe_title}"'
    
    if subtitle:
        safe_subtitle = sanitize_applescript_string(subtitle)
        script = f'display notification "{safe_message}" with title "{safe_title}" subtitle "{safe_subtitle}"'
    
    if sound:
        script += ' sound name "default"'
    
    run_applescript(script)
    return "Notification sent"


# =============================================================================
# Text-to-Speech
# =============================================================================

def speak_text(text: str, voice: str | None = None, rate: int | None = None) -> str:
    """Speak text using macOS text-to-speech."""
    args = ["say"]
    
    if voice:
        args.extend(["-v", voice])
    
    if rate:
        args.extend(["-r", str(rate)])
    
    args.append(text)
    
    try:
        subprocess.run(args, capture_output=True, timeout=120)
        return "Speech completed"
    except subprocess.TimeoutExpired:
        raise ExecutionError("Speech timed out")


# =============================================================================
# System Controls
# =============================================================================

def get_volume() -> dict:
    """Get current volume settings."""
    script = 'get volume settings'
    output = run_applescript(script)
    
    # Parse: "output volume:50, input volume:75, alert volume:100, output muted:false"
    result = {"level": 50, "muted": False}
    
    for part in output.split(","):
        part = part.strip()
        if part.startswith("output volume:"):
            result["level"] = int(part.split(":")[1])
        elif part.startswith("output muted:"):
            result["muted"] = part.split(":")[1].strip().lower() == "true"
    
    return result


def set_volume(level: int | None = None, mute: bool | None = None) -> str:
    """Set system volume."""
    if mute is not None:
        action = "with" if mute else "without"
        script = f'set volume {action} output muted'
        run_applescript(script)
        return f"Volume {'muted' if mute else 'unmuted'}"
    
    if level is not None:
        # AppleScript volume is 0-7, we convert from 0-100
        as_level = int(level / 100 * 7)
        script = f'set volume output volume {level}'
        run_applescript(script)
        return f"Volume set to {level}%"
    
    raise ExecutionError("Must specify level or mute")


def get_brightness() -> float:
    """Get current display brightness (0.0-1.0)."""
    script = 'tell application "System Events" to get value of slider 1 of group 1 of window "Control Center" of application process "ControlCenter"'
    
    # Alternative method using brightness command if available
    try:
        result = subprocess.run(
            ["brightness", "-l"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Parse output for brightness value
            for line in result.stdout.split("\n"):
                if "brightness" in line.lower():
                    parts = line.split()
                    for part in parts:
                        try:
                            val = float(part)
                            if 0 <= val <= 1:
                                return val
                        except ValueError:
                            continue
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Fallback: use AppleScript (less reliable)
    try:
        script = 'tell application "System Preferences" to quit'
        run_applescript(script, timeout=2)
    except ExecutionError:
        pass
    
    return 0.5  # Default if we can't determine


def set_brightness(level: float) -> str:
    """Set display brightness (0.0-1.0)."""
    # Try using brightness command first
    try:
        subprocess.run(
            ["brightness", str(level)],
            capture_output=True,
            timeout=5
        )
        return f"Brightness set to {int(level * 100)}%"
    except FileNotFoundError:
        pass
    
    # Fallback to AppleScript with System Events
    # Note: This may not work on all systems
    script = f'''
tell application "System Events"
    tell process "ControlCenter"
        -- This is a simplified approach
        key code 145  -- brightness down
    end tell
end tell
'''
    raise ExecutionError("Brightness control requires 'brightness' CLI tool. Install with: brew install brightness")


def get_dark_mode() -> bool:
    """Get current dark mode status."""
    script = 'tell application "System Events" to tell appearance preferences to get dark mode'
    result = run_applescript(script)
    return result.lower() == "true"


def set_dark_mode(enabled: bool) -> str:
    """Set dark mode on/off."""
    script = f'tell application "System Events" to tell appearance preferences to set dark mode to {str(enabled).lower()}'
    run_applescript(script)
    return f"Dark mode {'enabled' if enabled else 'disabled'}"


def toggle_dark_mode() -> str:
    """Toggle dark mode."""
    current = get_dark_mode()
    return set_dark_mode(not current)


def get_dnd_status() -> bool:
    """Get Do Not Disturb status."""
    # This is tricky on modern macOS - Focus mode replaced DND
    script = '''
tell application "System Events"
    tell process "ControlCenter"
        -- Check if Focus is enabled
        try
            return exists (first menu bar item of menu bar 1 whose description contains "Focus")
        end try
    end tell
end tell
'''
    try:
        result = run_applescript(script)
        return result.lower() == "true"
    except ExecutionError:
        return False


def toggle_dnd() -> str:
    """Toggle Do Not Disturb / Focus mode."""
    # Use keyboard shortcut approach
    script = '''
tell application "System Events"
    -- Open Control Center
    key code 49 using {control down}
    delay 0.5
    -- This is approximate - Focus behavior varies
end tell
'''
    # Alternative: use shortcuts
    try:
        run_shortcut("Toggle Do Not Disturb")
        return "Do Not Disturb toggled"
    except ExecutionError:
        pass
    
    raise ExecutionError("DND toggle requires a Shortcut named 'Toggle Do Not Disturb'. Create one in Shortcuts.app that toggles Focus mode.")


def sleep_display() -> str:
    """Put display to sleep."""
    subprocess.run(["pmset", "displaysleepnow"], capture_output=True)
    return "Display sleeping"


def lock_screen() -> str:
    """Lock the screen."""
    script = 'tell application "System Events" to keystroke "q" using {command down, control down}'
    run_applescript(script)
    return "Screen locked"


def sleep_system() -> str:
    """Put the system to sleep."""
    subprocess.run(["pmset", "sleepnow"], capture_output=True)
    return "System sleeping"


# =============================================================================
# Filesystem
# =============================================================================

def is_path_safe(path: str) -> bool:
    """Check if a path is within safe directories."""
    try:
        resolved = Path(path).resolve()
        for safe_dir in SAFE_DIRECTORIES:
            safe_resolved = Path(safe_dir).expanduser().resolve()
            if str(resolved).startswith(str(safe_resolved)):
                return True
        return False
    except Exception:
        return False


def list_files(path: str, show_hidden: bool = False) -> list[dict]:
    """List files in a directory."""
    if not is_path_safe(path):
        raise ExecutionError(f"Access denied: {path} is not in safe directories")
    
    target = Path(path).expanduser().resolve()
    
    if not target.exists():
        raise ExecutionError(f"Directory not found: {path}")
    
    if not target.is_dir():
        raise ExecutionError(f"Not a directory: {path}")
    
    files = []
    for item in target.iterdir():
        if not show_hidden and item.name.startswith("."):
            continue
        
        files.append({
            "name": item.name,
            "path": str(item),
            "is_dir": item.is_dir(),
            "size": item.stat().st_size if item.is_file() else None
        })
    
    return sorted(files, key=lambda x: (not x["is_dir"], x["name"].lower()))


def read_file(path: str, max_size: int = 1048576) -> str:
    """Read a text file."""
    if not is_path_safe(path):
        raise ExecutionError(f"Access denied: {path} is not in safe directories")
    
    target = Path(path).expanduser().resolve()
    
    if not target.exists():
        raise ExecutionError(f"File not found: {path}")
    
    if not target.is_file():
        raise ExecutionError(f"Not a file: {path}")
    
    if target.stat().st_size > max_size:
        raise ExecutionError(f"File too large (max {max_size} bytes)")
    
    try:
        return target.read_text()
    except UnicodeDecodeError:
        raise ExecutionError("File is not a text file")


def write_file(path: str, content: str, append: bool = False) -> str:
    """Write to a file."""
    if not is_path_safe(path):
        raise ExecutionError(f"Access denied: {path} is not in safe directories")
    
    target = Path(path).expanduser().resolve()
    
    # Create parent directories if needed
    target.parent.mkdir(parents=True, exist_ok=True)
    
    mode = "a" if append else "w"
    target.write_text(content) if not append else target.open("a").write(content)
    
    action = "appended to" if append else "written to"
    return f"Content {action} {path}"


def list_downloads() -> list[dict]:
    """List files in Downloads folder."""
    downloads = Path.home() / "Downloads"
    return list_files(str(downloads), show_hidden=False)
