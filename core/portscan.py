"""
VoidEye · core/portscan.py
TCP Port Scanner — mengintegrasikan fastscan.so (C module) dengan Python fallback.
BUG FIX #6: fastscan.c sebelumnya dead code, sekarang diintegrasikan penuh.
"""
from __future__ import annotations

import ctypes
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

_SO_PATH      = Path(__file__).parent.parent / "cmodules" / "fastscan.so"
MAX_PORT_RANGE = 10_000

COMMON_PORTS: dict[int, str] = {
    21:"FTP",  22:"SSH",   23:"Telnet",   25:"SMTP",   53:"DNS",
    80:"HTTP", 110:"POP3", 143:"IMAP",    443:"HTTPS", 445:"SMB",
    3306:"MySQL", 3389:"RDP", 5432:"PostgreSQL", 6379:"Redis",
    8080:"HTTP-Alt", 8443:"HTTPS-Alt", 27017:"MongoDB", 9200:"Elasticsearch",
}


@dataclass
class PortResult:
    port:    int
    open:    bool
    service: str
    ms:      float


class PortScan:
    def __init__(self, target: str, start: int = 1, end: int = 1024) -> None:
        if not target or len(target) > 253:
            raise ValueError("Target tidak valid.")
        if not (1 <= start <= 65535 and 1 <= end <= 65535):
            raise ValueError("Port harus antara 1 dan 65535.")
        if end < start:
            raise ValueError("End port harus >= start port.")
        if (end - start) > MAX_PORT_RANGE:
            raise ValueError(f"Range terlalu besar. Maksimal {MAX_PORT_RANGE} port per scan.")
        self.target = target.strip()
        self.start  = start
        self.end    = end
        self._lib   = self._load_c_lib()

    def _load_c_lib(self) -> Optional[ctypes.CDLL]:
        if not _SO_PATH.exists():
            console.print("[yellow]\u26a0[/yellow]  fastscan.so tidak ditemukan \u2014 Python fallback.")
            return None
        try:
            lib = ctypes.CDLL(str(_SO_PATH))
            lib.scan_port.restype  = ctypes.c_int
            lib.scan_port.argtypes = [ctypes.c_char_p, ctypes.c_int]
            console.print("[green]\u2713[/green]  C fastscan module loaded.")
            return lib
        except Exception as e:
            console.print(f"[yellow]\u26a0[/yellow]  Gagal load C lib: {e} \u2014 Python fallback.")
            return None

    def _scan_port_c(self, port: int) -> tuple[int, bool, float]:
        t0  = time.monotonic()
        ret = self._lib.scan_port(self.target.encode(), port)
        return port, ret == 1, round((time.monotonic() - t0) * 1000, 1)

    def _scan_port_py(self, port: int) -> tuple[int, bool, float]:
        t0 = time.monotonic()
        try:
            with socket.create_connection((self.target, port), timeout=1.5):
                return port, True, round((time.monotonic() - t0) * 1000, 1)
        except (socket.timeout, ConnectionRefusedError, OSError):
            return port, False, round((time.monotonic() - t0) * 1000, 1)

    def _scan_all(self) -> list[PortResult]:
        scan_fn = self._scan_port_c if self._lib else self._scan_port_py
        results: list[PortResult] = []
        with ThreadPoolExecutor(max_workers=150) as pool:
            futures = {pool.submit(scan_fn, p): p for p in range(self.start, self.end + 1)}
            for future in as_completed(futures):
                try:
                    port, is_open, ms = future.result()
                    results.append(PortResult(port=port, open=is_open,
                                              service=COMMON_PORTS.get(port, "unknown"), ms=ms))
                except Exception:
                    pass
        return sorted(results, key=lambda r: r.port)

    def run(self) -> list[PortResult]:
        total = self.end - self.start + 1
        console.rule(f"[bold cyan]Port Scan  \u00b7  [yellow]{self.target}[/yellow]  [dim]({self.start}\u2013{self.end})[/dim]")
        console.print(f"[dim]Scanning {total} ports\u2026[/dim]")
        results    = self._scan_all()
        open_ports = [r for r in results if r.open]
        if not open_ports:
            console.print("[yellow]Tidak ada port terbuka yang ditemukan.[/yellow]")
            return []
        t = Table(
            title=f"[bold cyan]Open Ports:[/bold cyan] [green]{len(open_ports)} found[/green]",
            box=box.ROUNDED, border_style="cyan", header_style="bold cyan",
        )
        t.add_column("Port",    width=8,  justify="right")
        t.add_column("Service", width=18)
        t.add_column("Status",  width=12)
        t.add_column("ms",      width=8,  justify="right")
        for r in open_ports:
            t.add_row(str(r.port), r.service, "[bold green]OPEN[/bold green]", f"{r.ms}")
        console.print(t)
        console.print(
            f"\n[bold]Scanned:[/bold] [cyan]{total}[/cyan]  "
            f"[bold]Open:[/bold] [green]{len(open_ports)}[/green]  "
            f"[bold]Closed:[/bold] [dim]{total - len(open_ports)}[/dim]\n"
        )
        return open_ports
