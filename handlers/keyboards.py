"""Inline-menu UI layer: typed callback payloads, keyboards, hints.

Pure presentation — no service imports, no handler logic. ``handlers/admin.py``
wires these into routers. Kept separate so admin.py stays about routing and
service commands rather than button layout.
"""

from aiogram import types
from aiogram.filters.callback_data import CallbackData


# Typed callback payloads replace ad-hoc "prefix:value" strings parsed by hand.
class Nav(CallbackData, prefix="nav"):
    """Navigate the menu tree. ``to`` is one of the menu screens."""

    to: str  # main | osint | scan | network | tools | stealth | help


class Hint(CallbackData, prefix="hint"):
    """Show usage hint for a command. ``key`` indexes ``HINTS``."""

    key: str


class Run(CallbackData, prefix="run"):
    """Run a no-argument command directly from a button. ``key`` names it."""

    key: str


def main_menu_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="🔍 OSINT", callback_data=Nav(to="osint").pack()),
                types.InlineKeyboardButton(text="🛰 Scan", callback_data=Nav(to="scan").pack()),
            ],
            [
                types.InlineKeyboardButton(text="🌐 Network", callback_data=Nav(to="network").pack()),
                types.InlineKeyboardButton(text="🤖 Agent", callback_data="run_agent"),
            ],
            [
                types.InlineKeyboardButton(text="🧰 Tools", callback_data=Nav(to="tools").pack()),
                types.InlineKeyboardButton(text="⚙️ Advanced", callback_data=Nav(to="stealth").pack()),
            ],
            [
                types.InlineKeyboardButton(text="ℹ️ Status", callback_data=Run(key="status").pack()),
                types.InlineKeyboardButton(text="📖 Help", callback_data=Nav(to="help").pack()),
            ],
            [
                types.InlineKeyboardButton(text="⚠️ Legal", callback_data=Run(key="about").pack()),
            ],
        ]
    )


def _back_button() -> list[types.InlineKeyboardButton]:
    return [types.InlineKeyboardButton(text="⬅️ Back", callback_data=Nav(to="main").pack())]


def _osint_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="🔍 /osint", callback_data=Hint(key="osint").pack()),
                types.InlineKeyboardButton(text="🌐 /dns", callback_data=Hint(key="dns").pack()),
            ],
            [
                types.InlineKeyboardButton(text="🧩 /subdomains", callback_data=Hint(key="subdomains").pack()),
                types.InlineKeyboardButton(text="📡 /headers", callback_data=Hint(key="headers").pack()),
            ],
            _back_button(),
        ]
    )


def _scan_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="🛰 /scan", callback_data=Hint(key="scan").pack()),
                types.InlineKeyboardButton(text="🚀 /scanfull", callback_data=Hint(key="scanfull").pack()),
            ],
            _back_button(),
        ]
    )


def _network_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="🌍 /ipinfo", callback_data=Hint(key="ipinfo").pack()),
                types.InlineKeyboardButton(text="🏓 /ping", callback_data=Hint(key="ping").pack()),
            ],
            _back_button(),
        ]
    )


def _tools_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="🔑 /password", callback_data=Run(key="password").pack()),
                types.InlineKeyboardButton(text="🆔 /uuid", callback_data=Run(key="uuid").pack()),
            ],
            [
                types.InlineKeyboardButton(text="🔐 /hash", callback_data=Hint(key="hash").pack()),
                types.InlineKeyboardButton(text="🔁 /b64", callback_data=Hint(key="b64").pack()),
            ],
            [
                types.InlineKeyboardButton(text="🔁 /b64decode", callback_data=Hint(key="b64decode").pack()),
                types.InlineKeyboardButton(text="🔗 /urlencode", callback_data=Hint(key="urlencode").pack()),
            ],
            [
                types.InlineKeyboardButton(text="📧 /email", callback_data=Hint(key="email").pack()),
                types.InlineKeyboardButton(text="🌤 /weather", callback_data=Hint(key="weather").pack()),
            ],
            [
                types.InlineKeyboardButton(text="🕒 /timestamp", callback_data=Run(key="timestamp").pack()),
                types.InlineKeyboardButton(text="🧠 /summary", callback_data=Run(key="summary").pack()),
            ],
            _back_button(),
        ]
    )


def _stealth_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="🕵️ /scapy", callback_data=Hint(key="scapy").pack()),
                types.InlineKeyboardButton(text="💥 /scapyfrag", callback_data=Hint(key="scapyfrag").pack()),
            ],
            [
                types.InlineKeyboardButton(text="👻 /scapydecoy", callback_data=Hint(key="scapydecoy").pack()),
                types.InlineKeyboardButton(text="🥷 /evade", callback_data=Hint(key="evade").pack()),
            ],
            [
                types.InlineKeyboardButton(text="🗺 /discover", callback_data=Hint(key="discover").pack()),
                types.InlineKeyboardButton(text="🛡 /vulns", callback_data=Hint(key="vulns").pack()),
            ],
            [
                types.InlineKeyboardButton(text="🌐 /proxyinfo", callback_data=Run(key="proxyinfo").pack()),
                types.InlineKeyboardButton(text="🧪 /proxytest", callback_data=Run(key="proxytest").pack()),
            ],
            [
                types.InlineKeyboardButton(text="🔍 /proxyfind", callback_data=Run(key="proxyfind").pack()),
                types.InlineKeyboardButton(text="🌍 /proxyfetch", callback_data=Run(key="proxyfetch").pack()),
            ],
            _back_button(),
        ]
    )


HINTS = {
    "osint": "🔍 Type: `/osint <domain>`\nExample: `/osint example.com`",
    "dns": "🌐 Type: `/dns <domain>`\nExample: `/dns example.com`",
    "subdomains": "🧩 Type: `/subdomains <domain>`\nExample: `/subdomains example.com`",
    "headers": "📡 Type: `/headers <domain>`\nExample: `/headers example.com`",
    "ssl": "🔒 Type: `/ssl <domain>`\nExample: `/ssl example.com`",
    "wayback": "📚 Type: `/wayback <domain>`\nExample: `/wayback example.com`",
    "scan": "🛰 Type: `/scan <IP>`\nExample: `/scan 1.1.1.1`",
    "scanfull": "🚀 Type: `/scanfull <IP>`\nExample: `/scanfull 1.1.1.1`",
    "ipinfo": "🌍 Type: `/ipinfo <IP>`\nExample: `/ipinfo 1.1.1.1`",
    "ping": "🏓 Type: `/ping <IP>`\nExample: `/ping 1.1.1.1`",
    "traceroute": "🛤 Type: `/traceroute <IP>`\nExample: `/traceroute 1.1.1.1`",
    "reverseip": "🔄 Type: `/reverseip <IP>`\nExample: `/reverseip 1.1.1.1`",
    "hash": "🔐 Type: `/hash <text>`\nExample: `/hash hello`",
    "b64": "🔁 Type: `/b64 <text>`\nExample: `/b64 hello`",
    "b64decode": "🔁 Type: `/b64decode <base64>`\nExample: `/b64decode aGVsbG8=`",
    "urlencode": "🔗 Type: `/urlencode <text>`\nExample: `/urlencode hello world`",
    "email": "📧 Type: `/email <email>`\nExample: `/email user@example.com`",
    "weather": "🌤 Type: `/weather <city>`\nExample: `/weather Tashkent`",
    "scapy": "🕵️ Type: `/scapy <IP> [ports]`\nExamples:\n/scapy 1.1.1.1\n/scapy 1.1.1.1 80,443\n/scapy 1.1.1.1 1-1000",
    "scapyfrag": "💥 Type: `/scapyfrag <IP> [ports]`\nFragmented SYN scan to evade simple IDS.",
    "scapydecoy": "👻 Type: `/scapydecoy <IP> [ports]`\nSends decoy packets from random source IPs.",
    "evade": "🥷 Type: `/evade <IP>`\nnmap with randomize-hosts, spoof-mac, source-port, data-length.",
    "discover": "🗺 Type: `/discover <subnet>`\nExample: `/discover 192.168.1.0/24`",
    "vulns": "🛡 Type: `/vulns <target>`\nRuns nmap `--script vuln` (safe checks only).",
    "proxyfetch": "🌍 Type: `/proxyfetch`\nFetches public proxy lists, tests them and saves working ones to data/proxies.txt.",
}

# screen key -> (markdown text, keyboard builder)
NAV_SCREENS = {
    "osint": ("🔍 *OSINT menu*\n\nBasic passive recon. More tools in /help.", _osint_keyboard),
    "scan": (
        "🛰 *Scan menu*\n\nSelect a command or type it manually:\n\n"
        "⚠️ Only scan targets you own or have permission to test.",
        _scan_keyboard,
    ),
    "network": ("🌐 *Network menu*\n\nBasic network utilities.", _network_keyboard),
    "tools": ("🧰 *Utility tools*\n\nHandy helpers.", _tools_keyboard),
    "stealth": ("⚙️ *Advanced menu*\n\nStealth scans, evasion, proxies and vuln discovery.", _stealth_keyboard),
    "main": ("👁 *Stealth scanner online.*\n\nChoose a category:", main_menu_keyboard),
}
