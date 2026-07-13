import asyncio
from dataclasses import dataclass
from typing import Optional

from utils.logger import logger


@dataclass(frozen=True)
class ShellResult:
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool = False


async def run_command(
    cmd: list[str],
    timeout: int = 120,
    cwd: Optional[str] = None,
) -> ShellResult:
    """Run an external command safely (no shell=True)."""
    logger.info("Running command: %s", " ".join(cmd))
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        logger.warning("Command timed out: %s", " ".join(cmd))
        return ShellResult(
            stdout="",
            stderr="Command timed out.",
            returncode=1,
            timed_out=True,
        )

    return ShellResult(
        stdout=stdout.decode("utf-8", errors="replace"),
        stderr=stderr.decode("utf-8", errors="replace"),
        returncode=proc.returncode or 0,
    )


class ScanLock:
    """Global lock preventing parallel scans."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._current_task: Optional[str] = None

    @property
    def is_locked(self) -> bool:
        return self._lock.locked()

    @property
    def current_task(self) -> Optional[str]:
        return self._current_task

    async def acquire(self, task_name: str) -> bool:
        if self.is_locked:
            return False
        await self._lock.acquire()
        self._current_task = task_name
        return True

    def release(self) -> None:
        self._current_task = None
        if self._lock.locked():
            self._lock.release()


scan_lock = ScanLock()
