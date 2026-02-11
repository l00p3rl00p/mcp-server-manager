# ENVIRONMENT.md — Workforce Nexus Suite (mcp-server-manager)

Host environment requirements, safety rules, and OS-specific paths for the **Server Manager** repo (inventory + GUI).

---

## 🔍 Core Dependency Rules

### Python
* **Minimum**: Python **3.9+**
* **Recommended**: Python **3.11+**
* **Isolation**: When installed as part of the suite, runs from the **central** Nexus environment under `~/.mcp-tools` (no workspace venv required).

### GUI runtime
* The GUI runs as a local web app (served from Python). No Node/Docker required for the default GUI.

---

## 🛠 Central Paths (Suite Home)

The suite uses predictable, user-owned paths:
* Nexus home: `~/.mcp-tools`
* Tools bin: `~/.mcp-tools/bin`
* Shared venv (optional): `~/.mcp-tools/.venv`
* Shared state + devlogs: `~/.mcpinv/`
* Inventory file (created on install if missing): `~/.mcp-tools/mcp-server-manager/inventory.yaml`

This repo also creates (if missing) subdirectories used by the GUI:
* `state/`
* `logs/`
* `artifacts/`

---

## 🖥 GUI Notes

* Default local URL: `http://localhost:8501`
* Logs are written to the suite’s active logs directory (central + writable).
* GUI actions that spawn subprocesses should be recorded to the shared devlog when `--devlog` is enabled.

---

## ⚙️ Safety Rules (No Disk Scans)

To reduce risk and surprise:
* Tools do **not** crawl your filesystem or walk up directory trees to “find” workspaces.
* Uninstall operations only touch **approved central locations** (e.g. `~/.mcp-tools`, `~/.mcpinv`, and the Nexus PATH block).
* If you need to clean a git workspace, the tools print manual cleanup commands instead of deleting workspace files.

---

## 🧾 Devlogs (Shared Diagnostics)

Shared JSONL devlogs live under:
* `~/.mcpinv/devlogs/nexus-YYYY-MM-DD.jsonl`

Behavior:
* Entries are appended as actions run.
* Old devlog files are pruned on use (90-day retention).

---

## 📝 Metadata
* **Status**: Hardened
* **Reference**: [ARCHITECTURE.md](./ARCHITECTURE.md) | [USER_OUTCOMES.md](./USER_OUTCOMES.md)

