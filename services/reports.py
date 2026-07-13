from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from aiogram import types

from config import MAX_MESSAGE_LENGTH, RESULTS_DIR


_last_report: Dict[int, str] = {}


def save_report(prefix: str, target: str, content: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{target}_{timestamp}.txt"
    path = Path(RESULTS_DIR) / filename
    path.write_text(content, encoding="utf-8")
    return path


def build_report(lines: List[str]) -> str:
    return "\n".join(lines)


def truncate_for_telegram(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 12] + "\n\n[truncated]"


def store_last_report(user_id: int, text: str) -> None:
    _last_report[user_id] = text


def get_last_report(user_id: int) -> Optional[str]:
    return _last_report.get(user_id)


async def send_report(message: types.Message, text: str, prefix: str = "") -> None:
    text = truncate_for_telegram(text)
    if prefix:
        text = f"{prefix}\n\n{text}"
    store_last_report(message.from_user.id, text)
    await message.answer(f"```\n{text}\n```", parse_mode="Markdown")
