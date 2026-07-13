from datetime import datetime, timezone

from aiogram import Router, types
from aiogram.filters import Command

from config import OSINT_TIMEOUT
from services.reports import build_report, save_report, send_report
from services.shell import run_command
from services.validators import ValidationError, validate_domain
from utils.logger import logger

osint_router = Router()


async def _run_osint(domain: str) -> str:
    lines = [
        f"OSINT Report for {domain}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "=" * 40,
        "",
    ]

    # crt.sh
    crt_url = f"https://crt.sh/?q=%.{domain}&output=json"
    result = await run_command(["curl", "-s", "--max-time", "30", crt_url], timeout=OSINT_TIMEOUT)
    lines.append(f"[+] crt.sh lookup ({'OK' if result.returncode == 0 else 'FAILED'})")
    lines.append(result.stdout if result.returncode == 0 else result.stderr)
    lines.append("")

    # whois
    result = await run_command(["whois", domain], timeout=OSINT_TIMEOUT)
    lines.append(f"[+] whois lookup ({'OK' if result.returncode == 0 else 'FAILED'})")
    lines.append(result.stdout if result.returncode == 0 else result.stderr)
    lines.append("")

    # dig ANY
    result = await run_command(["dig", "+short", "ANY", domain], timeout=OSINT_TIMEOUT)
    lines.append(f"[+] dig ANY ({'OK' if result.returncode == 0 else 'FAILED'})")
    lines.append(result.stdout if result.returncode == 0 else result.stderr)
    lines.append("")

    # sublist3r
    result = await run_command(["sublist3r", "-d", domain, "-o", "-"], timeout=OSINT_TIMEOUT)
    lines.append(f"[+] sublist3r ({'OK' if result.returncode == 0 else 'FAILED'})")
    lines.append(result.stdout if result.returncode == 0 else result.stderr)

    return build_report(lines)


@osint_router.message(Command("osint"))
async def cmd_osint(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /osint \u003cdomain\u003e")
        return

    try:
        domain = validate_domain(args[1])
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    logger.info("OSINT started for %s by admin", domain)
    await message.answer(f"🔍 Starting passive OSINT for `{domain}`...", parse_mode="Markdown")

    report = await _run_osint(domain)
    save_report("osint", domain, report)
    await send_report(message, report, prefix=f"🔍 OSINT report for `{domain}`")


@osint_router.message(Command("dns"))
async def cmd_dns(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /dns \u003cdomain\u003e")
        return

    try:
        domain = validate_domain(args[1])
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    logger.info("DNS lookup started for %s by admin", domain)
    await message.answer(f"🌐 Resolving DNS records for `{domain}`...", parse_mode="Markdown")

    lines = [f"DNS Report for {domain}", "=" * 40]
    for qtype in ("A", "MX", "NS", "TXT"):
        result = await run_command(["dig", "+short", qtype, domain], timeout=OSINT_TIMEOUT)
        lines.append(f"\n[+] {qtype} records")
        lines.append(result.stdout if result.returncode == 0 else result.stderr)

    report = build_report(lines)
    save_report("dns", domain, report)
    await send_report(message, report, prefix=f"🌐 DNS report for `{domain}`")


@osint_router.message(Command("subdomains"))
async def cmd_subdomains(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /subdomains \u003cdomain\u003e")
        return

    try:
        domain = validate_domain(args[1])
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    logger.info("Subdomain enumeration started for %s by admin", domain)
    await message.answer(f"🧩 Enumerating subdomains for `{domain}`...", parse_mode="Markdown")

    lines = [f"Subdomain Report for {domain}", "=" * 40]

    crt_url = f"https://crt.sh/?q=%.{domain}&output=json"
    result = await run_command(["curl", "-s", "--max-time", "30", crt_url], timeout=OSINT_TIMEOUT)
    lines.append("\n[+] crt.sh")
    lines.append(result.stdout if result.returncode == 0 else result.stderr)

    result = await run_command(["sublist3r", "-d", domain, "-o", "-"], timeout=OSINT_TIMEOUT)
    lines.append("\n[+] sublist3r")
    lines.append(result.stdout if result.returncode == 0 else result.stderr)

    report = build_report(lines)
    save_report("subdomains", domain, report)
    await send_report(message, report, prefix=f"🧩 Subdomain report for `{domain}`")
