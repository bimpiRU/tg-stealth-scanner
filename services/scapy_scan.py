"""Scapy-based stealth port scanner.

Separate from services/shell.py so it can be added/removed independently.
Requires root + NET_RAW (already granted in docker-compose.yml).
"""

import asyncio
import random
from typing import Optional

from scapy.all import IP, TCP, RandIP, conf, sr1

from services.validators import ValidationError, validate_ipv4
from utils.logger import logger

# Disable scapy verbosity to stdout
conf.verb = 0


_MAX_SCAPY_PORTS = 10_000


def _parse_ports(port_spec: str) -> list[int]:
    """Parse '80', '80,443', '1-1000' into a list of ports."""
    ports: set[int] = set()
    for part in port_spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            ports.update(range(int(start), int(end) + 1))
        elif part.isdigit():
            ports.add(int(part))
    if len(ports) > _MAX_SCAPY_PORTS:
        raise ValueError(f"Too many ports: {len(ports)} (max {_MAX_SCAPY_PORTS}).")
    return sorted(ports)


def _scapy_syn_scan(
    target_ip: str,
    ports: list[int],
    timeout: float = 2.0,
    source_port: Optional[int] = None,
    decoys: int = 0,
    fragment: bool = False,
) -> str:
    """Run a Scapy SYN scan synchronously (executed in thread pool).

    Args:
        target_ip: validated IPv4 address
        ports: list of target ports
        timeout: seconds to wait for each probe
        source_port: fixed source port or None for random
        decoys: number of decoy source IPs to send alongside real probes
        fragment: split IP packets into small fragments
    """
    open_ports: list[int] = []
    closed_ports: list[int] = []
    filtered_ports: list[int] = []

    sport = source_port or random.randint(40000, 65000)

    for dport in ports:
        # Base packet
        ip = IP(dst=target_ip, flags="MF" if fragment else 0)
        tcp = TCP(sport=sport, dport=dport, flags="S")
        pkt = ip / tcp

        probes = [pkt]
        if decoys > 0:
            for _ in range(decoys):
                decoy_ip = IP(dst=target_ip, src=RandIP())
                probes.append(decoy_ip / tcp)

        answered = False
        for probe in probes:
            resp = sr1(probe, timeout=timeout, verbose=0)
            if resp is None:
                continue
            answered = True
            if resp.haslayer(TCP):
                flags = resp[TCP].flags
                if "SA" in str(flags):
                    open_ports.append(dport)
                elif "RA" in str(flags) or "R" in str(flags):
                    closed_ports.append(dport)
                else:
                    filtered_ports.append(dport)

        if not answered:
            filtered_ports.append(dport)

    lines = [f"Scapy SYN scan for {target_ip}", "=" * 40]
    lines.append(f"Ports scanned: {len(ports)}")
    lines.append(f"Open ({len(open_ports)}): {', '.join(map(str, open_ports)) or 'none'}")
    lines.append(f"Closed ({len(closed_ports)}): {', '.join(map(str, closed_ports)) or 'none'}")
    lines.append(f"Filtered/no-response ({len(filtered_ports)}): {', '.join(map(str, filtered_ports)) or 'none'}")
    return "\n".join(lines)


async def scapy_syn_scan(
    target: str,
    port_spec: str = "top100",
    timeout: float = 2.0,
    source_port: Optional[int] = None,
    decoys: int = 0,
    fragment: bool = False,
) -> str:
    """Async wrapper around the synchronous Scapy scan."""
    try:
        target_ip = validate_ipv4(target, allow_private=False)
    except ValidationError as exc:
        return f"❌ {exc}"

    if port_spec == "top100":
        ports = [
            21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445,
            993, 995, 1723, 3306, 3389, 5900, 8080, 8443, 8888, 9000,
            9090, 9200, 9300, 10000, 27017, 5432, 6379, 11211, 5000,
            4567, 3000, 8000, 8081, 8082, 8083, 8084, 8085, 8086, 8087,
            8088, 8089, 8090, 8834, 50000, 50001, 50070, 50030, 50060,
            873, 2082, 2083, 2086, 2087, 2095, 2096, 2077, 2078, 3128,
            8008, 8009, 8010, 8880, 9001, 9002, 9003, 9418, 1080, 1025,
            1026, 1027, 1028, 1029, 1030, 1433, 1521, 2638, 3050, 3367,
            3690, 4333, 5100, 5433, 5555, 5666, 6000, 6001, 6377, 7001,
            7002, 9042, 9160, 9999, 10050, 10051, 12345, 31337,
        ]
    else:
        try:
            ports = _parse_ports(port_spec)
        except ValueError:
            return f"❌ Invalid port spec: {port_spec}. Use e.g. 80,443 or 1-1000"

    if not ports:
        return "❌ No ports to scan."

    logger.info("Scapy SYN scan started for %s ports:%s", target_ip, ports)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _scapy_syn_scan,
        target_ip,
        ports,
        timeout,
        source_port,
        decoys,
        fragment,
    )
