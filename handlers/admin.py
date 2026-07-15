import platform
import shutil
from datetime import datetime, timezone

from aiogram import Bot, Router, types
from aiogram.filters import Command

from handlers.keyboards import HINTS, NAV_SCREENS, Hint, Nav, Run, main_menu_keyboard
from services.assistant import ask_ai
from services.i18n import set_user_lang, t
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


@admin_router.message(Command("start"))
async def cmd_start(message: types.Message):
    text = t("start_welcome", user_id=message.from_user.id)
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
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
    text, keyboard = NAV_SCREENS[callback_data.to]
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard())


@admin_router.callback_query(Hint.filter())
async def cb_hint(callback: types.CallbackQuery, callback_data: Hint):
    await callback.answer()
    text = HINTS.get(callback_data.key, "Unknown command.")
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
        "/agent <task> — autonomous AI agent with tools (DeepSeek/Ollama)\n"
        f"{t('chat_hint', user_id=uid)}\n\n"
        f"{t('help_service', user_id=uid)}\n"
        "/status — bot status\n"
        "/about — legal notice\n"
        "/lang en|ru|uz — switch language\n"
        "/cancel — cancel scan\n\n"
        f"⚠️ {t('help_footer', user_id=uid)}"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())


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
        types.BotCommand(command="agent", description="Run autonomous AI agent"),
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
