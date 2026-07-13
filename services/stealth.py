"""Stealth helpers: proxy config, evasion delays, user-agent rotation.

This module is intentionally separate from the core handlers so it can be
added/removed without touching the reviewed main code.
"""

import os
import random
import time
from typing import Optional

from utils.logger import logger

PROXY_URL = os.getenv("PROXY_URL", "").strip()
PROXY_TYPE = os.getenv("PROXY_TYPE", "http").strip().lower()
EVADE_MIN_DELAY = float(os.getenv("EVADE_MIN_DELAY", "0.5"))
EVADE_MAX_DELAY = float(os.getenv("EVADE_MAX_DELAY", "2.0"))

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0",
]


def proxy_configured() -> bool:
    return bool(PROXY_URL)


def proxy_dict() -> dict[str, str]:
    """Return a requests/aiohttp compatible proxy dict when PROXY_URL is set."""
    if not PROXY_URL:
        return {}
    return {
        "http": PROXY_URL,
        "https": PROXY_URL,
    }


def aiohttp_proxy() -> Optional[str]:
    """Return proxy URL for aiohttp ClientSession."""
    return PROXY_URL if PROXY_URL else None


def random_user_agent() -> str:
    return random.choice(_USER_AGENTS)


def stealth_headers() -> dict[str, str]:
    return {
        "User-Agent": random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }


def random_source_port() -> int:
    """High ephemeral port, unlikely to be blocked by simple stateful filters."""
    return random.randint(40000, 65000)


async def jitter() -> None:
    """Random delay between requests to avoid rate-limit/trigger patterns."""
    delay = random.uniform(EVADE_MIN_DELAY, EVADE_MAX_DELAY)
    logger.info("Stealth jitter: sleeping %.2fs", delay)
    time.sleep(delay)


def evade_nmap_flags() -> list[str]:
    """Extra nmap flags that reduce fingerprinting/noise.

    Use with caution and only on authorized targets.
    """
    return [
        "--randomize-hosts",
        "--spoof-mac", "0",
        "--source-port", str(random_source_port()),
        "--data-length", str(random.randint(16, 64)),
        "--max-retries", "2",
    ]
