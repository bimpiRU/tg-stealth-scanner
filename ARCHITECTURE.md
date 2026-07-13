# Архитектура tg-stealth-scanner

Telegram-бот (aiogram 3, async) для авторизованного OSINT/скана. Single-admin, оборачивает системные CLI-тулзы (nmap, whois, dig, curl, openssl, sublist3r, traceroute, ping) и отдаёт отчёты в чат. ~1700 строк Python, деплой в Docker.

## Стек
- **aiogram 3.10** — бот-фреймворк, long polling, FSM (MemoryStorage)
- **aiohttp** — прямые HTTP (weather, AI API)
- **python-dotenv** — конфиг
- Внешние бинарники в Docker-образе (nmap, whois, dnsutils, sublist3r, openssl, traceroute)

## Слои

```
bot.py                 entrypoint: Bot+Dispatcher, регистрация роутеров/middleware, graceful shutdown
config.py              env-конфиг, создание results/logs dirs, валидация BOT_TOKEN/ADMIN_ID при старте

middlewares/           перехватчики message (порядок: admin → rate-limit)
  admin_filter.py      AdminMiddleware — пускает только ADMIN_ID (+опц. ADMIN_USERNAME)
  rate_limit.py        RateLimitMiddleware — cooldown между командами + sliding-window burst

handlers/              роутеры = presentation layer (парсят команду, валидируют, зовут services)
  admin.py             /start /help /status /about /cancel + inline-меню (callback-навигация) + set_bot_commands
  osint.py             /osint /dns /subdomains
  recon.py             /wayback /ipinfo /headers /ssl /ping /traceroute
  scan.py              /scan (nmap -sS -T2 -F), /scanfull (FSM-подтверждение "yes", nmap -sS -sV -O)
  utils.py             /password /uuid /hash /b64 /b64decode /urlencode /email /weather /timestamp /reverseip /summary

services/              бизнес-логика, без Telegram-зависимостей (кроме reports)
  shell.py             run_command() — asyncio subprocess, БЕЗ shell=True, timeout+kill; ScanLock (глобальный asyncio.Lock, 1 скан за раз)
  validators.py        validate_domain/email/ipv4 — regex + чёрный список shell-метасимволов + private-IP guard
  recon.py             ip_info, http_headers, ssl_info, wayback_snapshots, ping_host, traceroute_host
  reports.py           build/save/truncate отчётов, in-memory _last_report[user_id] (для /summary), send_report
  ai_summarizer.py     summarize() — POST в OpenAI-совместимый /chat/completions

utils/logger.py        RotatingFileHandler + console, TokenMaskingFilter (маскирует BOT_TOKEN в логах)

scripts/               ops: health_check.py (сканит /proc в контейнере), monitor.py (внешний, docker inspect → алерт в TG), autostart *.ps1/vbs (Windows)
```

## Поток запроса

```
Telegram update
  → AdminMiddleware   (не ADMIN_ID → drop, лог warning)
  → RateLimitMiddleware (cooldown/burst → отказ)
  → handler: split args → validators.validate_* → ошибка → ответ ❌
  → service слой:
       shell.run_command([бинарник, args], timeout)   ← create_subprocess_exec, без shell
       либо aiohttp напрямую (weather/AI)
  → reports.save_report() → файл в RESULTS_DIR
  → reports.send_report() → truncate(4000) → store_last_report → answer code-block
```

## Ключевые механики безопасности
- **Один пользователь**: всё режется по `ADMIN_ID` в middleware.
- **Command injection**: `run_command` использует `create_subprocess_exec` (список argv, не строка) + `FORBIDDEN_CHARS` regex в валидаторах отбрасывает `; & | $ ` ( ) < > *` и пр.
- **Private-IP guard**: публичные команды (`ipinfo/ping/traceroute/scanfull/reverseip`) требуют `allow_private=False`; `/scan` пускает приватные (для домашней сети).
- **Concurrency**: `ScanLock` — только один nmap за раз, `/cancel` и `/status` показывают состояние.
- **Секреты**: `TokenMaskingFilter` в логах; `.env` не в git.
- **Confirmation-gate**: `/scanfull` требует FSM-ответ `yes` (60s).

## Deploy
- **Dockerfile**: python:3.12-slim + сканеры apt, `USER root` (нужен для `nmap -sS` SYN).
- **docker-compose**: `cap_add: NET_RAW, NET_ADMIN`, volumes results/logs, `restart: always`, healthcheck.
- **monitor.py**: внешний watchdog (cron/Task Scheduler) → `docker inspect` → TG-алерт если контейнер down.

## Наблюдения (не критично)
- `ssl_info` в `services/recon.py` использует `sh -c "..."` с интерполяцией `domain` — единственное место с shell-строкой; спасает только то, что `validate_domain` уже прошёл. Хрупко.
- `ai_summarizer.py` читает env напрямую (дубль `config.py`) вместо импорта конфига.
- `/cancel` реально не убивает subprocess — только шлёт сообщение; scan останавливается сам после текущего шага.
- `store_last_report` кладёт уже усечённый (4000 символов) текст, поэтому AI-`/summary` резюмирует обрезанный отчёт, не полный файл.
