# Architecture - MCP Observer (mcp-server-manager)

**The technical blueprint for the Visual Control Surface & Dashboard.**

The **Observer** is the "Eyes" of the Workforce Nexus. It provides real-time observability, health monitoring, and lifecycle management for all indexed MCP servers. In v3.2.5, it introduces **Persistent Error Dismissal** and **Build-Drift Protection**.

---

## 🏗 Subsystem Breakdown

### 1. The Lifecycle Manager (`nexus_tray.py`)
The entry point for the desktop experience.
*   **Dual-Threading**: Flask (Backend) runs as a daemon thread, while `pystray` (System Tray) owns the main thread.
*   **Platform Anchors**: Implements the "Indigo Dot" (macOS) and System Tray icon (Windows).
*   **Control**: Handles "Open Dashboard" and "Stop & Quit" signals to ensure clean process termination.
*   **Detached Launch**: The `Start Nexus.command` script uses `nohup` and `disown` to strictly separate the backend process from the terminal window, ensuring the server persists even if the terminal is closed.

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

### 5. WebMCP Wrapper (`webmcp_server.py` + `sync_webmcp.py`)
An MCP stdio server (v2.0.0) that exposes the entire GUI backend as agent-callable tools with a **dynamic, self-updating capability registry**.

* **Protocol**: JSON-RPC 2.0 over stdin/stdout (MCP spec, `2024-11-05`).
* **Backend**: Proxies calls to `gui_bridge.py` at `http://127.0.0.1:5001` (configurable via `GUI_BASE_URL` env var).
* **Two-tier tool registry**: Static tools (hard-coded, always present) + Dynamic tools (persisted in `webmcp_capabilities.json`, auto-synced on build).
* **Agent Testing**: Allows any Claude agent to call `gui_status`, `gui_server_control`, `gui_forge`, etc. without a browser — enabling headless regression and UAT workflows.
* **Registration**: Registered in `~/.claude/settings.json`, `~/.gemini/antigravity/mcp_config.json`, and `~/.codex/config.toml` under key `nexus-gui`.

#### Dynamic Capability Registry (`webmcp_capabilities.json`)
Tracks all dynamically-registered tools next to `webmcp_server.py` (version-controlled).

**Post-build auto-sync flow:**
```
npm run build
  └─ tsc -b && vite build    ← compiles React/TS
  └─ postbuild               ← runs sync_webmcp.py automatically
       └─ GET /capabilities  ← asks Flask for its live route map
       └─ diff vs registry   ← adds new routes, removes stale ones
       └─ writes webmcp_capabilities.json
```

**Manual registry management via meta-tools:**
| Meta-tool | Purpose |
|---|---|
| `gui_sync_capabilities` | Fetch live Flask routes and reconcile registry |
| `gui_register_tool` | Manually add a new dynamic tool |
| `gui_unregister_tool` | Remove a dynamic tool (static tools protected) |
| `gui_list_registry` | List all tools, labelled static vs dynamic |

#### GUI Bridge Capabilities Endpoint (`GET /capabilities`)
Returns the full live Flask route map as machine-readable JSON — consumed by `sync_webmcp.py` and `gui_sync_capabilities` tool.

#### Static Tool Surface (always present)
| Tool | Endpoint | Purpose |
|---|---|---|
| `gui_health` | `GET /health` | Liveness check |
| `gui_status` | `GET /status` | Full system + server inventory |
| `gui_validate` | `GET /validate` | Config validation |
| `gui_system_drift` | `GET /system/drift` | Drift detection |
| `gui_logs` | `GET /logs` | Session log tail |
| `gui_server_logs` | `GET /server/logs/:id` | Per-server stdout/stderr |
| `gui_server_control` | `POST /server/control` | start / stop / restart |
| `gui_server_add` | `POST /server/add` | Register new server |
| `gui_server_delete` | `POST /server/delete` | Remove server |
| `gui_server_update` | `POST /server/update/:id` | Edit server metadata |
| `gui_nexus_catalog` | `GET /nexus/catalog` | Browse installable servers |
| `gui_nexus_run` | `POST /nexus/run` | Run catalog command |
| `gui_injector_clients` | `GET /injector/clients` | Detected MCP clients |
| `gui_injector_status` | `POST /injector/status` | Toggle server in a client |
| `gui_forge` | `POST /forge` | Scaffold new MCP server |
| `gui_forge_status` | `GET /forge/status/:id` | Poll forge task |
| `gui_librarian_roots` | `GET/POST/DELETE /librarian/roots` | Watched directories |
| `gui_librarian_add` | `POST /librarian/add` | Index resource |
| `gui_project_history` | `GET /project/history` | Change history |
| `gui_project_snapshot` | `POST /project/snapshot` | Take snapshot |
| `gui_export_report` | `GET /export/report` | HTML status report |

---

## 🔍 Data Flow: The Observation Loop

1. **Scan**: Bridge reads the central inventory.
2. **Ping**: Bridge sends health-check requests to registered servers.
3. **Telemetrize**: Bridge collects host system metrics.
4. **Push**: Bridge serves the aggregated state to the UI via the `/status` endpoint.
5. **Drift-Check**: At bootstrap, the suite compares `src/` vs `dist/` timestamps to ensure the served GUI matches the active codebase.

---

## 📝 Metadata
* **Status**: Stable Release (v3.2.11 "Dynamic Injection")
* **Author**: l00p3rl00p
* **Part of**: The Workforce Nexus Suite
