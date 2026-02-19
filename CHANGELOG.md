# Changelog - MCP Observer (mcp-server-manager)

## [3.2.1] - 2026-02-19

### Improvements
- **System Tray App**: `nexus_tray.py` — Flask runs as daemon thread; pystray owns main thread. GUI never requires a terminal.
- **Desktop Launcher**: `Start Nexus.command` placed on `~/Desktop` at install time. Double-click to start; move anywhere.
- `gui_bridge.py` direct invocation now redirects to tray. `NEXUS_HEADLESS=1` flag for CI/server environments.
- `pystray` + `Pillow` added to dependencies.

---

## [3.2.0] - 2026-02-19

### Security
- CORS restricted to `localhost:5173/5174` only — wildcard removed.
- `ForgeManager.tasks` writes now guarded by `threading.Lock` — eliminates race on concurrent forge requests.
- `NexusSessionLogger` file writes guarded by `threading.Lock` — prevents JSONL interleaving.

### Fixes
- Bare `except:` in `scan.py:120` → typed `(json.JSONDecodeError, KeyError)`.
- Bare `except:` in `verify_atp_v16.py:13` → `json.JSONDecodeError`.
- `App.tsx`: 20+ hardcoded `localhost:5001` URLs → single `API_BASE` constant (`VITE_API_URL`-driven).
- `setup.sh`: Added `set -o noclobber`.

---

## [2.0.0] - 2026-02-18

### 📊 Observability (The Agent HUD)
- **Token HUD**: Visual color-coded badges in the Command Hub showing the "Token Weight" of every call.
- **Sparkline Telemetry**: Real-time 60s trend lines for global CPU and Memory usage.
- **High-Fidelity PID Tracking**: Dashboard cards now show exact PID, RSS Memory, and CPU % for every managed server.
- **Absolute Storage Metrics**: Disk widgets now display total vs used bytes.

### 🛠️ Management & Control
- **Unified Command Catalog**: Central portal for executing maintenance tasks (Sync, Repair, Index) without the terminal.
- **Interactive Server Control**: GUID-based start/stop/restart logic with guided failure diagnostics.
- **Flask Bridge 2.0**: Updated binding to `0.0.0.0` for improved container/proxy compatibility.

### Fixed
- **Log Rotation**: Size-based rotation for `session.jsonl` to prevent disk overflow.

---

## [1.1.0] - 2026-02-15
- Initial release of the React/Vite GUI.
- Fleet management dashboard.
- Command state persistence.

---
*Status: Production Ready (v3.2.1)*
