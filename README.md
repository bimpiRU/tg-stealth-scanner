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

- 🔍 **OSINT** — `crt.sh`, `whois`, DNS-записи, `sublist3r`, HTTP-заголовки, SSL-сертификаты, Wayback Machine, а также `sherlock`, `maigret`, `subfinder`, `amass`, `httpx`, `katana`, `whatweb`, `exiftool` и `nuclei`
- 🛰 **Сканирование** — скрытый SYN-скан `nmap -sS -T2 -F` и расширенное сканирование по подтверждению
- 🥷 **Стелс** — Scapy SYN-скан, фрагментация, decoy-источники, эвейзивный nmap, HTTP(S)-прокси, авто-поиск публичных прокси
- 🌐 **Сеть** — геолокация IP, ping, traceroute, reverse DNS, обнаружение хостов в подсети (`/discover`)
- 🛡 **Уязвимости** — безопасное сканирование nmap NSE (`/vulns`, `/quickvulns`) только для авторизованных целей
- 🧰 **Утилиты** — генератор паролей, UUID, хеши, base64, URL-кодирование, погода, проверка email
- 🧠 **AI-суммаризация** — краткий пересказ отчётов через любой OpenAI-совместимый API
- 🌐 **Локализация** — переключение языка `/lang en|ru`, по умолчанию `ru`
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
DEFAULT_LANG=ru
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
| 🥷 Stealth | `/scapy`, `/scapyfrag`, `/scapydecoy`, `/evade`, `/discover`, `/vulns`, `/quickvulns`, `/proxyinfo`, `/proxytest`, `/proxyfind`, `/proxyfetch` |
| 🌐 Network | `/ipinfo`, `/ping`, `/traceroute`, `/reverseip` |
| 🧠 AI | `/agent`, `/ask`, `/summary` |
| ⚙️ Service | `/status`, `/about`, `/lang en\|ru\|uz` |

Примеры:

```text
/osint example.com
/scan 1.1.1.1
/discover 192.168.1.0/24
/vulns 1.1.1.1
/proxyfetch
/agent просканируй 1.1.1.1 и найди уязвимости
/ask что такое nmap
/lang ru
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

## 🧠 Локальная AI-модель Ollama / DeepSeek

Помимо OpenAI-совместимых API, бот может использовать локальную модель через [Ollama](https://ollama.com). По умолчанию поднимается сервис `ollama` внутри `docker-compose.yml` с моделью **DeepSeek-R1 7B**.

### Минимальные требования

- CPU: современный x86_64 процессор (для CPU-режима).
- RAM: минимум 8 ГБ, рекомендуется 16 ГБ+
- Диск: ~5 ГБ на модель `deepseek-r1:7b` (загружается при первом запуске).
- GPU (опционально): NVIDIA GPU с установленным `nvidia-container-toolkit`. Блок `deploy.resources.reservations.devices` в `docker-compose.yml` активирует GPU; на CPU-only хосте Docker Compose проигнорирует его.

### Переменные окружения

```env
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=deepseek-r1:7b
OLLAMA_TIMEOUT=120
AGENT_MAX_ITERATIONS=5
DB_PATH=/app/data/osint.db
```

### Загрузка модели

Модель можно скачать автоматически:

```bash
docker compose exec tg-stealth-scanner python scripts/pull_model.py
```

Или вручную через CLI контейнера `ollama`:

```bash
docker compose exec ollama ollama pull deepseek-r1:7b
```

Сервис `ollama` доступен только внутри сети Compose (порт `11434` не опубликован наружу). Контейнер бота ждёт, пока `ollama` станет `healthy`, прежде чем запускаться.

---

## 🥷 Стелс, прокси и сетевое обнаружение

Для HTTP(S)-запросов (не для raw nmap/scapy) можно настроить прокси и джиттер:

```env
PROXY_URL=http://user:pass@host:port
PROXY_TYPE=http
EVADE_MIN_DELAY=0.5
EVADE_MAX_DELAY=2.0
```

Также можно добавить свои прокси в файл `data/proxies.txt` (один на строку) или использовать команду `/proxyfetch`, которая загружает публичные списки, проверяет их и сохраняет рабочие.

⚠️ **Важно:**
- Публичные прокси часто нестабильны и могут логировать трафик.
- Прокси анонимизируют только HTTP(S)-запросы (OSINT, headers, ssl и т.д.).
- Raw-сканы (`nmap -sS`, Scapy) **не** используют прокси. Для их анонимизации нужен VPN/Tor на уровне сети хоста.

`/discover <subnet>` выполняет обнаружение хостов в явно указанной подсети, а `/vulns <target>` и `/quickvulns <target>` запускают только безопасные скрипты nmap NSE (`--script vuln`, `unsafe=0`) без эксплуатации.

---

## 🛡 Безопасность, приватность и легальность

- 🔑 **Токены и ID не хранятся в репозитории.** Все секреты читаются из файла `.env`, который добавлен в `.gitignore`.
- 👤 Бот работает **только** для пользователя с указанным `ADMIN_ID` (и опционально `ADMIN_USERNAME`).
- 🚫 Все пользовательские аргументы проверяются регулярками; запрещены символы `; & | $ \` ( ) { } < > * ? [ ] ! # = ~`.
- 🐚 Сканирование запускается через `subprocess` **без** `shell=True`.
- 📡 `nmap -sS` и Scapy требуют `NET_RAW` / `NET_ADMIN` — они уже указаны в `docker-compose.yml`.
- 🛡 Сканирование уязвимостей использует только безопасные NSE-скрипты (`unsafe=0`) и не эксплуатирует найденное.
- ⚠️ **Используй только на своих системах или с письменного разрешения владельца.**
- ⚠️ Не коммитьте рабочий `data/proxies.txt` — он в `.gitignore`. Шаблон хранится в `data/proxies.example.txt`.

---

## 🏗 Архитектура

```text
tg_stealth_scanner/
├── bot.py              # Точка входа, polling
├── config.py           # Конфигурация из env
├── Dockerfile          # Сборка на python:3.12-slim-bookworm + nmap/whois/curl/dnsutils + Go/Python OSINT tools
├── docker-compose.yml  # Запуск контейнера + Ollama
├── .env.example        # Шаблон переменных (без реальных секретов)
├── data/               # Шаблон списка прокси (proxies.example.txt) и SQLite база
├── handlers/           # Обработчики команд (admin, agent, chat, osint, recon, scan, utils, stealth)
├── middlewares/        # Фильтр админа и rate-limit
├── services/           # Сканеры, валидаторы, AI/Ollama, БД, отчёты, stealth/proxy/scapy/vuln
├── scripts/            # Health-check + pull_model + внешний мониторинг + автозапуск Windows
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
