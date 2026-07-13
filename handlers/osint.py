import asyncio
from datetime import datetime, timezone

from aiogram import Router, types
from aiogram.filters import Command

from config import OSINT_TIMEOUT
from handlers._helpers import arg_command
from services.recon import parse_crtsh
from services.reports import build_report, save_report, send_report
from services.shell import run_command
from services.validators import validate_domain
from utils.logger import logger

osint_router = Router()


def _tool_section(title: str, result) -> list[str]:
    ok = result.returncode == 0
    return [
        f"[+] {title} ({'OK' if ok else 'FAILED'})",
        result.stdout if ok else result.stderr,
        "",
    ]


async def _run_osint(domain: str) -> str:
    crt_url = f"https://crt.sh/?q=%.{domain}&output=json"

    # All four lookups are independent — run them concurrently instead of
    # serially (was up to 4 x OSINT_TIMEOUT of wall-clock).
    crt, whois_r, dig_r, sub_r = await asyncio.gather(
        run_command(["curl", "-s", "--max-time", "30", crt_url], timeout=OSINT_TIMEOUT),
        run_command(["whois", domain], timeout=OSINT_TIMEOUT),
        run_command(["dig", "+short", "ANY", domain], timeout=OSINT_TIMEOUT),
        run_command(["sublist3r", "-d", domain, "-o", "-"], timeout=OSINT_TIMEOUT),
    )

    lines = [
        f"OSINT Report for {domain}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "=" * 40,
        "",
        f"[+] crt.sh subdomains ({'OK' if crt.returncode == 0 else 'FAILED'})",
        parse_crtsh(crt.stdout) if crt.returncode == 0 else crt.stderr,
        "",
    ]
    lines += _tool_section("whois lookup", whois_r)
    lines += _tool_section("dig ANY", dig_r)
    lines += _tool_section("sublist3r", sub_r)

    return build_report(lines)


@osint_router.message(Command("osint"))
@arg_command(validate_domain, usage="Usage: /osint <domain>")
async def cmd_osint(message: types.Message, domain: str):
    logger.info("OSINT started for %s by admin", domain)
    await message.answer(f"🔍 Starting passive OSINT for `{domain}`...", parse_mode="Markdown")

    report = await _run_osint(domain)
    save_report("osint", domain, report)
    await send_report(message, report, prefix=f"🔍 OSINT report for `{domain}`")


@osint_router.message(Command("dns"))
@arg_command(validate_domain, usage="Usage: /dns <domain>")
async def cmd_dns(message: types.Message, domain: str):
    logger.info("DNS lookup started for %s by admin", domain)
    await message.answer(f"🌐 Resolving DNS records for `{domain}`...", parse_mode="Markdown")

    # A/MX/NS/TXT are independent lookups — fan them out concurrently.
    results = await asyncio.gather(
        *(
            run_command(["dig", "+short", qtype, domain], timeout=OSINT_TIMEOUT)
            for qtype in ("A", "MX", "NS", "TXT")
        )
    )

    lines = [f"DNS Report for {domain}", "=" * 40]
    for qtype, result in zip(("A", "MX", "NS", "TXT"), results):
        lines.append(f"\n[+] {qtype} records")
        lines.append(result.stdout if result.returncode == 0 else result.stderr)

    report = build_report(lines)
    save_report("dns", domain, report)
    await send_report(message, report, prefix=f"🌐 DNS report for `{domain}`")


@osint_router.message(Command("subdomains"))
@arg_command(validate_domain, usage="Usage: /subdomains <domain>")
async def cmd_subdomains(message: types.Message, domain: str):
    logger.info("Subdomain enumeration started for %s by admin", domain)
    await message.answer(f"🧩 Enumerating subdomains for `{domain}`...", parse_mode="Markdown")

    crt_url = f"https://crt.sh/?q=%.{domain}&output=json"
    crt, sub = await asyncio.gather(
        run_command(["curl", "-s", "--max-time", "30", crt_url], timeout=OSINT_TIMEOUT),
        run_command(["sublist3r", "-d", domain, "-o", "-"], timeout=OSINT_TIMEOUT),
    )

    lines = [f"Subdomain Report for {domain}", "=" * 40]
    lines.append("\n[+] crt.sh")
    lines.append(parse_crtsh(crt.stdout) if crt.returncode == 0 else crt.stderr)
    lines.append("\n[+] sublist3r")
    lines.append(sub.stdout if sub.returncode == 0 else sub.stderr)

    report = build_report(lines)
    save_report("subdomains", domain, report)
    await send_report(message, report, prefix=f"🧩 Subdomain report for `{domain}`")
