# The Observer: Features & Commands

## Overview
**The Observer (`mcp-server-manager`)** provides visibility and control over your entire MCP ecosystem. It scans your machine for potential servers, validates them, and serves as the central inventory.

## Features

### 1. 🖥️ GUI Dashboard
*   **Inventory View**: See all your MCP servers in one place.
*   **Health Checks**: Real-time status of your system (Docker, Processes, Nexus DB).
*   **Logs**: View live logs from the backend and the Librarian.
*   **Actions**: Run scans, checks, updates, and attach IDEs directly from the browser.

### 2. 🔍 Intelligent Scanning
*   **Discovery**: Finds servers via `package.json`, `pyproject.toml`, or `docker-compose.yml`.
*   **Gating**: Distinguishes between "Strong Signals" (auto-add) and "Candidates" (review queue).
*   **Inventory**: Maintains a curated YAML list at `~/.mcpinv/inventory.yaml`.

### 3. 💓 System Health
*   **Heartbeats**: Detects if servers are actually running (Docker containers, OS processes).
*   **Verification**: Ensures the internal databases and config files are intact.

## Command Reference

### Core
```bash
# Scan your system for MCP servers
python -m mcp_inventory.cli scan

# Launch the Web GUI
python -m mcp_inventory.cli gui
```

### Management
```bash
# Add a server manually
python -m mcp_inventory.cli add --name my-server --path /path/to/server

# Remove a server
python -m mcp_inventory.cli remove --name my-server

# List status of all servers
python -m mcp_inventory.cli list
```

### Diagnostics
```bash
# Check system health
python -m mcp_inventory.cli health

# Check for running instances
python -m mcp_inventory.cli running
```

---
**Part of the Workforce Nexus**
*   **The Surgeon**: `mcp-injector` (Configuration)
*   **The Observer**: `mcp-server-manager` (Dashboard)
*   **The Activator**: `repo-mcp-packager` (Automation)
*   **The Librarian**: `mcp-link-library` (Knowledge)
