"""Fetch and test public proxy lists.

Public proxies are convenient for OSINT but come with serious caveats:
- they can be slow, unreliable or already dead;
- they may log traffic or inject ads/malware;
- they do NOT anonymize raw TCP/UDP scans (nmap/scapy) — only HTTP(S) requests.

For real anonymity of raw scans use a VPN/Tor at host/network level.
"""

from __future__ import annotations

import asyncio
import re
from typing import Iterable

import aiohttp

from services.stealth import PROXY_TYPE, test_proxy
from utils.logger import logger

_PROXY_LIST_URLS = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
    "https://www.proxy-list.download/api/v1/get?type=http",
]

_PROXY_RE = re.compile(r"(?:https?://)?(?P<host>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(?P<port>\d{2,5})")


async def _fetch_text(session: aiohttp.ClientSession, url: str, timeout: int = 20) -> str:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status == 200:
                return await resp.text(errors="replace")
    except Exception as exc:
        logger.warning("Failed to fetch proxy list from %s: %s", url, exc)
    return ""


def _parse_proxies(text: str) -> list[str]:
    found: set[str] = set()
    for match in _PROXY_RE.finditer(text):
        host = match.group("host")
        port = match.group("port")
        # basic sanity check
        if int(port) > 65535:
            continue
        found.add(f"{host}:{port}")
    return sorted(found)


async def fetch_public_proxy_list(
    urls: Iterable[str] | None = None,
    max_test: int = 50,
    concurrency: int = 10,
) -> tuple[list[str], list[str]]:
    """Fetch public proxy lists and return (working_proxies, all_unique_proxies).

    Only the first ``max_test`` candidates are tested to keep runtime reasonable.
    """
    urls = list(urls or _PROXY_LIST_URLS)
    async with aiohttp.ClientSession() as session:
        texts = await asyncio.gather(*(_fetch_text(session, url) for url in urls))

    candidates: list[str] = []
    seen: set[str] = set()
    for text in texts:
        for proxy in _parse_proxies(text):
            if proxy not in seen:
                seen.add(proxy)
                candidates.append(proxy)

    logger.info("Fetched %d unique proxy candidates", len(candidates))

    # Test with limited concurrency
    semaphore = asyncio.Semaphore(concurrency)
    working: list[str] = []

    async def _test_one(proxy: str) -> bool:
        async with semaphore:
            return await test_proxy(proxy, timeout=12)

    # Cap testing to avoid long waits
    for proxy in candidates[:max_test]:
        if await _test_one(proxy):
            working.append(proxy)

    logger.info("Found %d working proxies out of %d tested", len(working), min(len(candidates), max_test))
    return working, candidates
