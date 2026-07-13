import base64
import hashlib
import secrets
import urllib.parse
import uuid
from datetime import datetime, timezone

import aiohttp
from aiogram import Router, types
from aiogram.filters import Command

from services.ai_summarizer import summarize
from services.reports import get_last_report, send_report
from services.shell import run_command
from services.validators import ValidationError, validate_domain, validate_email, validate_ipv4
from utils.logger import logger

utils_router = Router()


@utils_router.message(Command("password"))
async def cmd_password(message: types.Message):
    args = message.text.split(maxsplit=1)
    length = 16
    if len(args) >= 2:
        try:
            length = max(8, min(64, int(args[1])))
        except ValueError:
            await message.answer("Usage: /password [length 8-64]")
            return

    password = secrets.token_urlsafe(length)[:length]
    await message.answer(f"🔑 Generated password:\n`{password}`", parse_mode="Markdown")


@utils_router.message(Command("uuid"))
async def cmd_uuid(message: types.Message):
    await message.answer(f"🆔 `{uuid.uuid4()}`", parse_mode="Markdown")


@utils_router.message(Command("hash"))
async def cmd_hash(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /hash \u003ctext\u003e")
        return

    text = args[1]
    lines = [
        f"🔐 Hashes for: `{text[:50]}`",
        f"MD5: `{hashlib.md5(text.encode()).hexdigest()}`",
        f"SHA1: `{hashlib.sha1(text.encode()).hexdigest()}`",
        f"SHA256: `{hashlib.sha256(text.encode()).hexdigest()}`",
    ]
    await message.answer("\n".join(lines), parse_mode="Markdown")


@utils_router.message(Command("b64"))
async def cmd_b64(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /b64 \u003ctext\u003e — encodes text to base64")
        return

    text = args[1]
    encoded = base64.b64encode(text.encode()).decode()
    await message.answer(f"🔁 Base64:\n`{encoded}`", parse_mode="Markdown")


@utils_router.message(Command("b64decode"))
async def cmd_b64decode(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /b64decode \u003cbase64\u003e")
        return

    try:
        decoded = base64.b64decode(args[1]).decode("utf-8", errors="replace")
    except Exception as exc:
        await message.answer(f"❌ Decode error: {exc}")
        return

    await message.answer(f"🔁 Decoded:\n`{decoded}`", parse_mode="Markdown")


@utils_router.message(Command("urlencode"))
async def cmd_urlencode(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /urlencode \u003ctext\u003e")
        return

    import urllib.parse

    encoded = urllib.parse.quote(args[1])
    await message.answer(f"🔗 URL-encoded:\n`{encoded}`", parse_mode="Markdown")


@utils_router.message(Command("email"))
async def cmd_email(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /email \u003cemail\u003e")
        return

    try:
        email = validate_email(args[1])
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    domain = email.split("@", 1)[1]
    result = await run_command(["dig", "+short", "MX", domain], timeout=30)
    mx = result.stdout.strip() or "No MX records found."
    await message.answer(
        f"📧 Email: `{email}`\nDomain: `{domain}`\n\nMX records:\n```\n{mx}\n```",
        parse_mode="Markdown",
    )


@utils_router.message(Command("weather"))
async def cmd_weather(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /weather \u003ccity\u003e")
        return

    city = args[1].strip()
    try:
        async with aiohttp.ClientSession() as session:
            geo_url = "https://geocoding-api.open-meteo.com/v1/search"
            async with session.get(geo_url, params={"name": city, "count": "1"}) as resp:
                geo = await resp.json()
                if not geo.get("results"):
                    await message.answer(f"❌ City not found: `{city}`", parse_mode="Markdown")
                    return
                loc = geo["results"][0]
                lat = loc["latitude"]
                lon = loc["longitude"]
                name = loc.get("name", city)
                country = loc.get("country", "?")

            weather_url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current_weather": "true",
            }
            async with session.get(weather_url, params=params) as resp:
                data = await resp.json()
                current = data["current_weather"]
                temp = current["temperature"]
                wind = current["windspeed"]
                code = current["weathercode"]

        await message.answer(
            f"🌤 Weather in *{name}*, {country}\n"
            f"Temperature: `{temp}°C`\n"
            f"Wind speed: `{wind} km/h`\n"
            f"Weather code: `{code}`",
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.exception("Weather request failed")
        await message.answer(f"❌ Weather request failed: {exc}")


@utils_router.message(Command("reverseip"))
async def cmd_reverseip(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /reverseip \u003cIP\u003e")
        return

    try:
        ip = validate_ipv4(args[1], allow_private=False)
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    logger.info("Reverse DNS requested for %s", ip)
    result = await run_command(["dig", "+short", "-x", ip], timeout=30)
    output = result.stdout.strip() or "No PTR record found."
    await send_report(message, output, prefix=f"🔄 Reverse DNS for `{ip}`")


@utils_router.message(Command("summary"))
async def cmd_summary(message: types.Message):
    last = get_last_report(message.from_user.id)
    if not last:
        await message.answer(
            "❌ No report found. Run any scan/OSINT command first, then use /summary."
        )
        return

    await message.answer("🧠 Asking AI to summarize the last report...")
    summary = await summarize(last)
    if summary is None:
        await message.answer(
            "🧠 AI is not configured.\n\n"
            "Add to your `.env` file:\n"
            "```\n"
            "AI_API_KEY=sk-...\n"
            "AI_BASE_URL=https://api.openai.com/v1\n"
            "AI_MODEL=gpt-4o-mini\n"
            "```",
            parse_mode="Markdown",
        )
        return

    await send_report(message, summary, prefix="🧠 *AI Summary*")


@utils_router.message(Command("timestamp"))
async def cmd_timestamp(message: types.Message):
    now = datetime.now(timezone.utc)
    lines = [
        f"🕒 UTC: `{now.isoformat()}`",
        f"Unix: `{int(now.timestamp())}`",
    ]
    await message.answer("\n".join(lines), parse_mode="Markdown")
