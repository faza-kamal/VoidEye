"""
VoidEye · utils/helpers.py
Shared helper functions, logging, and output utilities.
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()


def print_error(msg: str) -> None:
    console.print(f"[bold red]✗[/bold red]  {msg}")


def print_success(msg: str) -> None:
    console.print(f"[bold green]✓[/bold green]  {msg}")


def print_info(msg: str) -> None:
    console.print(f"[bold cyan]ℹ[/bold cyan]  {msg}")


def print_warn(msg: str) -> None:
    console.print(f"[bold yellow]⚠[/bold yellow]  {msg}")


def save_json(data: Any, path: str) -> None:
    """Save data to a JSON file with timestamp metadata."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": data,
    }
    out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print_success(f"Saved → {out}")


def timestamp_str() -> str:
    """Return current UTC timestamp as a filename-safe string."""
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")
