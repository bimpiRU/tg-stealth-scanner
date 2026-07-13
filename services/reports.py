import html
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


_TRUNCATE_SUFFIX = "\n\n[truncated]"


def truncate_for_telegram(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - len(_TRUNCATE_SUFFIX)] + _TRUNCATE_SUFFIX


def _trim_partial_entity(text: str) -> str:
    """Drop a trailing HTML entity that truncation may have sliced in half.

    e.g. a cut landing inside ``&lt;`` -> ``&l`` would be invalid HTML and make
    aiogram's parser reject the message. We only strip an unterminated ``&...``
    tail (an ``&`` not yet closed by ``;``)."""
    amp = text.rfind("&")
    if amp != -1 and ";" not in text[amp:]:
        return text[:amp]
    return text


def store_last_report(user_id: int, text: str) -> None:
    _last_report[user_id] = text


def get_last_report(user_id: int) -> Optional[str]:
    return _last_report.get(user_id)


async def send_report(message: types.Message, text: str, prefix: str = "") -> None:
    # Store the FULL report (before truncation) so /summary sees everything.
    store_last_report(message.from_user.id, text)

    # Render via HTML with escaping: arbitrary tool output (whois, crt.sh JSON,
    # headers) may contain backticks or ``` that would break a Markdown code block
    # and make aiogram raise, dropping the reply. <pre> + html.escape is safe.
    #
    # Escape BEFORE truncating: html.escape expands `<`,`>`,`&` (e.g. `<` -> `&lt;`),
    # so escaping a text already at the 4000-char budget could push the message past
    # Telegram's 4096 hard limit and make .answer() raise. Truncating the escaped
    # string keeps the final payload bounded; _trim_partial_entity drops any HTML
    # entity the cut may have sliced in half.
    body = _trim_partial_entity(truncate_for_telegram(html.escape(text)))
    parts = []
    if prefix:
        parts.append(f"<b>{html.escape(prefix.replace('`', ''))}</b>")
    parts.append(f"<pre>{body}</pre>")
    await message.answer("\n\n".join(parts), parse_mode="HTML")
