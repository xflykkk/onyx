"""Logging utilities for Agent RAG."""

import logging
import sys
from typing import Optional


_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    date_format: Optional[str] = None,
) -> None:
    """
    Setup logging configuration.

    Args:
        level: Logging level
        format_string: Custom format string
        date_format: Custom date format
    """
    global _configured

    if _configured:
        return

    logging.basicConfig(
        level=level,
        format=format_string or _LOG_FORMAT,
        datefmt=date_format or _DATE_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Set lower log level for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("litellm").setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    # Ensure logging is configured
    if not _configured:
        setup_logging()

    # Prefix with agent_rag if not already
    if not name.startswith("agent_rag"):
        name = f"agent_rag.{name}"

    return logging.getLogger(name)


class LogContext:
    """Context manager for temporary log level changes."""

    def __init__(
        self,
        logger: logging.Logger,
        level: int,
    ) -> None:
        self.logger = logger
        self.level = level
        self.original_level: int = logging.NOTSET

    def __enter__(self) -> "LogContext":
        self.original_level = self.logger.level
        self.logger.setLevel(self.level)
        return self

    def __exit__(self, *args: object) -> None:
        self.logger.setLevel(self.original_level)
