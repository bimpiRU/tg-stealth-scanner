import json
from typing import Optional

from services.shell import run_command
from services.validators import ValidationError, validate_domain, validate_ipv4


async def ip_info(ip: str, timeout: int = 30) -> str:
    """Fetch public IP geolocation via ip-api.com (free, no key)."""
    result = await run_command(
        ["curl", "-s", f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,query"],
        timeout=timeout,
    )
    if result.returncode != 0:
        return f"Request failed:\n{result.stderr}"
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return f"Invalid response:\n{result.stdout}"

    if data.get("status") != "success":
        return f"API error: {data.get('message', 'unknown')}"

    lines = [
        f"IP: {data.get('query')}",
        f"Country: {data.get('country')} ({data.get('countryCode')})",
        f"Region: {data.get('regionName')}",
        f"City: {data.get('city')} {data.get('zip')}",
        f"Coordinates: {data.get('lat')}, {data.get('lon')}",
        f"Timezone: {data.get('timezone')}",
        f"ISP: {data.get('isp')}",
        f"Org: {data.get('org')}",
        f"AS: {data.get('as')}",
    ]
    return "\n".join(lines)


async def http_headers(domain: str, timeout: int = 30) -> str:
    """Fetch HTTP headers via curl -I."""
    try:
        validate_domain(domain)
    except ValidationError as exc:
        return str(exc)

    result = await run_command(
        ["curl", "-sI", "--max-time", str(timeout), f"http://{domain}"],
        timeout=timeout + 5,
    )
    if result.returncode != 0:
        return f"Request failed:\n{result.stderr}"
    return result.stdout


async def ssl_info(domain: str, timeout: int = 30) -> str:
    """Fetch SSL certificate info via openssl."""
    try:
        validate_domain(domain)
    except ValidationError as exc:
        return str(exc)

    result = await run_command(
        [
            "sh",
            "-c",
            f"echo | openssl s_client -servername {domain} -connect {domain}:443 2>/dev/null | openssl x509 -noout -subject -issuer -dates -serial",
        ],
        timeout=timeout,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return f"Could not retrieve certificate:\n{result.stderr or 'empty output'}"
    return result.stdout


async def wayback_snapshots(domain: str, timeout: int = 30) -> str:
    """Fetch recent Wayback Machine snapshots for a domain."""
    try:
        validate_domain(domain)
    except ValidationError as exc:
        return str(exc)

    url = f"https://web.archive.org/cdx/search/cdx?url={domain}/*&output=json&collapse=urlkey&limit=20"
    result = await run_command(
        ["curl", "-sL", "--max-time", str(timeout), "-A", "tg-stealth-scanner/1.0", url],
        timeout=timeout + 5,
    )
    if result.returncode != 0:
        return f"Request failed:\n{result.stderr}"

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return f"Invalid response:\n{result.stdout[:500]}"

    if not data or len(data) < 2:
        return "No Wayback snapshots found."

    lines = [f"Wayback snapshots for {domain}", "=" * 40]
    # data[0] is header
    for row in data[1:]:
        if len(row) >= 3:
            timestamp, original = row[1], row[2]
            archive_url = f"https://web.archive.org/web/{timestamp}/{original}"
            lines.append(archive_url)

    return "\n".join(lines)


async def ping_host(ip: str, timeout: int = 30) -> str:
    """Run ping -c 4."""
    try:
        validate_ipv4(ip, allow_private=False)
    except ValidationError as exc:
        return str(exc)

    result = await run_command(["ping", "-c", "4", ip], timeout=timeout)
    return result.stdout if result.returncode == 0 else result.stderr


async def traceroute_host(ip: str, timeout: int = 60) -> str:
    """Run traceroute."""
    try:
        validate_ipv4(ip, allow_private=False)
    except ValidationError as exc:
        return str(exc)

    result = await run_command(["traceroute", "-m", "20", ip], timeout=timeout)
    return result.stdout if result.returncode == 0 else result.stderr
