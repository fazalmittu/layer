"""
Dynamic wallpaper generator.
Creates a minimal, aesthetic dashboard wallpaper with year progress and live data.
"""

import subprocess
import requests
import json
import math
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
import os

from config import WEATHER_API_KEY

WALLPAPER_PATH = Path.home() / "Pictures" / "layer_wallpaper.png"

# Colors (minimal dark theme)
COLORS = {
    "bg": (13, 13, 17),
    "dot_empty": (35, 35, 45),
    "dot_filled": (120, 110, 255),
    "dot_today": (255, 120, 100),
    "text_primary": (255, 255, 255),
    "text_secondary": (140, 140, 155),
    "text_muted": (80, 80, 95),
    "accent": (120, 110, 255),
}


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
    
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except:
        return ImageFont.load_default()


# =============================================================================
# Data Fetchers
# =============================================================================

def get_year_progress() -> dict:
    """Calculate year progress."""
    now = datetime.now()
    year_start = date(now.year, 1, 1)
    year_end = date(now.year, 12, 31)
    today = now.date()
    
    total_days = (year_end - year_start).days + 1
    days_passed = (today - year_start).days + 1
    days_remaining = total_days - days_passed
    percent = (days_passed / total_days) * 100
    
    return {
        "year": now.year,
        "total_days": total_days,
        "days_passed": days_passed,
        "days_remaining": days_remaining,
        "percent": percent,
        "day_of_year": days_passed,
    }


def get_weather(city: str = "San Francisco") -> Optional[dict]:
    """Fetch current weather from OpenWeatherMap."""
    if not WEATHER_API_KEY:
        return None
    
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": city, "appid": WEATHER_API_KEY, "units": "imperial"}
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "temp": round(data["main"]["temp"]),
                "description": data["weather"][0]["description"].title(),
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
                set end of eventList to timeStr & " " & evtSummary
            end repeat
        end repeat
    end tell
    
    set AppleScript's text item delimiters to "|||"
    return eventList as text
    '''
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            events = result.stdout.strip().split("|||")
            return [{"text": e.strip()} for e in events if e.strip()][:4]
    except:
        pass
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
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            reminders = result.stdout.strip().split("|||")
            return [{"text": r.strip()} for r in reminders if r.strip()][:4]
    except:
        pass
    return []


# =============================================================================
# Image Generation
# =============================================================================

def draw_year_grid(draw: ImageDraw, x: int, y: int, progress: dict, dot_size: int = 8, gap: int = 4):
    """
    Draw a year progress grid (like GitHub contributions).
    52 columns (weeks) x 7 rows (days) = 364 dots + 1 or 2 extra
    """
    days_passed = progress["days_passed"]
    total_days = progress["total_days"]
    
    cols = 53  # 52 weeks + partial
    rows = 7   # days of week
    
    day = 0
    for col in range(cols):
        for row in range(rows):
            day += 1
            if day > total_days:
                break
            
            dot_x = x + col * (dot_size + gap)
            dot_y = y + row * (dot_size + gap)
            
            if day < days_passed:
                color = COLORS["dot_filled"]
            elif day == days_passed:
                color = COLORS["dot_today"]
            else:
                color = COLORS["dot_empty"]
            
            # Draw rounded rectangle (pill shape)
            radius = max(2, dot_size // 4)
            draw.rounded_rectangle(
                [dot_x, dot_y, dot_x + dot_size, dot_y + dot_size],
                radius=radius,
                fill=color
            )
    
    # Return dimensions for layout
    grid_width = cols * (dot_size + gap) - gap
    grid_height = rows * (dot_size + gap) - gap
    return grid_width, grid_height


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
    
    # Scale factor based on resolution (base is 2560 width)
    scale = width / 2560
    s = lambda x: int(x * scale)  # Scale helper
    
    # Solid dark background
    img = Image.new("RGB", (width, height), COLORS["bg"])
    draw = ImageDraw.Draw(img)
    
    # Fonts (scaled)
    font_huge = get_font(s(180), "bold")
    font_large = get_font(s(72), "light")
    font_medium = get_font(s(42), "regular")
    font_small = get_font(s(28), "regular")
    font_tiny = get_font(s(22), "regular")
    
    # Get data
    progress = get_year_progress()
    now = datetime.now()
    
    # === LEFT SIDE: Year Progress ===
    margin_left = s(200)
    margin_top = height // 5
    
    # Big percentage
    percent_str = f"{progress['percent']:.1f}%"
    draw.text(
        (margin_left, margin_top),
        percent_str,
        font=font_huge,
        fill=COLORS["text_primary"]
    )
    
    # "of [year] complete"
    draw.text(
        (margin_left, margin_top + s(190)),
        f"of {progress['year']} complete",
        font=font_large,
        fill=COLORS["text_secondary"]
    )
    
    # Stats line
    stats_y = margin_top + s(290)
    stats_text = f"{progress['days_passed']} days down  ·  {progress['days_remaining']} to go"
    draw.text(
        (margin_left, stats_y),
        stats_text,
        font=font_medium,
        fill=COLORS["text_muted"]
    )
    
    # Year grid (scaled)
    grid_y = stats_y + s(80)
    dot_size = s(14)
    dot_gap = s(4)
    draw_year_grid(draw, margin_left, grid_y, progress, dot_size=dot_size, gap=dot_gap)
    
    # Date below grid
    date_y = grid_y + 7 * (dot_size + dot_gap) + s(40)
    date_str = now.strftime("%A, %B %-d")
    draw.text(
        (margin_left, date_y),
        date_str,
        font=font_medium,
        fill=COLORS["text_secondary"]
    )
    
    # === RIGHT SIDE: Weather, Calendar, Reminders ===
    right_x = width - s(600)
    content_y = margin_top
    
    # Weather
    if show_weather:
        weather = get_weather(city)
        if weather:
            draw.text(
                (right_x, content_y),
                f"{weather['temp']}°",
                font=get_font(s(96), "light"),
                fill=COLORS["text_primary"]
            )
            draw.text(
                (right_x, content_y + s(110)),
                weather["description"],
                font=font_small,
                fill=COLORS["text_secondary"]
            )
            draw.text(
                (right_x, content_y + s(145)),
                weather["city"],
                font=font_tiny,
                fill=COLORS["text_muted"]
            )
            content_y += s(220)
    
    # Calendar
    if show_calendar:
        events = get_calendar_events()
        if events:
            content_y += s(30)
            draw.text(
                (right_x, content_y),
                "TODAY",
                font=font_tiny,
                fill=COLORS["accent"]
            )
            content_y += s(40)
            for event in events:
                text = event["text"][:40] + "..." if len(event["text"]) > 40 else event["text"]
                draw.text((right_x, content_y), text, font=font_small, fill=COLORS["text_secondary"])
                content_y += s(45)
    
    # Reminders
    if show_reminders:
        reminders = get_reminders()
        if reminders:
            content_y += s(40)
            draw.text(
                (right_x, content_y),
                "TASKS",
                font=font_tiny,
                fill=COLORS["accent"]
            )
            content_y += s(40)
            for reminder in reminders:
                text = reminder["text"][:40] + "..." if len(reminder["text"]) > 40 else reminder["text"]
                draw.text((right_x, content_y), f"○ {text}", font=font_small, fill=COLORS["text_secondary"])
                content_y += s(45)
    
    # Custom message (bottom left)
    if custom_message:
        draw.text(
            (margin_left, height - s(140)),
            custom_message,
            font=font_medium,
            fill=COLORS["text_muted"]
        )
    
    # Save with high DPI for Retina sharpness
    WALLPAPER_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Set DPI metadata for Retina displays (144 = 2x standard 72 DPI)
    img.save(str(WALLPAPER_PATH), "PNG", dpi=(144, 144))
    
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
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except:
        return False


def get_screen_resolution() -> tuple[int, int]:
    """Get the native display resolution (not scaled)."""
    try:
        result = subprocess.run(
            ["system_profiler", "SPDisplaysDataType", "-json"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for gpu in data.get("SPDisplaysDataType", []):
                for display in gpu.get("spdisplays_ndrvs", []):
                    # Try to get native/Retina resolution first
                    native = display.get("_spdisplays_native", "")
                    if native:
                        # Format: "3024 x 1964"
                        parts = native.split(" x ")
                        if len(parts) >= 2:
                            return int(parts[0].strip()), int(parts[1].split()[0].strip())
                    
                    # Fall back to pixels (native resolution)
                    pixels = display.get("_spdisplays_pixels", "")
                    if pixels:
                        parts = pixels.split(" x ")
                        if len(parts) >= 2:
                            return int(parts[0].strip()), int(parts[1].split()[0].strip())
    except:
        pass
    
    # Default to high resolution for modern Macs
    return 3024, 1964


def generate_and_set_wallpaper(
    city: str = "San Francisco",
    show_weather: bool = True,
    show_calendar: bool = True,
    show_reminders: bool = True,
    custom_message: Optional[str] = None,
) -> dict:
    """Generate a dynamic wallpaper and set it as desktop background."""
    try:
        width, height = get_screen_resolution()
        
        path = generate_wallpaper(
            city=city,
            show_weather=show_weather,
            show_calendar=show_calendar,
            show_reminders=show_reminders,
            custom_message=custom_message,
            width=width,
            height=height,
        )
        
        success = set_wallpaper(path)
        progress = get_year_progress()
        
        return {
            "success": success,
            "path": path,
            "resolution": f"{width}x{height}",
            "year_progress": f"{progress['percent']:.1f}%",
            "days_remaining": progress["days_remaining"],
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    result = generate_and_set_wallpaper(city="San Francisco")
    print(result)
