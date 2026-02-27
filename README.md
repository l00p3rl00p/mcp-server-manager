# MCP Observer: The System Monitor (mcp-server-manager)

**The visual control surface for the Workforce Nexus.**

The **Observer** tracks, monitors, and visualizes the state of your MCP ecosystem. In v3.2.1, it transitions from a standalone CLI tool to a persistent **System Tray App** that manages your entire server fleet.

## 🚀 Quick Start

To launch the Visual Dashboard and Tray App:
```bash
../nexus.sh
```

**What this does:**
1.  **Tray Launch**: Starts `nexus_tray.py` (Indigo dot) in your menu bar (macOS) or system tray (Windows).
2.  **Dashboard**: Opens your browser to `http://localhost:5001`.
3.  **Bridge**: The bridge acts as the backend for the GUI and serves built React assets.

> **Master View**: For full suite orchestration, see the [Master README](../README.md).

---

## 🌟 Capabilities (v3.2.1)

### 1. System Tray Anchor
- **Lifecycle**: GUI runs as a background service managed by the OS menu bar.
- **Auto-Exit**: Choose "Stop & Quit" from the tray to shutdown the back-end bridge.
- **One-Click**: Open the dashboard anytime without a terminal.

### 2. Nexus Forge (V3 Engine)
Transform any local folder or Git repository into a hardened MCP server.
- **Portability**: Automatically generates `ATP_COMPLIANCE_GUIDE.md` for forged servers.
- **Deterministic Wrapping**: Uses standard shebangs and absolute paths for reliability.

### 3. Metric Telemetry
- **Resource HUD**: Real-time CPU/RAM/Disk stats for the host and every managed process.
- **PID Tracking**: Dashboard cards show exact process health via `psutil`.

### 4. Direct UI Bridge
- **Port 5001**: The Flask bridge handles API requests and serves the React frontend directly from `gui/dist`.
- **Latency-Free**: Optimized JSON responses for sub-10ms state updates.

### 5. Seamless Injection (v3.3)
- **Inline Experience**: Inject servers directly from the dashboard card—no modals, no context switching.
- **Deep Observability**: Stream live logs per-server and audit health instantly.
- **Core Resilience**: Librarian auto-starts and runs self-healing checks on launch.

---

## 🔐 Safety & Governance
- **Localhost Bound**: The API Bridge only listens on `127.0.0.1`.
- **Noclobber**: All file operations respect the `set -o noclobber` safety mandate.

---

## 🔄 Drift Lifecycle Integration (v3.3.6+)

The Observer integrates with the Drift Lifecycle system:
- **Health Monitoring**: Tracks server health during drift detection
- **Forge Management**: Creates MCP servers compatible with drift detection
- **Deployment Visibility**: Shows deployed vs origin state in dashboard

See main repo: [Drift Lifecycle System](../DRIFT_LIFECYCLE_OUTCOMES.md)

---

## 📝 Metadata
* **Status**: Stable Release (v3.3.6)
* **GUI Port**: 5001
* **Part of**: The Workforce Nexus Suite
