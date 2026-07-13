import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = Path(os.getenv("RESULTS_DIR", BASE_DIR / "results"))
LOGS_DIR = Path(os.getenv("LOGS_DIR", BASE_DIR / "logs"))

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or 0)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")

MAX_MESSAGE_LENGTH = 4000

RATE_LIMIT_SECONDS = int(os.getenv("RATE_LIMIT_SECONDS", "10"))
RATE_LIMIT_BURST = int(os.getenv("RATE_LIMIT_BURST", "10"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

SCAN_TIMEOUT = int(os.getenv("SCAN_TIMEOUT", "180"))
OSINT_TIMEOUT = int(os.getenv("OSINT_TIMEOUT", "120"))

# Allow scanning private/RFC1918 IPs (e.g. 192.168.x.x, 10.x.x.x, 172.16-31.x.x).
# Only enable this when you are scanning your own network.
ALLOW_PRIVATE_IPS = os.getenv("ALLOW_PRIVATE_IPS", "false").lower() in ("true", "1", "yes")

AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "800"))

if not BOT_TOKEN or BOT_TOKEN == "твой_токен_из_BotFather":
    raise ValueError("Set a real BOT_TOKEN in the .env file before starting the bot.")

if not ADMIN_ID:
    raise ValueError("Set a real ADMIN_ID in the .env file.")
