"""Agent command handler.

Provides ``/agent <task>`` and a callback handler for the ``run_agent`` button.
"""

from aiogram import F, Router, types
from aiogram.filters import Command

from services import orchestrator
from utils.logger import logger

agent_router = Router()


@agent_router.message(Command("agent"))
async def cmd_agent(message: types.Message):
    """Run the local Ollama agent on a user task."""
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: `/agent <task>`", parse_mode="Markdown")
        return

    task = args[1]
    logger.info("Agent task requested: %s", task)
    await message.answer("🤖 Agent is thinking...")

    result = await orchestrator.run_agent(task)
    await message.answer(result, parse_mode="Markdown")


@agent_router.callback_query(F.data == "run_agent")
async def cb_run_agent(callback: types.CallbackQuery):
    """Handle a callback button that triggers the agent."""
    await callback.answer("🤖 Agent ready. Type /agent <task>.", show_alert=True)
    await callback.message.answer(
        "🤖 Agent is ready. Send `/agent <task>` to run it.",
        parse_mode="Markdown",
    )
