"""
Dynamic wallpaper generator.
Creates a minimal, clean dashboard wallpaper with live data.
"""

import subprocess
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
import os

from config import WEATHER_API_KEY
WALLPAPER_PATH = Path.home() / "Pictures" / "layer_wallpaper.png"

# Colors (minimal dark theme)
COLORS = {
    "bg_start": (18, 18, 24),      # Dark blue-gray
    "bg_end": (28, 28, 38),        # Slightly lighter
    "text_primary": (255, 255, 255),
    "text_secondary": (160, 160, 175),
    "text_muted": (100, 100, 115),
    "accent": (130, 120, 255),     # Soft purple
}

# Try to use nice fonts, fallback to defaults
def get_font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    """Get a font with fallbacks."""
    font_paths = {
        "bold": [
            "/System/Library/Fonts/SFNSDisplay.ttf",
            "/System/Library/Fonts/Supplemental/SF-Pro-Display-Bold.otf",
            "/Library/Fonts/SF-Pro-Display-Bold.otf",
            "/System/Library/Fonts/Helvetica.ttc",
        ],
        "regular": [
            "/System/Library/Fonts/SFNS.ttf",
            "/System/Library/Fonts/Supplemental/SF-Pro-Display-Regular.otf",
            "/Library/Fonts/SF-Pro-Display-Regular.otf",
            "/System/Library/Fonts/Helvetica.ttc",
        ],
        "light": [
            "/System/Library/Fonts/Supplemental/SF-Pro-Display-Light.otf",
            "/Library/Fonts/SF-Pro-Display-Light.otf",
            "/System/Library/Fonts/HelveticaNeue.ttc",
        ],
    }
    
    for path in font_paths.get(weight, font_paths["regular"]):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    
    # Ultimate fallback
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except:
        return ImageFont.load_default()


# =============================================================================
# Data Fetchers
# =============================================================================

def get_weather(city: str = "San Francisco") -> Optional[dict]:
    """Fetch current weather from OpenWeatherMap."""
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": WEATHER_API_KEY,
            "units": "imperial"
        }
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "temp": round(data["main"]["temp"]),
                "feels_like": round(data["main"]["feels_like"]),
                "description": data["weather"][0]["description"].title(),
                "icon": data["weather"][0]["icon"],
                "city": data["name"],
            }
    except Exception as e:
        print(f"Weather fetch failed: {e}")
    return None


def get_calendar_events() -> list[dict]:
    """Get today's calendar events via AppleScript."""
    script = '''
    use AppleScript version "2.4"
    use scripting additions
    use framework "Foundation"
    
    set today to current date
    set todayStart to today - (time of today)
    set todayEnd to todayStart + (24 * 60 * 60)
    
    set eventList to {}
    
    tell application "Calendar"
        repeat with cal in calendars
            set calEvents to (every event of cal whose start date ≥ todayStart and start date < todayEnd)
            repeat with evt in calEvents
                set evtStart to start date of evt
                set evtSummary to summary of evt
                set timeStr to text 1 thru 5 of (time string of evtStart)
                set end of eventList to timeStr & " - " & evtSummary
            end repeat
        end repeat
    end tell
    
    set AppleScript's text item delimiters to "|||"
    return eventList as text
    '''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            events = result.stdout.strip().split("|||")
            return [{"text": e.strip()} for e in events if e.strip()]
    except Exception as e:
        print(f"Calendar fetch failed: {e}")
    return []


def get_reminders() -> list[dict]:
    """Get incomplete reminders via AppleScript."""
    script = '''
    tell application "Reminders"
        set reminderList to {}
        repeat with remindersList in lists
            set incompleteReminders to (reminders of remindersList whose completed is false)
            repeat with r in incompleteReminders
                if (count of reminderList) < 5 then
                    set end of reminderList to name of r
                end if
            end repeat
        end repeat
        
        set AppleScript's text item delimiters to "|||"
        return reminderList as text
    end tell
    '''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            reminders = result.stdout.strip().split("|||")
            return [{"text": r.strip()} for r in reminders if r.strip()]
    except Exception as e:
        print(f"Reminders fetch failed: {e}")
    return []


# =============================================================================
# Image Generation
# =============================================================================

def create_gradient(width: int, height: int) -> Image.Image:
    """Create a subtle gradient background."""
    img = Image.new("RGB", (width, height))
    
    for y in range(height):
        ratio = y / height
        r = int(COLORS["bg_start"][0] + (COLORS["bg_end"][0] - COLORS["bg_start"][0]) * ratio)
        g = int(COLORS["bg_start"][1] + (COLORS["bg_end"][1] - COLORS["bg_start"][1]) * ratio)
        b = int(COLORS["bg_start"][2] + (COLORS["bg_end"][2] - COLORS["bg_start"][2]) * ratio)
        
        for x in range(width):
            img.putpixel((x, y), (r, g, b))
    
    return img


def generate_wallpaper(
    city: str = "San Francisco",
    show_weather: bool = True,
    show_calendar: bool = True,
    show_reminders: bool = True,
    custom_message: Optional[str] = None,
    width: int = 2560,
    height: int = 1600,
) -> str:
    """Generate the dynamic wallpaper."""
    
    # Create gradient background
    img = create_gradient(width, height)
    draw = ImageDraw.Draw(img)
    
    # Fonts
    font_time = get_font(220, "light")
    font_date = get_font(42, "regular")
    font_section = get_font(18, "bold")
    font_item = get_font(24, "regular")
    font_weather_temp = get_font(72, "light")
    font_weather_desc = get_font(22, "regular")
    font_message = get_font(28, "light")
    
    # Margins
    margin_left = 140
    margin_top = height // 4
    
    # Current time and date
    now = datetime.now()
    time_str = now.strftime("%-I:%M")
    am_pm = now.strftime("%p").lower()
    date_str = now.strftime("%A, %B %-d")
    
    # Draw time (large, left side)
    draw.text(
        (margin_left, margin_top),
        time_str,
        font=font_time,
        fill=COLORS["text_primary"]
    )
    
    # Get time width to position AM/PM
    time_bbox = draw.textbbox((margin_left, margin_top), time_str, font=font_time)
    time_width = time_bbox[2] - time_bbox[0]
    
    # Draw AM/PM smaller, next to time
    font_ampm = get_font(48, "light")
    draw.text(
        (margin_left + time_width + 15, margin_top + 160),
        am_pm,
        font=font_ampm,
        fill=COLORS["text_muted"]
    )
    
    # Draw date below time
    draw.text(
        (margin_left, margin_top + 230),
        date_str,
        font=font_date,
        fill=COLORS["text_secondary"]
    )
    
    # Right side content (weather, events, reminders)
    right_x = width - 500
    content_y = margin_top
    
    # Weather (top right)
    if show_weather:
        weather = get_weather(city)
        if weather:
            # Temperature
            draw.text(
                (right_x, content_y),
                f"{weather['temp']}°",
                font=font_weather_temp,
                fill=COLORS["text_primary"]
            )
            # Description and city
            draw.text(
                (right_x, content_y + 85),
                weather["description"],
                font=font_weather_desc,
                fill=COLORS["text_secondary"]
            )
            draw.text(
                (right_x, content_y + 115),
                weather["city"],
                font=font_section,
                fill=COLORS["text_muted"]
            )
            content_y += 180
    
    # Calendar events
    if show_calendar:
        events = get_calendar_events()
        if events:
            content_y += 30
            draw.text(
                (right_x, content_y),
                "TODAY",
                font=font_section,
                fill=COLORS["accent"]
            )
            content_y += 35
            
            for event in events[:4]:  # Max 4 events
                text = event["text"]
                if len(text) > 35:
                    text = text[:32] + "..."
                draw.text(
                    (right_x, content_y),
                    text,
                    font=font_item,
                    fill=COLORS["text_secondary"]
                )
                content_y += 38
    
    # Reminders
    if show_reminders:
        reminders = get_reminders()
        if reminders:
            content_y += 30
            draw.text(
                (right_x, content_y),
                "TASKS",
                font=font_section,
                fill=COLORS["accent"]
            )
            content_y += 35
            
            for reminder in reminders[:4]:  # Max 4 reminders
                text = reminder["text"]
                if len(text) > 35:
                    text = text[:32] + "..."
                # Draw checkbox
                draw.text(
                    (right_x, content_y),
                    "○  " + text,
                    font=font_item,
                    fill=COLORS["text_secondary"]
                )
                content_y += 38
    
    # Custom message (bottom left)
    if custom_message:
        draw.text(
            (margin_left, height - 150),
            custom_message,
            font=font_message,
            fill=COLORS["text_muted"]
        )
    
    # Subtle accent line
    line_y = margin_top + 290
    draw.line(
        [(margin_left, line_y), (margin_left + 60, line_y)],
        fill=COLORS["accent"],
        width=3
    )
    
    # Save
    WALLPAPER_PATH.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(WALLPAPER_PATH), "PNG", quality=95)
    
    return str(WALLPAPER_PATH)


def set_wallpaper(image_path: str) -> bool:
    """Set the desktop wallpaper via AppleScript."""
    script = f'''
    tell application "System Events"
        tell every desktop
            set picture to "{image_path}"
        end tell
    end tell
    '''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Set wallpaper failed: {e}")
        return False


def get_screen_resolution() -> tuple[int, int]:
    """Get the main display resolution using system_profiler."""
    try:
        result = subprocess.run(
            ["system_profiler", "SPDisplaysDataType", "-json"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            displays = data.get("SPDisplaysDataType", [])
            for gpu in displays:
                for display in gpu.get("spdisplays_ndrvs", []):
                    resolution = display.get("_spdisplays_resolution", "")
                    # Format is like "2560 x 1600" or "3024 x 1964 @ 120.00Hz"
                    if resolution:
                        parts = resolution.split(" x ")
                        if len(parts) >= 2:
                            width = int(parts[0].strip())
                            height = int(parts[1].split()[0].strip())
                            return width, height
    except Exception as e:
        print(f"Resolution detection failed: {e}")
    
    return 2560, 1600  # Sensible default for Retina MacBooks


def generate_and_set_wallpaper(
    city: str = "San Francisco",
    show_weather: bool = True,
    show_calendar: bool = True,
    show_reminders: bool = True,
    custom_message: Optional[str] = None,
) -> dict:
    """Generate a dynamic wallpaper and set it as desktop background."""
    try:
        # Get screen resolution
        width, height = get_screen_resolution()
        
        # Generate wallpaper
        path = generate_wallpaper(
            city=city,
            show_weather=show_weather,
            show_calendar=show_calendar,
            show_reminders=show_reminders,
            custom_message=custom_message,
            width=width,
            height=height,
        )
        
        # Set as wallpaper
        success = set_wallpaper(path)
        
        return {
            "success": success,
            "path": path,
            "resolution": f"{width}x{height}",
            "message": "Wallpaper generated and set" if success else "Generated but failed to set"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    # Test
    result = generate_and_set_wallpaper(
        city="San Francisco",
        custom_message="Focus on what matters."
    )
    print(result)

