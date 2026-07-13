from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message

from config import ADMIN_ID, ADMIN_USERNAME
from utils.logger import logger


class AdminMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        user = event.from_user
        if not user:
            return None

        if user.id != ADMIN_ID:
            logger.warning("Unauthorized access attempt from user_id=%s", user.id)
            return None

        if ADMIN_USERNAME and user.username and user.username.lower() != ADMIN_USERNAME.lower().lstrip("@"):
            logger.warning("Unauthorized access attempt from username=%s", user.username)
            return None

        return await handler(event, data)
