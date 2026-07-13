"""Stealth/extra scanner commands — added as a plugin without changing core handlers.

Commands:
    /scapy <IP> [ports]      — Scapy SYN scan (top100 by default)
    /scapyfrag <IP> [ports]  — fragmented Scapy SYN scan
    /scapydecoy <IP> [ports] — Scapy SYN scan with decoy IPs
    /evade <IP>              — nmap scan with extra evasion flags
    /proxyinfo               — show current proxy configuration
    /proxytest               — test HTTP(S) proxy connectivity

Use only on targets you own or have explicit permission to test.
"""

import aiohttp
from aiogram import Router, types
from aiogram.filters import Command

from config import SCAN_TIMEOUT
from services.reports import save_report, send_report
from services.scapy_scan import scapy_syn_scan
from services.shell import run_command, scan_lock
from services.stealth import (
    EVADE_MAX_DELAY,
    EVADE_MIN_DELAY,
    PROXY_TYPE,
    PROXY_URL,
    aiohttp_proxy,
    evade_nmap_flags,
    proxy_configured,
)
from services.validators import ValidationError, validate_ipv4
from utils.logger import logger

stealth_router = Router()


@stealth_router.message(Command("proxyinfo"))
async def cmd_proxyinfo(message: types.Message):
    if proxy_configured():
        text = (
            f"🌐 Proxy configured\n"
            f"Type: `{PROXY_TYPE}`\n"
            f"URL: `{PROXY_URL}`\n"
            f"Jitter: {EVADE_MIN_DELAY}s – {EVADE_MAX_DELAY}s"
        )
    else:
        text = (
            "🌐 No proxy configured.\n\n"
            "Set in `.env`:\n"
            "```\n"
            "PROXY_URL=http://user:pass@host:port\n"
            "PROXY_TYPE=http\n"
            "EVADE_MIN_DELAY=0.5\n"
            "EVADE_MAX_DELAY=2.0\n"
            "```"
        )
    await message.answer(text, parse_mode="Markdown")


@stealth_router.message(Command("proxytest"))
async def cmd_proxytest(message: types.Message):
    if not proxy_configured():
        await message.answer("❌ Proxy is not configured. Set PROXY_URL in .env")
        return

    await message.answer("🌐 Testing proxy via httpbin.org/ip...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://httpbin.org/ip",
                proxy=aiohttp_proxy(),
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json()
                origin = data.get("origin", "unknown")
                await message.answer(f"🌐 Proxy origin IP: `{origin}`", parse_mode="Markdown")
    except Exception as exc:
        logger.exception("Proxy test failed")
        await message.answer(f"❌ Proxy test failed: {exc}")


@stealth_router.message(Command("scapy"))
async def cmd_scapy(message: types.Message):
    args = (message.text or "").split(maxsplit=2)
    if len(args) < 2:
        await message.answer("Usage: /scapy <IP> [ports]\nExamples:\n/scapy 1.1.1.1\n/scapy 1.1.1.1 80,443\n/scapy 1.1.1.1 1-1000")
        return

    try:
        target_ip = validate_ipv4(args[1], allow_private=False)
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    ports = args[2] if len(args) > 2 else "top100"

    if not await scan_lock.acquire(f"scapy {target_ip}"):
        await message.answer("⏳ Another scan is already running. Wait or use /cancel.")
        return

    try:
        logger.info("Scapy scan started for %s by admin", target_ip)
        await message.answer(
            f"🕵️ Starting Scapy SYN scan of `{target_ip}` (ports: `{ports}`)...",
            parse_mode="Markdown",
        )
        output = await scapy_syn_scan(target_ip, port_spec=ports)
        save_report("scapy", target_ip, output)
        await send_report(message, output, prefix=f"🕵️ Scapy scan for `{target_ip}`")
    finally:
        scan_lock.release()


@stealth_router.message(Command("scapyfrag"))
async def cmd_scapyfrag(message: types.Message):
    args = (message.text or "").split(maxsplit=2)
    if len(args) < 2:
        await message.answer("Usage: /scapyfrag <IP> [ports]")
        return

    try:
        target_ip = validate_ipv4(args[1], allow_private=False)
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    ports = args[2] if len(args) > 2 else "top100"

    if not await scan_lock.acquire(f"scapyfrag {target_ip}"):
        await message.answer("⏳ Another scan is already running. Wait or use /cancel.")
        return

    try:
        logger.info("Fragmented Scapy scan started for %s by admin", target_ip)
        await message.answer(
            f"🕵️ Starting *fragmented* Scapy SYN scan of `{target_ip}`...",
            parse_mode="Markdown",
        )
        output = await scapy_syn_scan(target_ip, port_spec=ports, fragment=True)
        save_report("scapyfrag", target_ip, output)
        await send_report(message, output, prefix=f"🕵️ Fragmented Scapy scan for `{target_ip}`")
    finally:
        scan_lock.release()


@stealth_router.message(Command("scapydecoy"))
async def cmd_scapydecoy(message: types.Message):
    args = (message.text or "").split(maxsplit=2)
    if len(args) < 2:
        await message.answer("Usage: /scapydecoy <IP> [ports]\nSends decoy packets from random source IPs.")
        return

    try:
        target_ip = validate_ipv4(args[1], allow_private=False)
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    ports = args[2] if len(args) > 2 else "top100"

    if not await scan_lock.acquire(f"scapydecoy {target_ip}"):
        await message.answer("⏳ Another scan is already running. Wait or use /cancel.")
        return

    try:
        logger.info("Decoy Scapy scan started for %s by admin", target_ip)
        await message.answer(
            f"🕵️ Starting Scapy SYN scan with *decoys* for `{target_ip}`...",
            parse_mode="Markdown",
        )
        output = await scapy_syn_scan(target_ip, port_spec=ports, decoys=3)
        save_report("scapydecoy", target_ip, output)
        await send_report(message, output, prefix=f"🕵️ Decoy Scapy scan for `{target_ip}`")
    finally:
        scan_lock.release()


@stealth_router.message(Command("evade"))
async def cmd_evade(message: types.Message):
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /evade <IP>\nRuns nmap with extra evasion flags (randomize-hosts, spoof-mac, source-port, data-length).")
        return

    try:
        target_ip = validate_ipv4(args[1], allow_private=False)
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    if not await scan_lock.acquire(f"evade {target_ip}"):
        await message.answer("⏳ Another scan is already running. Wait or use /cancel.")
        return

    try:
        logger.info("Evasive nmap scan started for %s by admin", target_ip)
        await message.answer(
            f"🥷 Starting evasive nmap scan of `{target_ip}`...",
            parse_mode="Markdown",
        )
        flags = evade_nmap_flags()
        cmd = ["nmap", "-sS", "-T2", "-F"] + flags + [target_ip]
        result = await run_command(cmd, timeout=SCAN_TIMEOUT * 2, cancellable=True)
        output = result.stdout if result.returncode == 0 else result.stderr
        if scan_lock.cancelled:
            output = "🛑 Scan cancelled by admin."
        save_report("evade", target_ip, output)
        await send_report(message, output, prefix=f"🥷 Evasive nmap scan for `{target_ip}`")
    finally:
        scan_lock.release()
