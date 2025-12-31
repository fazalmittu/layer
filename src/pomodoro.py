"""
Pomodoro Timer Manager.
Handles work/break cycles with notifications and focus mode.
"""

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Awaitable
from dataclasses import dataclass, field


class SessionType(str, Enum):
    WORK = "work"
    BREAK = "break"


@dataclass
class PomodoroState:
    """Current state of the pomodoro timer."""
    active: bool = False
    session_type: SessionType = SessionType.WORK
    start_time: datetime | None = None
    duration_minutes: int = 25
    work_duration: int = 25
    break_duration: int = 5
    sessions_completed: int = 0
    focus_mode_enabled: bool = False
    # Store original volume to restore later
    original_volume: int | None = None


class PomodoroManager:
    """
    Manages pomodoro timer sessions with async background tasks.
    """
    
    def __init__(self):
        self.state = PomodoroState()
        self._timer_task: asyncio.Task | None = None
        self._on_session_complete: Callable[[], Awaitable[None]] | None = None
        self._on_break_complete: Callable[[], Awaitable[None]] | None = None
    
    def set_callbacks(
        self,
        on_session_complete: Callable[[], Awaitable[None]],
        on_break_complete: Callable[[], Awaitable[None]]
    ):
        """Set callbacks for session completion events."""
        self._on_session_complete = on_session_complete
        self._on_break_complete = on_break_complete
    
    @property
    def is_active(self) -> bool:
        return self.state.active
    
    @property
    def time_remaining(self) -> int:
        """Get remaining time in seconds."""
        if not self.state.active or not self.state.start_time:
            return 0
        
        elapsed = datetime.now() - self.state.start_time
        total_seconds = self.state.duration_minutes * 60
        remaining = total_seconds - elapsed.total_seconds()
        return max(0, int(remaining))
    
    @property
    def time_remaining_formatted(self) -> str:
        """Get remaining time as MM:SS string."""
        remaining = self.time_remaining
        minutes = remaining // 60
        seconds = remaining % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def get_status(self) -> dict:
        """Get current pomodoro status."""
        return {
            "active": self.state.active,
            "session_type": self.state.session_type.value if self.state.active else None,
            "time_remaining_seconds": self.time_remaining,
            "time_remaining": self.time_remaining_formatted if self.state.active else None,
            "sessions_completed": self.state.sessions_completed,
            "work_duration": self.state.work_duration,
            "break_duration": self.state.break_duration,
            "focus_mode_enabled": self.state.focus_mode_enabled,
        }
    
    async def start(
        self,
        work_duration: int = 25,
        break_duration: int = 5,
        focus_mode: bool = True,
        original_volume: int | None = None,
    ) -> dict:
        """Start a new pomodoro work session."""
        if self.state.active:
            return {"error": "Pomodoro already active"}
        
        # Cancel any existing timer
        await self._cancel_timer()
        
        # Set up state
        self.state = PomodoroState(
            active=True,
            session_type=SessionType.WORK,
            start_time=datetime.now(),
            duration_minutes=work_duration,
            work_duration=work_duration,
            break_duration=break_duration,
            sessions_completed=0,
            focus_mode_enabled=focus_mode,
            original_volume=original_volume,
        )
        
        # Start the timer
        self._timer_task = asyncio.create_task(self._run_timer())
        
        return self.get_status()
    
    async def stop(self) -> dict:
        """Stop the current pomodoro session."""
        if not self.state.active:
            return {"error": "No active pomodoro"}
        
        await self._cancel_timer()
        
        sessions = self.state.sessions_completed
        original_volume = self.state.original_volume
        
        self.state = PomodoroState()
        
        return {
            "stopped": True,
            "sessions_completed": sessions,
            "original_volume": original_volume,
        }
    
    async def skip(self) -> dict:
        """Skip to the next phase (work -> break or break -> work)."""
        if not self.state.active:
            return {"error": "No active pomodoro"}
        
        await self._cancel_timer()
        
        if self.state.session_type == SessionType.WORK:
            # Skipping work → count as completed, start break
            self.state.sessions_completed += 1
            await self._start_break()
        else:
            # Skipping break → start new work session
            await self._start_work()
        
        return self.get_status()
    
    async def _start_work(self):
        """Start a work session."""
        self.state.session_type = SessionType.WORK
        self.state.duration_minutes = self.state.work_duration
        self.state.start_time = datetime.now()
        self._timer_task = asyncio.create_task(self._run_timer())
    
    async def _start_break(self):
        """Start a break session."""
        self.state.session_type = SessionType.BREAK
        self.state.duration_minutes = self.state.break_duration
        self.state.start_time = datetime.now()
        self._timer_task = asyncio.create_task(self._run_timer())
    
    async def _run_timer(self):
        """Background task that waits for timer completion."""
        try:
            duration_seconds = self.state.duration_minutes * 60
            await asyncio.sleep(duration_seconds)
            
            if self.state.session_type == SessionType.WORK:
                self.state.sessions_completed += 1
                if self._on_session_complete:
                    await self._on_session_complete()
                await self._start_break()
            else:
                if self._on_break_complete:
                    await self._on_break_complete()
                await self._start_work()
                
        except asyncio.CancelledError:
            pass
    
    async def _cancel_timer(self):
        """Cancel the current timer task."""
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
            try:
                await self._timer_task
            except asyncio.CancelledError:
                pass
        self._timer_task = None


# Global instance
pomodoro_manager = PomodoroManager()


