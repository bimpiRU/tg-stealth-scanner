"""Natural-language chat handler.

This router is included *last* in ``bot.py`` so it only catches text messages
that were not handled by command routers.
"""

from aiogram import F, Router, types

from services.assistant import ask_ai, log_agent_request, parse_intent
from services.i18n import t

chat_router = Router()


@chat_router.message(F.text)
async def chat_text_handler(message: types.Message):
    """Route natural-language messages to existing commands or AI."""
    text = message.text or ""
    parsed = parse_intent(text)
    intent = parsed["intent"]

    if intent == "agent":
        await _handle_agent(message, parsed["text"])
        return

    if intent == "unknown":
        await _handle_unknown(message, text)
        return

    await _route_intent(message, parsed)


async def _route_intent(message: types.Message, parsed: dict):
    intent = parsed["intent"]
    args = parsed.get("args", [])
    uid = message.from_user.id

    if intent == "scan":
        if not args:
            await message.answer("Usage: `scan <IP>`", parse_mode="Markdown")
            return
        from handlers.scan import cmd_scan
        await cmd_scan(message)

    elif intent == "osint":
        if not args:
            await message.answer("Usage: `osint <domain>`", parse_mode="Markdown")
            return
        from handlers.osint import cmd_osint
        await cmd_osint(message)

    elif intent == "discover":
        if not args:
            await message.answer("Usage: `discover <subnet>`", parse_mode="Markdown")
            return
        from handlers.stealth import cmd_discover
        await cmd_discover(message)

    elif intent == "vulns":
        if not args:
            await message.answer("Usage: `vulns <target>`", parse_mode="Markdown")
            return
        from handlers.stealth import cmd_vulns
        await cmd_vulns(message)

    elif intent == "proxyfetch":
        from handlers.stealth import cmd_proxyfetch
        await cmd_proxyfetch(message)

    elif intent == "help":
        from handlers.admin import cmd_help
        await cmd_help(message)

    elif intent == "status":
        from handlers.admin import cmd_status
        await cmd_status(message)

    elif intent == "lang":
        if not args:
            await message.answer(t("lang_usage", user_id=uid))
            return
        from handlers.admin import cmd_lang
        await cmd_lang(message)

    elif intent == "ask":
        if not args:
            await message.answer(t("ask_usage", user_id=uid))
            return
        await _answer_ai(message, args[0])


async def _handle_agent(message: types.Message, text: str):
    log_agent_request(message.from_user.id, text)
    await message.answer(t("agent_request_logged", user_id=message.from_user.id))


async def _handle_unknown(message: types.Message, text: str):
    answer = await ask_ai(text)
    if answer is None:
        uid = message.from_user.id
        await message.answer(
            f"{t('unknown_command_help', user_id=uid)}\n\n"
            f"{t('chat_hint', user_id=uid)}"
        )
        return
    await message.answer(answer, parse_mode="Markdown")


async def _answer_ai(message: types.Message, question: str):
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
