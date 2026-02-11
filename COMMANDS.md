# Workforce Nexus: Exhaustive Command Reference

This document provides a complete list of commands for all modules in the Workforce Nexus suite.

Scope note: to avoid documentation drift, this table lists **only commands/flags that are verifiably present in this repo workspace** (i.e., `python3 … --help` shows them). Global wrappers (e.g. `mcp-activator`) may exist after installation, but their exact CLI surface depends on the installed shims.

---

## 🚀 The Activator (repo-mcp-packager)
**Main Responsibility**: Orchestration, Multi-tool Installation, and Workspace Sync.

| Action | Direct Command |
| :--- | :--- |
| **Industrial Install / Bootstrap** | `python3 bootstrap.py --permanent` *(alias: --industrial)* |
| **Lite Install / Bootstrap** | `python3 bootstrap.py --lite` |
| **Sync Workspace (Update)** | `python3 bootstrap.py --sync` *(alias: --update)* |
| **Launch Dashboard** | `python3 bootstrap.py --gui` |
| **Standalone Repo Installer** | `python3 serverinstaller/install.py` |
| **Full Wipe (Start Fresh) (CLI-only)** | `python3 uninstall.py --kill-venv --purge-data` |

---

## 👁️ The Observer (mcp-server-manager)
**Main Responsibility**: Real-time observability, health monitoring, and the Visual Dashboard.

| Action | Global Command | Direct Module Command |
| :--- | :--- | :--- |
| **Launch Dashboard** | `mcp-observer gui` | `python3 -m mcp_inventory.cli gui` |
| **Scan Workspace** | `mcp-observer scan .` | `python3 -m mcp_inventory.cli scan .` |
| **List Inventory** | `mcp-observer list` | `python3 -m mcp_inventory.cli list` |
| **Check Synergy** | `mcp-observer check-synergy` | `python3 -m mcp_inventory.cli check-synergy` |
| **Check Heartbeats** | `mcp-observer running` | `python3 -m mcp_inventory.cli running` |

---

## 💉 The Surgeon (mcp-injector)
**Main Responsibility**: Precise JSON configuration injection for IDEs (Claude, Cursor, etc.).

| Action | Direct Command |
| :--- | :--- |
| **Inject Server (interactive)** | `python3 mcp_injector.py --add` *(optionally use --config PATH or --client NAME)* |
| **Remove Server** | `python3 mcp_injector.py --remove` |
| **List Config** | `python3 mcp_injector.py --list` |
| **List Known Clients** | `python3 mcp_injector.py --list-clients` |
| **Startup Detect + Prompt Inject** | `python3 mcp_injector.py --startup-detect` |

*Supported Clients: `claude`, `cursor`, `vscode`, `xcode`, `codex`, `aistudio`, `google-antigravity` (alias of AI Studio)*

---

## 📚 The Librarian (mcp-link-library)
**Main Responsibility**: Knowledge persistence, link storage, and local codebase indexing.

| Action | Direct Command |
| :--- | :--- |
| **Add URL** | `python3 mcp.py --add` |
| **Index Directory** | `python3 mcp.py --index` |
| **Search Knowledge** | `python3 mcp.py --search` |
| **Index Sibling Tools** | `python3 mcp.py --index-suite` |
| **Run as MCP server (stdio) (CLI-only)** | `python3 mcp.py --server` |

---

## 🌍 Directory Context Rules

### 1. Where to run what?
*   **Autonomous Bootstrap**: Run `python3 bootstrap.py --permanent` from a standalone copy of the bootstrapper. It will automatically fetch the rest of the Workforce Nexus suite from GitHub if sibling repositories are not found.
*   **Installation/Dev Mode**: Run from the root of a full workspace.
*   **Daily Global Use**: Once installed, run `mcp-surgeon`, `mcp-observer`, etc., from **any directory** in your terminal.
*   **Standalone Installer**: Run `python3 serverinstaller/install.py` from the root of the repository you wish to package.

### 2. Service Management
*   **Starting GUI**: `mcp-observer gui`
*   **Stopping GUI**: Press `Ctrl + C` in the terminal where it's running.
*   **Restarting**: Just rerun the command. It will automatically re-index your active servers.

### 3. PATH Setup
If `mcp-` commands are not found, add this to your `~/.zshrc` (macOS) or `~/.bashrc`:
```bash
export PATH="$HOME/.mcp-tools/bin:$PATH"
```

---

## 🧩 GUI Widget Coverage

The Nexus GUI scaffold in `repo-mcp-packager/gui/` now maps **every executable command** in this `COMMANDS.md` table to a widget action.

* Widgets are **tier-gated** (`lite`, `standard`, `permanent`): unsupported actions render visually unchecked.
* Widget execution routes through a safe backend allowlist (`widget_id`-based), then reports stdout/stderr and exit code.
* Scope model is preserved: each repo remains standalone, while suite commands still assemble the integrated package.
