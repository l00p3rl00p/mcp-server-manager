# Build Contract: Unit 1 - Core Backend Resilience

## 1. Outcome Statement
The `nexus-librarian` (Core Type-0) must auto-start with the GUI. Injection commands must use `mcp-surgeon` correctly without triggering help-screens.

## Q1–Q4 (Quadrants)
- **Q1 (Front Door)**: Starting Nexus via tray/launcher results in a running backend and a reachable Dashboard.
- **Q2 (Doctor + Evidence)**: A doctor command proves core services + injection work, and the evidence is appendable to the canonical `EVIDENCE.md`.
- **Q3 (Architecture)**: Auto-start behavior is explicit and discoverable in docs; no “magic” background work without a visible status surface.
- **Q4 (Sealed Core)**: Core service auto-start is deterministic, bounded, and does not spawn uncontrolled processes.

## 2. Technical Strategy
### A. Auto-Start Logic (`gui_bridge.py`)
- Modify `ProjectManager.__init__` to trigger `ensure_core_services()`.
- `ensure_core_services()` checks if `librarian` is running. If not, starts it.
- **Constraint**: Must use the `mcp-librarian` binary from `bin_dir`.

### B. Injection Logic Repair (`gui_bridge.py`)
- The current `nexus_run_command` splits arguments naively. 
- **Fix**: Identify `mcp-surgeon` calls and ensure flags like `--add` and `--client` are passed as distinct list elements, not a single string blob.

## 3. Verification Plan
- **Pre-Check**: `/status` shows Librarian: `stopped`.
- **Post-Check**: `/status` shows Librarian: `online` (PID present).
- **Injection Test**: `curl ... /nexus/run` with injection payload returns `{"success": true}`.

## Doctor (Must Run)
- `python3 -m unittest tests/test_status_payload.py`
- `python3 -m unittest tests/test_gui_e2e_http.py`
- `python3 -m unittest tests/test_cli_smoke.py`

## Q2 Evidence (Canonical Location)
Append evidence to:
- `/Users/almowplay/Developer/Github/mcp-creater-manager/EVIDENCE.md`

Minimum evidence payload:
- A `curl` (or GUI action) showing `/status` before + after core auto-start.
- One successful `/nexus/run` injection execution (stdout + exit code captured).
