from aiogram import Router, types
from aiogram.filters import Command

from config import OSINT_TIMEOUT
from services.recon import http_headers, ip_info, ping_host, ssl_info, traceroute_host, wayback_snapshots
from services.reports import save_report, send_report
from services.validators import ValidationError, validate_domain, validate_ipv4
from utils.logger import logger

recon_router = Router()


@recon_router.message(Command("wayback"))
async def cmd_wayback(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /wayback \u003cdomain\u003e")
        return

    try:
        domain = validate_domain(args[1])
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    logger.info("Wayback snapshots requested for %s", domain)
    await message.answer(f"📚 Fetching Wayback snapshots for `{domain}`...", parse_mode="Markdown")

    output = await wayback_snapshots(domain, timeout=OSINT_TIMEOUT)
    save_report("wayback", domain, output)
    await send_report(message, output, prefix=f"📚 Wayback snapshots for `{domain}`")


@recon_router.message(Command("ipinfo"))
async def cmd_ipinfo(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /ipinfo \u003cIP\u003e")
        return

    try:
        target_ip = validate_ipv4(args[1], allow_private=False)
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    logger.info("IP info requested for %s", target_ip)
    await message.answer(f"🌍 Getting info for `{target_ip}`...", parse_mode="Markdown")

    output = await ip_info(target_ip, timeout=OSINT_TIMEOUT)
    save_report("ipinfo", target_ip, output)
    await send_report(message, output, prefix=f"🌍 IP info for `{target_ip}`")


@recon_router.message(Command("headers"))
async def cmd_headers(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /headers \u003cdomain\u003e")
        return

    try:
        domain = validate_domain(args[1])
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    logger.info("HTTP headers requested for %s", domain)
    await message.answer(f"📡 Fetching headers for `{domain}`...", parse_mode="Markdown")

    output = await http_headers(domain, timeout=OSINT_TIMEOUT)
    save_report("headers", domain, output)
    await send_report(message, output, prefix=f"📡 Headers for `{domain}`")


@recon_router.message(Command("ssl"))
async def cmd_ssl(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /ssl \u003cdomain\u003e")
        return

    try:
        domain = validate_domain(args[1])
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    logger.info("SSL info requested for %s", domain)
    await message.answer(f"🔒 Fetching SSL certificate for `{domain}`...", parse_mode="Markdown")

    output = await ssl_info(domain, timeout=OSINT_TIMEOUT)
    save_report("ssl", domain, output)
    await send_report(message, output, prefix=f"🔒 SSL info for `{domain}`")


@recon_router.message(Command("ping"))
async def cmd_ping(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /ping \u003cIP\u003e")
        return

    try:
        target_ip = validate_ipv4(args[1], allow_private=False)
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    logger.info("Ping requested for %s", target_ip)
    await message.answer(f"🏓 Pinging `{target_ip}`...", parse_mode="Markdown")

    output = await ping_host(target_ip, timeout=OSINT_TIMEOUT)
    save_report("ping", target_ip, output)
    await send_report(message, output, prefix=f"🏓 Ping result for `{target_ip}`")


@recon_router.message(Command("traceroute"))
async def cmd_traceroute(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /traceroute \u003cIP\u003e")
        return

    try:
        target_ip = validate_ipv4(args[1], allow_private=False)
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    logger.info("Traceroute requested for %s", target_ip)
    await message.answer(f"🛤 Traceroute to `{target_ip}`...", parse_mode="Markdown")

    output = await traceroute_host(target_ip, timeout=OSINT_TIMEOUT)
    save_report("traceroute", target_ip, output)
    await send_report(message, output, prefix=f"🛤 Traceroute to `{target_ip}`")
