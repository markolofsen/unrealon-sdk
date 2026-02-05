"""
Unified CLI for parsers using Click.

Provides declarative CLI with interactive menu when run without arguments.

Usage:
    from unrealon.parsers import cli_options, CLIConfig

    @cli_options("My Parser")
    def main(config: CLIConfig):
        with get_monitor("myparser", dev_mode=config.dev) as m:
            parser = MyParser(m)
            parser.run(pages=config.pages, limit=config.limit)

    if __name__ == "__main__":
        main()
"""
from __future__ import annotations

import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from ..exceptions import StopInterrupt

# -- Config dataclass ----------------------------------------------------------

@dataclass
class CLIConfig:
    """CLI configuration passed to parser."""
    pages: int = 3
    limit: int = 0
    skip_details: bool = False
    headless: bool = True
    continuous: bool = False
    dev: bool = False
    prod: bool = False

    # Custom options (for parser-specific settings)
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def mode(self) -> str:
        """Get mode string (dev/prod)."""
        return "dev" if self.dev else "prod"


# -- Interruptible sleep wrapper ----------------------------------------------

_original_sleep = time.sleep
_current_monitor: Any = None


def _interruptible_sleep(seconds: float) -> None:
    """Sleep that checks for interrupts every 0.5s."""
    if _current_monitor is None:
        _original_sleep(seconds)
        return

    remaining = seconds
    while remaining > 0:
        _current_monitor.check_interrupt()
        chunk = min(0.5, remaining)
        _original_sleep(chunk)
        remaining -= chunk


def _patch_sleep(monitor: Any) -> None:
    """Patch time.sleep globally to check interrupts."""
    global _current_monitor
    _current_monitor = monitor
    time.sleep = _interruptible_sleep
    monitor.log.debug("time.sleep patched for interrupt checking")


def _unpatch_sleep() -> None:
    """Restore original time.sleep."""
    global _current_monitor
    _current_monitor = None
    time.sleep = _original_sleep


# -- Config display -----------------------------------------------------------

console = Console()


def print_config(config: CLIConfig, parser_name: str = "", api_url: str = "", grpc_server: str = "") -> None:
    """Print configuration summary before running."""
    console.print()

    # Config table
    table = Table(show_header=False, box=None, padding=(0, 1), expand=False)
    table.add_column("Key", style="dim")
    table.add_column("Value", style="bold")

    mode_style = "yellow" if config.dev else "green"
    mode_text = f"[{mode_style}]{config.mode.upper()}[/{mode_style}]"

    table.add_row("Mode", mode_text)
    if api_url:
        table.add_row("API", api_url)
    if grpc_server:
        table.add_row("gRPC", grpc_server)
    table.add_row("Pages", str(config.pages))

    if config.limit > 0:
        table.add_row("Limit", str(config.limit))

    if config.continuous:
        table.add_row("Mode", "[cyan]continuous[/cyan]")

    if config.skip_details:
        table.add_row("Details", "[dim]skipped[/dim]")

    console.print(Panel(
        table,
        title=f"[bold]{parser_name}[/bold]" if parser_name else None,
        border_style="dim",
        expand=False,
    ))
    console.print()


# -- Interactive menu ---------------------------------------------------------

def show_interactive_menu(parser_name: str) -> CLIConfig:
    """Show interactive menu and return config."""
    try:
        console.print()
        console.print(Panel.fit(
            f"[bold cyan]{parser_name}[/bold cyan]",
            border_style="cyan",
        ))
        console.print()

        # Mode selection - highlight default (1)
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="bold yellow")
        table.add_column("Mode", style="white")
        table.add_column("Description", style="dim")

        # Default option highlighted
        table.add_row("[bold green]1[/bold green]", "[bold green]Quick Run[/bold green]", "[green]3 pages → prod (default)[/green]")
        table.add_row("2", "Custom Run", "Configure pages, limit, etc.")
        table.add_row("3", "Dev Mode", "1 page → localhost")
        table.add_row("4", "Continuous", "Wait for commands from Unrealon")
        table.add_row("q", "Quit", "Exit without running")

        console.print(table)
        console.print()

        choice = Prompt.ask(
            "[bold]Select mode[/bold]",
            choices=["1", "2", "3", "4", "q"],
            default="1"
        )

        if choice == "q":
            console.print("[dim]Bye![/dim]")
            sys.exit(0)

        config: CLIConfig

        if choice == "1":
            # Quick run - defaults
            config = CLIConfig(pages=3, limit=0, dev=False, prod=True)

        elif choice == "3":
            # Dev mode
            config = CLIConfig(pages=1, limit=5, dev=True, prod=False)

        elif choice == "4":
            # Continuous mode
            dev = Confirm.ask("Use dev server?", default=False)
            config = CLIConfig(continuous=True, dev=dev, prod=not dev)

        else:
            # Custom run (choice == "2")
            console.print()
            console.print("[bold]Custom Configuration[/bold]")
            console.print()

            pages = IntPrompt.ask("Pages to parse", default=3)
            limit = IntPrompt.ask("Item limit (0 = no limit)", default=0)
            skip_details = Confirm.ask("Skip detail pages?", default=False)
            headless = Confirm.ask("Headless browser?", default=True)
            dev = Confirm.ask("Use dev server?", default=False)

            config = CLIConfig(
                pages=pages,
                limit=limit,
                skip_details=skip_details,
                headless=headless,
                dev=dev,
                prod=not dev,
            )

        # Show config summary
        print_config(config, parser_name)

        return config

    except KeyboardInterrupt:
        console.print()
        console.print("[dim]Interrupted. Bye![/dim]")
        sys.exit(0)


# -- Click decorator ----------------------------------------------------------

F = TypeVar("F", bound=Callable[..., Any])


def cli_options(parser_name: str, default_pages: int = 3) -> Callable[[F], F]:
    """
    Decorator that adds Click CLI options to a parser main function.

    If run without arguments, shows interactive menu.
    Otherwise uses CLI arguments.

    Usage:
        @cli_options("My Parser")
        def main(config: CLIConfig):
            # config has: pages, limit, skip_details, headless, continuous, dev
            ...
    """
    def decorator(func: F) -> F:
        @click.command()
        @click.option("--pages", "-p", type=int, default=None,
                      help=f"Number of pages to parse (default: {default_pages})")
        @click.option("--limit", "-l", type=int, default=None,
                      help="Limit number of items (0 = no limit)")
        @click.option("--skip-details", is_flag=True, default=False,
                      help="Skip fetching detail pages")
        @click.option("--headless/--no-headless", default=True,
                      help="Run browser in headless mode")
        @click.option("--continuous", is_flag=True, default=False,
                      help="Wait for commands from Unrealon")
        @click.option("--dev", is_flag=True, default=False,
                      help="Use dev servers (localhost)")
        @click.option("--prod", is_flag=True, default=False,
                      help="Use production servers")
        @click.pass_context
        def wrapper(
            ctx: click.Context,
            pages: int | None,
            limit: int | None,
            skip_details: bool,
            headless: bool,
            continuous: bool,
            dev: bool,
            prod: bool,
        ) -> None:
            # Check if any arguments were provided
            args_provided = any([
                pages is not None,
                limit is not None,
                skip_details,
                not headless,
                continuous,
                dev,
                prod,
            ])

            if not args_provided and sys.stdin.isatty():
                # Interactive mode
                config = show_interactive_menu(parser_name)
            else:
                # CLI mode
                config = CLIConfig(
                    pages=pages if pages is not None else default_pages,
                    limit=limit if limit is not None else 0,
                    skip_details=skip_details,
                    headless=headless,
                    continuous=continuous,
                    dev=dev,
                    prod=prod if prod else not dev,
                )
                # Show config for CLI mode too
                if sys.stdin.isatty():
                    print_config(config, parser_name)

            func(config)

        return wrapper  # type: ignore

    return decorator


# -- Legacy compatibility functions -------------------------------------------

def create_parser_cli(description: str, default_pages: int = 3) -> CLIConfig:
    """
    Legacy function for backward compatibility.

    Creates CLI config from sys.argv using argparse-style parsing.
    For new code, use @cli_options decorator instead.
    """
    import argparse

    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--pages", "-p", type=int, default=default_pages)
    ap.add_argument("--limit", "-l", type=int, default=0)
    ap.add_argument("--skip-details", action="store_true")
    ap.add_argument("--headless", action="store_true", default=True)
    ap.add_argument("--no-headless", action="store_false", dest="headless")
    ap.add_argument("--continuous", action="store_true")
    ap.add_argument("--dev", action="store_true")
    ap.add_argument("--prod", action="store_true")

    args = ap.parse_args()

    return CLIConfig(
        pages=args.pages,
        limit=args.limit,
        skip_details=args.skip_details,
        headless=args.headless,
        continuous=args.continuous,
        dev=args.dev,
        prod=args.prod if args.prod else not args.dev,
    )


# -- Run helpers ----------------------------------------------------------------

def run_continuous(
    monitor: Any,
    run_func: Callable[[dict], None],
    config: CLIConfig,
) -> None:
    """
    Run in continuous mode, waiting for commands.

    Args:
        monitor: Monitor instance
        run_func: Function to call on "run" command, receives params dict
        config: CLI config for defaults
    """
    run_count = 0

    def handle_run(params: dict) -> dict:
        nonlocal run_count

        if monitor.is_paused:
            monitor.log.warning("Cannot run: parser is paused")
            return {"status": "error", "message": "paused"}

        run_count += 1
        monitor.set_busy()
        monitor.log.info("=== Run #%d ===", run_count)

        _patch_sleep(monitor)
        try:
            run_func(params)
            return {"status": "ok", "run": run_count}
        except StopInterrupt:
            monitor.log.info("Run #%d stopped by command", run_count)
            return {"status": "stopped", "run": run_count}
        except Exception as e:
            monitor.log.error("Run failed: %s", e)
            monitor.increment_errors()
            return {"status": "error", "message": str(e)}
        finally:
            _unpatch_sleep()
            monitor.set_idle()

    monitor.client.on_command("run", handle_run)
    monitor.set_idle()
    monitor.log.info("Continuous mode: waiting for commands (run/pause/resume/stop)")

    try:
        while not monitor.should_stop:
            _original_sleep(1)
    except KeyboardInterrupt:
        monitor.log.info("Interrupted, exiting...")
        import os
        os._exit(0)

    monitor.log.info("Stopped after %d runs", run_count)
