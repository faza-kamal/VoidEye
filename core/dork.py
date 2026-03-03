"""
VoidEye · core/dork.py
Google Dork generator — does NOT scrape Google directly.
"""
from __future__ import annotations
from typing import Optional
import pyperclip
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

DORK_TEMPLATES: dict[str, list[str]] = {
    "files": [
        'site:{target} ext:pdf',
        'site:{target} ext:xls OR ext:xlsx',
        'site:{target} ext:doc OR ext:docx',
        'site:{target} ext:sql',
        'site:{target} ext:bak',
        'site:{target} ext:log',
        'site:{target} ext:env',
        'site:{target} ext:config',
        'site:{target} intitle:"index of"',
        'site:{target} filetype:txt inurl:password',
    ],
    "admin": [
        'site:{target} inurl:admin',
        'site:{target} inurl:login',
        'site:{target} inurl:dashboard',
        'site:{target} inurl:wp-admin',
        'site:{target} inurl:phpmyadmin',
        'site:{target} intitle:"admin panel"',
        'site:{target} inurl:cpanel',
        'site:{target} inurl:webmail',
        'site:{target} inurl:portal',
        'site:{target} inurl:administrator',
    ],
    "creds": [
        'site:{target} intext:"password" filetype:txt',
        'site:{target} intext:"username" intext:"password"',
        'site:{target} intitle:"index of" intext:".env"',
        'site:{target} ext:env DB_PASSWORD',
        'site:{target} intext:"api_key" OR intext:"api key"',
        'site:{target} inurl:config intext:password',
        '"@{target}" intext:password site:pastebin.com',
        '"@{target}" intext:password site:github.com',
    ],
    "github": [
        'site:github.com "{target}" password',
        'site:github.com "{target}" secret',
        'site:github.com "{target}" api_key',
        'site:github.com "{target}" token',
        'site:github.com "{target}" credentials',
        'site:github.com "{target}" private_key',
        'site:github.com "{target}" .env',
    ],
}


class DorkGenerator:
    def __init__(self, keyword: str, category: Optional[str] = None) -> None:
        self.keyword  = keyword.strip()
        self.category = category

    def _generate(self) -> dict[str, list[str]]:
        cats = [self.category] if self.category else list(DORK_TEMPLATES.keys())
        result: dict[str, list[str]] = {}
        for cat in cats:
            result[cat] = [
                tpl.replace("{target}", self.keyword)
                for tpl in DORK_TEMPLATES.get(cat, [])
            ]
        return result

    def run(self) -> None:
        console.rule(f"[bold cyan]Google Dork Generator  ·  [yellow]{self.keyword}[/yellow]")
        dorks = self._generate()
        all_dorks: list[str] = []

        for cat, queries in dorks.items():
            table = Table(
                title=f"[bold cyan]{cat.upper()}[/bold cyan]",
                box=box.ROUNDED, border_style="cyan",
                show_header=False,
            )
            table.add_column("dork", style="yellow")
            for q in queries:
                table.add_row(q)
                all_dorks.append(q)
            console.print(table)

        console.print(f"\n[dim]Total dorks generated: {len(all_dorks)}[/dim]")
        copy = console.input("\n[bold cyan]Copy all dorks to clipboard? (y/N):[/bold cyan] ")
        if copy.strip().lower() == "y":
            try:
                pyperclip.copy("\n".join(all_dorks))
                console.print("[green]✓[/green] Copied to clipboard!")
            except Exception:
                console.print("[yellow]⚠[/yellow] Clipboard not available (install xclip / xsel)")
