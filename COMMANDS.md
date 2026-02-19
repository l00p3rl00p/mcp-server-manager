# Workforce Nexus: Command Reference

This document provides a complete, exhaustive list of commands for the Workforce Nexus suite. It merges and supersedes previous quick-start guides.

> **Note**: All `mcp-*` commands assume you have the `~/.mcp-tools/bin` directory in your PATH. If not, you can run the underlying `python3` scripts directly from your workspace.

---

## 🛠️ Core Lifecycle (The Activator)
**Module**: `repo-mcp-packager`
**Bin**: `mcp-activator` (or `python3 bootstrap.py`)

Responsible for installation, synchronization, and uninstallation.

| Goal | Command | Description |
| :--- | :--- | :--- |
| **Install / Bootstrap** | `python3 bootstrap.py --permanent` | Installs the suite to `~/.mcp-tools`. |
| **Update / Sync** | `mcp-activator --sync` | **Crucial**: Syncs your git workspace changes to the active runtime. |
| **Repair** | `mcp-activator --repair` | Fixes missing dependencies or broken venvs. |
| **Uninstall (Wipe)** | `python3 uninstall.py --purge-data --kill-venv` | **Factory Reset**: Removes `~/.mcp-tools` and all data. |

---

## 👁️ Observability (The Observer)
**Module**: `mcp-server-manager`
**Bin**: `mcp-observer`

Responsible for the Visual Dashboard, server health monitoring, and inventory management.

| Goal | Command | Description |
| :--- | :--- | :--- |
| **Launch Dashboard** | `mcp-observer gui` | Starts the Web GUI (Default: http://localhost:8501). |
| **Health Check** | `mcp-observer health` | Runs diagnostics on all suite components. |
| **List Servers** | `mcp-observer list` | Lists all registered MCP servers. |
| **Scan Workspace** | `mcp-observer scan .` | Auto-discovers MCP servers in the current directory. |
| **Check Processes** | `mcp-observer running` | Shows running MCP-related processes (Docker, Python). |

---

## 💉 Integration (The Surgeon)
**Module**: `mcp-injector`
**Bin**: `mcp-surgeon`

Responsible for configuring IDEs (Claude, Cursor, VSCode) to use your MCP servers.

| Goal | Command | Description |
| :--- | :--- | :--- |
| **Inject Server** | `mcp-surgeon --add <server> --client <ide>` | `mcp-surgeon --add notebooklm --client claude` |
| **List Clients** | `mcp-surgeon --list-clients` | Shows detected IDE configuration files. |
| **List Injected** | `mcp-surgeon --client <ide> --list` | Shows servers currently configured in a specific IDE. |
| **Remove Server** | `mcp-surgeon --remove <server>` | Removes a server from all known IDE configs. |

---

## 📚 Knowledge (The Librarian)
**Module**: `mcp-link-library`
**Bin**: `mcp-librarian` (or `mcp.py`)

Responsible for persistent indexing, file watching, and resource retrieval.

| Goal | Command | Description |
| :--- | :--- | :--- |
| **Start Server** | `mcp-librarian --server` | Runs the MCP stdio server (for IDE usage). |
| **Start Watcher** | `mcp-librarian --watch` | **New**: Real-time file monitoring for indexed roots. |
| **Add Resource** | `mcp-librarian --add <url/file>` | Indexes a specific URL or local file. |
| **Index Directory** | `mcp-librarian --index <path>` | Recursively indexes a local directory. |
| **Search** | `mcp-librarian --search <query>` | semantic/text search across the knowledge base. |

---

## 🐛 Troubleshooting & Maintenance

### How to Reset/Reinstall
If the system is out of sync or behaving erratically:

1.  **Uninstall / Wipe**:
    ```bash
    # From mcp-server-manager or repo-mcp-packager directory
    python3 uninstall.py --purge-data --kill-venv
    ```
2.  **Reinstall**:
    ```bash
    python3 bootstrap.py --permanent
    ```
3.  **Sync (if developing)**:
    ```bash
    mcp-activator --sync
    ```
