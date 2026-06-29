"""Nested configuration models for StringDB-Link.

This module provides nested Pydantic models for better organization
of configuration settings.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class StringDBAPIConfigModel(BaseModel):
    """StringDB API configuration model."""

    base_url: str = Field(
        default="https://version-12-0.string-db.org/api",
        description="Base URL for StringDB API",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds",
    )
    rate_limit_per_second: float = Field(
        default=1.0,
        gt=0.0,
        le=10.0,
        description="API rate limit (requests per second)",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts",
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Base delay for retries in seconds",
    )
    user_agent: str = Field(
        default="StringDB-Link/0.1.0",
        description="User agent string for API requests",
    )
    caller_identity: str = Field(
        default="StringDB-Link/0.1.0",
        description="Caller identity string for identifying the client to STRING API",
    )
    endpoints: dict[str, str] = Field(
        default={
            "resolve": "json/get_string_ids",
            "network": "json/network",
            "interactions": "json/interaction_partners",
            "enrichment": "json/enrichment",
            "annotations": "json/functional_annotation",
            "images": "image/network",
            "homology": "json/homology",
            "homology_best": "json/homology_best",
            "ppi_enrichment": "json/ppi_enrichment",
            "enrichment_image": "image/enrichment",
        },
        description="API endpoint paths",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Ensure base URL doesn't end with forward slash."""
        return v.rstrip("/")


class CacheConfigModel(BaseModel):
    """Cache configuration model."""

    enabled: bool = Field(default=True, description="Enable caching")
    default_ttl: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Default cache TTL in seconds",
    )
    identifier_ttl: int = Field(
        default=86400,
        ge=3600,
        le=604800,
        description="Identifier cache TTL in seconds",
    )
    network_ttl: int = Field(
        default=43200,
        ge=1800,
        le=172800,
        description="Network cache TTL in seconds",
    )
    enrichment_ttl: int = Field(
        default=21600,
        ge=1800,
        le=86400,
        description="Enrichment cache TTL in seconds",
    )
    image_ttl: int = Field(
        default=7200,
        ge=300,
        le=43200,
        description="Image cache TTL in seconds",
    )
    max_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Maximum cache size",
    )

    def get_ttl(self, cache_type: str) -> int:
        """Get cache TTL for a specific cache type."""
        cache_ttls = {
            "identifier": self.identifier_ttl,
            "network": self.network_ttl,
            "enrichment": self.enrichment_ttl,
            "image": self.image_ttl,
        }
        return cache_ttls.get(cache_type, self.default_ttl)


class CORSConfigModel(BaseModel):
    """CORS configuration model."""

    allow_origins: list[str] = Field(
        # Never default to "*" together with allow_credentials=True (Container &
        # Deployment Hardening Standard v1 / CORS spec): a wildcard credentialed
        # origin is rejected by browsers and is an unsafe default. Production
        # origins are injected at runtime via CORS__ALLOW_ORIGINS (env).
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins",
    )
    allow_credentials: bool = Field(
        default=True,
        description="Allow CORS credentials",
    )
    allow_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed CORS methods",
    )
    allow_headers: list[str] = Field(
        default=["*"],
        description="Allowed CORS headers",
    )

    @field_validator("allow_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("allow_methods", mode="before")
    @classmethod
    def parse_methods(cls, v: Any) -> list[str]:
        """Parse CORS methods from string or list."""
        if isinstance(v, str):
            return [method.strip().upper() for method in v.split(",") if method.strip()]
        return [method.upper() for method in v]

    @field_validator("allow_headers", mode="before")
    @classmethod
    def parse_headers(cls, v: Any) -> list[str]:
        """Parse CORS headers from string or list."""
        if isinstance(v, str):
            return [header.strip() for header in v.split(",") if header.strip()]
        return v


class LoggingConfigModel(BaseModel):
    """Logging configuration model."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    format: Literal["json", "text"] = Field(
        default="json",
        description="Log format: json or text",
    )
    file_enabled: bool = Field(default=False, description="Enable file logging")
    file_path: str = Field(
        default="./logs/stringdb-link.log",
        description="Log file path",
    )
    file_max_size: int = Field(
        default=10485760,
        ge=1048576,
        le=104857600,
        description="Max log file size",
    )
    file_backup_count: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of log file backups",
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate log level is uppercase."""
        return v.upper()


class SecurityConfigModel(BaseModel):
    """Security configuration model."""

    api_key_required: bool = Field(default=False, description="Require API key")
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Rate limit requests per window",
    )
    rate_limit_window: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Rate limit window in seconds",
    )


class PerformanceConfigModel(BaseModel):
    """Performance configuration model."""

    max_concurrent_requests: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Maximum concurrent requests",
    )
    connection_pool_size: int = Field(
        default=20,
        ge=5,
        le=100,
        description="HTTP connection pool size",
    )
    connection_pool_max_size: int = Field(
        default=100,
        ge=10,
        le=500,
        description="Maximum HTTP connection pool size",
    )
    keepalive_timeout: int = Field(
        default=5,
        ge=1,
        le=30,
        description="Connection keepalive timeout",
    )


class HealthCheckConfigModel(BaseModel):
    """Health check configuration model."""

    enabled: bool = Field(default=True, description="Enable health checks")
    interval: int = Field(
        default=30,
        ge=10,
        le=300,
        description="Health check interval in seconds",
    )
    timeout: int = Field(
        default=10,
        ge=1,
        le=60,
        description="Health check timeout in seconds",
    )


class MCPConfigModel(BaseModel):
    """MCP configuration model."""

    path: str = Field(default="/mcp", description="MCP endpoint path")
    server_name: str = Field(
        default="StringDB-Link Server",
        description="MCP server name",
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Ensure MCP path starts with forward slash."""
        if not v.startswith("/"):
            return f"/{v}"
        return v
