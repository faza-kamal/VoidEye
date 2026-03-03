"""
VoidEye · core/onion.py
Search .onion links via Ahmia.fi using Tor SOCKS5 proxy.
"""
from __future__ import annotations
from urllib.parse import quote_plus  # BUG FIX #4: safe URL encoding
import asyncio
import random
import re
from dataclasses import dataclass
from typing import Optional

import aiohttp
from aiohttp_socks import ProxyConnector
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

TOR_PROXY    = "socks5h://127.0.0.1:9050"
AHMIA_URL    = "https://ahmia.fi/search/?q={query}"
HEADERS      = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
RATE_LIMIT_MIN = 1.0   # seconds
RATE_LIMIT_MAX = 3.0


@dataclass
class OnionResult:
    title:       str
    onion_url:   str
    description: str


class OnionSearch:
    def __init__(self, query: str, use_tor: bool = True) -> None:
        self.query   = query.strip()
        self.use_tor = use_tor

    def _parse_results(self, html: str) -> list[OnionResult]:
        soup    = BeautifulSoup(html, "html.parser")
        results: list[OnionResult] = []

        for item in soup.select("li.result"):
            try:
                title_tag = item.select_one("h4")
                link_tag  = item.select_one("cite") or item.select_one("a[href*='.onion']")
                desc_tag  = item.select_one("p.description") or item.select_one("p")

                title = title_tag.get_text(strip=True) if title_tag else "Unknown"
                url   = ""
                if link_tag:
                    raw = link_tag.get_text(strip=True) if link_tag.name == "cite" else link_tag.get("href", "")
                    onion_match = re.search(r"[a-z2-7]{16,56}\.onion\S*", raw)
                    if onion_match:
                        url = "http://" + onion_match.group(0)
                desc  = desc_tag.get_text(strip=True)[:200] if desc_tag else ""

                if url:
                    results.append(OnionResult(title=title, onion_url=url, description=desc))
            except Exception:
                continue

        return results

    async def run(self) -> list[OnionResult]:
        console.rule(f"[bold cyan]Onion Search  ·  [yellow]{self.query}[/yellow]")

        if self.use_tor:
            console.print("[dim]Using Tor proxy (socks5h://127.0.0.1:9050)…[/dim]")
        else:
            console.print("[yellow]⚠[/yellow] Tor proxy disabled — search will use clearnet Ahmia endpoint")

        # Random delay (rate limiting)
        delay = random.uniform(RATE_LIMIT_MIN, RATE_LIMIT_MAX)
        console.print(f"[dim]Waiting {delay:.1f}s before request…[/dim]")
        await asyncio.sleep(delay)

        url  = f"https://ahmia.fi/search/?q={quote_plus(self.query)}"  # BUG FIX #4
        html = await self._fetch(url)

        if not html:
            console.print("[red]✗[/red] Failed to fetch results. Is Tor running?")
            return []

        results = self._parse_results(html)

        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return []

        table = Table(
            title=f"[bold cyan]Results for:[/bold cyan] [yellow]{self.query}[/yellow]",
            box=box.ROUNDED, border_style="cyan", header_style="bold cyan", show_lines=True,
        )
        table.add_column("Title",       style="white",      width=24)
        table.add_column("Onion URL",   style="cyan",       width=50)
        table.add_column("Description", style="dim",        width=40)

        for r in results:
            table.add_row(r.title, r.onion_url, r.description)

        console.print(table)
        console.print(f"\n[bold]{len(results)}[/bold] results found.\n")
        return results

    async def _fetch(self, url: str) -> Optional[str]:
        try:
            if self.use_tor:
                connector = ProxyConnector.from_url(TOR_PROXY)
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        return await resp.text()
            else:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        return await resp.text()
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            return None
