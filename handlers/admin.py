import platform
import shutil
from datetime import datetime, timezone

from aiogram import Bot, Router, types
from aiogram.filters import Command

from services.shell import scan_lock
from utils.logger import logger

admin_router = Router()

_START_TIME = datetime.now(timezone.utc)

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
                types.InlineKeyboardButton(text="🔍 OSINT", callback_data="cat:osint"),
                types.InlineKeyboardButton(text="🛰 Scan", callback_data="cat:scan"),
            ],
            [
                types.InlineKeyboardButton(text="🌐 Network", callback_data="cat:network"),
                types.InlineKeyboardButton(text="🧰 Tools", callback_data="cat:tools"),
            ],
            [
                types.InlineKeyboardButton(text="ℹ️ Status", callback_data="cmd:status"),
                types.InlineKeyboardButton(text="📖 Help", callback_data="cat:help"),
            ],
            [
                types.InlineKeyboardButton(text="⚠️ Legal", callback_data="cmd:about"),
            ],
        ]
    )


def _back_button() -> list[types.InlineKeyboardButton]:
    return [types.InlineKeyboardButton(text="⬅️ Back", callback_data="menu:main")]


def _osint_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="🔍 /osint", callback_data="hint:osint"),
                types.InlineKeyboardButton(text="🌐 /dns", callback_data="hint:dns"),
            ],
            [
                types.InlineKeyboardButton(text="🧩 /subdomains", callback_data="hint:subdomains"),
                types.InlineKeyboardButton(text="📡 /headers", callback_data="hint:headers"),
            ],
            [
                types.InlineKeyboardButton(text="🔒 /ssl", callback_data="hint:ssl"),
                types.InlineKeyboardButton(text="📚 /wayback", callback_data="hint:wayback"),
            ],
            _back_button(),
        ]
    )


def _scan_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="🛰 /scan", callback_data="hint:scan"),
                types.InlineKeyboardButton(text="🚀 /scanfull", callback_data="hint:scanfull"),
            ],
            [
                types.InlineKeyboardButton(text="⛔ /cancel", callback_data="cmd:cancel"),
            ],
            _back_button(),
        ]
    )


def _network_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="🌍 /ipinfo", callback_data="hint:ipinfo"),
                types.InlineKeyboardButton(text="🏓 /ping", callback_data="hint:ping"),
            ],
            [
                types.InlineKeyboardButton(text="🛤 /traceroute", callback_data="hint:traceroute"),
                types.InlineKeyboardButton(text="🔄 /reverseip", callback_data="hint:reverseip"),
            ],
            _back_button(),
        ]
    )


def _tools_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="🔑 /password", callback_data="cmd:password"),
                types.InlineKeyboardButton(text="🆔 /uuid", callback_data="cmd:uuid"),
            ],
            [
                types.InlineKeyboardButton(text="🔐 /hash", callback_data="hint:hash"),
                types.InlineKeyboardButton(text="🔁 /b64", callback_data="hint:b64"),
            ],
            [
                types.InlineKeyboardButton(text="🔁 /b64decode", callback_data="hint:b64decode"),
                types.InlineKeyboardButton(text="🔗 /urlencode", callback_data="hint:urlencode"),
            ],
            [
                types.InlineKeyboardButton(text="📧 /email", callback_data="hint:email"),
                types.InlineKeyboardButton(text="🌤 /weather", callback_data="hint:weather"),
            ],
            [
                types.InlineKeyboardButton(text="🕒 /timestamp", callback_data="cmd:timestamp"),
                types.InlineKeyboardButton(text="🧠 /summary", callback_data="cmd:summary"),
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


@admin_router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👁 *Stealth scanner online.*\n\n"
        "Choose a category or type /help for the command list.",
        parse_mode="Markdown",
        reply_markup=_main_menu_keyboard(),
    )


@admin_router.callback_query(lambda c: c.data == "menu:main")
async def cb_main_menu(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "👁 *Stealth scanner online.*\n\nChoose a category:",
        parse_mode="Markdown",
        reply_markup=_main_menu_keyboard(),
    )


@admin_router.callback_query(lambda c: c.data == "cat:help")
async def cb_help(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_help(callback.message)


@admin_router.callback_query(lambda c: c.data == "cat:osint")
async def cb_osint_menu(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "🔍 *OSINT menu*\n\nSelect a command or type it manually:",
        parse_mode="Markdown",
        reply_markup=_osint_keyboard(),
    )


@admin_router.callback_query(lambda c: c.data == "cat:scan")
async def cb_scan_menu(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "🛰 *Scan menu*\n\nSelect a command or type it manually:\n\n"
        "⚠️ Only scan targets you own or have permission to test.",
        parse_mode="Markdown",
        reply_markup=_scan_keyboard(),
    )


@admin_router.callback_query(lambda c: c.data == "cat:network")
async def cb_network_menu(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "🌐 *Network menu*\n\nSelect a command or type it manually:",
        parse_mode="Markdown",
        reply_markup=_network_keyboard(),
    )


@admin_router.callback_query(lambda c: c.data == "cat:tools")
async def cb_tools_menu(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "🧰 *Utility tools*\n\nSelect a command:",
        parse_mode="Markdown",
        reply_markup=_tools_keyboard(),
    )


@admin_router.callback_query(lambda c: c.data.startswith("hint:"))
async def cb_hint(callback: types.CallbackQuery):
    await callback.answer()
    key = callback.data.split(":", 1)[1]
    text = _HINTS.get(key, "Unknown command.")
    await callback.message.answer(text, parse_mode="Markdown")


@admin_router.callback_query(lambda c: c.data.startswith("cmd:"))
async def cb_run_command(callback: types.CallbackQuery):
    key = callback.data.split(":", 1)[1]
    await callback.answer()
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
    if not scan_lock.is_locked:
        await message.answer("✅ No scan is running.")
        return
    logger.info("Admin requested cancel of %s", scan_lock.current_task)
    await message.answer(
        "⚠️ Cancel signal sent. The current scan will stop as soon as the subprocess finishes its current step."
    )


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
