import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message

from config import RATE_LIMIT_BURST, RATE_LIMIT_SECONDS, RATE_LIMIT_WINDOW
from utils.logger import logger


class RateLimitMiddleware(BaseMiddleware):
    def __init__(
        self,
        default_seconds: int = RATE_LIMIT_SECONDS,
        burst_limit: int = RATE_LIMIT_BURST,
        window_seconds: int = RATE_LIMIT_WINDOW,
    ) -> None:
        self.default_seconds = default_seconds
        self.burst_limit = burst_limit
        self.window_seconds = window_seconds
        self._last_command: Dict[int, float] = {}
        self._window_commands: Dict[int, list[float]] = {}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id if event.from_user else 0
        now = time.monotonic()

        # Per-user cooldown between commands
        last = self._last_command.get(user_id, 0)
        if now - last < self.default_seconds:
            await event.answer(f"⏳ Wait {self.default_seconds} seconds between commands.")
            return None

        # Sliding window burst limit
        window = self._window_commands.setdefault(user_id, [])
        window[:] = [t for t in window if now - t < self.window_seconds]
        if len(window) >= self.burst_limit:
            await event.answer("🚫 Too many commands in the last minute. Slow down.")
            return None

        self._last_command[user_id] = now
        window.append(now)

        return await handler(event, data)
