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


_MAX_OUTPUT_BYTES = 1_000_000  # cap per stream (~1 MB) to bound memory


async def run_command(
    cmd: list[str],
    timeout: int = 120,
    cwd: Optional[str] = None,
    input_data: Optional[str] = None,
    cancellable: bool = False,
    max_output_bytes: int = _MAX_OUTPUT_BYTES,
) -> ShellResult:
    """Run an external command safely (no shell=True).

    stdin is closed (DEVNULL) by default so a child can never block waiting for
    input. Pass ``input_data`` to feed a command's stdin (used to pipe one tool's
    output into another without an intermediate shell).

    When ``cancellable`` is set the running process is registered with
    ``scan_lock`` so that ``/cancel`` can terminate it mid-flight.

    stdout/stderr are capped at ``max_output_bytes`` each so a pathological tool
    (e.g. crt.sh JSON for a huge domain) can't blow up memory.
    """
    logger.info("Running command: %s", " ".join(cmd))
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE if input_data is not None else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    if cancellable:
        scan_lock.register_proc(proc)
    stdin_bytes = input_data.encode("utf-8") if input_data is not None else None
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=stdin_bytes), timeout=timeout
        )
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
    finally:
        if cancellable:
            scan_lock.clear_proc()

    return ShellResult(
        stdout=_decode_capped(stdout, max_output_bytes),
        stderr=_decode_capped(stderr, max_output_bytes),
        returncode=proc.returncode or 0,
    )


def _decode_capped(raw: bytes, limit: int) -> str:
    if len(raw) > limit:
        raw = raw[:limit]
        suffix = b"\n[output truncated]"
        return raw.decode("utf-8", errors="replace") + suffix.decode()
    return raw.decode("utf-8", errors="replace")


class ScanLock:
    """Global lock preventing parallel scans, with cooperative cancellation.

    A cancellable command registers its live process here so that ``/cancel``
    can actually ``kill()`` it, instead of only setting a flag the scan reads
    after it finishes.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._current_task: Optional[str] = None
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._cancelled: bool = False

    @property
    def is_locked(self) -> bool:
        return self._lock.locked()

    @property
    def current_task(self) -> Optional[str]:
        return self._current_task

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    async def acquire(self, task_name: str) -> bool:
        if self.is_locked:
            return False
        await self._lock.acquire()
        self._current_task = task_name
        self._cancelled = False
        self._proc = None
        return True

    def register_proc(self, proc: asyncio.subprocess.Process) -> None:
        """Track the process backing the current scan step."""
        self._proc = proc

    def clear_proc(self) -> None:
        self._proc = None

    def cancel(self) -> bool:
        """Kill the running scan process. Returns True if a scan was cancelled."""
        if not self.is_locked:
            return False
        self._cancelled = True
        proc = self._proc
        if proc is not None and proc.returncode is None:
            proc.kill()
        return True

    def release(self) -> None:
        self._current_task = None
        self._proc = None
        if self._lock.locked():
            self._lock.release()


scan_lock = ScanLock()
