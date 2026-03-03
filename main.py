#!/usr/bin/env python3
"""
VoidEye - Modular OSINT Framework
Author : faza-kamal  (github.com/faza-kamal)
License: MIT
"""

import sys
import argparse
import asyncio

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich import box

from core.username import UsernameScan
from core.email import EmailScan
from core.domain import DomainScan
from core.dork import DorkGenerator
from core.onion import OnionSearch
from core.portscan import PortScan          # FIX: fastscan.c integration
from utils.helpers import print_error

console = Console()

BANNER = r"""[bold cyan]
 ██╗   ██╗ ██████╗ ██╗██████╗ ███████╗██╗   ██╗███████╗
 ██║   ██║██╔═══██╗██║██╔══██╗██╔════╝╚██╗ ██╔╝██╔════╝
 ██║   ██║██║   ██║██║██║  ██║█████╗   ╚████╔╝ █████╗  
 ╚██╗ ██╔╝██║   ██║██║██║  ██║██╔══╝    ╚██╔╝  ██╔══╝  
  ╚████╔╝ ╚██████╔╝██║██████╔╝███████╗   ██║   ███████╗
   ╚═══╝   ╚═════╝ ╚═╝╚═════╝ ╚══════╝   ╚═╝   ╚══════╝[/bold cyan]
[dim]  [ Modular OSINT Framework ]  ·  github.com/faza-kamal/VoidEye[/dim]
"""


def show_menu() -> None:
    console.print(BANNER)
    table = Table(box=box.ROUNDED, border_style="cyan", show_header=False, width=42, padding=(0, 2))
    table.add_column("opt", style="bold yellow")
    table.add_column("module", style="white")
    table.add_row("[1]", "Username Scan")
    table.add_row("[2]", "Email Scan")
    table.add_row("[3]", "Domain / IP Scan")
    table.add_row("[4]", "Google Dork Generator")
    table.add_row("[5]", "Onion Search")
    table.add_row("[6]", "Port Scanner")
    table.add_row("[0]", "[red]Exit[/red]")
    console.print(Panel(table, title="[bold cyan]─── VoidEye Menu ───[/bold cyan]", border_style="cyan"))


def interactive_mode() -> None:
    show_menu()
    choice = Prompt.ask("\n[bold cyan]voidEye[/bold cyan] [dim]›[/dim]")
    handlers = {
        "1": lambda: asyncio.run(UsernameScan(Prompt.ask("[yellow]  Username[/yellow]")).run()),
        "2": lambda: asyncio.run(EmailScan(Prompt.ask("[yellow]  Email[/yellow]")).run()),
        "3": lambda: DomainScan(Prompt.ask("[yellow]  Domain / IP[/yellow]")).run(),
        "4": lambda: DorkGenerator(Prompt.ask("[yellow]  Keyword[/yellow]")).run(),
        "5": lambda: asyncio.run(OnionSearch(Prompt.ask("[yellow]  Query[/yellow]")).run()),
        "0": lambda: (console.print("\n[dim]Goodbye.[/dim]\n"), sys.exit(0)),
    }
    action = handlers.get(choice)
    if action:
        action()
    else:
        print_error("Invalid option. Use 0-5.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="voideye",
        description="VoidEye — Modular OSINT Framework by faza-kamal",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    sub = parser.add_subparsers(dest="module", metavar="MODULE")

    p_user = sub.add_parser("username", help="Search username across platforms")
    p_user.add_argument("target")
    p_user.add_argument("-o", "--output", default=None, help="Export results to JSON")

    p_email = sub.add_parser("email", help="Email OSINT lookup")
    p_email.add_argument("target")

    p_domain = sub.add_parser("domain", help="Domain / IP OSINT")
    p_domain.add_argument("target")
    p_domain.add_argument("--banner", action="store_true", help="Enable C banner grabbing")

    p_dork = sub.add_parser("dork", help="Google Dork generator")
    p_dork.add_argument("keyword")
    p_dork.add_argument("-c", "--category", choices=["files", "admin", "creds", "github"], default=None)

    p_onion = sub.add_parser("onion", help="Search .onion links via Ahmia.fi")
    p_onion.add_argument("query")
    p_onion.add_argument("--no-tor", action="store_true", help="Disable Tor proxy")

    return parser


def run_cli(args: argparse.Namespace) -> None:
    dispatch = {
        "username": lambda: asyncio.run(UsernameScan(args.target, output=args.output).run()),
        "email":    lambda: asyncio.run(EmailScan(args.target).run()),
        "domain":   lambda: DomainScan(args.target, banner=getattr(args, "banner", False)).run(),
        "dork":     lambda: DorkGenerator(args.keyword, category=args.category).run(),
        "onion":    lambda: asyncio.run(OnionSearch(args.query, use_tor=not args.no_tor).run()),
        "portscan": lambda: PortScan(args.target, args.start, args.end).run(),
    }
    action = dispatch.get(args.module)
    if action:
        action()
    else:
        interactive_mode()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.module is None:
        interactive_mode()
    else:
        run_cli(args)


if __name__ == "__main__":
    main()
