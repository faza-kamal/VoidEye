"""
VoidEye · core/domain.py
Domain / IP OSINT: WHOIS, DNS records, subdomain enum, banner grab.
"""
from __future__ import annotations
import ctypes
import os
import socket
from pathlib import Path
from typing import Optional

import dns.resolver
import whois
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()

# Path to compiled C shared library
_SO_PATH = Path(__file__).parent.parent / "cmodules" / "bannergrab.so"

# Common subdomains to enumerate
COMMON_SUBS = [
    "www", "mail", "ftp", "dev", "staging", "api", "admin",
    "test", "blog", "shop", "vpn", "ssh", "smtp", "pop", "imap",
    "ns1", "ns2", "cdn", "docs", "git", "ci", "status",
]


class DomainScan:
    def __init__(self, target: str, banner: bool = False) -> None:
        self.target = target.strip().rstrip("/")
        self.banner = banner
        self._lib   = self._load_c_lib() if banner else None

    # ─── load C shared lib ───
    def _load_c_lib(self) -> Optional[ctypes.CDLL]:
        if _SO_PATH.exists():
            try:
                lib = ctypes.CDLL(str(_SO_PATH))
                lib.grab_banner.restype  = ctypes.c_int
                lib.grab_banner.argtypes = [
                    ctypes.c_char_p,  # host
                    ctypes.c_int,     # port
                    ctypes.c_char_p,  # out_buf
                    ctypes.c_int,     # buf_size
                ]
                console.print("[green]✓[/green] C bannergrab module loaded")
                return lib
            except Exception as e:
                console.print(f"[yellow]⚠[/yellow] Failed to load C lib: {e}")
        else:
            console.print("[yellow]⚠[/yellow] bannergrab.so not found — compile cmodules/bannergrab.c first")
        return None

    # ─── banner grab via C ───
    def _grab_banner_c(self, host: str, port: int = 80) -> Optional[str]:
        if not self._lib:
            return None
        buf = ctypes.create_string_buffer(4096)
        ret = self._lib.grab_banner(host.encode(), port, buf, 4096)
        if ret == 0:
            return buf.value.decode(errors="ignore").strip()
        return None

    # ─── fallback pure Python banner grab ───
    def _grab_banner_py(self, host: str, port: int = 80) -> Optional[str]:
        try:
            with socket.create_connection((host, port), timeout=5) as s:
                s.sendall(b"HEAD / HTTP/1.0\r\nHost: " + host.encode() + b"\r\n\r\n")
                return s.recv(1024).decode(errors="ignore").strip()
        except Exception:
            return None

    # ─── WHOIS ───
    def _whois(self) -> dict:
        try:
            w = whois.whois(self.target)
            return {
                "registrar":    getattr(w, "registrar", "N/A"),
                "creation_date":str(getattr(w, "creation_date", "N/A")),
                "expiry_date":  str(getattr(w, "expiration_date", "N/A")),
                "name_servers": getattr(w, "name_servers", []),
                "org":          getattr(w, "org", "N/A"),
                "country":      getattr(w, "country", "N/A"),
            }
        except Exception as e:
            return {"error": str(e)}

    # ─── DNS records ───
    def _dns_records(self) -> dict[str, list[str]]:
        records: dict[str, list[str]] = {}
        for rtype in ("A", "AAAA", "MX", "TXT", "NS", "CNAME"):
            try:
                answers = dns.resolver.resolve(self.target, rtype)
                records[rtype] = [str(r) for r in answers]
            except Exception:
                records[rtype] = []
        return records

    # ─── reverse DNS ───
    def _reverse_dns(self) -> Optional[str]:
        try:
            return socket.gethostbyaddr(self.target)[0]
        except Exception:
            return None

    # ─── subdomain enumeration ───
    def _subdomain_enum(self) -> list[str]:
        found: list[str] = []
        for sub in COMMON_SUBS:
            fqdn = f"{sub}.{self.target}"
            try:
                socket.getaddrinfo(fqdn, None)
                found.append(fqdn)
            except socket.gaierror:
                pass
            except Exception:
                pass  # BUG FIX #5: tangkap semua exception
        return found

    # ─── render ───
    def _render(
        self,
        whois_data: dict,
        dns_data:   dict[str, list[str]],
        reverse:    Optional[str],
        subdomains: list[str],
        banner:     Optional[str],
    ) -> None:
        # WHOIS table
        t_whois = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        t_whois.add_column("k", style="cyan", width=16)
        t_whois.add_column("v", style="white")
        for k, v in whois_data.items():
            val = ", ".join(v) if isinstance(v, list) else str(v)
            t_whois.add_row(k.replace("_", " ").title(), val or "[dim]N/A[/dim]")

        # DNS table
        t_dns = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        t_dns.add_column("type", style="cyan", width=8)
        t_dns.add_column("records", style="white")
        for rtype, vals in dns_data.items():
            t_dns.add_row(rtype, "\n".join(vals) if vals else "[dim]—[/dim]")

        console.print(Panel(t_whois, title="[bold cyan]WHOIS[/bold cyan]", border_style="cyan"))
        console.print(Panel(t_dns,   title="[bold cyan]DNS Records[/bold cyan]", border_style="cyan"))

        if reverse:
            console.print(f"[cyan]Reverse DNS:[/cyan] {reverse}")

        if subdomains:
            console.print(Panel(
                "\n".join(f"[green]✓[/green] {s}" for s in subdomains),
                title=f"[bold cyan]Subdomains ({len(subdomains)} found)[/bold cyan]",
                border_style="cyan",
            ))
        else:
            console.print("[dim]No common subdomains found.[/dim]")

        if banner:
            console.print(Panel(
                Text(banner[:500], style="dim green"),
                title="[bold cyan]Banner Grab[/bold cyan]",
                border_style="cyan",
            ))

    def run(self) -> None:
        console.rule(f"[bold cyan]Domain / IP Scan  ·  [yellow]{self.target}[/yellow]")
        console.print("[dim]Running WHOIS…[/dim]")
        whois_data = self._whois()
        console.print("[dim]Running DNS lookup…[/dim]")
        dns_data   = self._dns_records()
        reverse    = self._reverse_dns()
        console.print("[dim]Enumerating subdomains…[/dim]")
        subdomains = self._subdomain_enum()
        banner_txt = None
        if self.banner:
            console.print("[dim]Grabbing banner…[/dim]")
            banner_txt = self._grab_banner_c(self.target) or self._grab_banner_py(self.target)
        self._render(whois_data, dns_data, reverse, subdomains, banner_txt)
