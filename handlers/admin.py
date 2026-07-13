import platform
import shutil
from datetime import datetime, timezone

from aiogram import Bot, Router, types
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData

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
    "main": ("👁 *Stealth scanner online.*\n\nChoose a category:", _main_menu_keyboard),
}


@admin_router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👁 *Stealth scanner online.*\n\n"
        "Choose a category or type /help for the command list.",
        parse_mode="Markdown",
        reply_markup=_main_menu_keyboard(),
    )


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
    elif key == "cancel":
        await cmd_cancel(callback.message)
    else:
        await callback.message.answer(f"Type `/{key}` manually in the chat.", parse_mode="Markdown")


@admin_router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "📖 *Available commands*\n\n"
        "*OSINT*\n"
        "/osint <domain> — passive recon\n"
        "/dns <domain> — DNS records\n"
        "/subdomains <domain> — subdomain enumeration\n"
        "/headers <domain> — HTTP headers\n"
        "/ssl <domain> — SSL certificate\n"
        "/wayback <domain> — Wayback snapshots\n\n"
        "*Scan*\n"
        "/scan <IP> — stealth nmap SYN\n"
        "/scanfull <IP> — extended nmap\n\n"
        "*Network*\n"
        "/ipinfo <IP> — geolocation\n"
        "/ping <IP> — ping\n"
        "/traceroute <IP> — traceroute\n"
        "/reverseip <IP> — reverse DNS\n\n"
        "*Tools*\n"
        "/password [length] — password generator\n"
        "/uuid — generate UUID\n"
        "/hash <text> — MD5/SHA1/SHA256\n"
        "/b64 <text> — base64 encode\n"
        "/b64decode <base64> — base64 decode\n"
        "/urlencode <text> — URL encode\n"
        "/email <email> — email validation + MX\n"
        "/weather <city> — current weather\n"
        "/timestamp — current time\n\n"
        "*AI*\n"
        "/summary — summarize the last report (configure AI_API_KEY)\n\n"
        "*Service*\n"
        "/status — bot status\n"
        "/about — legal notice\n"
        "/cancel — cancel scan"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=_main_menu_keyboard())


@admin_router.message(Command("about"))
async def cmd_about(message: types.Message):
    await message.answer(_ABOUT_TEXT, parse_mode="Markdown")


@admin_router.message(Command("status"))
async def cmd_status(message: types.Message):
    uptime = datetime.now(timezone.utc) - _START_TIME
    total, used, free = shutil.disk_usage("/app")
    lock_status = "busy" if scan_lock.is_locked else "idle"
    current = scan_lock.current_task or "none"

    text = (
        f"🤖 *Status*\n"
        f"Uptime: `{uptime}`\n"
        f"Python: `{platform.python_version()}`\n"
        f"Scanner: `{lock_status}`\n"
        f"Current task: `{current}`\n"
        f"Disk free: `{free // (2**30)} GB`"
    )
    await message.answer(text, parse_mode="Markdown")


@admin_router.message(Command("cancel"))
async def cmd_cancel(message: types.Message):
    task = scan_lock.current_task
    if not scan_lock.cancel():
        await message.answer("✅ No scan is running.")
        return
    logger.info("Admin cancelled %s", task)
    await message.answer(f"🛑 Killed running scan: `{task}`", parse_mode="Markdown")


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
        types.BotCommand(command="timestamp", description="Current UTC/unix time"),
        types.BotCommand(command="status", description="Bot status"),
        types.BotCommand(command="about", description="Legal notice"),
        types.BotCommand(command="cancel", description="Cancel scan"),
    ]
    await bot.set_my_commands(commands)
