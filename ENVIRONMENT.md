# Environment - Local MCP-Server Discovery + Inventory

Technical requirements and configuration details for the `mcpinv` tool.

---

## 📋 Table of Contents
1. [Core Requirements](#-core-requirements)
2. [FileSystem Impact](#-filesystem-impact)
3. [Configuration Defaults](#-configuration-defaults)
4. [Accuracy Conventions](#-accuracy-conventions)

---

## 🔍 Core Requirements

* **Python**: 3.10+ required for core logic and async operations.
* **Docker CLI**: Optional, but required for detecting heartbeat signals from containers.
* **Operating System**: macOS and Linux are primary targets. Windows is supported but may show variations in process and port discovery logic.

---

## 📂 FileSystem Impact

`mcpinv` stores all user data in a hidden directory in your home folder:
* **Config**: `~/.mcpinv/config.json`
* **Inventory**: `~/.mcpinv/inventory.yaml` (The source of truth)

---

## ⚙️ Configuration Defaults

### Scan Roots
By default, the tool looks in common development locations:
* `~/Code`
* `~/Projects`
* `~/Dev`
* `~/Documents`

### Exclusions
To maintain performance and reduce noise, these directories are always skipped:
* `.git`, `node_modules`, `.venv`
* Cache directories and build outputs

---

## 🌟 Accuracy Conventions

You can improve detection accuracy by adding these markers to your projects:

### 1. Manifest File
Place an `mcp.server.json` file in your project root. This acts as a **Strong Signal** that triggers automatic inventory addition.

### 2. .env Marker
Add an explicit name to your `.env` file:
```bash
MCP_SERVER_NAME=your-server-name
```
This upgrades a `.env` file from a **Weak Signal** (auto-reject) to a **Strong Signal** (confirmed).
