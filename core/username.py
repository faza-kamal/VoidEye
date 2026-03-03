"""
VoidEye · core/username.py
Async username OSINT scanner across multiple platforms.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

import aiohttp
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

# BUG FIX #2: tambah flag status_only untuk platform tanpa keyword not_found
# Platform dengan not_found kosong tidak bisa dibedakan found/not-found dari body,
# sehingga kita hanya cek HTTP 200 (status_only=True) untuk menghindari false positive.
PLATFORMS: list[dict] = [
    {"name":"GitHub",      "url":"https://github.com/{}",                   "not_found":"Not Found"},
    {"name":"GitLab",      "url":"https://gitlab.com/{}",                   "not_found":"404"},
    {"name":"Twitter/X",   "url":"https://twitter.com/{}",                  "not_found":"This account doesn't exist"},
    {"name":"Instagram",   "url":"https://www.instagram.com/{}/",           "not_found":"Sorry, this page"},
    {"name":"TikTok",      "url":"https://www.tiktok.com/@{}",              "not_found":"Couldn't find this account"},
    {"name":"Reddit",      "url":"https://www.reddit.com/user/{}",          "not_found":"Sorry, nobody on Reddit"},
    {"name":"LinkedIn",    "url":"https://www.linkedin.com/in/{}",          "not_found":"", "status_only":True},
    {"name":"YouTube",     "url":"https://www.youtube.com/@{}",             "not_found":"", "status_only":True},
    {"name":"Twitch",      "url":"https://www.twitch.tv/{}",                "not_found":"Sorry. Unless you've got a time machine"},
    {"name":"Pinterest",   "url":"https://www.pinterest.com/{}/",           "not_found":"", "status_only":True},
    {"name":"Keybase",     "url":"https://keybase.io/{}",                   "not_found":"", "status_only":True},
    {"name":"HackerNews",  "url":"https://news.ycombinator.com/user?id={}", "not_found":"No such user"},
    {"name":"ProductHunt", "url":"https://www.producthunt.com/@{}",         "not_found":"", "status_only":True},
    {"name":"Steam",       "url":"https://steamcommunity.com/id/{}",        "not_found":"The specified profile could not be found"},
    {"name":"Dev.to",      "url":"https://dev.to/{}",                       "not_found":"404"},
    {"name":"Medium",      "url":"https://medium.com/@{}",                  "not_found":"", "status_only":True},
    {"name":"Telegram",    "url":"https://t.me/{}",                         "not_found":"If you have Telegram"},
    {"name":"SoundCloud",  "url":"https://soundcloud.com/{}",               "not_found":"", "status_only":True},
    {"name":"Pastebin",    "url":"https://pastebin.com/u/{}",               "not_found":"", "status_only":True},
    {"name":"Gravatar",    "url":"https://en.gravatar.com/{}",              "not_found":"", "status_only":True},
    {"name":"HackTheBox",  "url":"https://app.hackthebox.com/profile/{}",   "not_found":"", "status_only":True},
    {"name":"TryHackMe",   "url":"https://tryhackme.com/p/{}",              "not_found":"", "status_only":True},
    {"name":"Replit",      "url":"https://replit.com/@{}",                  "not_found":"", "status_only":True},
    {"name":"Snapchat",    "url":"https://www.snapchat.com/add/{}",         "not_found":"", "status_only":True},
    {"name":"Spotify",     "url":"https://open.spotify.com/user/{}",        "not_found":"", "status_only":True},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
CONCURRENCY = 10
TIMEOUT     = 10


@dataclass
class ScanResult:
    platform:    str
    url:         str
    found:       bool
    status_code: int
    response_ms: float
    error:       Optional[str] = field(default=None)


class UsernameScan:
    def __init__(self, username: str, output: Optional[str] = None) -> None:
        self.username = username.strip().lower()
        self.output   = output
        self.results: list[ScanResult] = []

    async def _check(
        self,
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore,
        platform: dict,
    ) -> ScanResult:
        url          = platform["url"].format(self.username)
        not_found_kw = platform.get("not_found", "")

        async with semaphore:
            t0 = time.monotonic()
            try:
                async with session.get(url, headers=HEADERS, allow_redirects=True) as resp:
                    elapsed = round((time.monotonic() - t0) * 1000, 1)
                    status  = resp.status
                    if platform.get("status_only", False):  # BUG FIX #2
                        found = (status == 200)
                    else:
                        body  = await resp.text(errors="ignore")
                        found = status == 200 and not (not_found_kw and not_found_kw.lower() in body.lower())
                    return ScanResult(
                        platform=platform["name"], url=url,
                        found=found, status_code=status, response_ms=elapsed,
                    )
            except Exception as exc:
                elapsed = round((time.monotonic() - t0) * 1000, 1)
                return ScanResult(
                    platform=platform["name"], url=url,
                    found=False, status_code=0, response_ms=elapsed, error=str(exc)[:80],
                )

    def _render_table(self, results: list[ScanResult]) -> Table:
        table = Table(
            title=f"[bold cyan]Username:[/bold cyan] [yellow]{self.username}[/yellow]",
            box=box.ROUNDED, border_style="cyan", header_style="bold cyan",
        )
        table.add_column("Platform",  style="white",  width=16)
        table.add_column("Status",    width=12)
        table.add_column("HTTP",      width=5,  justify="center")
        table.add_column("ms",        width=8,  justify="right")
        table.add_column("URL",       style="dim")
        for r in results:
            if r.error:
                s = "[dim yellow]ERROR[/dim yellow]"
            elif r.found:
                s = "[bold green]FOUND[/bold green]"
            else:
                s = "[dim red]NOT FOUND[/dim red]"
            table.add_row(r.platform, s, str(r.status_code) if r.status_code else "-",
                          f"{r.response_ms}", r.url if r.found else "[dim]—[/dim]")
        return table

    async def run(self) -> list[ScanResult]:
        console.rule(f"[bold cyan]Username Scan  ·  [yellow]{self.username}[/yellow]")
        semaphore = asyncio.Semaphore(CONCURRENCY)
        timeout   = aiohttp.ClientTimeout(total=TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            self.results = await asyncio.gather(*[
                self._check(session, semaphore, p) for p in PLATFORMS
            ])
        self.results.sort(key=lambda r: (not r.found, r.platform))
        console.print(self._render_table(self.results))
        found = sum(1 for r in self.results if r.found)
        console.print(
            f"\n[bold]Results:[/bold] [green]{found} FOUND[/green]  "
            f"[dim]{len(self.results) - found} not found[/dim]  "
            f"across [cyan]{len(self.results)}[/cyan] platforms\n"
        )
        if self.output:
            self._export(self.output)
        return self.results

    def _export(self, path: str) -> None:
        data = {
            "username": self.username,
            "summary":  {"total": len(self.results), "found": sum(1 for r in self.results if r.found)},
            "results":  [asdict(r) for r in self.results],
        }
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, indent=2), encoding="utf-8")
        console.print(f"[green]✓[/green] Exported → [cyan]{out}[/cyan]")
