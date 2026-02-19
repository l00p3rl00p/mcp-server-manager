# Architecture - MCP Observer (mcp-server-manager)

**The technical blueprint for the Visual Control Surface & Dashboard.**

The **Observer** is the "Eyes" of the Workforce Nexus. It provides real-time observability, health monitoring, and lifecycle management for all indexed MCP servers. In v3.2.5, it introduces **Persistent Error Dismissal** and **Build-Drift Protection**.

---

## 🏗 Subsystem Breakdown

### 1. The Lifecycle Manager (`nexus_tray.py`)
The entry point for the desktop experience.
* **Dual-Threading**: Flask (Backend) runs as a daemon thread, while `pystray` (System Tray) owns the main thread.
* **Platform Anchors**: Implements the "Indigo Dot" (macOS) and System Tray icon (Windows).
* **Control**: Handles "Open Dashboard" and "Stop & Quit" signals to ensure clean process termination.

### 2. The GUI Bridge (`gui_bridge.py`)
The backend API for the React dashboard.
* **Unified Serving**: In production mode, Flask serves the built React assets directly from `gui/dist`.
* **Telemetry**: Integrates `psutil` to stream real-time CPU, RAM, and Disk metrics.
* **Inventory Management**: Interfaces with `inventory.yaml` to track server status (Online/Stopped/Pending).
* **Session Persistence**: Stores `active_context.json` to remember the active project and user-dismissed errors across restarts.

### 3. Nexus Forge Engine (`forge/`)
The subsystem for creating new MCP servers from scratch.
* **Async Tasks**: Uses a dedicated thread pool to clone remote repos or wrap local folders without stalling the UI.
* **Snapshot Recovery**: Automatically captures timestamped backups of the inventory before any forge operation.

### 4. Direct UI (`gui/`)
A high-performance React + Vite dashboard.
* **Micro-Animations**: Provides instant visual feedback for server state changes.
- **Token HUD**: Displays the "Token Weight" of every interaction using heuristic estimation.

---

## 🔍 Data Flow: The Observation Loop

1. **Scan**: Bridge reads the central inventory.
2. **Ping**: Bridge sends health-check requests to registered servers.
3. **Telemetrize**: Bridge collects host system metrics.
4. **Push**: Bridge serves the aggregated state to the UI via the `/status` endpoint.
5. **Drift-Check**: At bootstrap, the suite compares `src/` vs `dist/` timestamps to ensure the served GUI matches the active codebase.

---

## 📝 Metadata
* **Status**: Stable Release (v3.2.5)
* **Author**: l00p3rl00p
* **Part of**: The Workforce Nexus Suite
