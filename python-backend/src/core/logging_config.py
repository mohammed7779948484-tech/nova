"""Structured logging configuration using structlog.

Configures structlog with JSON output for production and
console output for development.  Also integrates stdlib logging
so that third-party libraries (uvicorn, httpx, etc.) flow through
the same pipeline.

In production mode (log_format="json"), also adds a
TimedRotatingFileHandler for daily log file rotation (FR-044).
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

import structlog


def setup_logging(log_format: str = "console") -> None:
    """Configure structlog + stdlib logging integration.

    Args:
        log_format: "json" for production, "console" for development.
    """
    from src.core.pii_scrubber import PIIScrubberProcessor

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            PIIScrubberProcessor(),
            renderer,
        ],
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)

    # Always add stdout handler
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    root_logger.addHandler(stdout_handler)

    # In production, also add daily rotating file handler (FR-044)
    if log_format == "json":
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_dir / "nova.log",
            when="midnight",
            backupCount=30,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
