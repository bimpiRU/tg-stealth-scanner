"""Stealth helpers: proxy config, evasion delays, user-agent rotation.

This module is intentionally separate from the core handlers so it can be
added/removed without touching the reviewed main code.
"""

import asyncio
import os
import random
from pathlib import Path
from typing import Optional

import aiohttp

from utils.logger import logger

PROXY_URL = os.getenv("PROXY_URL", "").strip()
PROXY_TYPE = os.getenv("PROXY_TYPE", "http").strip().lower()
EVADE_MIN_DELAY = float(os.getenv("EVADE_MIN_DELAY", "0.5"))
EVADE_MAX_DELAY = float(os.getenv("EVADE_MAX_DELAY", "2.0"))
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PROXY_LIST_PATH = DATA_DIR / "proxies.txt"

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0",
]


_MAX_PROXY_LIST_SIZE = 5_000


def _load_proxy_list() -> list[str]:
    """Load proxies from data/proxies.txt (one per line)."""
    if not PROXY_LIST_PATH.exists():
        # Copy example file so the user has a template and the bot keeps working.
        example = PROXY_LIST_PATH.with_suffix(".example.txt")
        if example.exists():
            try:
                PROXY_LIST_PATH.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
            except OSError:
                return []
        else:
            return []
    lines = PROXY_LIST_PATH.read_text(encoding="utf-8").splitlines()
    proxies = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
    return proxies[:_MAX_PROXY_LIST_SIZE]


def proxy_configured() -> bool:
    return bool(PROXY_URL) or bool(_load_proxy_list())


def all_proxies() -> list[str]:
    """Return configured proxy plus any from the list file."""
    proxies = []
    if PROXY_URL:
        proxies.append(PROXY_URL)
    proxies.extend(_load_proxy_list())
    return proxies


def random_proxy() -> Optional[str]:
    proxies = all_proxies()
    return random.choice(proxies) if proxies else None


def proxy_dict() -> dict[str, str]:
    """Return a requests/aiohttp compatible proxy dict when a single proxy is active."""
    proxy = random_proxy()
    if not proxy:
        return {}
    return {"http": proxy, "https": proxy}


def aiohttp_proxy() -> Optional[str]:
    """Return a proxy URL for aiohttp ClientSession."""
    proxy = random_proxy()
    if not proxy:
        return None
    if "://" not in proxy:
        proxy = f"{PROXY_TYPE}://{proxy}"
    return proxy


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
    await asyncio.sleep(delay)


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


async def test_proxy(proxy: str, timeout: int = 15) -> bool:
    """Check if a proxy can reach httpbin.org/ip."""
    if "://" not in proxy:
        proxy = f"{PROXY_TYPE}://{proxy}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://httpbin.org/ip",
                proxy=proxy,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                return resp.status == 200
    except Exception as exc:
        logger.debug("Proxy %s failed: %s", proxy, exc)
        return False


async def find_working_proxy() -> Optional[str]:
    """Test all known proxies and return the first working one."""
    proxies = all_proxies()
    if not proxies:
        return None
    random.shuffle(proxies)
    for proxy in proxies:
        if await test_proxy(proxy):
            return proxy
    return None
