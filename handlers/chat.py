"""Natural-language chat handler.

This router is included *last* in ``bot.py`` so it only catches text messages
that were not handled by command routers.
"""

from aiogram import F, Router, types

from services.assistant import ask_ai_local, log_agent_request, parse_intent
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

    def _set_command_text():
        if args:
            message.text = f"/{intent} {args[0]}"
        else:
            message.text = f"/{intent}"

    if intent == "scan":
        if not args:
            await message.answer("Usage: `scan <IP>`", parse_mode="Markdown")
            return
        from handlers.scan import cmd_scan
        _set_command_text()
        await cmd_scan(message)

    elif intent == "osint":
        if not args:
            await message.answer("Usage: `osint <domain>`", parse_mode="Markdown")
            return
        from handlers.osint import cmd_osint
        _set_command_text()
        await cmd_osint(message)

    elif intent == "discover":
        if not args:
            await message.answer("Usage: `discover <subnet>`", parse_mode="Markdown")
            return
        from handlers.stealth import cmd_discover
        _set_command_text()
        await cmd_discover(message)

    elif intent == "vulns":
        if not args:
            await message.answer("Usage: `vulns <target>`", parse_mode="Markdown")
            return
        from handlers.stealth import cmd_vulns
        _set_command_text()
        await cmd_vulns(message)

    elif intent == "proxyfetch":
        from handlers.stealth import cmd_proxyfetch
        _set_command_text()
        await cmd_proxyfetch(message)

    elif intent == "help":
        from handlers.admin import cmd_help
        _set_command_text()
        await cmd_help(message)

    elif intent == "status":
        from handlers.admin import cmd_status
        _set_command_text()
        await cmd_status(message)

    elif intent == "lang":
        if not args:
            await message.answer(t("lang_usage", user_id=uid))
            return
        from handlers.admin import cmd_lang
        _set_command_text()
        await cmd_lang(message)

    elif intent == "ask":
        if not args:
            await message.answer(t("ask_usage", user_id=uid))
            return
        await _answer_ai(message, args[0])


async def _handle_agent(message: types.Message, text: str):
    """Forward natural-language agent requests to /agent."""
    from handlers.agent import cmd_agent

    message.text = f"/agent {text}"
    await cmd_agent(message)


async def _handle_unknown(message: types.Message, text: str):
    answer = await ask_ai_local(text)
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
    answer = await ask_ai_local(question)
    if answer is None:
        await message.answer(
            "🤖 AI is not configured.\n\n"
            "Either start the local Ollama service or add a remote key to your `.env`:\n"
            "```\n"
            "OLLAMA_MODEL=deepseek-r1:7b\n"
            "AI_API_KEY=sk-...\n"
            "AI_BASE_URL=https://api.openai.com/v1\n"
            "```",
            parse_mode="Markdown",
        )
        return
    await message.answer(answer, parse_mode="Markdown")
