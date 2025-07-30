"""MCP server entry point for StringDB-Link.

This module provides the entry point for the MCP server specifically
designed for Claude Desktop integration.
"""

import asyncio
import os
import sys

from stringdb_link.logging_config import configure_logging
from stringdb_link.server_manager import UnifiedServerManager


def main() -> None:
    """Start MCP server."""
    # Set transport mode and disable FastMCP banner/colors
    os.environ["TRANSPORT"] = "stdio"
    os.environ["FASTMCP_DISABLE_BANNER"] = "1"
    os.environ["FASTMCP_LOG_LEVEL"] = "WARNING"
    os.environ["NO_COLOR"] = "1"  # Disable ANSI colors

    # Configure logging (will automatically use stderr for stdio mode)
    logger = configure_logging()

    try:
        logger.info("Starting STDIO MCP server")
        manager = UnifiedServerManager(logger=logger)
        asyncio.run(manager.start_stdio_server())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        # Log errors to stderr (won't interfere with STDIO protocol)
        logger.exception("MCP server error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
