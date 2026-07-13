from handlers.admin import admin_router, set_bot_commands
from handlers.agent import agent_router
from handlers.chat import chat_router
from handlers.osint import osint_router
from handlers.recon import recon_router
from handlers.scan import scan_router
from handlers.stealth import stealth_router
from handlers.utils import utils_router

__all__ = [
    "admin_router",
    "agent_router",
    "chat_router",
    "osint_router",
    "recon_router",
    "scan_router",
    "stealth_router",
    "utils_router",
    "set_bot_commands",
]
