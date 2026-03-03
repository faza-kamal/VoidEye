"""
VoidEye · core/email.py
Email OSINT: DNS MX lookup, Gravatar, public footprint.
"""
from __future__ import annotations
import asyncio
import hashlib
import re
from typing import Optional
import aiohttp
import dns.resolver
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 10


class EmailScan:
    def __init__(self, email: str) -> None:
        self.email  = email.strip().lower()
        self._valid = bool(re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", self.email))

    def _domain(self) -> str: return self.email.split("@")[1]
    def _local(self)  -> str: return self.email.split("@")[0]

    def _mx_lookup(self) -> list[str]:
        try:
            return sorted([str(r.exchange).rstrip(".") for r in dns.resolver.resolve(self._domain(), "MX")])
        except Exception:
            return []

    async def _gravatar(self, session: aiohttp.ClientSession) -> Optional[str]:
        md5 = hashlib.md5(self.email.encode()).hexdigest()
        try:
            async with session.get(f"https://www.gravatar.com/avatar/{md5}?d=404", headers=HEADERS) as resp:
                if resp.status == 200:
                    return f"https://www.gravatar.com/{md5}"
        except Exception:
            pass
        return None

    async def _github_footprint(self, session: aiohttp.ClientSession) -> Optional[str]:
        try:
            async with session.get(
                # BUG FIX #3: gunakan full email, bukan hanya local part
                f"https://api.github.com/search/users?q={self.email}+in:email",
                headers={**HEADERS, "Accept": "application/vnd.github+json"},
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("total_count", 0) > 0:
                        return data["items"][0].get("html_url")
        except Exception:
            pass
        return None

    async def _reddit_footprint(self, session: aiohttp.ClientSession) -> Optional[str]:
        try:
            async with session.get(
                f"https://www.reddit.com/search.json?q={self._local()}&type=user&limit=1",
                headers=HEADERS,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    children = data.get("data", {}).get("children", [])
                    if children:
                        return f"https://www.reddit.com/user/{children[0]['data']['name']}"
        except Exception:
            pass
        return None

    async def run(self) -> None:
        if not self._valid:
            console.print(f"[red]Invalid email:[/red] {self.email}")
            return
        console.rule(f"[bold cyan]Email Scan  ·  [yellow]{self.email}[/yellow]")
        mx_records = self._mx_lookup()
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
            gravatar, github, reddit = await asyncio.gather(
                self._gravatar(session), self._github_footprint(session), self._reddit_footprint(session),
            )
        t = Table(box=box.SIMPLE, show_header=False)
        t.add_column("k", style="cyan", width=14)
        t.add_column("v")
        t.add_row("Email",      self.email)
        t.add_row("Domain",     self._domain())
        t.add_row("MX Records", "\n".join(mx_records) if mx_records else "[red]None found[/red]")
        t.add_row("Gravatar",   gravatar or "[dim]Not found[/dim]")
        t.add_row("GitHub",     github   or "[dim]Not found[/dim]")
        t.add_row("Reddit",     reddit   or "[dim]Not found[/dim]")
        console.print(Panel(t, title="[bold cyan]Email OSINT[/bold cyan]", border_style="cyan"))
