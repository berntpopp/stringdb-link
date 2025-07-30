"""Configuration management for StringDB-Link.

This module handles all configuration settings using Pydantic settings,
supporting environment variables, .env files, and validation.
"""

from __future__ import annotations

# Import from the new nested configuration structure
from .config_new import Settings, get_settings, reload_settings, settings

# Re-export for backward compatibility
__all__ = ["Settings", "get_settings", "reload_settings", "settings"]
