# Local MCP-Server Discovery + Inventory (mcpinv)

**A scan-wide / accept-strict tool for managing MCP servers across your machine—now with a built-in GUI dashboard.**

Never lose track of an MCP server again. `mcpinv` discovers, validates, and inventories your MCP servers with high precision and low noise. It includes both a powerful CLI and a lightweight web-based GUI for visual management.

---

## ⚡ Quick Start

### 1. Installation
The GUI is automatically installed alongside the CLI.
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configure & Scan
```bash
# Add a root directory to scan
mcpinv config --add-root ~/Developer

# Run a scan to discover servers
mcpinv scan
```

### 3. Launch the GUI (Optional)
If you prefer visual management, launch the dashboard:
```bash
mcpinv gui
```
Then open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 📋 Table of Contents

1. [Overview](#-overview)
2. [Features](#-features)
3. [GUI Dashboard](#-gui-dashboard)
4. [The Scan → Gate → Accept Workflow](#-the-scan--gate--accept-workflow)
5. [Inventory Management](#-inventory-management)
6. [Heartbeat & Running Status](#-heartbeat--running-status)
7. [Standardizing with mcp.server.json](#-standardizing-with-mcpserverjson)
8. [Git-Packager Workspace](#-git-packager-workspace)
9. [Standalone vs Integrated: Understanding the Trade-offs](#-standalone-vs-integrated-understanding-the-trade-offs)
10. [Contributing](#-contributing)
11. [License](#-license)

---

## 🔍 Overview

`mcpinv` is designed to solve the "tool sprawl" problem. It scans your machine for potential MCP servers using broad triggers but applies a strict **MCP Gate** to ensure only legitimate servers enter your inventory.

The goal is to provide a curated, human-editable `inventory.yaml` that serves as the source of truth for all your MCP tools.

---

## 🌟 Features

* **Intelligent Scanning**: Uses broad triggers (.env, Dockerfile, etc.) to find candidates.
* **Strict Gating**: Auto-accepts strong signals, flags medium signals for review, and rejects noise.
* **Built-in GUI Dashboard**: Visualize your inventory, scan results, and server health.
* **Human-Editable Inventory**: Authoritative list stored in `~/.mcpinv/inventory.yaml`.
* **Heartbeat Visibility**: Detects running Docker containers and MCP-related processes.
* **Explainability**: Shows *why* a folder was detected as an MCP server.

---

## 📊 GUI Dashboard

The GUI is a lightweight web interface that provides high-level visibility into your MCP ecosystem.

### How to use it:
* **Launch**: Run `mcpinv gui` in your terminal.
* **Access**: Navigate to `http://localhost:8501`.
* **Optional**: The GUI is a companion to the CLI; you can perform almost all actions from either interface.

### What it shows:
1. **Application Health**: Current state, last successful run, and mode.
2. **Inventory Status**: Visual list of confirmed, review-worthy, and rejected servers.
3. **Heartbeat & Signals**: Real-time view of what is likely running on your system.
4. **Command Execution**: Timeline and outcomes of recent discovery runs.

---

## 🔄 The Scan → Gate → Accept Workflow

### Phase 1: Scan (Wide Net)
Looks for any folders that *might* be MCP-ish based on:
* `.env` files
* `docker-compose.yml` / `Dockerfile`
* `package.json` / `pyproject.toml`
* README mentions of "MCP"

### Phase 2: Gate (Accept Strict)
Candidates must pass a **Strong Signal** to be auto-accepted:
* `package.json` includes `@modelcontextprotocol/*`
* Code contains `modelcontextprotocol` imports
* `mcp.server.json` manifest present
* Docker labels like `io.mcp.*`

### Phase 3: Review
Medium-confidence candidates (e.g., README says MCP but code is unclear) are placed in a **Review Bucket** for manual approval.

---

## 🗃 Inventory Management

Your inventory is stored at `~/.mcpinv/inventory.yaml`. You can edit it by hand or use the CLI/GUI:

```bash
# Add something manually if detection missed it
mcpinv add --name browser-agent --path "/Users/me/code/browser-agent"

# If it's a Docker Compose service
mcpinv add --name browser-agent --path "/Users/me/code/browser-agent" --compose docker-compose.yml --service mcp
```

---

## 💓 Heartbeat & Running Status

Check which servers are likely running right now:
```bash
# Via CLI
mcpinv running

# Via GUI
# View the health dashboard at http://localhost:8501
```
This performs a best-effort check of Docker containers and OS processes to provide visibility into your active tools.

---

## ⚙️ Standardizing with mcp.server.json

For near-perfect discovery, drop an `mcp.server.json` file in any MCP folder:
```json
{ 
  "name": "browser-agent", 
  "transport": "http" 
}
```
This acts as a "Strong Signal" that skips the review bucket and auto-accepts during a scan.

---

## 🤝 Git-Packager Workforce Suite

This tool is the **Observer (Monitor)** for the complete four-component workforce ecosystem:

| Tool | Persona | Purpose |
| --- | --- | --- |
| **mcp-injector** | The Surgeon | Safely manage MCP server configs in IDE JSON files |
| **mcp-server-manager** | The Observer | Discover, track, and monitor health of all MCP servers |
| **repo-mcp-packager** | The Activator | Install, package, and update MCP servers with automation |
| **mcp-link-library** | The Librarian | Curated knowledge base and document engine for AI tools |

### Integrated Benefits
* **Universal Bootstrapping**: `mcpinv bootstrap` aligns and fetches all 4 tools.
* **One-Click Lifecycle**: Launch `update` directly from the inventory dashboard.
* **Knowledge Health**: Dashboard monitors Librarian data integrity and index status.

---

## 🎯 Standalone vs Integrated: Understanding the Trade-offs

### Can This Tool Work Standalone?

**Yes**, but with important limitations. Understanding what you gain and lose helps you decide how to use it.

### 📊 Standalone Usage

**What you can do:**
- ✅ **Discover** existing MCP servers on your system
- ✅ **Inventory** them in `~/.mcpinv/inventory.yaml`
- ✅ **Visualize** what servers you have via GUI
- ✅ **Check status** of running servers (Docker, processes)
- ✅ **Manually add** servers to inventory
- ✅ **Audit** your MCP ecosystem

**What you cannot do:**
- ❌ **Install** new repos as MCP servers (requires `repo-mcp-packager`)
- ❌ **Auto-configure** IDE configs (requires `mcp-injector`)
- ❌ **Convert** legacy repos into MCP servers (requires `repo-mcp-packager`)
- ❌ **One-click setup** from discovery to running (requires full suite)

**Best for:**
- Users who manually install MCP servers
- Teams wanting visibility into existing MCP infrastructure
- Auditing/documentation purposes
- "Read-only" MCP ecosystem management

### 🚀 Integrated Usage (Full Git-Packager Suite)

**What you gain with `repo-mcp-packager`:**
- ✅ **Click "Install"** in GUI → repo becomes MCP server automatically
- ✅ **Environment setup** handled (Python venvs, Node, Docker)
- ✅ **Legacy script conversion** via MCP bridge generation
- ✅ **Clean uninstall** that surgically removes installations
- ✅ **Complete autonomy** from discovery to deployment

**What you gain with `mcp-injector`:**
- ✅ **Auto-configure IDEs** (Claude, Cursor, etc.) from inventory
- ✅ **One-click "Attach to All IDEs"** from GUI
- ✅ **Safe JSON editing** with validation and backups
- ✅ **No bracket hell** when managing IDE configs

**Best for:**
- Users who want zero-friction MCP server installation
- Teams building MCP ecosystems from scratch
- Anyone who values "drop and run" simplicity
- Developers who hate manual configuration

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

---

## 📝 License

This project is licensed under the MIT License.
