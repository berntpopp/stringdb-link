"""FastAPI dependencies for StringDB-Link routes.

This module provides dependency injection for common services
and utilities used across route handlers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from stringdb_link.api.client import StringDBClient
from stringdb_link.config import Settings, get_settings
from stringdb_link.logging_config import get_logger
from stringdb_link.services.stringdb_service import StringDBService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from structlog.typing import FilteringBoundLogger


async def get_stringdb_client() -> AsyncGenerator[StringDBClient, None]:
    """Dependency to get StringDB client instance.

    Yields:
        StringDB client with proper lifecycle management
    """
    settings = get_settings()
    client = StringDBClient(caller_identity=settings.stringdb_api.caller_identity)
    try:
        yield client
    finally:
        await client.close()


def get_settings_dependency() -> Settings:
    """Dependency to get application settings.

    Returns:
        Application settings instance
    """
    return get_settings()


def get_logger_dependency() -> FilteringBoundLogger:
    """Dependency to get logger instance.

    Returns:
        Structured logger instance
    """
    return get_logger("stringdb_api")


# Type aliases for cleaner route signatures
StringDBClientDep = Depends(get_stringdb_client)
SettingsDep = Depends(get_settings_dependency)
LoggerDep = Depends(get_logger_dependency)


async def get_stringdb_service(
    client: StringDBClient = StringDBClientDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> StringDBService:
    """Dependency to get StringDB service instance.

    Args:
        client: StringDB client dependency
        logger: Logger dependency

    Returns:
        StringDB service instance
    """
    return StringDBService(client=client, logger=logger)


StringDBServiceDep = Depends(get_stringdb_service)
