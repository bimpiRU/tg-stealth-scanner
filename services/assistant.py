"""Natural-language intent parsing and conversational AI assistant.

Keeps regex/keyword matching intentionally simple. New intents are just new
entries in ``_INTENT_PATTERNS``.
"""

import json
import re
from datetime import datetime, timezone
from typing import Optional

import aiohttp

from config import AI_API_KEY, AI_BASE_URL, AI_MAX_TOKENS, AI_MODEL, BASE_DIR
from services.ai_summarizer import is_configured
from utils.logger import logger

_AGENT_KEYWORDS = re.compile(
    r"\b(agent|админ|admin|kimi|кими|агент)\b",
    re.IGNORECASE,
)

# Order matters: first match wins.
_INTENT_PATTERNS = [
    ("scan", re.compile(r"\b(scan|скан|skan|сканировать|skanerlash)\b", re.IGNORECASE)),
    ("osint", re.compile(r"\b(osint|осинт)\b", re.IGNORECASE)),
    ("discover", re.compile(r"\b(discover|discovery|сеть|subnet|подсеть|tarmoq)\b", re.IGNORECASE)),
    ("vulns", re.compile(r"\b(vulns|vuln|vulnerability|уязвимости|zaiflik|zaif)\b", re.IGNORECASE)),
    ("proxyfetch", re.compile(r"\b(proxyfetch|proxy|прокси|proksi)\b", re.IGNORECASE)),
    ("help", re.compile(r"\b(help|помощь|yordam|yardam)\b", re.IGNORECASE)),
    ("status", re.compile(r"\b(status|статус|holat)\b", re.IGNORECASE)),
    ("lang", re.compile(r"\b(lang|язык|til|tilni)\b", re.IGNORECASE)),
    ("ask", re.compile(r"\b(ask|вопрос|savol)\b", re.IGNORECASE)),
]

_IP_RE = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
_SUBNET_RE = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}\b")
_DOMAIN_RE = re.compile(
    r"\b(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+"
    r"[a-z0-9][a-z0-9\-]{0,61}[a-z0-9]\b",
    re.IGNORECASE,
)

_ASSISTANT_PROMPT = (
    "You are a concise cybersecurity assistant for a Telegram bot. "
    "Answer the user's question briefly and accurately. "
    "If the question is about the bot, mention relevant commands like /scan, /osint, /help."
)

AGENT_INBOX_PATH = BASE_DIR / "data" / "agent_inbox.jsonl"


def parse_intent(text: str) -> dict:
    """Return intent dict: {"intent": ..., "args": [...]} or {"intent": "unknown", "text": ...}."""
    text = (text or "").strip()
    if not text:
        return {"intent": "unknown", "text": text}

    lower = text.lower()

    if _AGENT_KEYWORDS.search(lower):
        return {"intent": "agent", "text": text}

    for intent, pattern in _INTENT_PATTERNS:
        match = pattern.search(lower)
        if match:
            args = _extract_args(intent, text, match)
            return {"intent": intent, "args": args}

    return {"intent": "unknown", "text": text}


def _extract_args(intent: str, text: str, match: re.Match) -> list[str]:
    if intent == "scan":
        ip = _IP_RE.search(text)
        return [ip.group(0)] if ip else []

    if intent == "discover":
        subnet = _SUBNET_RE.search(text)
        return [subnet.group(0)] if subnet else []

    if intent in ("osint", "vulns"):
        domain = _DOMAIN_RE.search(text)
        if domain:
            return [domain.group(0).lower()]
        ip = _IP_RE.search(text)
        if ip:
            return [ip.group(0)]
        return []

    if intent == "lang":
        rest = text[match.end():].strip()
        if rest:
            return [rest.split()[0].lower()]
        return []

    if intent == "ask":
        rest = text[match.end():].strip()
        return [rest] if rest else []

    return []


async def ask_ai(question: str) -> Optional[str]:
    """Ask the configured AI a question. Returns None if AI is not configured."""
    if not is_configured():
        return None

    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": _ASSISTANT_PROMPT},
            {"role": "user", "content": question[:12000]},
        ],
        "max_tokens": AI_MAX_TOKENS,
        "temperature": 0.5,
    }

    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{AI_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error("AI API error %s: %s", resp.status, body)
                    return f"AI API error: {resp.status}"
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.exception("AI ask failed")
        return f"AI ask failed: {exc}"


def log_agent_request(user_id: int, text: str) -> None:
    """Append an agent request to the JSONL inbox."""
    AGENT_INBOX_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "text": text,
    }
    with AGENT_INBOX_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
