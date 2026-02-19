# Workforce Nexus: Commands (Quick Start)

This file is the **human-first** quick command sheet.

For the exhaustive, verifiable command matrix, see `COMMANDS.md`.

---

## Run Standalone (Observer)

CLI help:

```bash
python3 -m mcp_inventory.cli --help
```

Launch GUI:

```bash
python3 -m mcp_inventory.cli gui
```

Default URL: `http://localhost:8501`

---

## Install / Repair the Full Suite

This repo’s `bootstrap.py` is a **safe forwarder** (no disk scanning). It will:
- use `../repo-mcp-packager/bootstrap.py` if present, or
- use `~/.mcp-tools/repo-mcp-packager/bootstrap.py` if installed, or
- (TTY-only) offer to fetch Activator into `~/.mcp-tools`.

```bash
python3 bootstrap.py --permanent
```

Non-interactive suite install (clones missing repos into `~/.mcp-tools`, no disk scanning):

```bash
python3 bootstrap.py --install-suite --permanent
```

Diagnostics:

```bash
python3 bootstrap.py --install-suite --permanent --devlog
```

---

## Uninstall (Central-Only, Safe by Default)

Full wipe:

```bash
python3 uninstall.py --purge-data --kill-venv
```

Dry run:

```bash
python3 uninstall.py --purge-data --kill-venv --dry-run
```

Diagnostics:

```bash
python3 uninstall.py --purge-data --kill-venv --verbose --devlog
```
