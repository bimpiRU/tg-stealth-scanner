"""Tool registry for the local Ollama/DeepSeek agent.

Each tool is a dict with metadata plus an async runner. Runners persist results
via ``reports.save_report(..., save_to_db=True)`` and return a short text summary.
"""

import asyncio
import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from config import OSINT_TIMEOUT, SCAN_TIMEOUT
from services.recon import ip_info, parse_crtsh
from services.reports import build_report, save_report
from services.shell import run_command
from services.validators import ValidationError, validate_domain, validate_ipv4
from utils.logger import logger


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _graceful_missing(stderr: str, tool: str) -> str:
    """Return a friendly message when an external tool binary is missing."""
    return (
        f"{tool} is not installed or not in PATH.\n"
        f"Install it in the Docker image to enable this tool.\n"
        f"Error: {stderr[:300]}"
    )


def _looks_like_missing(stderr: str) -> bool:
    lowered = stderr.lower()
    return any(
        phrase in lowered
        for phrase in ("not found", "no such file", "command not found", "cannot find")
    )


async def _run_shell_tool(cmd: list[str], timeout: int, label: str) -> str:
    try:
        result = await run_command(cmd, timeout=timeout)
    except (FileNotFoundError, OSError) as exc:
        return _graceful_missing(str(exc), label)

    if result.returncode != 0:
        if _looks_like_missing(result.stderr):
            return _graceful_missing(result.stderr, label)
        return f"{label} failed:\n{result.stderr}"
    return result.stdout


async def run_osint(domain: str) -> str:
    """Passive OSINT: crt.sh, whois, dig, sublist3r."""
    try:
        domain = validate_domain(domain)
    except ValidationError as exc:
        return str(exc)

    crt_url = f"https://crt.sh/?q=%.{domain}&output=json"
    crt, whois_r, dig_r, sub_r = await asyncio.gather(
        run_command(["curl", "-s", "--max-time", "30", crt_url], timeout=OSINT_TIMEOUT),
        run_command(["whois", domain], timeout=OSINT_TIMEOUT),
        run_command(["dig", "+short", "ANY", domain], timeout=OSINT_TIMEOUT),
        run_command(["sublist3r", "-d", domain, "-o", "-"], timeout=OSINT_TIMEOUT),
    )

    lines = [
        f"OSINT Report for {domain}",
        f"Generated: {_now()}",
        "=" * 40,
        "",
        f"[+] crt.sh subdomains ({'OK' if crt.returncode == 0 else 'FAILED'})",
        parse_crtsh(crt.stdout) if crt.returncode == 0 else crt.stderr,
        "",
        f"[+] whois lookup ({'OK' if whois_r.returncode == 0 else 'FAILED'})",
        whois_r.stdout if whois_r.returncode == 0 else whois_r.stderr,
        "",
        f"[+] dig ANY ({'OK' if dig_r.returncode == 0 else 'FAILED'})",
        dig_r.stdout if dig_r.returncode == 0 else dig_r.stderr,
        "",
        f"[+] sublist3r ({'OK' if sub_r.returncode == 0 else 'FAILED'})",
        sub_r.stdout if sub_r.returncode == 0 else sub_r.stderr,
    ]
    report = build_report(lines)
    save_report("osint", domain, report, save_to_db=True, target_type="domain")
    return f"OSINT completed for {domain}.\n{report[:1000]}"


async def run_subdomain_enum(domain: str) -> str:
    """Subdomain enumeration via crt.sh and sublist3r."""
    try:
        domain = validate_domain(domain)
    except ValidationError as exc:
        return str(exc)

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
    save_report("subdomains", domain, report, save_to_db=True, target_type="domain")
    return f"Subdomain enumeration completed for {domain}.\n{report[:1000]}"


async def run_dns(domain: str) -> str:
    """DNS A/MX/NS/TXT lookup."""
    try:
        domain = validate_domain(domain)
    except ValidationError as exc:
        return str(exc)

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
    save_report("dns", domain, report, save_to_db=True, target_type="domain")
    return f"DNS lookup completed for {domain}.\n{report[:1000]}"


async def run_ip_info(ip: str) -> str:
    """Public IP geolocation."""
    try:
        validate_ipv4(ip, allow_private=False)
    except ValidationError as exc:
        return str(exc)

    report = await ip_info(ip)
    save_report("ipinfo", ip, report, save_to_db=True, target_type="ip")
    return f"IP info for {ip}:\n{report}"


async def run_scan(ip: str) -> str:
    """Stealth nmap SYN scan of an IP."""
    try:
        validate_ipv4(ip, allow_private=False)
    except ValidationError as exc:
        return str(exc)

    result = await run_command(
        ["nmap", "-sS", "-T2", "-F", ip],
        timeout=SCAN_TIMEOUT,
    )
    report = result.stdout if result.returncode == 0 else result.stderr
    save_report("scan", ip, report, save_to_db=True, target_type="ip")
    return f"Stealth scan completed for {ip}.\n{report[:1500]}"


async def run_discover(subnet: str) -> str:
    """nmap host discovery on a subnet."""
    result = await run_command(
        ["nmap", "-sn", "-T3", "--max-retries", "2", subnet],
        timeout=300,
    )
    report = result.stdout if result.returncode == 0 else result.stderr
    safe_name = subnet.replace("/", "_")
    save_report("discover", safe_name, report, save_to_db=True, target_type="subnet")
    return f"Host discovery completed for {subnet}.\n{report[:1500]}"


async def run_vulns(ip: str) -> str:
    """nmap vulnerability NSE scan on an IP."""
    try:
        validate_ipv4(ip, allow_private=False)
    except ValidationError as exc:
        return str(exc)

    result = await run_command(
        [
            "nmap",
            "-sV",
            "--script", "vuln",
            "--script-args", "unsafe=0",
            "-T3",
            "--max-retries", "2",
            ip,
        ],
        timeout=600,
    )
    report = result.stdout if result.returncode == 0 else result.stderr
    save_report("vulns", ip, report, save_to_db=True, target_type="ip")
    return f"Vulnerability scan completed for {ip}.\n{report[:1500]}"


async def run_sherlock(username: str) -> str:
    """Run Sherlock username OSINT."""
    result = await _run_shell_tool(
        ["sherlock", username, "--print-all", "--timeout", "10"],
        timeout=OSINT_TIMEOUT,
        label="sherlock",
    )
    save_report("sherlock", username, result, save_to_db=True, target_type="username")
    return f"Sherlock result for {username}:\n{result[:1500]}"


async def run_maigret(username: str) -> str:
    """Run Maigret username OSINT."""
    result = await _run_shell_tool(
        ["maigret", username, "--timeout", "10", "--no-recursive"],
        timeout=OSINT_TIMEOUT,
        label="maigret",
    )
    save_report("maigret", username, result, save_to_db=True, target_type="username")
    return f"Maigret result for {username}:\n{result[:1500]}"


async def run_theharvester(domain: str) -> str:
    """Run theHarvester email/subdomain enumeration."""
    try:
        domain = validate_domain(domain)
    except ValidationError as exc:
        return str(exc)

    result = await _run_shell_tool(
        ["theHarvester", "-d", domain, "-b", "all"],
        timeout=OSINT_TIMEOUT,
        label="theHarvester",
    )
    save_report("theharvester", domain, result, save_to_db=True, target_type="domain")
    return f"theHarvester result for {domain}:\n{result[:1500]}"


_SELECT_RE = re.compile(r"^\s*SELECT\s+", re.IGNORECASE)
_FORBIDDEN_RE = re.compile(
    r"\b(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|TRUNCATE|REPLACE|ATTACH|DETACH|PRAGMA)\b",
    re.IGNORECASE,
)


async def query_db(sql: str) -> str:
    """Run a read-only SELECT query against the local SQLite DB."""
    from services.db import DB_PATH

    sql = sql.strip()
    if not _SELECT_RE.match(sql):
        return "Only SELECT statements are allowed."
    if _FORBIDDEN_RE.search(sql):
        return "Forbidden keyword detected in query."

    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql).fetchall()
            data = [dict(row) for row in rows]
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
    except Exception as exc:
        return f"Database query failed: {exc}"


Tool = dict[str, Any]


def _make_tool(
    name: str,
    description: str,
    parameters: dict[str, Any],
    runner: Callable[..., Any],
) -> Tool:
    return {
        "name": name,
        "description": description,
        "parameters": parameters,
        "runner": runner,
    }


TOOLS: list[Tool] = [
    _make_tool(
        "run_osint",
        "Passive OSINT on a domain (crt.sh, whois, dig, sublist3r).",
        {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Domain to investigate, e.g. example.com",
                }
            },
            "required": ["domain"],
        },
        run_osint,
    ),
    _make_tool(
        "run_subdomain_enum",
        "Enumerate subdomains for a domain via crt.sh and sublist3r.",
        {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Domain to enumerate, e.g. example.com",
                }
            },
            "required": ["domain"],
        },
        run_subdomain_enum,
    ),
    _make_tool(
        "run_dns",
        "Lookup DNS A/MX/NS/TXT records for a domain.",
        {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Domain to resolve, e.g. example.com",
                }
            },
            "required": ["domain"],
        },
        run_dns,
    ),
    _make_tool(
        "run_ip_info",
        "Fetch geolocation and ISP info for a public IPv4 address.",
        {
            "type": "object",
            "properties": {
                "ip": {
                    "type": "string",
                    "description": "Public IPv4 address, e.g. 1.1.1.1",
                }
            },
            "required": ["ip"],
        },
        run_ip_info,
    ),
    _make_tool(
        "run_scan",
        "Run a stealth nmap SYN scan on an IP.",
        {
            "type": "object",
            "properties": {
                "ip": {
                    "type": "string",
                    "description": "Public IPv4 address to scan.",
                }
            },
            "required": ["ip"],
        },
        run_scan,
    ),
    _make_tool(
        "run_discover",
        "Run nmap host discovery on a subnet.",
        {
            "type": "object",
            "properties": {
                "subnet": {
                    "type": "string",
                    "description": "Subnet in CIDR notation, e.g. 192.168.1.0/24",
                }
            },
            "required": ["subnet"],
        },
        run_discover,
    ),
    _make_tool(
        "run_vulns",
        "Run nmap vulnerability NSE scripts on an IP (safe checks only).",
        {
            "type": "object",
            "properties": {
                "ip": {
                    "type": "string",
                    "description": "Public IPv4 address to scan.",
                }
            },
            "required": ["ip"],
        },
        run_vulns,
    ),
    _make_tool(
        "run_sherlock",
        "Run Sherlock username OSINT lookup.",
        {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Username to investigate.",
                }
            },
            "required": ["username"],
        },
        run_sherlock,
    ),
    _make_tool(
        "run_maigret",
        "Run Maigret username OSINT lookup.",
        {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Username to investigate.",
                }
            },
            "required": ["username"],
        },
        run_maigret,
    ),
    _make_tool(
        "run_theharvester",
        "Run theHarvester email/subdomain enumeration on a domain.",
        {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Domain to investigate, e.g. example.com",
                }
            },
            "required": ["domain"],
        },
        run_theharvester,
    ),
    _make_tool(
        "query_db",
        "Run a read-only SELECT query against the local findings database.",
        {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "A SELECT SQL statement, e.g. SELECT * FROM findings LIMIT 10",
                }
            },
            "required": ["sql"],
        },
        query_db,
    ),
]

TOOL_BY_NAME = {tool["name"]: tool for tool in TOOLS}


def tools_description() -> str:
    """Return a compact JSON description of all tools for the LLM prompt."""
    return json.dumps(
        [
            {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            }
            for tool in TOOLS
        ],
        indent=2,
    )
