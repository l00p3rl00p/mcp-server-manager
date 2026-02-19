# MCP Observer: The System Monitor (mcp-server-manager)

**The Eyes of the Workforce Nexus.**

The **Observer** is a specialized tool for tracking, monitoring, and visualizing the state of your MCP ecosystem. It ensures that you always know *what* is running, *where* it is installed, and *how* healthy it is.

## 🚀 Quick Start

To launch the Visual Dashboard (and install dependencies if missing):
```bash
../nexus.sh
```

**What this does:**
1.  **Verification**: Checks system health and security flags.
2.  **Launching**: Starts the system tray app and opens your browser.
3.  **Desktop**: Ensures "Start Nexus.command" is on your Desktop.

> **Part of the Workforce Nexus Suite**: For full orchestration and global command setup, see the [Master README](../README.md).

---

## 🌟 Core Capabilities

### 1. Nexus Forge (The Factory)
Transform any local folder or Git repository into a hardened MCP server.
- **Portability Mandate**: Automatically generates `ATP_COMPLIANCE_GUIDE.md` for every forged server, ensuring downstream agents know how to use it safely.
- **Async Build**: Long-running clone/build tasks happen in the background without blocking the UI.
- **Strawberry Test**: Verifies logic fidelity before the server goes live.

### 2. Inventory Awareness
Automatically scans and catalogs MCP servers in your workspace or installed centrally in `~/.mcp-tools`.
- Tracks: Source path, Installation type (venv/docker), Config status.
- Prevents "Ghost Servers" (forgotten processes).

### 3. Health & Diagnostics
Runs deep diagnostic checks on every registered server.
- **Connectivity**: Can the server be reached?
- **Responsiveness**: Is it replying to JSON-RPC pings?
- **Environment**: Are dependencies valid?

### 4. The GUI Dashboard
Includes a built-in web dashboard (React-based) for visual management.
- **Launch**: `mcp-observer gui`
- **Features**: 
  - Real-time status indicators (Green/Red).
  - One-click server toggling.
  - Integration with the Librarian for knowledge browsing.
  - **Token Cost Transparency**: Visual badges for every command execution.

---

## 📝 Metadata
* **Status**: Production Ready (v3.1.0)
* **Author**: l00p3rl00p
* **Part of**: The Nexus Workforce Suite
