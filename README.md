# Local MCP-Server Discovery + Inventory (mcpinv)

**A scan-wide / accept-strict tool for managing MCP servers across your machine.**

Never lose track of an MCP server again. `mcpinv` discovers, validates, and inventories your MCP servers with high precision and low noise.

---

## ⚡ Quick Start

### 1. Installation
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

---

## 📋 Table of Contents

1. [Overview](#-overview)
2. [Features](#-features)
3. [The Scan → Gate → Accept Workflow](#-the-scan--gate--accept-workflow)
4. [Inventory Management](#-inventory-management)
5. [Heartbeat & Running Status](#-heartbeat--running-status)
6. [Standardizing with mcp.server.json](#-standardizing-with-mcpserverjson)
7. [Git-Packager Workspace](#-git-packager-workspace)
8. [Contributing](#-contributing)
9. [License](#-license)

---

## 🔍 Overview

`mcpinv` is designed to solve the "tool sprawl" problem. It scans your machine for potential MCP servers using broad triggers but applies a strict **MCP Gate** to ensure only legitimate servers enter your inventory.

The goal is to provide a curated, human-editable `inventory.yaml` that serves as the source of truth for all your MCP tools.

---

## 🌟 Features

* **Intelligent Scanning**: Uses broad triggers (.env, Dockerfile, etc.) to find candidates.
* **Strict Gating**: Auto-accepts strong signals, flags medium signals for review, and rejects noise.
* **Human-Editable Inventory**: Authoritative list stored in `~/.mcpinv/inventory.yaml`.
* **Heartbeat Visibility**: Detects running Docker containers and MCP-related processes.
* **Explainability**: Shows *why* a folder was detected as an MCP server.

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

Your inventory is stored at `~/.mcpinv/inventory.yaml`. You can edit it by hand or use the CLI:

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
mcpinv running
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

## 🤝 Git-Packager Workspace

Part of the **Git-Packager** suite:

| Tool | Purpose |
|------|--------|
| **mcp-injector** | Safely manage MCP server configs in IDE JSON files |
| **mcp-server-manager** (this tool) | Discover and track MCP servers across your system |
| **repo-mcp-packager** | Install and package MCP servers with automation |

### Integrated Usage
* **mcpinv bootstrap**: Checks for and fetches missing workspace components.
* **Attach to IDE**: Use the inventory from `mcpinv` to drive `mcp-injector` for one-click IDE setup.

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

---

## 📝 License

This project is licensed under the MIT License.
