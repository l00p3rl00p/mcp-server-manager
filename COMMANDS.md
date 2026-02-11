# Workforce Nexus: Exhaustive Command Reference

This document provides a complete list of commands for all modules in the Workforce Nexus suite. Once the suite is installed in **Industrial** or **Standard** mode, use the **Global Command** for convenience from any directory.

---

## 🚀 The Activator (repo-mcp-packager)
**Main Responsibility**: Orchestration, Multi-tool Installation, and Workspace Sync.

| Action | Global Command | Direct Module Command |
| :--- | :--- | :--- |
| **Full Bootstrap** | `mcp-activator --industrial` | `python3 bootstrap.py --industrial` |
| **Standard Install** | `mcp-activator --standard` | `python3 bootstrap.py --standard` |
| **Lite Install** | `mcp-activator --lite` | `python3 bootstrap.py --lite` |
| **Sync Workspace** | `mcp-activator --sync` | `python3 bootstrap.py --sync` |
| **Launch Dashboard** | `mcp-activator --gui` | `python3 bootstrap.py --gui` |
| **Standalone Repo** | N/A | `python3 serverinstaller/install.py` |

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

| Action | Global Command | Direct Module Command |
| :--- | :--- | :--- |
| **Inject Server** | `mcp-surgeon add [client] [name] [cmd]` | `python3 mcp_injector.py add ...` |
| **Remove Server** | `mcp-surgeon remove [client] [name]` | `python3 mcp_injector.py remove ...` |
| **List Config** | `mcp-surgeon list [client]` | `python3 mcp_injector.py list ...` |
| **Guided Mode** | `mcp-surgeon interactive` | `python3 mcp_injector.py interactive` |

*Supported Clients: `claude`, `cursor`, `vscode`, `xcode`, `codex`, `aistudio`*

---

## 📚 The Librarian (mcp-link-library)
**Main Responsibility**: Knowledge persistence, link storage, and local codebase indexing.

| Action | Global Command | Direct Module Command |
| :--- | :--- | :--- |
| **Add URL** | `mcp-librarian --add [url]` | `python3 mcp.py --add [url]` |
| **Index Workspace** | `mcp-librarian --index [path]` | `python3 mcp.py --index [path]` |
| **Search Knowledge** | `mcp-librarian --search "query"` | `python3 mcp.py --search "query"` |
| **Index Sibling Tools**| `mcp-librarian --index-suite` | `python3 mcp.py --index-suite` |
| **Wipe Index** | N/A | `python3 mcp.py --clear` |

---

## 🌍 Directory Context Rules

### 1. Where to run what?
*   **Autonomous Bootstrap**: Run `python3 bootstrap.py --industrial` from a standalone copy of the bootstrapper. It will automatically fetch the rest of the Workforce Nexus suite from GitHub if sibling repositories are not found.
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
