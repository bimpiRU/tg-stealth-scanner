# 🤖 tg-stealth-scanner

> Telegram-управляемый сканер безопасности в Docker. Пассивный OSINT, скрытое сканирование портов и сетевые утилиты под рукой — через удобный интерфейс-кнопки.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?logo=python" alt="Python 3.12">
  <img src="https://img.shields.io/badge/aiogram-3.x-2CA5E0?logo=telegram" alt="aiogram 3.x">
  <img src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker" alt="Docker ready">
  <img src="https://img.shields.io/badge/nmap-7.94+-brightgreen?logo=nmap" alt="nmap">
</p>

---

## ✨ Возможности

- 🔍 **OSINT** — `crt.sh`, `whois`, DNS-записи, `sublist3r`, HTTP-заголовки, SSL-сертификаты, Wayback Machine
- 🛰 **Сканирование** — скрытый SYN-скан `nmap -sS -T2 -F` и расширенное сканирование по подтверждению
- 🌐 **Сеть** — геолокация IP, ping, traceroute, reverse DNS
- 🧰 **Утилиты** — генератор паролей, UUID, хеши, base64, URL-кодирование, погода, проверка email
- 🧠 **AI-суммаризация** — краткий пересказ отчётов через любой OpenAI-совместимый API
- 🔐 **Безопасность** — фильтрация ввода от Command Injection, rate-limit, доступ только для администратора
- 🎛 **Интерфейс** — категории и команды в виде inline-кнопок

---

## 🚀 Быстрый старт

### 1. Клонируй репозиторий

```bash
git clone https://github.com/bimpiRU/tg-stealth-scanner.git
cd tg-stealth-scanner
```

### 2. Настрой переменные окружения

```bash
cp .env.example .env
```

Отредактируй `.env` (этот файл никогда не попадает в git):

```env
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_ID=your_telegram_user_id
ADMIN_USERNAME=your_telegram_username
```

Получи токен у [@BotFather](https://t.me/BotFather), а свой `ADMIN_ID` — у [@userinfobot](https://t.me/userinfobot).

### 3. Запусти в Docker

```bash
docker compose up --build -d
```

Бот запустится в фоне и автоматически перезапустится при падении (`restart: always`).

### 4. Проверь статус

```bash
docker compose ps
docker compose logs -f
```

---

## 🎮 Использование

Отправь боту `/start`. Откроется меню с категориями:

| Категория | Команды |
|-----------|---------|
| 🔍 OSINT | `/osint`, `/dns`, `/subdomains`, `/headers`, `/ssl`, `/wayback` |
| 🛰 Scan | `/scan`, `/scanfull`, `/cancel` |
| 🌐 Network | `/ipinfo`, `/ping`, `/traceroute`, `/reverseip` |
| 🧰 Tools | `/password`, `/uuid`, `/hash`, `/b64`, `/b64decode`, `/urlencode`, `/email`, `/weather`, `/timestamp`, `/summary` |

Примеры:

```text
/osint example.com
/scan 1.1.1.1
/weather Tashkent
/email user@example.com
/summary
```

---

## 🧠 Подключение AI

Добавь в `.env` ключ от любого OpenAI-совместимого сервиса (OpenAI, Groq, OpenRouter, локальный Ollama и т.д.):

```env
AI_API_KEY=sk-...
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
AI_MAX_TOKENS=800
```

После любого скана используй `/summary` — бот кратко перескажет ключевые находки.

---

## 🛡 Безопасность, приватность и легальность

- 🔑 **Токены и ID не хранятся в репозитории.** Все секреты читаются из файла `.env`, который добавлен в `.gitignore`.
- 👤 Бот работает **только** для пользователя с указанным `ADMIN_ID`.
- 🚫 Все пользовательские аргументы проверяются регулярками; запрещены символы `; & | $ \` ( ) { } < > * ? [ ] ! # = ~`.
- 🐚 Сканирование запускается через `subprocess` **без** `shell=True`.
- 📡 `nmap -sS` требует `NET_RAW` / `NET_ADMIN` — они уже указаны в `docker-compose.yml`.
- ⚠️ **Используй только на своих системах или с письменного разрешения владельца.**

---

## 🏗 Архитектура

```text
tg_stealth_scanner/
├── bot.py              # Точка входа, polling
├── config.py           # Конфигурация из env
├── Dockerfile          # Сборка на python:3.12-slim + nmap/whois/curl/dnsutils
├── docker-compose.yml  # Запуск контейнера
├── .env.example        # Шаблон переменных (без реальных секретов)
├── handlers/           # Обработчики команд
├── middlewares/        # Фильтр админа и rate-limit
├── services/           # Сканеры, валидаторы, AI, отчёты
├── scripts/            # Health-check + внешний мониторинг + автозапуск Windows
└── utils/              # Логгер
```

---

## 🔧 Полезные команды

```bash
# Пересобрать и перезапустить
docker compose up --build -d

# Посмотреть логи
docker compose logs -f

# Остановить
docker compose down

# Зайти внутрь контейнера
docker exec -it tg-stealth-scanner bash

# Проверить health извне
python scripts/monitor.py
```

### 📡 Внешний мониторинг

Файл `scripts/monitor.py` проверяет, запущен ли контейнер, и шлёт алерт в Telegram при сбое. Добавь в планировщик задач Windows или cron:

```bash
*/5 * * * * cd /path/to/tg-stealth-scanner && python scripts/monitor.py
```

### 🔄 Автозапуск Windows

Ярлык для автозапуска создаётся командой:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "scripts\install-startup-shortcut.ps1"
```

После этого контейнер будет подниматься автоматически при входе в Windows.

---

## 📝 Лицензия

MIT — используй на свой страх и риск. Автор не несёт ответственности за несанкционированное использование.

---

<p align="center">
  Сделано с целью обучения и легального пентестинга.
</p>
