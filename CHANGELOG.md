# Changelog - MCP Observer (mcp-server-manager)

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
*Status: Production Ready (v2.0.0)*
