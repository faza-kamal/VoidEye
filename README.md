<div align="center">

```
 ██╗   ██╗ ██████╗ ██╗██████╗ ███████╗██╗   ██╗███████╗
 ██║   ██║██╔═══██╗██║██╔══██╗██╔════╝╚██╗ ██╔╝██╔════╝
 ██║   ██║██║   ██║██║██║  ██║█████╗   ╚████╔╝ █████╗  
 ╚██╗ ██╔╝██║   ██║██║██║  ██║██╔══╝    ╚██╔╝  ██╔══╝  
  ╚████╔╝ ╚██████╔╝██║██████╔╝███████╗   ██║   ███████╗
   ╚═══╝   ╚═════╝ ╚═╝╚═════╝ ╚══════╝   ╚═╝   ╚══════╝
```

**Modular OSINT Framework — CLI + TUI**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Author](https://img.shields.io/badge/Author-faza--kamal-cyan)](https://github.com/faza-kamal)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS-lightgrey)](https://github.com/faza-kamal/VoidEye)

</div>

---

## Overview

**VoidEye** is a modular, production-ready OSINT (Open-Source Intelligence) framework written in Python 3.11+ with high-performance C modules for time-critical operations. It features an interactive TUI menu and a full CLI interface.

> ⚠️ **Legal Notice:** VoidEye is built for **educational, research, and authorized security assessments only**. Use it only on systems you own or have explicit permission to test. Unauthorized use against third-party systems is illegal.

---

## Features

| Module | Description |
|--------|-------------|
| **Username Scan** | Async search across 25+ platforms with status/timing |
| **Email OSINT** | DNS MX lookup, Gravatar, GitHub/Reddit footprint |
| **Domain / IP Scan** | WHOIS, DNS records, reverse DNS, subdomain enum, banner grab |
| **Google Dork Generator** | 40+ dork templates — files, admin, creds, GitHub |
| **Onion Search** | Ahmia.fi scraper via Tor SOCKS5 proxy |

---

## Architecture

```
VoidEye/
├── main.py              # CLI + TUI entry point (argparse + rich)
├── core/
│   ├── username.py      # Async username scanner (aiohttp)
│   ├── email.py         # Email OSINT (dnspython + aiohttp)
│   ├── domain.py        # Domain/IP OSINT (whois + dns + C module)
│   ├── dork.py          # Google dork generator
│   └── onion.py         # Ahmia.fi Tor search (aiohttp-socks)
├── cmodules/
│   ├── bannergrab.c     # TCP banner grabber (compiled → .so)
│   ├── fastscan.c       # Non-blocking port scanner (compiled → .so)
│   └── Makefile
├── utils/
│   └── helpers.py       # Shared utilities (logging, JSON export)
├── output/              # Auto-created scan output directory
├── requirements.txt
└── README.md
```

### Why C Modules?

Python's GIL and interpreted overhead make tight TCP socket loops slow. The C shared libraries (`bannergrab.so`, `fastscan.so`) are loaded via `ctypes` and called directly — giving near-native performance for network I/O operations while keeping Python as the orchestration layer.

---

## Installation

```bash
# 1. Clone
git clone https://github.com/faza-kamal/VoidEye.git
cd VoidEye

# 2. Create virtualenv (recommended)
python3 -m venv .venv && source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Compile C modules (requires gcc)
cd cmodules && make && cd ..
```

### Tor Setup (for Onion Search)
```bash
# Arch Linux
sudo pacman -S tor
sudo systemctl start tor

# Debian/Ubuntu
sudo apt install tor
sudo systemctl start tor
```

---

## Usage

### Interactive TUI
```bash
python3 main.py
```

### CLI Mode
```bash
# Username scan (with JSON export)
python3 main.py username faza-kamal -o output/result.json

# Email OSINT
python3 main.py email target@example.com

# Domain scan with banner grabbing (requires compiled C module)
python3 main.py domain example.com --banner

# Google dork generator
python3 main.py dork "example.com" -c creds

# Onion search via Tor
python3 main.py onion "cybersecurity forums"

# Onion search without Tor (clearnet only)
python3 main.py onion "topic" --no-tor
```

---

## C Module Integration

```python
import ctypes
from pathlib import Path

lib = ctypes.CDLL(str(Path("cmodules/bannergrab.so")))
lib.grab_banner.restype  = ctypes.c_int
lib.grab_banner.argtypes = [ctypes.c_char_p, ctypes.c_int,
                             ctypes.c_char_p, ctypes.c_int]

buf = ctypes.create_string_buffer(4096)
ret = lib.grab_banner(b"example.com", 80, buf, 4096)
if ret == 0:
    print(buf.value.decode())
```

---

## Roadmap

### MVP (v0.1)
- [x] Project structure + architecture
- [x] Username async scanner (25 platforms)
- [x] Email OSINT (MX, Gravatar, footprint)
- [x] Domain scan (WHOIS, DNS, subdomain enum)
- [x] Google dork generator
- [x] Onion search via Ahmia + Tor
- [x] C modules: bannergrab + fastscan
- [x] Rich TUI + argparse CLI

### v0.2 — Enhanced
- [ ] Plugin system (drop-in Python modules in `plugins/`)
- [ ] IP geolocation (ip-api.com)
- [ ] Phone OSINT module
- [ ] Shodan/Censys integration (API key)
- [ ] HTML report export

### v0.3 — Advanced
- [ ] Config file (`~/.config/voideye/config.toml`)
- [ ] Profile/session saving
- [ ] Docker container
- [ ] CI/CD with GitHub Actions
- [ ] Rate-limit profile management

---

## Ethical Use

VoidEye is developed for:
- Authorized penetration testing
- OSINT research and education
- Personal digital footprint auditing
- CTF (Capture The Flag) challenges

**Never use VoidEye against systems without explicit written authorization.**

---

## License

MIT License © 2024 faza-kamal

---

<div align="center">

**[github.com/faza-kamal/VoidEye](https://github.com/faza-kamal/VoidEye)**

</div>
