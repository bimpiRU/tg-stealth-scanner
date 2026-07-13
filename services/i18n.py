"""Simple i18n helper.

Language is chosen from env DEFAULT_LANG (en/ru) and can be overridden
per-user in memory. Existing handlers are updated gradually; new handlers
use this module from the start.
"""

import os
from typing import Optional

DEFAULT_LANG = os.getenv("DEFAULT_LANG", "en").strip().lower()
if DEFAULT_LANG not in ("en", "ru"):
    DEFAULT_LANG = "en"

_user_langs: dict[int, str] = {}


_TRANSLATIONS = {
    "start_welcome": {
        "en": "👁 *Stealth scanner online.*\n\nChoose a category or type /help for the command list.",
        "ru": "👁 *Стелс-сканер онлайн.*\n\nВыбери категорию или напиши /help для списка команд.",
    },
    "choose_category": {
        "en": "Choose a category:",
        "ru": "Выбери категорию:",
    },
    "unknown_command": {
        "en": "Unknown command.",
        "ru": "Неизвестная команда.",
    },
    "usage": {
        "en": "Usage",
        "ru": "Использование",
    },
    "scan_only_authorized": {
        "en": "⚠️ Only scan targets you own or have permission to test.",
        "ru": "⚠️ Сканируй только свои системы или те, на которые есть письменное разрешение.",
    },
    "proxy_not_configured": {
        "en": "❌ Proxy is not configured. Set PROXY_URL in .env or add proxies to data/proxies.txt",
        "ru": "❌ Прокси не настроен. Укажи PROXY_URL в .env или добавь прокси в data/proxies.txt",
    },
    "proxy_working": {
        "en": "🌐 Working proxy found",
        "ru": "🌐 Рабочий прокси найден",
    },
    "proxy_test_failed": {
        "en": "❌ Proxy test failed",
        "ru": "❌ Проверка прокси не удалась",
    },
    "no_working_proxy": {
        "en": "❌ No working proxy found from the list.",
        "ru": "❌ Из списка не найдено рабочих прокси.",
    },
    "scan_started": {
        "en": "Starting scan of `{target}`...",
        "ru": "Запускаю сканирование `{target}`...",
    },
    "scan_cancelled": {
        "en": "🛑 Scan cancelled by admin.",
        "ru": "🛑 Сканирование отменено админом.",
    },
    "no_scan_running": {
        "en": "✅ No scan is running.",
        "ru": "✅ Ни одно сканирование не запущено.",
    },
    "another_scan_running": {
        "en": "⏳ Another scan is already running. Wait or use /cancel.",
        "ru": "⏳ Уже выполняется другое сканирование. Подожди или используй /cancel.",
    },
    "network_discovery_started": {
        "en": "🗺 Starting network discovery for `{subnet}`...",
        "ru": "🗺 Запускаю обнаружение хостов в сети `{subnet}`...",
    },
    "vuln_scan_started": {
        "en": "🛡 Starting vulnerability scan for `{target}`...",
        "ru": "🛡 Запускаю сканирование уязвимостей `{target}`...",
    },
    "lang_set": {
        "en": "Language set to English.",
        "ru": "Язык изменён на русский.",
    },
    "lang_usage": {
        "en": "Usage: /lang en|ru",
        "ru": "Использование: /lang en|ru",
    },
    "help_header": {
        "en": "📖 *Available commands*",
        "ru": "📖 *Доступные команды*",
    },
    "help_osint": {
        "en": "*OSINT*",
        "ru": "*OSINT*",
    },
    "help_scan": {
        "en": "*Scan*",
        "ru": "*Сканирование*",
    },
    "help_network": {
        "en": "*Network*",
        "ru": "*Сеть*",
    },
    "help_tools": {
        "en": "*Tools*",
        "ru": "*Утилиты*",
    },
    "help_stealth": {
        "en": "*Stealth*",
        "ru": "*Стелс*",
    },
    "help_ai": {
        "en": "*AI*",
        "ru": "*ИИ*",
    },
    "help_service": {
        "en": "*Service*",
        "ru": "*Сервис*",
    },
    "help_footer": {
        "en": "Only scan targets you own or have permission to test.",
        "ru": "Сканируй только свои системы или те, на которые есть письменное разрешение.",
    },
    "proxyfetch_warning": {
        "en": "⚠️ Public proxies may log traffic and do not anonymize raw packets. Use VPN/Tor for real anonymity.",
        "ru": "⚠️ Публичные прокси могут логировать трафик и не анонимизируют raw-пакеты. Для реальной анонимности используй VPN/Tor.",
    },
    "proxyfetch_started": {
        "en": "🌐 Fetching public proxy lists...",
        "ru": "🌐 Загружаю публичные списки прокси...",
    },
    "cancel_no_scan": {
        "en": "✅ No scan is running.",
        "ru": "✅ Ни одно сканирование не запущено.",
    },
    "cancel_killed": {
        "en": "🛑 Killed running scan: `{task}`",
        "ru": "🛑 Остановлено сканирование: `{task}`",
    },
    "status_header": {
        "en": "🤖 *Status*",
        "ru": "🤖 *Статус*",
    },
    "status_uptime": {
        "en": "Uptime",
        "ru": "Аптайм",
    },
    "status_python": {
        "en": "Python",
        "ru": "Python",
    },
    "status_scanner": {
        "en": "Scanner",
        "ru": "Сканер",
    },
    "status_current_task": {
        "en": "Current task",
        "ru": "Текущая задача",
    },
    "status_disk_free": {
        "en": "Disk free",
        "ru": "Свободно на диске",
    },
}


def set_user_lang(user_id: int, lang: str) -> bool:
    lang = lang.lower().strip()
    if lang not in ("en", "ru"):
        return False
    _user_langs[user_id] = lang
    return True


def get_user_lang(user_id: Optional[int] = None) -> str:
    if user_id is None:
        return DEFAULT_LANG
    return _user_langs.get(user_id, DEFAULT_LANG)


def t(key: str, user_id: Optional[int] = None, **kwargs) -> str:
    lang = get_user_lang(user_id)
    text = _TRANSLATIONS.get(key, {}).get(lang, _TRANSLATIONS.get(key, {}).get("en", key))
    if kwargs:
        text = text.format(**kwargs)
    return text
