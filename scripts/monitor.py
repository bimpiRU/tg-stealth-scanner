#!/usr/bin/env python3
"""External health monitor for the tg-stealth-scanner container.

Can be scheduled via cron / Windows Task Scheduler / systemd timer.
Sends a Telegram message to ADMIN_ID if the container is down or unhealthy.

Example cron (every 5 minutes):
    */5 * * * * cd /path/to/BotCreate/tg_stealth_scanner && python scripts/monitor.py
"""

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path


def load_env() -> dict:
    env = {}
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key] = value.strip().strip('"').strip("'")
    return env


def send_telegram(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()


def container_status(name: str = "tg-stealth-scanner") -> tuple[str, str]:
    """Return (state, health) for the container."""
    try:
        state = subprocess.check_output(
            ["docker", "inspect", "-f", "{{.State.Status}}", name],
            stderr=subprocess.STDOUT,
            text=True,
        ).strip()
    except subprocess.CalledProcessError as exc:
        return ("missing", exc.output.strip())

    try:
        health = subprocess.check_output(
            ["docker", "inspect", "-f", "{{.State.Health.Status}}", name],
            stderr=subprocess.STDOUT,
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        health = "unknown"

    return (state, health)


def main() -> int:
    env = load_env()
    token = env.get("BOT_TOKEN", os.getenv("BOT_TOKEN", ""))
    admin_id = env.get("ADMIN_ID", os.getenv("ADMIN_ID", ""))
    container_name = env.get("CONTAINER_NAME", os.getenv("CONTAINER_NAME", "tg-stealth-scanner"))

    if not token or not admin_id:
        print("BOT_TOKEN and ADMIN_ID must be set", file=sys.stderr)
        return 1

    state, health = container_status(container_name)

    if state != "running":
        send_telegram(
            token,
            admin_id,
            f"🚨 *tg-stealth-scanner monitor*\n\nContainer `{container_name}` is *{state}*.",
        )
        return 1

    if health and health not in ("", "healthy", "unknown"):
        send_telegram(
            token,
            admin_id,
            f"⚠️ *tg-stealth-scanner monitor*\n\nContainer `{container_name}` is `{state}` but health is `{health}`.",
        )
        return 1

    print(f"Container {container_name}: {state}, health: {health}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
