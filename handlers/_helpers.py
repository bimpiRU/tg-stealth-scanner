"""Shared helpers for command handlers.

``arg_command`` removes the split/validate/error boilerplate that every
single-argument command repeated by hand. A decorated handler keeps the plain
``async def handler(message)`` signature aiogram introspects, but receives the
already-parsed, already-validated argument as a second positional value.

    @router.message(Command("dns"))
    @arg_command(validate_domain, usage="Usage: /dns <domain>")
    async def cmd_dns(message: types.Message, domain: str):
        ...

Aiogram only ever sees the wrapper, whose signature is pinned to exactly
``(message: types.Message)`` — so dependency injection (message, and only
message) is unaffected. Handlers that also need FSM ``state`` or take optional
arguments are intentionally left un-decorated.
"""

import inspect
from functools import wraps
from typing import Awaitable, Callable, Optional

from aiogram import types

from services.validators import ValidationError

Validator = Callable[[str], str]
Handler = Callable[[types.Message, str], Awaitable[None]]

_MESSAGE_ONLY_SIGNATURE = inspect.Signature(
    parameters=[inspect.Parameter("message", inspect.Parameter.POSITIONAL_OR_KEYWORD)]
)


def arg_command(
    validator: Optional[Validator] = None,
    *,
    usage: str,
) -> Callable[[Handler], Callable[[types.Message], Awaitable[None]]]:
    """Wrap a ``(message, value)`` handler as a ``(message)`` handler.

    - Missing argument -> replies with ``usage`` and stops.
    - ``validator`` raising ``ValidationError`` -> replies ``❌ <error>`` and stops.
    - Otherwise calls the inner handler with the parsed (and validated) value.
    """

    def decorator(func: Handler) -> Callable[[types.Message], Awaitable[None]]:
        @wraps(func)
        async def wrapper(message: types.Message) -> None:
            parts = (message.text or "").split(maxsplit=1)
            if len(parts) < 2 or not parts[1].strip():
                await message.answer(usage)
                return
            value = parts[1].strip()
            if validator is not None:
                try:
                    value = validator(value)
                except ValidationError as exc:
                    await message.answer(f"❌ {exc}")
                    return
            await func(message, value)

        # functools.wraps sets __wrapped__, which inspect.signature (and thus
        # aiogram's DI) would follow back to func's (message, value) signature and
        # try to inject a non-existent "value". Pin the wrapper's own signature so
        # aiogram injects only "message".
        wrapper.__signature__ = _MESSAGE_ONLY_SIGNATURE
        return wrapper

    return decorator
