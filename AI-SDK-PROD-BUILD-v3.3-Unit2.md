# Build Contract: Unit 2 - Functional Interface (The "No Modal" UI)

## 1. Outcome Statement
Rip out the center-screen Injection Modal. Replace it with an inline **Command Drawer** in the Server Card. Add a **dedicated Logs View** for deep observability.

## Q1–Q4 (Quadrants)
- **Q1 (Front Door)**: A human can inject and view logs without hunting for hidden menus/modals.
- **Q2 (Doctor + Evidence)**: A deterministic test covers the drawer/logs surfaces plus at least one human-failure scenario (empty/error/loading).
- **Q3 (Architecture)**: UI surfaces and backing endpoints are named and stable (no “mystery” state).
- **Q4 (Sealed Core)**: UI does not fabricate data; it reflects real server state/endpoints.

## 2. Technical Strategy
### A. The "Command Drawer" (`ServerCard.tsx`)
- **State**: Expand existing card state to include `showInjector: boolean`.
- **UI**: Add an `AnimatePresence` drawer below the metrics row.
- **Content**: Move the client selector + "Inject" button here.
- **Feedback**: Show success/failure toast, but kept the drawer open for logs.

## Build Matrix (Implementation Contract)

| Item | Surface | Requirement |
|---|---|---|
| Drawer injection | Server Card | No modal; injection controls live in-card; result feedback is visible |
| Per-server logs | Server Card / Logs view | “View last start log” (or equivalent) shows the correct server’s stdout/stderr |
| Human-failure UAT | Empty/error states | Empty logs/server offline show a clear error + next action (no silent failure) |

### B. Deep Observability (`LogsPanel.tsx`)
- **New Component**: A dedicated panel/tab that tails logs for a specific server ID.
- **Route**: `gui_bridge.py` update to serve `/logs/<server_id>`. (Wait... we might need a backend tweak for this dedicated stream).
- **Interim**: Use the existing global log stream but filter by `server_id` client-side.

### C. Contextual Audit (`AuditButton.tsx`)
- Add a small icon button to the card header: "Generate Audit Report for <Server>".

## 3. Verification Plan
- **Pre-Check**: Clicking "Inject" currently opens a large modal.
- **Post-Check**: Clicking "Inject" slides down a drawer inside the card.
- **Logs**: A new "Logs" button appears on the card, opening a view with specific stdout.

## Doctor (Must Run)
- `python3 -m unittest tests/test_gui_e2e_http.py`
- `python3 -m unittest tests/test_gui_writable_logs.py`
- `python3 -m unittest tests/test_gui_optimization.py`

## Q2 Evidence (Canonical Location)
Append evidence to:
- `/Users/almowplay/Developer/Github/mcp-creater-manager/EVIDENCE.md`

Minimum evidence payload:
- Screenshot (or log) showing drawer replaces modal.
- Proof logs are per-server (server id requested + returned lines).
- One human-failure UAT note (empty logs, server not running, 404) with expected UI response.
