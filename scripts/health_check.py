#!/usr/bin/env python3
"""Simple health check for the bot process inside the container."""

import os
import sys


def check_bot_process() -> bool:
    """Check if the main bot process is running."""
    own_pid = os.getpid()
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        pid = int(entry)
        if pid == own_pid:
            continue
        try:
            cmdline = open(f"/proc/{pid}/cmdline", "rb").read().decode("utf-8", errors="replace")
        except (OSError, PermissionError):
            continue
        if "python" in cmdline and "bot.py" in cmdline:
            return True
    return False


def main() -> int:
    if not check_bot_process():
        print("Bot process not found", file=sys.stderr)
        return 1
    print("Bot process is healthy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
