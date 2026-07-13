"""Network discovery and authorized vulnerability scanning.

These functions require explicit target/subnet from the admin and should only
be used on networks you own or have written permission to test.
"""

from services.shell import run_command, scan_lock
from services.validators import ValidationError, validate_ipv4
from utils.logger import logger


async def discover_hosts(subnet: str, timeout: int = 300) -> str:
    """Run nmap ping sweep against an explicit subnet.

    Example subnet: 192.168.1.0/24
    """
    logger.info("Network discovery started for %s", subnet)
    result = await run_command(
        ["nmap", "-sn", "-T3", "--max-retries", "2", subnet],
        timeout=timeout,
        cancellable=True,
    )
    if scan_lock.cancelled:
        return "🛑 Scan cancelled by admin."
    return result.stdout if result.returncode == 0 else result.stderr


async def vuln_scan(target: str, timeout: int = 600) -> str:
    """Run nmap vulnerability NSE scripts against an explicit target.

    Uses safe/vuln categories only — no exploitation.
    """
    logger.info("Vulnerability scan started for %s", target)
    result = await run_command(
        [
            "nmap",
            "-sV",
            "--script", "vuln",
            "--script-args", "unsafe=0",
            "-T3",
            "--max-retries", "2",
            target,
        ],
        timeout=timeout,
        cancellable=True,
    )
    if scan_lock.cancelled:
        return "🛑 Scan cancelled by admin."
    return result.stdout if result.returncode == 0 else result.stderr


async def quick_vuln_scan(target: str, timeout: int = 300) -> str:
    """Faster version: top ports + vuln scripts."""
    logger.info("Quick vuln scan started for %s", target)
    result = await run_command(
        [
            "nmap",
            "-sV",
            "--top-ports", "100",
            "--script", "vuln",
            "--script-args", "unsafe=0",
            "-T4",
            target,
        ],
        timeout=timeout,
        cancellable=True,
    )
    if scan_lock.cancelled:
        return "🛑 Scan cancelled by admin."
    return result.stdout if result.returncode == 0 else result.stderr
