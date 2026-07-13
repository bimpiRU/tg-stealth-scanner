import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import LOGS_DIR


class TokenMaskingFilter(logging.Filter):
    """Replace BOT_TOKEN-like values in log records to avoid leaking secrets."""

    _token_pattern = re.compile(r"\d{8,10}:[A-Za-z0-9_-]{35}")

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._token_pattern.sub("***", str(record.msg))
        if record.args:
            record.args = tuple(self._token_pattern.sub("***", str(arg)) for arg in record.args)
        return True


def setup_logger(name: str = "tg_stealth_scanner") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(TokenMaskingFilter())
    logger.addHandler(console_handler)

    log_file = Path(LOGS_DIR) / "bot.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(TokenMaskingFilter())
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()
