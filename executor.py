"""
Command execution module.
Handles AppleScript execution, shell commands, input sanitization, and timeouts.
"""

import subprocess
from config import APPLESCRIPT_TIMEOUT


class ExecutionError(Exception):
    """Raised when command execution fails."""
    pass


def sanitize_applescript_string(text: str, handle_newlines: bool = False) -> str:
    """
    Escape special characters for safe AppleScript string inclusion.
    
    Handles:
    - Backslashes -> \\
    - Double quotes -> \\"
    - Tabs -> spaces (AppleScript doesn't handle \\t well in strings)
    
    If handle_newlines is True, newlines are replaced with a placeholder
    that will be processed later with AppleScript linefeed concatenation.
    """
    # Escape backslashes first (before adding more)
    text = text.replace("\\", "\\\\")
    # Escape double quotes
    text = text.replace('"', '\\"')
    # Replace tabs with spaces
    text = text.replace("\t", "    ")
    # Handle carriage returns
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    
    if handle_newlines:
        # Use a placeholder that we'll replace with AppleScript linefeed concatenation
        text = text.replace("\n", "{{NEWLINE}}")
    
    return text


def build_applescript_string_with_newlines(text: str) -> str:
    """
    Build an AppleScript string expression that handles newlines properly.
    
    Converts text with newlines into AppleScript concatenation:
    "Line 1" & linefeed & "Line 2"
    """
    # First sanitize, marking newlines with placeholder
    sanitized = sanitize_applescript_string(text, handle_newlines=True)
    
    # Split by newline placeholder and join with AppleScript linefeed
    parts = sanitized.split("{{NEWLINE}}")
    
    if len(parts) == 1:
        # No newlines, just return quoted string
        return f'"{parts[0]}"'
    
    # Build concatenation: "part1" & linefeed & "part2" & linefeed & "part3"
    quoted_parts = [f'"{part}"' for part in parts]
    return " & linefeed & ".join(quoted_parts)


def run_applescript(script: str, timeout: int = APPLESCRIPT_TIMEOUT) -> str:
    """
    Execute an AppleScript and return the output.
    
    Args:
        script: The AppleScript code to execute
        timeout: Maximum execution time in seconds
        
    Returns:
        The script output as a string
        
    Raises:
        ExecutionError: If execution fails or times out
    """
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


def open_application(app_name: str) -> str:
    """
    Open a macOS application using the 'open' command.
    
    Args:
        app_name: The exact macOS application name (e.g., "Spotify")
        
    Returns:
        Success message
        
    Raises:
        ExecutionError: If the app cannot be opened
    """
    try:
        result = subprocess.run(
            ["open", "-a", app_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            # Check for common "not found" error
            if "Unable to find application" in error_msg or result.returncode == 1:
                raise ExecutionError(f"Application '{app_name}' is not installed on this machine")
            raise ExecutionError(error_msg or f"Failed to open {app_name}")
            
        return f"Successfully opened {app_name}"
        
    except FileNotFoundError:
        raise ExecutionError("'open' command not found - are you running on macOS?")


def get_notes_accounts() -> list[str]:
    """
    Get list of available Notes accounts.
    
    Returns:
        List of account names
    """
    script = 'tell application "Notes" to get name of every account'
    output = run_applescript(script)
    
    if not output:
        return []
    
    # Output is comma-separated: "iCloud, On My Mac"
    accounts = [a.strip() for a in output.split(",")]
    return accounts


def create_note(title: str, content: str) -> str:
    """
    Create a new Apple Note with the given title and content.
    Uses iCloud account if available, falls back to "On My Mac".
    
    Args:
        title: Note title
        content: Note body content
        
    Returns:
        Success message
        
    Raises:
        ExecutionError: If note creation fails
    """
    # Sanitize title (no newlines in titles - replace with spaces)
    safe_title = sanitize_applescript_string(title.replace("\n", " ").replace("\r", " "))
    
    # Build content string with proper newline handling
    content_expr = build_applescript_string_with_newlines(content)
    
    # Get available accounts
    try:
        accounts = get_notes_accounts()
    except ExecutionError as e:
        raise ExecutionError(f"Failed to access Notes app: {e}")
    
    if not accounts:
        raise ExecutionError("No Notes accounts found on this machine")
    
    # Prefer iCloud, fallback to "On My Mac", otherwise use first available
    target_account = None
    for preferred in ["iCloud", "On My Mac"]:
        if preferred in accounts:
            target_account = preferred
            break
    
    if target_account is None:
        target_account = accounts[0]
    
    # Build AppleScript for note creation (without activate - silent creation)
    # Use a variable for body content to handle newlines via concatenation
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
        # Check for folder not found error
        if "folder" in error_str.lower() and "Notes" in error_str:
            raise ExecutionError(f"Notes folder not found in account '{target_account}'")
        raise

