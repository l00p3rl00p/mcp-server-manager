# Build Contract: Unit 1 - Core Backend Resilience

## 1. Outcome Statement
The `nexus-librarian` (Core Type-0) must auto-start with the GUI. Injection commands must use `mcp-surgeon` correctly without triggering help-screens.

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
