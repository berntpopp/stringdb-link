"""Configuration management for StringDB-Link with nested models.

This module provides the main configuration class that uses nested Pydantic models
for better organization and maintainability.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .config_models import (
    CacheConfigModel,
    CORSConfigModel,
    HealthCheckConfigModel,
    LoggingConfigModel,
    MCPConfigModel,
    PerformanceConfigModel,
    SecurityConfigModel,
    StringDBAPIConfigModel,
)


class Settings(BaseSettings):
    """Main application settings with nested configuration models."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__",
    )

    # Server Configuration
    host: str = Field(default="127.0.0.1", description="Server host address")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    transport: Literal["http", "stdio", "unified"] = Field(
        default="unified",
        description="Transport mode: http, stdio, or unified",
    )
    reload: bool = Field(default=False, description="Enable auto-reload in development")

    # Development Configuration
    debug: bool = Field(default=False, description="Enable debug mode")
    development_mode: bool = Field(default=False, description="Enable development mode")

    # Nested Configuration Models
    stringdb_api: StringDBAPIConfigModel = Field(
        default_factory=StringDBAPIConfigModel,
        description="StringDB API configuration",
    )
    cache: CacheConfigModel = Field(
        default_factory=CacheConfigModel,
        description="Caching configuration",
    )
    cors: CORSConfigModel = Field(
        default_factory=CORSConfigModel,
        description="CORS configuration",
    )
    logging: LoggingConfigModel = Field(
        default_factory=LoggingConfigModel,
        description="Logging configuration",
    )
    security: SecurityConfigModel = Field(
        default_factory=SecurityConfigModel,
        description="Security configuration",
    )
    performance: PerformanceConfigModel = Field(
        default_factory=PerformanceConfigModel,
        description="Performance configuration",
    )
    health_check: HealthCheckConfigModel = Field(
        default_factory=HealthCheckConfigModel,
        description="Health check configuration",
    )
    mcp: MCPConfigModel = Field(
        default_factory=MCPConfigModel,
        description="MCP configuration",
    )

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.development_mode or self.debug or self.reload

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.is_development

    # Backward compatibility properties for existing code
    @property
    def stringdb_base_url(self) -> str:
        """Get StringDB base URL for backward compatibility."""
        return self.stringdb_api.base_url

    @property
    def stringdb_request_timeout(self) -> int:
        """Get StringDB request timeout for backward compatibility."""
        return self.stringdb_api.timeout

    @property
    def stringdb_rate_limit_delay(self) -> float:
        """Get StringDB rate limit delay for backward compatibility."""
        return 1.0 / self.stringdb_api.rate_limit_per_second

    @property
    def stringdb_max_retries(self) -> int:
        """Get StringDB max retries for backward compatibility."""
        return self.stringdb_api.max_retries

    @property
    def stringdb_retry_delay(self) -> float:
        """Get StringDB retry delay for backward compatibility."""
        return self.stringdb_api.retry_delay

    @property
    def cache_enabled(self) -> bool:
        """Get cache enabled status for backward compatibility."""
        return self.cache.enabled

    @property
    def cache_default_ttl(self) -> int:
        """Get cache default TTL for backward compatibility."""
        return self.cache.default_ttl

    @property
    def cache_identifier_ttl(self) -> int:
        """Get cache identifier TTL for backward compatibility."""
        return self.cache.identifier_ttl

    @property
    def cache_network_ttl(self) -> int:
        """Get cache network TTL for backward compatibility."""
        return self.cache.network_ttl

    @property
    def cache_enrichment_ttl(self) -> int:
        """Get cache enrichment TTL for backward compatibility."""
        return self.cache.enrichment_ttl

    @property
    def cache_image_ttl(self) -> int:
        """Get cache image TTL for backward compatibility."""
        return self.cache.image_ttl

    @property
    def cache_max_size(self) -> int:
        """Get cache max size for backward compatibility."""
        return self.cache.max_size

    @property
    def cors_allow_origins(self) -> list[str]:
        """Get CORS allow origins for backward compatibility."""
        return self.cors.allow_origins

    @property
    def cors_allow_credentials(self) -> bool:
        """Get CORS allow credentials for backward compatibility."""
        return self.cors.allow_credentials

    @property
    def cors_allow_methods(self) -> list[str]:
        """Get CORS allow methods for backward compatibility."""
        return self.cors.allow_methods

    @property
    def cors_allow_headers(self) -> list[str]:
        """Get CORS allow headers for backward compatibility."""
        return self.cors.allow_headers

    @property
    def log_level(self) -> str:
        """Get log level for backward compatibility."""
        return self.logging.level

    @property
    def log_format(self) -> str:
        """Get log format for backward compatibility."""
        return self.logging.format

    @property
    def log_file_enabled(self) -> bool:
        """Get log file enabled for backward compatibility."""
        return self.logging.file_enabled

    @property
    def log_file_path(self) -> str:
        """Get log file path for backward compatibility."""
        return self.logging.file_path

    @property
    def log_file_max_size(self) -> int:
        """Get log file max size for backward compatibility."""
        return self.logging.file_max_size

    @property
    def log_file_backup_count(self) -> int:
        """Get log file backup count for backward compatibility."""
        return self.logging.file_backup_count

    @property
    def connection_pool_size(self) -> int:
        """Get connection pool size for backward compatibility."""
        return self.performance.connection_pool_size

    @property
    def connection_pool_max_size(self) -> int:
        """Get connection pool max size for backward compatibility."""
        return self.performance.connection_pool_max_size

    @property
    def keepalive_timeout(self) -> int:
        """Get keepalive timeout for backward compatibility."""
        return self.performance.keepalive_timeout

    @property
    def mcp_path(self) -> str:
        """Get MCP path for backward compatibility."""
        return self.mcp.path

    @property
    def mcp_server_name(self) -> str:
        """Get MCP server name for backward compatibility."""
        return self.mcp.server_name

    def get_stringdb_url(self, endpoint: str) -> str:
        """Get full StringDB API URL for an endpoint."""
        base = self.stringdb_api.base_url.rstrip("/")
        endpoint = endpoint.lstrip("/")
        return f"{base}/{endpoint}"

    def get_cache_ttl(self, cache_type: str) -> int:
        """Get cache TTL for a specific cache type."""
        return self.cache.get_ttl(cache_type)


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment and files."""
    global settings
    settings = Settings()
    return settings


# Configuration accessors for nested models
def get_stringdb_api_config() -> StringDBAPIConfigModel:
    """Get StringDB API configuration."""
    return settings.stringdb_api


def get_cache_config() -> CacheConfigModel:
    """Get cache configuration."""
    return settings.cache


def get_cors_config() -> CORSConfigModel:
    """Get CORS configuration."""
    return settings.cors


def get_logging_config() -> LoggingConfigModel:
    """Get logging configuration."""
    return settings.logging


def get_security_config() -> SecurityConfigModel:
    """Get security configuration."""
    return settings.security


def get_performance_config() -> PerformanceConfigModel:
    """Get performance configuration."""
    return settings.performance


def get_health_check_config() -> HealthCheckConfigModel:
    """Get health check configuration."""
    return settings.health_check


def get_mcp_config() -> MCPConfigModel:
    """Get MCP configuration."""
    return settings.mcp
