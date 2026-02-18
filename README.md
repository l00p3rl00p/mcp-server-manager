# MCP Observer: The System Monitor (mcp-server-manager)

**The Eyes of the Workforce Nexus.**

The **Observer** is a specialized tool for tracking, monitoring, and visualizing the state of your MCP ecosystem. It ensures that you always know *what* is running, *where* it is installed, and *how* healthy it is.

## 🚀 Quick Start (Standalone)

To launch the Visual Dashboard immediately:
```bash
python3 -m mcp_inventory.cli gui
```

> **Part of the Workforce Nexus Suite**: For full orchestration and global command setup, see the [Master README](../README.md).

---

## 🌟 Core Capabilities

### 1. Inventory Awareness
Automatically scans and catalogs MCP servers in your workspace or installed centrally in `~/.mcp-tools`.
- Tracks: Source path, Installation type (venv/docker), Config status.
- Prevents "Ghost Servers" (forgotten processes).

### 2. Health & Diagnostics
Runs deep diagnostic checks on every registered server.
- **Connectivity**: Can the server be reached?
- **Responsiveness**: Is it replying to JSON-RPC pings?
- **Environment**: Are dependencies valid?

### 3. The GUI Dashboard
Includes a built-in web dashboard (Streamlit-based) for visual management.
- **Launch**: `mcp-observer gui`
- **Features**: 
  - Real-time status indicators (Green/Red).
  - One-click server toggling.
  - Integration with the Librarian for knowledge browsing.

---

## 🛠️ Usage

### CLI Mode (Human/Agent)
```bash
# Scan current directory for servers
python3 -m mcp_inventory.cli scan .

# List known inventory
python3 -m mcp_inventory.cli list

# Run health check
python3 -m mcp_inventory.cli health

# Launch GUI
python3 -m mcp_inventory.cli gui
```

### Standalone Operation
The Observer functions independently. It does not require the full Nexus suite to be present. It can managing a single repo's servers just as well as a full industrial cluster.

---

## 📝 Metadata
* **Status**: Production Ready
* **Author**: l00p3rl00p
* **Part of**: The Nexus Workforce Suite
