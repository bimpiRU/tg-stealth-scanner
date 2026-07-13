import platform
import shutil
from datetime import datetime, timezone

from aiogram import Bot, Router, types
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData

from services.assistant import ask_ai
from services.i18n import set_user_lang, t
from services.shell import scan_lock
from utils.logger import logger

admin_router = Router()

_START_TIME = datetime.now(timezone.utc)


# Typed callback payloads replace ad-hoc "prefix:value" strings parsed by hand.
class Nav(CallbackData, prefix="nav"):
    """Navigate the menu tree. ``to`` is one of the menu screens."""

    to: str  # main | osint | scan | network | tools | help


class Hint(CallbackData, prefix="hint"):
    """Show usage hint for a command. ``key`` indexes ``_HINTS``."""

    key: str


class Run(CallbackData, prefix="run"):
    """Run a no-argument command directly from a button. ``key`` names it."""

    key: str


_ABOUT_TEXT = (
    "⚠️ *Legal notice*\n\n"
    "This bot is designed for *authorized security research and passive OSINT* "
    "on targets you own or have explicit written permission to test.\n\n"
    "Unauthorized scanning, intrusion, or data collection against third-party "
    "systems may violate local and international laws. The author assumes no "
    "liability for misuse.\n\n"
    "Use responsibly."
)


def _main_menu_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="🔍 OSINT", callback_data=Nav(to="osint").pack()),
                types.InlineKeyboardButton(text="🛰 Scan", callback_data=Nav(to="scan").pack()),
            ],
            [
                types.InlineKeyboardButton(text="🌐 Network", callback_data=Nav(to="network").pack()),
                types.InlineKeyboardButton(text="🧰 Tools", callback_data=Nav(to="tools").pack()),
            ],
            [
                types.InlineKeyboardButton(text="🥷 Stealth", callback_data=Nav(to="stealth").pack()),
                types.InlineKeyboardButton(text="ℹ️ Status", callback_data=Run(key="status").pack()),
            ],
            [
                types.InlineKeyboardButton(text="📖 Help", callback_data=Nav(to="help").pack()),
                types.InlineKeyboardButton(text="🤖 AI", callback_data=Nav(to="help").pack()),
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
            [
                types.InlineKeyboardButton(text="🔒 /ssl", callback_data=Hint(key="ssl").pack()),
                types.InlineKeyboardButton(text="📚 /wayback", callback_data=Hint(key="wayback").pack()),
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
            [
                types.InlineKeyboardButton(text="⛔ /cancel", callback_data=Run(key="cancel").pack()),
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
            [
                types.InlineKeyboardButton(text="🛤 /traceroute", callback_data=Hint(key="traceroute").pack()),
                types.InlineKeyboardButton(text="🔄 /reverseip", callback_data=Hint(key="reverseip").pack()),
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


_HINTS = {
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

_NAV_SCREENS = {
    "osint": ("🔍 *OSINT menu*\n\nSelect a command or type it manually:", _osint_keyboard),
    "scan": (
        "🛰 *Scan menu*\n\nSelect a command or type it manually:\n\n"
        "⚠️ Only scan targets you own or have permission to test.",
        _scan_keyboard,
    ),
    "network": ("🌐 *Network menu*\n\nSelect a command or type it manually:", _network_keyboard),
    "tools": ("🧰 *Utility tools*\n\nSelect a command:", _tools_keyboard),
    "stealth": ("🥷 *Stealth menu*\n\nAdvanced scans, evasion, proxies and vulnerability discovery:", _stealth_keyboard),
    "main": ("👁 *Stealth scanner online.*\n\nChoose a category:", _main_menu_keyboard),
}


@admin_router.message(Command("start"))
async def cmd_start(message: types.Message):
    text = t("start_welcome", user_id=message.from_user.id)
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=_main_menu_keyboard(),
    )


@admin_router.message(Command("lang"))
async def cmd_lang(message: types.Message):
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        await message.answer(t("lang_usage", user_id=message.from_user.id))
        return
    lang = args[1].strip().lower()
    if set_user_lang(message.from_user.id, lang):
        await message.answer(t("lang_set", user_id=message.from_user.id))
    else:
        await message.answer(t("lang_usage", user_id=message.from_user.id))


@admin_router.message(Command("ask"))
async def cmd_ask(message: types.Message):
    """Answer a question via the configured AI."""
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        await message.answer(t("ask_usage", user_id=message.from_user.id))
        return

    question = args[1]
    await message.answer("🤖 Thinking...")
    answer = await ask_ai(question)
    if answer is None:
        await message.answer(
            "🤖 AI is not configured.\n\n"
            "Add to your `.env` file:\n"
            "```\n"
            "AI_API_KEY=sk-...\n"
            "AI_BASE_URL=https://api.openai.com/v1\n"
            "AI_MODEL=gpt-4o-mini\n"
            "```",
            parse_mode="Markdown",
        )
        return
    await message.answer(answer, parse_mode="Markdown")


@admin_router.callback_query(Nav.filter())
async def cb_nav(callback: types.CallbackQuery, callback_data: Nav):
    await callback.answer()
    if callback_data.to == "help":
        await cmd_help(callback.message)
        return
    text, keyboard = _NAV_SCREENS[callback_data.to]
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard())


@admin_router.callback_query(Hint.filter())
async def cb_hint(callback: types.CallbackQuery, callback_data: Hint):
    await callback.answer()
    text = _HINTS.get(callback_data.key, "Unknown command.")
    await callback.message.answer(text, parse_mode="Markdown")


@admin_router.callback_query(Run.filter())
async def cb_run_command(callback: types.CallbackQuery, callback_data: Run):
    await callback.answer()
    key = callback_data.key
    if key == "password":
        from handlers.utils import cmd_password
        await cmd_password(callback.message)
    elif key == "uuid":
        from handlers.utils import cmd_uuid
        await cmd_uuid(callback.message)
    elif key == "timestamp":
        from handlers.utils import cmd_timestamp
        await cmd_timestamp(callback.message)
    elif key == "status":
        await cmd_status(callback.message)
    elif key == "about":
        await cmd_about(callback.message)
    elif key == "summary":
        from handlers.utils import cmd_summary
        await cmd_summary(callback.message)
    elif key == "proxyinfo":
        from handlers.stealth import cmd_proxyinfo
        await cmd_proxyinfo(callback.message)
    elif key == "proxytest":
        from handlers.stealth import cmd_proxytest
        await cmd_proxytest(callback.message)
    elif key == "proxyfind":
        from handlers.stealth import cmd_proxyfind
        await cmd_proxyfind(callback.message)
    elif key == "proxyfetch":
        from handlers.stealth import cmd_proxyfetch
        await cmd_proxyfetch(callback.message)
    elif key == "cancel":
        await cmd_cancel(callback.message)
    else:
        await callback.message.answer(f"Type `/{key}` manually in the chat.", parse_mode="Markdown")


@admin_router.message(Command("help"))
async def cmd_help(message: types.Message):
    uid = message.from_user.id
    text = (
        f"{t('help_header', user_id=uid)}\n\n"
        f"{t('help_osint', user_id=uid)}\n"
        "/osint <domain> — passive recon\n"
        "/dns <domain> — DNS records\n"
        "/subdomains <domain> — subdomain enumeration\n"
        "/headers <domain> — HTTP headers\n"
        "/ssl <domain> — SSL certificate\n"
        "/wayback <domain> — Wayback snapshots\n\n"
        f"{t('help_scan', user_id=uid)}\n"
        "/scan <IP> — stealth nmap SYN\n"
        "/scanfull <IP> — extended nmap\n\n"
        f"{t('help_network', user_id=uid)}\n"
        "/ipinfo <IP> — geolocation\n"
        "/ping <IP> — ping\n"
        "/traceroute <IP> — traceroute\n"
        "/reverseip <IP> — reverse DNS\n\n"
        f"{t('help_tools', user_id=uid)}\n"
        "/password [length] — password generator\n"
        "/uuid — generate UUID\n"
        "/hash <text> — MD5/SHA1/SHA256\n"
        "/b64 <text> — base64 encode\n"
        "/b64decode <base64> — base64 decode\n"
        "/urlencode <text> — URL encode\n"
        "/email <email> — email validation + MX\n"
        "/weather <city> — current weather\n"
        "/timestamp — current time\n\n"
        f"{t('help_stealth', user_id=uid)}\n"
        "/scapy <IP> [ports] — Scapy SYN scan\n"
        "/scapyfrag <IP> [ports] — fragmented SYN scan\n"
        "/scapydecoy <IP> [ports] — SYN scan with decoys\n"
        "/evade <IP> — evasive nmap\n"
        "/discover <subnet> — network host discovery\n"
        "/vulns <target> — vulnerability scan (nmap NSE)\n"
        "/quickvulns <target> — fast vuln scan top 100 ports\n"
        "/proxyinfo — proxy config\n"
        "/proxytest — test proxy\n"
        "/proxyfind — find working proxy from list\n"
        "/proxyfetch — fetch public proxy lists\n\n"
        f"{t('help_ai', user_id=uid)}\n"
        "/summary — summarize the last report (configure AI_API_KEY)\n"
        "/ask <question> — ask the AI assistant\n"
        f"{t('chat_hint', user_id=uid)}\n\n"
        f"{t('help_service', user_id=uid)}\n"
        "/status — bot status\n"
        "/about — legal notice\n"
        "/lang en|ru|uz — switch language\n"
        "/cancel — cancel scan\n\n"
        f"⚠️ {t('help_footer', user_id=uid)}"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=_main_menu_keyboard())


@admin_router.message(Command("about"))
async def cmd_about(message: types.Message):
    await message.answer(_ABOUT_TEXT, parse_mode="Markdown")


@admin_router.message(Command("status"))
async def cmd_status(message: types.Message):
    uid = message.from_user.id
    uptime = datetime.now(timezone.utc) - _START_TIME
    total, used, free = shutil.disk_usage("/app")
    lock_status = "busy" if scan_lock.is_locked else "idle"
    current = scan_lock.current_task or "none"

    text = (
        f"{t('status_header', user_id=uid)}\n"
        f"{t('status_uptime', user_id=uid)}: `{uptime}`\n"
        f"{t('status_python', user_id=uid)}: `{platform.python_version()}`\n"
        f"{t('status_scanner', user_id=uid)}: `{lock_status}`\n"
        f"{t('status_current_task', user_id=uid)}: `{current}`\n"
        f"{t('status_disk_free', user_id=uid)}: `{free // (2**30)} GB`"
    )
    await message.answer(text, parse_mode="Markdown")


@admin_router.message(Command("cancel"))
async def cmd_cancel(message: types.Message):
    uid = message.from_user.id
    task = scan_lock.current_task
    if not scan_lock.cancel():
        await message.answer(t("cancel_no_scan", user_id=uid))
        return
    logger.info("Admin cancelled %s", task)
    await message.answer(t("cancel_killed", user_id=uid, task=task), parse_mode="Markdown")


async def set_bot_commands(bot: Bot) -> None:
    commands = [
        types.BotCommand(command="start", description="Main menu"),
        types.BotCommand(command="help", description="Command list"),
        types.BotCommand(command="osint", description="Passive OSINT on domain"),
        types.BotCommand(command="dns", description="DNS records"),
        types.BotCommand(command="subdomains", description="Subdomain enumeration"),
        types.BotCommand(command="headers", description="HTTP headers"),
        types.BotCommand(command="ssl", description="SSL certificate"),
        types.BotCommand(command="wayback", description="Wayback snapshots"),
        types.BotCommand(command="ipinfo", description="IP geolocation"),
        types.BotCommand(command="ping", description="ICMP ping"),
        types.BotCommand(command="traceroute", description="Traceroute"),
        types.BotCommand(command="scan", description="Stealth nmap scan"),
        types.BotCommand(command="scanfull", description="Extended nmap scan"),
        types.BotCommand(command="reverseip", description="Reverse DNS lookup"),
        types.BotCommand(command="password", description="Generate secure password"),
        types.BotCommand(command="uuid", description="Generate UUID v4"),
        types.BotCommand(command="hash", description="MD5/SHA1/SHA256 hashes"),
        types.BotCommand(command="b64", description="Base64 encode"),
        types.BotCommand(command="b64decode", description="Base64 decode"),
        types.BotCommand(command="urlencode", description="URL encode text"),
        types.BotCommand(command="email", description="Email validation + MX"),
        types.BotCommand(command="weather", description="Current weather by city"),
        types.BotCommand(command="summary", description="Summarize last report with AI"),
        types.BotCommand(command="ask", description="Ask the AI assistant"),
        types.BotCommand(command="timestamp", description="Current UTC/unix time"),
        types.BotCommand(command="lang", description="Switch language en|ru|uz"),
        types.BotCommand(command="scapy", description="Scapy SYN scan"),
        types.BotCommand(command="scapyfrag", description="Fragmented Scapy SYN scan"),
        types.BotCommand(command="scapydecoy", description="Scapy SYN scan with decoys"),
        types.BotCommand(command="evade", description="Evasive nmap scan"),
        types.BotCommand(command="discover", description="Network discovery subnet"),
        types.BotCommand(command="vulns", description="Vulnerability scan (safe NSE)"),
        types.BotCommand(command="quickvulns", description="Fast vuln scan top 100 ports"),
        types.BotCommand(command="proxyinfo", description="Show proxy config"),
        types.BotCommand(command="proxytest", description="Test proxy connectivity"),
        types.BotCommand(command="proxyfind", description="Find working proxy from list"),
        types.BotCommand(command="proxyfetch", description="Fetch public proxy lists"),
        types.BotCommand(command="status", description="Bot status"),
        types.BotCommand(command="about", description="Legal notice"),
        types.BotCommand(command="cancel", description="Cancel scan"),
    ]
    await bot.set_my_commands(commands)
