"""StringDB-Link: High-performance API server for STRING protein-protein interaction database.

This package provides both REST API and MCP (Model Context Protocol) access to the STRING
protein-protein interaction database, enabling modern AI applications to query protein
networks, functional enrichment, and interaction data.
"""

__version__ = "1.0.0"
__author__ = "StringDB-Link Development Team"
__email__ = "dev@stringdb-link.org"
__license__ = "MIT"
__url__ = "https://github.com/stringdb-link/stringdb-link"

from typing import Final

# Package metadata
VERSION: Final[str] = __version__
AUTHOR: Final[str] = __author__
EMAIL: Final[str] = __email__
LICENSE: Final[str] = __license__
URL: Final[str] = __url__

# API version for backward compatibility
API_VERSION: Final[str] = "v1"

# Default configuration values
DEFAULT_HOST: Final[str] = "127.0.0.1"
DEFAULT_PORT: Final[int] = 8000
DEFAULT_TRANSPORT: Final[str] = "unified"

__all__ = [
    "API_VERSION",
    "AUTHOR",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "DEFAULT_TRANSPORT",
    "EMAIL",
    "LICENSE",
    "URL",
    "VERSION",
]
