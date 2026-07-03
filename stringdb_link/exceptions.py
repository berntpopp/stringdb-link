"""Custom exceptions for StringDB-Link.

This module defines custom exception classes for different types of errors
that can occur during StringDB API operations and server functionality.
"""

from __future__ import annotations

from typing import Any


class StringDBLinkError(Exception):
    """Base exception class for StringDB-Link errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Error message
            status_code: HTTP status code if applicable
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}

    def __str__(self) -> str:
        """Return string representation of the error."""
        return self.message

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        result: dict[str, Any] = {
            "error": self.__class__.__name__,
            "message": self.message,
        }
        if self.status_code:
            result["status_code"] = self.status_code
        if self.details:
            result["details"] = self.details
        return result


class StringDBAPIError(StringDBLinkError):
    """Exception raised when StringDB API returns an error."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
        endpoint: str | None = None,
    ) -> None:
        """Initialize the API error.

        Args:
            message: Error message
            status_code: HTTP status code from StringDB API
            response_data: Raw response data from API
            endpoint: API endpoint that caused the error
        """
        details: dict[str, Any] = {}
        if response_data:
            details["response_data"] = response_data
        if endpoint:
            details["endpoint"] = endpoint

        super().__init__(message, status_code, details)
        self.response_data = response_data
        self.endpoint = endpoint


class StringDBTimeoutError(StringDBAPIError):
    """Exception raised when StringDB API request times out."""

    def __init__(
        self,
        message: str = "StringDB API request timed out",
        timeout: float | None = None,
        endpoint: str | None = None,
    ) -> None:
        """Initialize the timeout error.

        Args:
            message: Error message
            timeout: Timeout value that was exceeded
            endpoint: API endpoint that timed out
        """
        details: dict[str, Any] = {}
        if timeout:
            details["timeout"] = timeout
        if endpoint:
            details["endpoint"] = endpoint

        super().__init__(message, 408, details, endpoint)
        self.timeout = timeout


class StringDBRateLimitError(StringDBAPIError):
    """Exception raised when StringDB API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "StringDB API rate limit exceeded",
        retry_after: int | None = None,
        endpoint: str | None = None,
    ) -> None:
        """Initialize the rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
            endpoint: API endpoint that was rate limited
        """
        details: dict[str, Any] = {}
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(message, 429, details, endpoint)
        self.retry_after = retry_after


class ValidationError(StringDBLinkError):
    """Exception raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any | None = None,
        validation_errors: list[dict[str, Any]] | None = None,
    ) -> None:
        """Initialize the validation error.

        Args:
            message: Error message
            field: Field that failed validation
            value: Value that failed validation
            validation_errors: List of Pydantic validation errors
        """
        details: dict[str, Any] = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = value
        if validation_errors:
            details["validation_errors"] = validation_errors

        super().__init__(message, 400, details)
        self.field = field
        self.value = value
        self.validation_errors = validation_errors


class ProteinNotFoundError(StringDBLinkError):
    """Exception raised when a protein identifier cannot be resolved."""

    def __init__(
        self,
        identifier: str,
        species: int | None = None,
        message: str | None = None,
    ) -> None:
        """Initialize the protein not found error.

        Args:
            identifier: Protein identifier that was not found
            species: Species ID if specified
            message: Custom error message
        """
        if not message:
            message = f"Protein identifier '{identifier}' not found"
            if species:
                message += f" in species {species}"

        details: dict[str, Any] = {"identifier": identifier}
        if species:
            details["species"] = species

        super().__init__(message, 404, details)
        self.identifier = identifier
        self.species = species


class NetworkError(StringDBLinkError):
    """Exception raised when network operations fail."""

    def __init__(
        self,
        message: str,
        original_error: Exception | None = None,
        endpoint: str | None = None,
    ) -> None:
        """Initialize the network error.

        Args:
            message: Error message
            original_error: Original exception that caused this error
            endpoint: Network endpoint that failed
        """
        details: dict[str, Any] = {}
        if original_error:
            details["original_error"] = str(original_error)
            details["error_type"] = type(original_error).__name__
        if endpoint:
            details["endpoint"] = endpoint

        super().__init__(message, 502, details)
        self.original_error = original_error
        self.endpoint = endpoint


class CacheError(StringDBLinkError):
    """Exception raised when cache operations fail."""

    def __init__(
        self,
        message: str,
        cache_key: str | None = None,
        operation: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize the cache error.

        Args:
            message: Error message
            cache_key: Cache key involved in the operation
            operation: Cache operation that failed (get, set, delete)
            original_error: Original exception that caused this error
        """
        details: dict[str, Any] = {}
        if cache_key:
            details["cache_key"] = cache_key
        if operation:
            details["operation"] = operation
        if original_error:
            details["original_error"] = str(original_error)

        super().__init__(message, 500, details)
        self.cache_key = cache_key
        self.operation = operation
        self.original_error = original_error


class ConfigurationError(StringDBLinkError):
    """Exception raised when configuration is invalid."""

    def __init__(
        self,
        message: str,
        setting: str | None = None,
        value: Any | None = None,
    ) -> None:
        """Initialize the configuration error.

        Args:
            message: Error message
            setting: Configuration setting that is invalid
            value: Invalid value
        """
        details: dict[str, Any] = {}
        if setting:
            details["setting"] = setting
        if value is not None:
            details["value"] = value

        super().__init__(message, 500, details)
        self.setting = setting
        self.value = value


class MCPError(StringDBLinkError):
    """Exception raised when MCP operations fail."""

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize the MCP error.

        Args:
            message: Error message
            tool_name: MCP tool name that failed
            original_error: Original exception that caused this error
        """
        details: dict[str, Any] = {}
        if tool_name:
            details["tool_name"] = tool_name
        if original_error:
            details["original_error"] = str(original_error)

        super().__init__(message, 500, details)
        self.tool_name = tool_name
        self.original_error = original_error


class ServiceUnavailableError(StringDBLinkError):
    """Exception raised when a service is temporarily unavailable."""

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        service: str | None = None,
        retry_after: int | None = None,
    ) -> None:
        """Initialize the service unavailable error.

        Args:
            message: Error message
            service: Name of the unavailable service
            retry_after: Seconds to wait before retrying
        """
        details: dict[str, Any] = {}
        if service:
            details["service"] = service
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(message, 503, details)
        self.service = service
        self.retry_after = retry_after


class StringDBServiceError(StringDBLinkError):
    """Exception raised when service layer operations fail."""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        original_error: Exception | None = None,
        status_code: int | None = None,
    ) -> None:
        """Initialize the service error.

        Args:
            message: Error message
            operation: Service operation that failed
            original_error: Original exception that caused this error
            status_code: HTTP status code override (defaults to 500)
        """
        details: dict[str, Any] = {}
        if operation:
            details["operation"] = operation
        if original_error:
            details["original_error"] = str(original_error)
            details["error_type"] = type(original_error).__name__

        super().__init__(message, status_code or 500, details)
        self.operation = operation
        self.original_error = original_error
