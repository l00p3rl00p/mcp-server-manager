# User Outcomes - Nexus Observer & Forge (mcp-server-manager)

This document defines success for the **Nexus Observer**, the visual control surface for the ecosystem, and the **Forge**, the engine for logic hardening and server transformation.

---

## 🔗 Canonical Outcomes & Mission (Project Scope)

This repo-level `USER_OUTCOMES.md` is subordinate to the canonical [Workforce Nexus Mission Statement](/Users/almowplay/Developer/Github/mcp-creater-manager/USER_OUTCOMES.md).

## Core Mission Statement - READ ONLY- NEVER EDIT

The mission is to provide a unified visual command center for the entire MCP ecosystem, enabling real-time telemetry, lifecycle management, and the rapid transformation of arbitrary codebases into production-ready MCP servers via the Forge engine. It eliminates terminal dependency and manual boilerplate, guaranteeing a premium, observable, and highly efficient server environment.

### The Rule of Ones: The COMMANDER System Architecture
The Nexus Observer & Forge act as the central nervous system and factory of the suite, anchored in:
- **One Install Path:** Served as the primary OS-integrated GUI surface within the Unified Nexus.
- **One Entry Point:** The "Nexus Commander" dashboard and the OS System Tray (Indigo Dot).
- **One Status:** A unified, real-time health dashboard for all local and remote MCP servers.
- **One Log:** Centralized observability for the dashboard backend, the Forge engine, and server lifecycle events.


---

## 📋 Table of Contents
1. [Successful Outcomes](#-successful-outcomes)
2. [High-Fidelity Signals](#-high-fidelity-signals)
3. [Design Guardrails](#-design-guardrails)

---

## 🔍 Successful Outcomes (Nexus Observer & Forge)

As a user, I want:

### 1. Unified Visual Control (The Observer)
* **Real-Time Telemetry**: See CPU, memory, and process health for every managed MCP server in a single, responsive dashboard.
* **Token Auditing**: View the "Token Weight" and cost-efficiency metrics of my agent interactions to optimize my tool usage.
* **System Tray Persistence**: The Observer runs as an OS-native tray app (Indigo Dot), allowing the dashboard to remain active even if the terminal is closed.

### 2. Rapid Logic Hardening (The Forge)
* **One-Click Server Creation**: Transform any local directory containing Python or Node scripts into a fully functional MCP server using the "Forge" interface.
* **ATP-Compliance Injection**: Automatically wrap forged servers with ATP security layers, including AST-based sandboxing and `noclobber` shell protections.
* **Zero-Knowledge Deployment**: Build and deploy a new server without writing a single line of boilerplate JSON or manifest code.

### 3. Deep Observability
* **Live Log Streaming**: View the standard output and error streams of any server directly in the GUI to debug integration issues in real-time.
* **Contextual Audit Reports**: Click a single button on any server card to get a full security and performance audit of that specific component.

### 4. Zero-Friction Maintenance
* **One-Click Injection**: Inject forged servers into IDEs (Claude, Cursor) directly from the dashboard card via the integrated Surgeon (mcp-injector) link.
* **Automated Repair Feedback**: Visually detect when local server code has drifted from the managed mirror and prompt a `--repair`.

### 2. Intelligent Discovery & Autonomy
* **Autonomous Bootstrap**: The Activator can fetch the entire Workforce Nexus suite from GitHub, allowing it to move from "standalone script" to "suite architect" without local source siblings.
* **Inventory Awareness**: The installer identifies all available components (Python, Node, Docker) and allows selective installation to prevent "package bloat."
* **Local Source Parity**: In developer mode, the tool installs the application *exactly as it exists* in the local root, respecting custom modifications.

### 3. Trust & Transparency
* **Surgical Integrity**: The `uninstall` command surgically reverses only the changes it made, ensuring the host is returned to its pre-installation state.
* **Before/After Verification**: Clear reports allow the operator (human or agent) to verify every change. No stealth modifications to PATH or Registry.

### 4. Universal Observability
* **Visual Status**: The user can see the health and connection status of all Nexus components (Observer, Librarian, Injector, Activator) in a single dashboard.
* **Graceful Degradation**: The system functions even if components are missing, clearly indicating what is available vs. what needs installation.

### 5. Resilient Lifecycle
* **Atomic Rollback**: If an installation fails at any step, the system automatically reverts to a clean state, leaving no partial artifacts.
* **Safe Upgrades**: The `mcp-activator --repair` command is the single unified update loop, ensuring all central tools stay synchronized with the latest security and feature patches.
* **Context-Locked Execution**: Entry points carry their own venv and PYTHONPATH, ensuring they work regardless of the user's active terminal environment.

### 6. Best-in-Class Tokenization & Efficiency (ATP)
* **Code over Tools**: Agents should prefer writing code (filtering, mapping, reducing) over multiple sequential tool calls.
* **On-Demand Discovery**: Implement `searchApi` logic to avoid context bloat from pre-loading large tool catalogs.
* **Parallel Execution**: Leverage `Promise.all` patterns for concurrent API and LLM sub-agent calls to reduce wall-clock time.
* **Aggregated Context**: Only return necessary, processed data to the main LLM context, keeping raw high-volume data isolated in the execution environment.

---

## 🚀 Roadmap to 100% Compliance

To fully align with these outcomes, the following enhancements are planned:

*   **GUI Reliability (Target 95%+)**: ~~Transition GUI from a blocking process to a background service with PID management.~~ **IMPLEMENTED (UAT EVIDENCE PENDING)** — System tray (`pystray`) + Desktop launcher. Flask runs as daemon thread. No terminal required.
*   **Librarian Synergy**: Implement a dynamic watcher so the Librarian indexes changes in real-time, not just on installation.
*   **Operational Awareness**: Add "version health" checks to the GUI dashboard to visually signal when a `--repair` is required.

### 2026-02-11 Alignment Update
* **Injector Startup Detect**: Added startup detection/prompt flow for common IDE clients, including `claude`, `codex`, and `aistudio` (plus `google-antigravity` alias).
* **Package-Created Component Injection Policy**: If full Nexus components are detected (`~/.mcp-tools/bin`), the injector prompts injection only for components that are **actual MCP servers over stdio** (currently `nexus-librarian`). Other Nexus binaries (e.g. `mcp-activator`, `mcp-observer`) are CLIs and should not be injected into MCP clients.
* **Tier-Aware GUI Control Surface**: GUI command widgets now map to command catalog behavior with visual unchecked state for unsupported tier actions.
* **Central-Only Uninstall Policy**: Full wipes only touch approved central locations (e.g. `~/.mcp-tools`, `~/.mcpinv`, and the Nexus PATH block). No disk scans or directory-tree climbing during uninstall.
* **Uninstall Safety + Diagnostics**: Uninstall now prints an explicit deletion plan and requires confirmation (unless `--yes`). Added `--verbose` and `--devlog` (JSONL) with 90-day retention for diagnostics.
* **Bootstrap Safety Policy**: Workspace detection avoids filesystem crawling (checks only `cwd` + script-sibling workspace). If a workspace `.env` is present, the installer warns about potential conflicts with the central install.

### 2026-02-19 Alignment Update (v3.2.1)
* **L1 GUI Outcome**: User can start and stop the GUI without a terminal. Double-click `Start Nexus.command` on Desktop → menu-bar icon appears → click to open Dashboard or stop.
* **OS Visibility**: Server on/off state is visible in the macOS menu bar without opening a browser or terminal.
* **Browser Independence**: Closing the browser tab does not stop the server — lifecycle is owned by the tray icon, not the browser.

### 2026-02-19 Alignment Update (v3.2.10)
* **One-Click Injection**: The "Forge" capability now extends to the Dashboard. Generic servers can be injected into any supported IDE (Claude, VSCode, Cursor) via a dedicated UI modal, eliminating CLI friction.
* **Visual Semantics**: The sidebar now actively communicates system state via "Pulse Dots" (Red=Fatal, Blue=Update), reducing the need to constantly check the dashboard for critical issues.
* **Resilient Lifecycle**: The `Start Nexus.command` script is now fully detached, ensuring the backend survives inconsistent terminal states or user closures.

### 2026-02-19 Alignment Update (v3.3 - Zero-Friction Suite)
* **Zero-Friction Command Suite**: Double-clickable `.command` (Mac) and `.bat` (Windows) scripts provided for both Unified Root and Per-Repo tasks. No terminal knowledge required for core maintenance.
* **Sync Gridlock Resilience**: The `mcp-activator --sync` engine now handles git conflicts automatically via forced resets and cleans for the industrial environment.
* **Contextual GUI Foundations**: Replaced center-screen modals with inline **Command Drawers** for server injection. Integrated contextual Audit Report buttons into every Server Card.
* **Dynamic Workspace Detection**: The bootstrap engine now utilizes 3-tier deep heuristic checks to identify development workspaces regardless of the caller's initial working directory.

---

## 🚥 High-Fidelity Signals

* **Success**: `.librarian/manifest.json` correctly lists all artifacts, and `verify.py` reports `[VERIFIED]` for all items.
* **Failure**: Encountering an interactive prompt in `--headless` mode.
* **Success**: Running `uninstall.py` removes the `# Nexus Block` from `.zshrc` without deleting other aliases (legacy installs may still contain `# Shesha Block`).

---

## 🛡 Design Guardrails

* **No Sudo**: Reject any feature that requires global `sudo` permissions if a local `.venv` alternative exists.
* **No Unmanaged Overwrites**: Reject any "auto-update" feature that replaces local configuration without a manifest-backed snapshot.
* **Respect Local Code**: Treatment of the current repository state as the "source of truth." Never overwrite local changes with upstream templates.
* **Token Stewardship**: Prioritize "Zero-Token Data Processing" (client-side filtering) to minimize LLM round-trips and context saturation. (DELIVERED)
* **Isolation of Concerns**: Execution logic should run in an isolated environment, keeping host system secrets (SSH keys, unrelated tokens) protected from untrusted code. (DELIVERED)
* **Cost Transparency**: Users must see the "Token Weight" of every interaction to make informed decisions. (DELIVERED)
* **ATP Compliance**: Shell operations must default to `noclobber` to prevent accidental data loss. (DELIVERED)
* **Non-Blocking Interfaces**: Critical actions (like Injection) must utilize **inline expansion** (accordions/drawers) instead of center-screen modals. The UI must NEVER obscure real-time error toasts or logs. (IMPLEMENTED — UAT EVIDENCE PENDING)
* **Lifecycle Persistence**: Servers must maintain their last known state (Running/Stopped) across Nexus restarts. New servers auto-start upon creation. Unexpected stops must trigger a logged error event.
* **Contextual Help**: Operation tab 'Help/Info' buttons must be scoped to the specific card (e.g., inside 'Custom Run') to avoid UI clutter. (IMPLEMENTED — UAT EVIDENCE PENDING)
* **Deep Observability**: A dedicated Logging View is required. Users must be able to view detailed, per-server `stdout/stderr` streams. A global **"Nexus System Log"** must be prominently available to debug the orchestrator itself, distinct from the ephemeral Command Hub output.
* **Contextual Audit**: The 'Audit Report' capability must be available per-component (Server/Librarian/System) rather than a generic global action. (IMPLEMENTED — UAT EVIDENCE PENDING)
* **Core Reliability**: The `nexus-librarian` and other Type-0 Core Dependency MUST auto-start with the GUI and auto-restart on failure. A "Stopped" CORE is a System Defect. (IMPLEMENTED — UAT EVIDENCE PENDING)
* **Managed Mirror Policy**: The industrial runtime environment (`~/.mcp-tools`) is a **Managed Mirror**. Any local changes in the mirror are considered "drift" and will be automatically overwritten by the workspace or GitHub on `--repair` to ensure deterministic stability. (IMPLEMENTED — UAT EVIDENCE PENDING)
* **Zero-Friction Maintenance**: Common maintenance tasks (Install, Sync, Dashboard, Health) must be accessible via OS-native double-clickable scripts located at the project root. (IMPLEMENTED — UAT EVIDENCE PENDING)

---

## ✅ Evidence Links (Verified)

These outcomes have repo-wide evidence in the root `EVIDENCE.md` (not just code presence):

* **Cost Transparency / Token Weight**: Unit 23
* **ATP Shell Safety (`noclobber`)**: Unit 24
* **ATP Sandbox Isolation + Strawberry Test**: Unit 22
* **ATP Tooling (`search_api`, `execute_code`, `--json`, `/llm/batch`)**: Unit 20

---
### 2026-02-25 Mission Audit Results (v3.3.5 Red Team)
**Mission Score: 90%** | Anchored to: *"Unified visual command center — zero terminal dependency, real-time telemetry, Forge engine."*

| Feature | Status | Confidence |
|---|---|---|
| Real-time telemetry (CPU/RAM/Disk per server) | ✅ | 85% |
| System Tray Persistence (no terminal needed) | ✅ | 90% |
| Token Auditing visible in GUI | ✅ | 82% |
| Forge: local dir → MCP server (one-click) | ✅ | 88% |
| ATP-compliance injection into forged servers | ✅ | 92% |
| Live log streaming per server | ✅ | 85% |
| Contextual audit report per server card | ✅ | 83% |
| One-click IDE injection from dashboard | ✅ | 83% |
| **Drift detection → prompt `--repair` (GAP-R2)** | ✅ | 90% |
| Auto-start `nexus-librarian` on GUI launch | ✅ | 82% |
| No center-screen modals (inline drawers only) | ✅ | 90% |
| GUI labels: Commander (not Bridge) | ✅ | 99% |
| Observer ATP / help-crash fixed (GAP-003/4) | ✅ | 95% |

---
*Status: v3.3.5 RELEASED — 2026-02-25. GAP-R2 Closed.*

