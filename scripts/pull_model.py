#!/usr/bin/env python3
"""Pull the configured Ollama model and wait until the service is ready.

Uses only stdlib so it does not add extra Python dependencies.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import NoReturn


def get_env() -> tuple[str, str, int]:
    host = os.getenv("OLLAMA_HOST", "http://ollama:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "deepseek-r1:7b")
    timeout = int(os.getenv("OLLAMA_TIMEOUT", "120"))
    return host, model, timeout


def wait_for_ollama(host: str, timeout: int) -> bool:
    """Poll /api/tags until Ollama responds or the timeout expires."""
    deadline = time.monotonic() + timeout
    url = f"{host}/api/tags"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    return True
        except urllib.error.URLError:
            pass
        except Exception:
            pass
        time.sleep(2)
    return False


def pull_model(host: str, model: str, timeout: int) -> bool:
    """POST /api/pull for the given model and stream the response to completion."""
    url = f"{host}/api/pull"
    payload = json.dumps({"name": model}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            # Response is NDJSON; read it fully to ensure the pull completes.
            for line in response:
                line = line.decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if data.get("error"):
                    print(f"Pull error: {data['error']}", file=sys.stderr)
                    return False
                status = data.get("status", "")
                if status:
                    print(f"ollama pull: {status}")
        return True
    except urllib.error.HTTPError as exc:
        print(f"HTTP error while pulling model: {exc.code} {exc.reason}", file=sys.stderr)
        return False
    except urllib.error.URLError as exc:
        print(f"Connection error while pulling model: {exc.reason}", file=sys.stderr)
        return False


def main() -> NoReturn:
    host, model, timeout = get_env()
    print(f"Waiting for Ollama at {host} (timeout {timeout}s)...")
    if not wait_for_ollama(host, timeout):
        print(f"Ollama did not become ready at {host} within {timeout}s", file=sys.stderr)
        sys.exit(1)

    print(f"Pulling model '{model}'...")
    if pull_model(host, model, timeout):
        print(f"Model '{model}' is ready.")
        sys.exit(0)
    else:
        print(f"Failed to pull model '{model}'.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
