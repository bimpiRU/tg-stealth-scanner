"""Architecture review + functional tests for tg-stealth-scanner.

Lightweight version: checks memory guards and runs quick reachability/scan
commands on the requested target, then reports to Telegram.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from services.reports import save_report
from services.scapy_scan import scapy_syn_scan
from services.shell import run_command
from services.validators import validate_ipv4
from services.vuln_scan import discover_hosts

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
TARGET = os.getenv("TEST_TARGET", "172.16.11.11")
TARGET_SUBNET = os.getenv("TEST_TARGET_SUBNET", "172.16.11.0/24")
FALLBACK_TARGET = os.getenv("TEST_FALLBACK_TARGET", "192.168.0.1")
FALLBACK_SUBNET = os.getenv("TEST_FALLBACK_SUBNET", "192.168.0.0/24")

results: list[str] = []


def log(section: str, text: str) -> None:
    results.append(f"\n=== {section} ===\n{text.strip()}")


async def send_telegram(text: str) -> None:
    if not BOT_TOKEN or not ADMIN_ID:
        print("BOT_TOKEN or ADMIN_ID not set, skipping Telegram send")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_ID,
        "text": text[:3900],
        "parse_mode": "Markdown",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    print(f"Telegram API error {resp.status}: {await resp.text()}")
    except Exception as exc:
        print(f"Failed to send Telegram message: {exc}")


def check_memory_guards() -> str:
    lines = []
    from services.reports import _MAX_TRACKED_USERS, _MAX_RESULT_FILES
    lines.append(f"In-memory report cache max users: {_MAX_TRACKED_USERS}")
    lines.append(f"Result files max on disk: {_MAX_RESULT_FILES}")

    from utils.logger import setup_logger
    logger = setup_logger("test")
    rotating = [h for h in logger.handlers if hasattr(h, "maxBytes")]
    if rotating:
        lines.append(f"Log rotation: {rotating[0].maxBytes / 1024 / 1024:.0f} MB x {rotating[0].backupCount}")
    else:
        lines.append("WARNING: no rotating log handler")

    from services.shell import _MAX_OUTPUT_BYTES
    lines.append(f"Shell output cap: {_MAX_OUTPUT_BYTES / 1024 / 1024:.1f} MB")

    from services.scapy_scan import _MAX_SCAPY_PORTS
    lines.append(f"Scapy max ports: {_MAX_SCAPY_PORTS}")

    from services.stealth import _MAX_PROXY_LIST_SIZE
    lines.append(f"Proxy list max size: {_MAX_PROXY_LIST_SIZE}")

    from services.proxy_fetcher import _MAX_PARSED_PROXIES
    lines.append(f"Proxy fetch parse max: {_MAX_PARSED_PROXIES}")

    lines.append(f"ALLOW_PRIVATE_IPS: {config.ALLOW_PRIVATE_IPS}")
    return "\n".join(lines)


async def is_reachable(target: str) -> bool:
    r = await run_command(["ping", "-c", "2", "-W", "2", target], timeout=10)
    return r.returncode == 0 and " 0% packet loss" in r.stdout


async def test_target(target: str) -> str:
    lines = [f"Target: {target}"]

    reachable = await is_reachable(target)
    lines.append(f"Reachable via ping: {reachable}")
    if not reachable:
        lines.append("Skipping heavy scans on unreachable host.")
        return "\n".join(lines)

    lines.append("\n[nmap -sS -T4 -p22,80,443,445,8080]")
    r = await run_command(["nmap", "-sS", "-T4", "-p22,80,443,445,8080", target], timeout=60)
    lines.append(r.stdout if r.returncode == 0 else r.stderr)

    lines.append("\n[scapy SYN top5]")
    lines.append(await scapy_syn_scan(target, port_spec="22,80,443,445,8080", timeout=1.0))

    return "\n".join(lines)


async def test_subnet(subnet: str) -> str:
    lines = [f"Subnet: {subnet}"]
    lines.append("\n[nmap -sn -T4 --max-retries 1]")
    r = await run_command(["nmap", "-sn", "-T4", "--max-retries", "1", subnet], timeout=120)
    lines.append(r.stdout if r.returncode == 0 else r.stderr)
    return "\n".join(lines)


async def main() -> None:
    if not BOT_TOKEN or not ADMIN_ID:
        print("Set BOT_TOKEN and ADMIN_ID env vars")
        sys.exit(1)

    start = time.time()
    await send_telegram("🧪 *Architecture review started*\nTarget: " + TARGET)

    log("Architecture review", check_memory_guards())

    try:
        validate_ipv4(TARGET)
        log("Validation", f"{TARGET} parsed OK (private allowed by ALLOW_PRIVATE_IPS)")
    except Exception as exc:
        log("Validation", f"ERROR: {exc}")

    # Primary target
    log(f"Primary target: {TARGET}", await test_target(TARGET))
    log(f"Primary subnet: {TARGET_SUBNET}", await test_subnet(TARGET_SUBNET))

    # Fallback local target
    log(f"Fallback target: {FALLBACK_TARGET}", await test_target(FALLBACK_TARGET))
    log(f"Fallback subnet: {FALLBACK_SUBNET}", await test_subnet(FALLBACK_SUBNET))

    elapsed = time.time() - start
    log("Summary", f"Total elapsed: {elapsed:.1f}s\nResults dir: {config.RESULTS_DIR}")

    report = "\n".join(results)
    report_path = save_report("architecture_test", TARGET.replace("/", "_"), report)
    print(f"Report saved: {report_path}")

    chunks = []
    current = "🧪 *Architecture review results*\n\n"
    for line in results:
        if len(current) + len(line) > 3800:
            chunks.append(current)
            current = line + "\n"
        else:
            current += line + "\n"
    if current:
        chunks.append(current)

    for i, chunk in enumerate(chunks):
        await send_telegram(f"[{i+1}/{len(chunks)}] {chunk}")
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
