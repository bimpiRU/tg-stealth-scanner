from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import SCAN_TIMEOUT
from services.reports import save_report, send_report
from services.shell import ScanLock, run_command, scan_lock
from services.validators import ValidationError, validate_ipv4
from utils.logger import logger

scan_router = Router()


class ScanConfirm(StatesGroup):
    waiting_for_confirm = State()


async def _run_nmap(target_ip: str, full: bool = False) -> str:
    if full:
        cmd = ["nmap", "-sS", "-sV", "-O", "--top-ports", "1000", "-T3", target_ip]
        timeout = SCAN_TIMEOUT * 2
    else:
        cmd = ["nmap", "-sS", "-T2", "-F", target_ip]
        timeout = SCAN_TIMEOUT

    result = await run_command(cmd, timeout=timeout)
    output = result.stdout if result.returncode == 0 else result.stderr
    if not output.strip():
        output = "Scan completed but produced no output."
    return output


@scan_router.message(Command("scan"))
async def cmd_scan(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /scan \u003cIP\u003e")
        return

    try:
        target_ip = validate_ipv4(args[1], allow_private=True)
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    if not await scan_lock.acquire(f"scan {target_ip}"):
        await message.answer("⏳ Another scan is already running. Wait or use /cancel.")
        return

    try:
        logger.info("Stealth scan started for %s by admin", target_ip)
        await message.answer(
            f"🛰 Starting stealth scan of `{target_ip}`...\nThis may take up to 2 minutes.",
            parse_mode="Markdown",
        )
        output = await _run_nmap(target_ip, full=False)
        save_report("scan", target_ip, output)
        await send_report(message, output, prefix=f"🛰 Scan result for `{target_ip}`")
    finally:
        scan_lock.release()


@scan_router.message(Command("scanfull"))
async def cmd_scanfull(message: types.Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /scanfull \u003cIP\u003e")
        return

    try:
        target_ip = validate_ipv4(args[1], allow_private=False)
    except ValidationError as exc:
        await message.answer(f"❌ {exc}")
        return

    await state.update_data(target_ip=target_ip)
    await state.set_state(ScanConfirm.waiting_for_confirm)
    await message.answer(
        f"⚠️ You are about to run an *extended* scan of `{target_ip}`.\n"
        f"This is slower and noisier than a stealth scan.\n\n"
        f"Reply `yes` within 60 seconds to confirm, or anything else to cancel.",
        parse_mode="Markdown",
    )


@scan_router.message(ScanConfirm.waiting_for_confirm, F.text.lower() == "yes")
async def cmd_scanfull_confirmed(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target_ip = data.get("target_ip")
    await state.clear()

    if not target_ip:
        await message.answer("❌ Confirmation state expired. Run /scanfull again.")
        return

    if not await scan_lock.acquire(f"scanfull {target_ip}"):
        await message.answer("⏳ Another scan is already running. Wait or use /cancel.")
        return

    try:
        logger.info("Full scan started for %s by admin", target_ip)
        await message.answer(
            f"🚀 Starting full scan of `{target_ip}`...\nThis may take several minutes.",
            parse_mode="Markdown",
        )
        output = await _run_nmap(target_ip, full=True)
        save_report("scanfull", target_ip, output)
        await send_report(message, output, prefix=f"🚀 Full scan result for `{target_ip}`")
    finally:
        scan_lock.release()


@scan_router.message(ScanConfirm.waiting_for_confirm)
async def cmd_scanfull_cancelled(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Full scan cancelled.")
