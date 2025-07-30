"""Command-line interface for StringDB-Link.

This module provides a CLI for starting the server in different modes
and performing various administrative tasks.
"""

from __future__ import annotations

import asyncio
import sys

from rich.console import Console
from rich.table import Table
import typer

from . import API_VERSION, VERSION
from .config import get_settings, reload_settings
from .logging_config import configure_logging
from .server_manager import UnifiedServerManager

app = typer.Typer(
    name="stringdb-link",
    help=(
        "StringDB-Link: High-performance unified API server for STRING "
        "protein-protein interaction database"
    ),
    add_completion=False,
    no_args_is_help=True,
)

console = Console()


@app.command()
def version() -> None:
    """Show version information."""
    table = Table(title="StringDB-Link Version Information")
    table.add_column("Component", style="cyan")
    table.add_column("Version", style="green")

    table.add_row("StringDB-Link", VERSION)
    table.add_row("API Version", API_VERSION)
    table.add_row(
        "Python",
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    )

    console.print(table)


@app.command()
def config(
    show_sensitive: bool = typer.Option(
        False,
        "--show-sensitive",
        help="Show sensitive configuration values",
    ),
) -> None:
    """Show current configuration."""
    settings = get_settings()

    table = Table(title="StringDB-Link Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Description", style="dim")

    # List of sensitive settings to hide
    sensitive_settings = {
        "api_key",
        "secret",
        "password",
        "token",
    }

    for field_name, field_info in settings.model_fields.items():
        value = getattr(settings, field_name)

        # Hide sensitive values unless explicitly requested
        if not show_sensitive and any(
            sensitive in field_name.lower() for sensitive in sensitive_settings
        ):
            value = "***HIDDEN***"

        description = field_info.description or ""
        table.add_row(field_name, str(value), description)

    console.print(table)


@app.command()
def validate_config() -> None:
    """Validate configuration settings."""
    try:
        settings = reload_settings()
        console.print("[green]✓[/green] Configuration is valid")

        # Show some key settings
        console.print(f"Transport mode: {settings.transport}")
        console.print(f"Server: {settings.host}:{settings.port}")
        console.print(f"StringDB API: {settings.stringdb_base_url}")
        console.print(f"Cache enabled: {settings.cache_enabled}")

    except Exception as e:
        console.print(f"[red]✗[/red] Configuration validation failed: {e}")
        raise typer.Exit(1)


@app.command()
def server(
    host: str = typer.Option(
        None,
        "--host",
        "-h",
        help="Server host address",
    ),
    port: int = typer.Option(
        None,
        "--port",
        "-p",
        help="Server port",
    ),
    transport: str = typer.Option(
        None,
        "--transport",
        "-t",
        help="Transport mode: http, stdio, or unified",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        help="Enable auto-reload (development only)",
    ),
    log_level: str = typer.Option(
        None,
        "--log-level",
        help="Logging level",
    ),
) -> None:
    """Start the StringDB-Link server."""
    settings = get_settings()

    # Override settings with command line arguments
    if host:
        settings.host = host
    if port:
        settings.port = port
    if transport:
        settings.transport = transport
    if log_level:
        settings.log_level = log_level.upper()
    if reload:
        settings.reload = reload

    # Validate transport mode
    if settings.transport not in ("http", "stdio", "unified"):
        console.print(

                f"[red]Error:[/red] Invalid transport mode '{settings.transport}'. "
                "Must be: http, stdio, or unified"

        )
        raise typer.Exit(1)

    # Configure logging
    logger = configure_logging()

    # Create and start server
    server_manager = UnifiedServerManager(logger=logger)

    try:
        asyncio.run(start_server(server_manager, settings))
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Server error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def mcp() -> None:
    """Start MCP server for Claude Desktop integration."""
    settings = get_settings()
    settings.transport = "stdio"

    # Configure logging for STDIO mode (stderr only)
    logger = configure_logging()

    # Create and start MCP server
    server_manager = UnifiedServerManager(logger=logger)

    try:
        asyncio.run(server_manager.start_stdio_server())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        # Log errors to stderr (won't interfere with STDIO protocol)
        logger.error("MCP server error", error=str(e), exc_info=True)
        sys.exit(1)


@app.command()
def health() -> None:
    """Check server health.

    Requires a running server instance.
    """
    import httpx

    settings = get_settings()

    try:
        with httpx.Client() as client:
            response = client.get(f"http://{settings.host}:{settings.port}/api/health")

        if response.status_code == 200:
            data = response.json()
            console.print("[green]✓[/green] Server is healthy")

            table = Table(title="Health Check Results")
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="green")

            for key, value in data.items():
                table.add_row(key, str(value))

            console.print(table)
        else:
            console.print(f"[red]✗[/red] Server health check failed: {response.status_code}")
            raise typer.Exit(1)

    except httpx.ConnectError:
        console.print("[red]✗[/red] Cannot connect to server. Is it running?")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Health check error: {e}")
        raise typer.Exit(1)


async def start_server(server_manager: UnifiedServerManager, settings) -> None:
    """Start the server based on transport mode."""
    if settings.transport == "unified":
        await server_manager.start_unified_server(
            host=settings.host,
            port=settings.port,
            reload=settings.reload,
        )
    elif settings.transport == "http":
        await server_manager.start_http_only_server(
            host=settings.host,
            port=settings.port,
            reload=settings.reload,
        )
    elif settings.transport == "stdio":
        await server_manager.start_stdio_server()
    else:
        msg = f"Invalid transport mode: {settings.transport}"
        raise ValueError(msg)


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
