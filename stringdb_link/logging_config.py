"""Logging configuration for StringDB-Link.

This module sets up structured logging using structlog with appropriate
formatters and handlers for different environments.
"""

from __future__ import annotations

import hashlib
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import structlog
from rich.console import Console
from rich.logging import RichHandler

from .config import settings

# HTTP status constants
HTTP_CLIENT_ERROR = 400

# Event-dict keys whose values can carry caller-supplied protein/gene
# identifiers, the STRING URLs that embed those identifiers in their query
# string, or raw exception text interpolated from them. Such values may be
# patient-derived (GDPR Art. 9), so they are digested rather than logged raw.
_REDACT_KEYS: frozenset[str] = frozenset(
    {
        "identifiers",
        "identifier",
        "url",
        "urls",
        "query",
        "q",
        "error",
        "error_message",
        "detail",
        "exception",
    },
)

if TYPE_CHECKING:
    from structlog.typing import EventDict, FilteringBoundLogger, Processor, WrappedLogger


def _digest(value: object) -> str:
    """Return a short, non-reversible digest of a sensitive value.

    Keeps log lines correlatable (identical inputs share a digest) without
    exposing the raw identifier/URL/exception text.
    """
    raw = value if isinstance(value, str) else repr(value)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()[:12]


def redact_sensitive_processor(
    _logger: WrappedLogger,
    _method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """structlog processor that strips PII carriers before rendering.

    - Drops ``exc_info`` and any rendered ``exception`` frames so raw exception
      strings/tracebacks (which interpolate identifiers/URLs) are never emitted;
      ``error_type`` is preserved for triage.
    - Replaces the value of every denylisted key with a non-reversible digest.
    """
    event_dict.pop("exc_info", None)
    event_dict.pop("exception", None)
    for key in list(event_dict):
        if key in _REDACT_KEYS and event_dict[key] is not None:
            event_dict[key] = _digest(event_dict[key])
    return event_dict


class RedactingFilter(logging.Filter):
    """Scrub the stdlib traceback channel from every emitted record.

    ``logging.Logger.exception()`` (used pervasively for error handling, and
    the target of structlog's ``.exception()``) hard-sets ``exc_info=True`` on
    the record *after* the structlog processor chain runs, so a processor alone
    cannot remove it. A rendered traceback ends in the exception's ``str`` --
    which interpolates caller identifiers/URLs (possibly patient-derived, GDPR
    Art. 9). We drop ``exc_info``/``stack_info`` on all records; the structured
    ``error_type`` field survives for triage. Trade-off: tracebacks are never
    written to logs (accepted under the fleet "no PII in logs" contract).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return True


def configure_stdlib_logging() -> None:
    """Configure standard library logging."""
    # Set root logger level
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure handlers based on environment
    if settings.is_development:
        # Rich handler for development
        console = Console(stderr=True)
        handler = RichHandler(
            console=console,
            show_time=True,
            show_path=True,
            markup=True,
            rich_tracebacks=True,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
    else:
        # Standard handler for production
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        handler.setFormatter(formatter)

    handler.setLevel(getattr(logging, settings.log_level))
    handler.addFilter(RedactingFilter())
    root_logger.addHandler(handler)

    # Add file handler if enabled
    if settings.log_file_enabled:
        add_file_handler(root_logger)

    # Configure specific loggers
    configure_third_party_loggers()


def add_file_handler(logger: logging.Logger) -> None:
    """Add rotating file handler to logger."""
    log_path = Path(settings.log_file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_path,
        maxBytes=settings.log_file_max_size,
        backupCount=settings.log_file_backup_count,
        encoding="utf-8",
    )

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, settings.log_level))
    file_handler.addFilter(RedactingFilter())

    logger.addHandler(file_handler)


def configure_third_party_loggers() -> None:
    """Configure third-party library loggers."""
    # Reduce verbosity of third-party loggers
    loggers_config = {
        "httpx": "WARNING",
        "httpcore": "WARNING",
        "uvicorn.access": "WARNING" if not settings.debug else "INFO",
        "uvicorn.error": "INFO",
        "fastapi": "INFO",
        "fastmcp": "WARNING" if not settings.debug else "INFO",
        "mcp": "WARNING" if not settings.debug else "INFO",
    }

    for logger_name, level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, level))


def configure_structlog() -> None:
    """Configure structlog for structured logging."""
    # Shared processors
    shared_processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.debug:
        shared_processors.append(structlog.dev.set_exc_info)

    # Redaction runs last in the shared chain: after set_exc_info (so exc_info
    # is present to strip) but before any renderer turns exception frames into
    # text. This closes the PII-in-logs class for every call site at the sink.
    shared_processors.append(redact_sensitive_processor)

    # Configure processors based on format
    processors: list[Processor]
    if settings.log_format == "json":
        processors = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    elif settings.is_development:
        processors = [*shared_processors, structlog.dev.ConsoleRenderer(colors=True)]
    else:
        processors = [*shared_processors, structlog.dev.ConsoleRenderer(colors=False)]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def configure_logging() -> FilteringBoundLogger:
    """Configure complete logging setup and return logger."""
    # Set up stdlib logging first
    configure_stdlib_logging()

    # Then configure structlog
    configure_structlog()

    # Return configured logger
    return cast("FilteringBoundLogger", structlog.get_logger("stringdb_link"))


def get_logger(name: str) -> FilteringBoundLogger:
    """Get a logger instance for a specific module."""
    return cast("FilteringBoundLogger", structlog.get_logger(name))


def log_request(
    logger: FilteringBoundLogger,
    method: str,
    url: str,
    status_code: int | None = None,
    duration: float | None = None,
    **kwargs: Any,
) -> None:
    """Log HTTP request with structured data."""
    log_data = {
        "event": "http_request",
        "method": method,
        "url": url,
        **kwargs,
    }

    if status_code is not None:
        log_data["status_code"] = status_code

    if duration is not None:
        log_data["duration_ms"] = round(duration * 1000, 2)

    if status_code and status_code >= HTTP_CLIENT_ERROR:
        logger.warning("HTTP request failed", **log_data)
    else:
        logger.info("HTTP request completed", **log_data)


def log_stringdb_request(
    logger: FilteringBoundLogger,
    endpoint: str,
    method: str = "POST",
    status_code: int | None = None,
    duration: float | None = None,
    *,
    cache_hit: bool = False,
    **kwargs: Any,
) -> None:
    """Log StringDB API request with structured data."""
    log_data = {
        "endpoint": endpoint,
        "method": method,
        "cache_hit": cache_hit,
        **kwargs,
    }

    if status_code is not None:
        log_data["status_code"] = status_code

    if duration is not None:
        log_data["duration_ms"] = round(duration * 1000, 2)

    if cache_hit:
        logger.debug("StringDB request served from cache", **log_data)
    elif status_code and status_code >= 400:
        logger.warning("StringDB request failed", **log_data)
    else:
        logger.info("StringDB request completed", **log_data)


def log_server_startup(
    logger: FilteringBoundLogger,
    transport: str,
    host: str,
    port: int,
    **kwargs: Any,
) -> None:
    """Log server startup information."""
    logger.info(
        "Server starting",
        transport=transport,
        host=host,
        port=port,
        debug=settings.debug,
        development_mode=settings.development_mode,
        **kwargs,
    )


def log_error(
    logger: FilteringBoundLogger,
    error: Exception,
    context: str | None = None,
    **kwargs: Any,
) -> None:
    """Log error with structured data and context."""
    log_data = {
        "event": "error",
        "error_type": type(error).__name__,
        "error_message": str(error),
        **kwargs,
    }

    if context:
        log_data["context"] = context

    # Add exception info for unexpected errors
    if not isinstance(error, (ValueError, TypeError)):
        logger.error("Error occurred", **log_data, exc_info=True)
    else:
        logger.error("Error occurred", **log_data)


def log_performance(
    logger: FilteringBoundLogger,
    operation: str,
    duration: float,
    **kwargs: Any,
) -> None:
    """Log performance metrics."""
    logger.info(
        "Performance metric",
        event_type="performance",
        operation=operation,
        duration_ms=round(duration * 1000, 2),
        **kwargs,
    )


def log_cache_operation(
    logger: FilteringBoundLogger,
    operation: str,
    key: str,
    hit: bool = False,
    **kwargs: Any,
) -> None:
    """Log cache operation."""
    logger.debug(
        "Cache operation",
        event_type="cache_operation",
        operation=operation,
        key=key,
        hit=hit,
        **kwargs,
    )
