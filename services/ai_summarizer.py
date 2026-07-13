import os
from typing import Optional

import aiohttp

from utils.logger import logger

AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "800"))

_SYSTEM_PROMPT = (
    "You are a concise cybersecurity analyst. Summarize the given scan/OSINT report "
    "in 3-5 bullet points. Highlight: key findings, risks, open ports/services, "
    "interesting subdomains, and actionable next steps. Be brief."
)


def is_configured() -> bool:
    return bool(AI_API_KEY and AI_API_KEY not in ("your_api_key", "sk-xxx"))


async def summarize(text: str) -> Optional[str]:
    if not is_configured():
        return None

    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": text[:12000]},
        ],
        "max_tokens": AI_MAX_TOKENS,
        "temperature": 0.3,
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
        logger.exception("AI summarization failed")
        return f"AI summarization failed: {exc}"
