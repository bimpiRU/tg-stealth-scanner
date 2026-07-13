"""Stealth/extra scanner commands — added as a plugin without changing core handlers.

Commands:
    /scapy <IP> [ports]      — Scapy SYN scan (top100 by default)
    /scapyfrag <IP> [ports]  — fragmented Scapy SYN scan
    /scapydecoy <IP> [ports] — Scapy SYN scan with decoy IPs
    /evade <IP>              — nmap scan with extra evasion flags
    /discover <subnet>       — nmap ping sweep of an explicit subnet
    /vulns <target>          — nmap vuln NSE scan (safe, no exploit)
    /quickvulns <target>     — fast vuln scan on top 100 ports
    /proxyinfo               — show current proxy configuration
    /proxytest               — test a random proxy
    /proxyfind               — find first working proxy from the list

Use only on targets/networks you own or have explicit written permission to test.
"""

import re

import aiohttp
from aiogram import Router, types
from aiogram.filters import Command

from config import SCAN_TIMEOUT
from services.i18n import t
from services.proxy_fetcher import fetch_public_proxy_list
from services.reports import save_report, send_report
from services.scapy_scan import scapy_syn_scan
from services.shell import run_command, scan_lock
from services.stealth import (
    DATA_DIR,
    EVADE_MAX_DELAY,
    EVADE_MIN_DELAY,
    PROXY_TYPE,
    aiohttp_proxy,
    evade_nmap_flags,
    find_working_proxy,
    proxy_configured,
    test_proxy,
)
from services.validators import ValidationError, validate_ipv4
from services.vuln_scan import discover_hosts, quick_vuln_scan, vuln_scan
from utils.logger import logger

stealth_router = Router()


def _usage(label: str, text: str) -> str:
    return f"{t('usage')}: `/{label} {text}`"


@stealth_router.message(Command("proxyinfo"))
async def cmd_proxyinfo(message: types.Message):
    if proxy_configured():
        text = (
            f"🌐 {t('proxy_working') if True else t('proxy_test_failed')}\n"
            f"Type: `{PROXY_TYPE}`\n"
            f"Jitter: {EVADE_MIN_DELAY}s – {EVADE_MAX_DELAY}s\n\n"
            f"Add proxies one per line to `data/proxies.txt` (format `host:port` or full URL), "
            f"or use `/proxyfetch` to load public lists automatically."
        )
    else:
        text = t("proxy_not_configured") + "\nUse `/proxyfetch` to search public proxy lists."
    await message.answer(text, parse_mode="Markdown")


@stealth_router.message(Command("proxytest"))
async def cmd_proxytest(message: types.Message):
    if not proxy_configured():
        await message.answer(t("proxy_not_configured"))
        return

    await message.answer("🌐 Testing a random proxy via httpbin.org/ip...")
    proxy = aiohttp_proxy()
    try:
        if proxy and await test_proxy(proxy):
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://httpbin.org/ip",
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    data = await resp.json()
                    origin = data.get("origin", "unknown")
                    await message.answer(f"🌐 {t('proxy_working')}: `{proxy}`\nOrigin IP: `{origin}`", parse_mode="Markdown")
        else:
            await message.answer(t("proxy_test_failed"))
    except Exception as exc:
        logger.exception("Proxy test failed")
        await message.answer(f"❌ {t('proxy_test_failed')}: {exc}")


@stealth_router.message(Command("proxyfind"))
async def cmd_proxyfind(message: types.Message):
    if not proxy_configured():
        await message.answer(t("proxy_not_configured"))
        return

    await message.answer("🌐 Searching for a working proxy from the list...")
    working = await find_working_proxy()
    if working:
        await message.answer(f"🌐 {t('proxy_working')}: `{working}`", parse_mode="Markdown")
    else:
        await message.answer(t("no_working_proxy"))


@stealth_router.message(Command("proxyfetch"))
async def cmd_proxyfetch(message: types.Message):
    await message.answer(
        "🌐 Fetching public proxy lists. This may take a minute.\n"
        "⚠️ Public proxies are unreliable and may log traffic. "
        "They only hide HTTP(S) recon, not raw nmap/scapy packets."
    )

    if not await scan_lock.acquire("proxyfetch"):
        await message.answer(t("another_scan_running"))
        return

    try:
        working, candidates = await fetch_public_proxy_list(max_test=50, concurrency=10)
        if working:
            proxy_file = DATA_DIR / "proxies.txt"
            proxy_file.parent.mkdir(parents=True, exist_ok=True)
            existing = set()
            if proxy_file.exists():
                existing = {
                    line.strip()
                    for line in proxy_file.read_text(encoding="utf-8").splitlines()
                    if line.strip() and not line.startswith("#")
                }
            # keep existing and append new
            new = [p for p in working if p not in existing]
            with proxy_file.open("a", encoding="utf-8") as fh:
                if new:
                    fh.write("\n".join(new) + "\n")

            await message.answer(
                f"🌐 Fetched `{len(candidates)}` candidates, found `{len(working)}` working.\n"
                f"Added `{len(new)}` new proxies to `data/proxies.txt`.\n"
                f"Total in file: `{len(existing) + len(new)}`",
                parse_mode="Markdown",
            )
        else:
            await message.answer(
                f"❌ No working proxies found from `{len(candidates)}` candidates.\n"
                "Try again later or add your own proxies to data/proxies.txt."
            )
    except Exception as exc:
        logger.exception("proxyfetch failed")
        await message.answer(f"❌ Proxy fetch failed: {exc}")
    finally:
        scan_lock.release()


@stealth_router.message(Command("scapy"))
async def cmd_scapy(message: types.Message):
    args = (message.text or "").split(maxsplit=2)
    if len(args) < 2:
        await message.answer(
            _usage("scapy", "<IP> [ports]") + "\nExamples:\n/scapy 1.1.1.1\n/scapy 1.1.1.1 80,443\n/scapy 1.1.1.1 1-1000"
        )
        return

    try:
        target_ip = validate_ipv4(args[1], allow_private=False)
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    ports = args[2] if len(args) > 2 else "top100"

    if not await scan_lock.acquire(f"scapy {target_ip}"):
        await message.answer(t("another_scan_running"))
        return

    try:
        logger.info("Scapy scan started for %s by admin", target_ip)
        await message.answer(
            f"🕵️ {t('scan_started', target=target_ip)} (ports: `{ports}`)",
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
        await message.answer(_usage("scapyfrag", "<IP> [ports]"))
        return

    try:
        target_ip = validate_ipv4(args[1], allow_private=False)
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    ports = args[2] if len(args) > 2 else "top100"

    if not await scan_lock.acquire(f"scapyfrag {target_ip}"):
        await message.answer(t("another_scan_running"))
        return

    try:
        logger.info("Fragmented Scapy scan started for %s by admin", target_ip)
        await message.answer(
            f"💥 {t('scan_started', target=target_ip)} (fragmented SYN)",
            parse_mode="Markdown",
        )
        output = await scapy_syn_scan(target_ip, port_spec=ports, fragment=True)
        save_report("scapyfrag", target_ip, output)
        await send_report(message, output, prefix=f"💥 Fragmented Scapy scan for `{target_ip}`")
    finally:
        scan_lock.release()


@stealth_router.message(Command("scapydecoy"))
async def cmd_scapydecoy(message: types.Message):
    args = (message.text or "").split(maxsplit=2)
    if len(args) < 2:
        await message.answer(_usage("scapydecoy", "<IP> [ports]") + "\nSends decoy packets from random source IPs.")
        return

    try:
        target_ip = validate_ipv4(args[1], allow_private=False)
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    ports = args[2] if len(args) > 2 else "top100"

    if not await scan_lock.acquire(f"scapydecoy {target_ip}"):
        await message.answer(t("another_scan_running"))
        return

    try:
        logger.info("Decoy Scapy scan started for %s by admin", target_ip)
        await message.answer(
            f"👻 {t('scan_started', target=target_ip)} (with decoys)",
            parse_mode="Markdown",
        )
        output = await scapy_syn_scan(target_ip, port_spec=ports, decoys=3)
        save_report("scapydecoy", target_ip, output)
        await send_report(message, output, prefix=f"👻 Decoy Scapy scan for `{target_ip}`")
    finally:
        scan_lock.release()


@stealth_router.message(Command("evade"))
async def cmd_evade(message: types.Message):
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        await message.answer(_usage("evade", "<IP>") + "\nRuns nmap with extra evasion flags.")
        return

    try:
        target_ip = validate_ipv4(args[1], allow_private=False)
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    if not await scan_lock.acquire(f"evade {target_ip}"):
        await message.answer(t("another_scan_running"))
        return

    try:
        logger.info("Evasive nmap scan started for %s by admin", target_ip)
        await message.answer(
            f"🥷 {t('scan_started', target=target_ip)}",
            parse_mode="Markdown",
        )
        flags = evade_nmap_flags()
        cmd = ["nmap", "-sS", "-T2", "-F"] + flags + [target_ip]
        result = await run_command(cmd, timeout=SCAN_TIMEOUT * 2, cancellable=True)
        output = result.stdout if result.returncode == 0 else result.stderr
        if scan_lock.cancelled:
            output = t("scan_cancelled")
        save_report("evade", target_ip, output)
        await send_report(message, output, prefix=f"🥷 Evasive nmap scan for `{target_ip}`")
    finally:
        scan_lock.release()


_SUBNET_REGEX = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/(\d{1,2})$")


def _validate_subnet(value: str) -> str:
    value = value.strip()
    match = _SUBNET_REGEX.match(value)
    if not match:
        raise ValidationError("Invalid subnet format. Use e.g. 192.168.1.0/24")
    for octet in match.groups()[:4]:
        if int(octet) > 255:
            raise ValidationError("Invalid subnet octet.")
    prefix = int(match.group(5))
    if prefix < 8 or prefix > 30:
        raise ValidationError("Subnet prefix must be between /8 and /30.")
    return value


@stealth_router.message(Command("discover"))
async def cmd_discover(message: types.Message):
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        await message.answer(_usage("discover", "<subnet>") + "\nExample: `/discover 192.168.1.0/24`")
        return

    try:
        subnet = _validate_subnet(args[1])
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    if not await scan_lock.acquire(f"discover {subnet}"):
        await message.answer(t("another_scan_running"))
        return

    try:
        logger.info("Network discovery started for %s by admin", subnet)
        await message.answer(
            f"🗺 {t('network_discovery_started', target=subnet)}",
            parse_mode="Markdown",
        )
        output = await discover_hosts(subnet)
        save_report("discover", subnet.replace("/", "_"), output)
        await send_report(message, output, prefix=f"🗺 Network discovery for `{subnet}`")
    finally:
        scan_lock.release()


@stealth_router.message(Command("vulns"))
async def cmd_vulns(message: types.Message):
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        await message.answer(_usage("vulns", "<target>") + "\nRuns nmap `--script vuln` (safe checks only).")
        return

    try:
        target = validate_ipv4(args[1], allow_private=False)
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    if not await scan_lock.acquire(f"vulns {target}"):
        await message.answer(t("another_scan_running"))
        return

    try:
        logger.info("Vuln scan started for %s by admin", target)
        await message.answer(
            f"🛡 {t('vuln_scan_started', target=target)}\n"
            "This runs safe NSE checks only — no exploitation.",
            parse_mode="Markdown",
        )
        output = await vuln_scan(target)
        save_report("vulns", target, output)
        await send_report(message, output, prefix=f"🛡 Vulnerability scan for `{target}`")
    finally:
        scan_lock.release()


@stealth_router.message(Command("quickvulns"))
async def cmd_quickvulns(message: types.Message):
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        await message.answer(_usage("quickvulns", "<target>") + "\nFast vuln scan on top 100 ports.")
        return

    try:
        target = validate_ipv4(args[1], allow_private=False)
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    if not await scan_lock.acquire(f"quickvulns {target}"):
        await message.answer(t("another_scan_running"))
        return

    try:
        logger.info("Quick vuln scan started for %s by admin", target)
        await message.answer(
            f"🛡 {t('vuln_scan_started', target=target)} (quick, top 100 ports)",
            parse_mode="Markdown",
        )
        output = await quick_vuln_scan(target)
        save_report("quickvulns", target, output)
        await send_report(message, output, prefix=f"🛡 Quick vuln scan for `{target}`")
    finally:
        scan_lock.release()
