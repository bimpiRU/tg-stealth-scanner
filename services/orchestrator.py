"""Local Ollama/DeepSeek agent orchestrator.

Implements a tiny ReAct loop: the model can call registered tools by emitting
JSON inside ``<tool>...</tool>`` tags. Tool results are appended to the chat
context and sent back to the model.
"""

import json
import re
from typing import Any, Optional

import aiohttp

from config import AGENT_MAX_ITERATIONS, OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TIMEOUT
from services.tools import TOOL_BY_NAME, tools_description
from utils.logger import logger


_SYSTEM_PROMPT = (
    "You are an autonomous cybersecurity assistant running inside a Telegram bot. "
    "You have access to the tools listed below. "
    "Think step by step and decide whether a tool is needed. "
    "If you need a tool, respond ONLY with a JSON object wrapped in \u003ctool\u003e tags:\n"
    "\u003ctool\u003e{\"tool\": \"run_dns\", \"arguments\": {\"domain\": \"example.com\"}}\u003c/tool\u003e\n"
    "If no tool is needed, answer directly in plain text. "
    "Do not combine tool calls and prose in the same message."
)

_TOOL_CALL_RE = re.compile(r"<tool>(.*?)</tool>", re.DOTALL)
_CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
_JSON_OBJ_RE = re.compile(r"\{.*?\}", re.DOTALL)


def _normalize_host(host: str) -> str:
    return host.rstrip("/")


def _build_url(host: str, path: str) -> str:
    return f"{_normalize_host(host)}{path}"


async def is_available() -> bool:
    """Check whether the Ollama server is reachable."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                _build_url(OLLAMA_HOST, "/"),
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                return resp.status in (200, 404)
    except Exception as exc:
        logger.debug("Ollama health check failed: %s", exc)
        return False


async def _chat(messages: list[dict[str, str]]) -> Optional[str]:
    """Send messages to Ollama /api/chat and return the assistant's content."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.3},
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                _build_url(OLLAMA_HOST, "/api/chat"),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=OLLAMA_TIMEOUT),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error("Ollama API error %s: %s", resp.status, body)
                    return f"Ollama API error: {resp.status}\n{body[:500]}"
                data = await resp.json()
                return data.get("message", {}).get("content", "")
    except Exception as exc:
        logger.exception("Ollama request failed")
        return f"Ollama request failed: {exc}"


def _extract_balanced_json(text: str, start: int) -> Optional[str]:
    """Extract a JSON object from text starting at ``start`` using brace balancing."""
    if start >= len(text) or text[start] != "{":
        return None
    balance = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            balance += 1
        elif ch == "}":
            balance -= 1
            if balance == 0:
                return text[start : i + 1]
    return None


def _looks_like_tool_call(obj: dict) -> bool:
    return isinstance(obj, dict) and "tool" in obj and "arguments" in obj


def _parse_tool_call(text: str) -> Optional[dict[str, Any]]:
    """Extract a tool call from model output.

    Tries, in order:
    1. Explicit ``<tool>...</tool>`` tags.
    2. Markdown `` ```json {...} ``` `` code blocks.
    3. Any JSON object containing ``tool`` and ``arguments`` keys.
    """
    # 1. Explicit tool tags
    match = _TOOL_CALL_RE.search(text)
    if match:
        raw = match.group(1).strip()
        try:
            parsed = json.loads(raw)
            if _looks_like_tool_call(parsed):
                return parsed
        except json.JSONDecodeError:
            pass

    # 2. Markdown code blocks
    for block in _CODE_BLOCK_RE.findall(text):
        try:
            parsed = json.loads(block.strip())
            if _looks_like_tool_call(parsed):
                return parsed
        except json.JSONDecodeError:
            continue

    # 3. Any balanced JSON object with tool/arguments keys
    for match in _JSON_OBJ_RE.finditer(text):
        raw = _extract_balanced_json(text, match.start())
        if raw is None:
            continue
        try:
            parsed = json.loads(raw)
            if _looks_like_tool_call(parsed):
                return parsed
        except json.JSONDecodeError:
            continue

    return None


async def _execute_tool(name: str, arguments: dict[str, Any]) -> str:
    tool = TOOL_BY_NAME.get(name)
    if tool is None:
        return f"Unknown tool: {name}"

    runner = tool["runner"]
    try:
        return await runner(**arguments)
    except Exception as exc:
        logger.exception("Tool %s failed", name)
        return f"Tool {name} failed: {exc}"


async def run_agent(user_message: str) -> str:
    """Run the ReAct agent with the registered tools."""
    if not await is_available():
        return (
            "Local AI agent is unavailable.\n"
            "Make sure Ollama is running and reachable at "
            f"{OLLAMA_HOST} (model: {OLLAMA_MODEL})."
        )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": _SYSTEM_PROMPT + "\n\nTools:\n" + tools_description()},
        {"role": "user", "content": user_message},
    ]

    for iteration in range(AGENT_MAX_ITERATIONS):
        response = await _chat(messages)
        if response is None:
            return "Ollama did not return a response."

        tool_call = _parse_tool_call(response)
        if tool_call is None:
            return response

        name = tool_call.get("tool", "")
        arguments = tool_call.get("arguments", {})
        if not isinstance(arguments, dict):
            return f"Invalid tool arguments for {name}: {arguments}"

        logger.info("Agent iteration %s: calling %s(%s)", iteration + 1, name, arguments)
        messages.append({"role": "assistant", "content": response})

        result = await _execute_tool(name, arguments)
        messages.append(
            {
                "role": "user",
                "content": f"Tool result from {name}:\n{result[:4000]}",
            }
        )

    final = await _chat(messages)
    return final or "Agent reached the maximum number of iterations without a final answer."


async def chat(question: str) -> str:
    """Simple conversational call to Ollama without tools."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are a concise cybersecurity assistant for a Telegram bot. "
                "Answer briefly and accurately."
            ),
        },
        {"role": "user", "content": question[:12000]},
    ]
    result = await _chat(messages)
    return result or "Ollama returned an empty response."
