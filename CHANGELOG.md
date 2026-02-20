# Changelog - MCP Observer (mcp-server-manager)

## [3.3.1] - 2026-02-20
- **Deterministic Server Start**: Added runtime selection + per-server venv setup to prevent “start lies” and missing-dependency crashes.
- **Truthful Logs**: Start logs now include resolved command, requires-python, setup-log pointers, and exit markers.
- **Maintenance Endpoints**: Added dry-run support and fixed python upgrade to use `pyproject.toml` editable installs.
- **OS Navigation (GUI)**: Added `/os/pick_file` and `/os/pick_folder` endpoints and wired GUI “Browse…”/“Pick File…” buttons (non-headless only).

## [3.3.0] - 2026-02-19
- **Core Resilience**: `nexus-librarian` (and other Type-0 dependencies) now auto-start if missing when the GUI launches.
- **Inline Injection**: Replaced the blocking Injection Modal with a non-intrusive "Accordion Drawer" directly inside the Server Card.
- **Functional Parity**: Fixed `mcp-surgeon` argument parsing in the backend to ensure injection commands execute correctly (no more "Help Screen" failures).
- **Deep Observability**: Added a "Contextual Audit" button to every server card for instant log access.

## [3.2.8] - 2026-02-19
- **Librarian Empowerment**: Added "OPEN" and "EDIT" buttons to the Librarian tab. You can now open URLs in your browser or files in your native OS handler (Folders/PDFs/etc) directly from the GUI.
- **Native Editing**: The Librarian now supports an "EDIT" action for local files, opening them in your system's default editor.
- **CLI Parity**: Added `--open <id>` and `--edit <id>` to the `mcp-librarian` CLI.
- **Navigation Optimization**: Reordered the sidebar: Operations is now 3rd, prioritizing real-time system activity.

## [3.2.7] - 2026-02-19
- **Forge Persistence**: Successful forge results are now persisted in `active_context.json` and remain visible even after page refresh or app restart.
- **IDE Integration Hardening**: Added "Google AI Antigravity" to the supported IDE list. Replaced prompt-based injection with a robust dropdown UI.
- **Security Policy Update**: Whitelisted `python3` and `npx` in the Bridge task runner to allow the injector to function correctly.
- **Manual Config Access**: Added an inline JSON preview for manual configuration if auto-injection is not desired.

## [3.2.5] - 2026-02-19
- **GUI Drift Protection**: Integrated a mandatory build-drift check in `nexus-verify.py`. The suite now prevents serving stale UI assets by comparing `src/` vs `dist/` timestamps.
- **Persistent Dismissal**: Added "Dismiss All" to the Recovery Needed section. Acknowledged errors are persisted in `active_context.json` so they stay hidden across restarts.
- **Auto-Build Standard**: `setup.sh` now ensures the GUI is built after dependencies are installed or refreshed.

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
## [3.2.10] - 2026-02-19
- **Dashboard Injection Workflow**: Added a dedicated "Inject" action to server cards. Opens a modal to check current install status across IDEs (Claude/Cursor/VSCode) and inject with one click.
- **Visual Alert System**: Added pulsing "Red Dot" (Operations) for fatal errors and "Blue Dot" (Lifecycle) for available updates to the sidebar.
- **Startup Resilience**: The `Start Nexus.command` script now correctly detaches from the terminal using `nohup`, allowing the window to be closed without killing the backend.
- **Control Fixes**: Resolved a critical `NameError` in `gui_bridge.py` that prevented Start/Stop actions.
- **UX Polish**: Metric cards now have proper spacing. Inventory view state (List vs Card) is persisted across reloads.
- **Safe Command Execution**: The Injector now uses the robust `mcp-surgeon` wrapper instead of raw python calls.

---
*Status: Stable Release (v3.2.10)*
