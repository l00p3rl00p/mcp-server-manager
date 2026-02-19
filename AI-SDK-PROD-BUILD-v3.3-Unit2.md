# Build Contract: Unit 2 - Functional Interface (The "No Modal" UI)

## 1. Outcome Statement
Rip out the center-screen Injection Modal. Replace it with an inline **Command Drawer** in the Server Card. Add a **dedicated Logs View** for deep observability.

## 2. Technical Strategy
### A. The "Command Drawer" (`ServerCard.tsx`)
- **State**: Expand existing card state to include `showInjector: boolean`.
- **UI**: Add an `AnimatePresence` drawer below the metrics row.
- **Content**: Move the client selector + "Inject" button here.
- **Feedback**: Show success/failure toast, but kept the drawer open for logs.

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
