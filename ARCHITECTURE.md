# Architecture - Git Repo MCP Converter & Installer

**The technical blueprint for the Workforce Nexus Activator.**

This document provides a low-density, comprehensive deep dive into the internal logic, state machines, and modular subsystems that power the `repo-mcp-packager`. It is intended for developers and architects who need to understand exactly how the system achieves industrial-grade reliability.

---

## 🔍 Core Philosophy: The Clean Room Installer

The Activator follows the **Clean Room** principle. It treats every repository as a potentially hostile or cluttered environment and ensures that:

1.  **Zero-Dep Bootstrap**: The core installer requires only the Python Standard Library.
2.  **Volatile Isolation**: Dependencies are kept in local `.venv` or `node_modules` folders, never installed globally.
3.  **Surgical Traceability**: Every bit flipped or file created is recorded in a manifest for atomic reversal.

---

## 🏗 Subsystem Breakdown

### 1. The Probe Layer (`audit.py`)
The Probe layer is the system's "Sensory Organ." It performs non-destructive environment discovery.

*   **Capabilities**: Detects Shell type (bash/zsh), Python paths, Node/NPM availability, Docker daemon status, and PATH hygiene.
*   **Safety**: Uses restricted subprocess calls to prevent side effects during auditing.
*   **Output**: Generates an `EnvironmentAudit` object used to gate installation strategies.

### 2. The Execution Engine (`install.py`)
The "Workhorse" of the suite. It orchestrates the transition from raw code to a managed service.

*   **Structural Audit**: Scans the project root for markers (`pyproject.toml`, `package.json`, `requirements.txt`).
*   **Strategy Resolution**: Determines if the project should be a Managed Venv, a Lite Wrapper, or a Docker service.
*   **Dependency Management**: Handles `pip install` and `npm install` with configurable timeouts and atomic failure handling.

### 3. The Sync & Injection Layer (`mcp_injector.py`)
The "Surgeon" that bridges the gap between the installer and the user's IDE.

*   **Bracket Hell Prevention**: Specialized JSON parser that handles comma placement and list management for IDE config files.
*   **Atomic Transactions**: Always creates a `.backup` before writing. Uses temporary files and `os.replace` to prevent corruption.
*   **Startup Detection & Prompting**: Can auto-detect common MCP-capable IDE clients at startup and prompt injection.
*   **Suite Component Injection**: When full Nexus binaries are detected, injection is component-aware and prompted per created component.

### 4. The Bridge Generator (`bridge.py`)
Converts legacy scripts into AI-accessible MCP tools.

*   **Pattern Matching**: Scans for `if __name__ == "__main__":` and typical function signatures.
*   **Wrapper Logic**: Generates a FastAPI-based (standard) or stdio-based (lite) MCP server that imports and executes the original functions.

---

## 🔐 Universal Safety Protocol (USP)

The USP is active across all Reliability Tiers (Lite, Standard, Permanent).

### Phase 1: Pre-flight
Before a single byte is written:
1.  **Write Test**: Verifies write permissions in the installation root.
2.  **Storage Audit**: Verifies there is at least 100MB of free space (enough for a standard venv).
3.  **Conflict Check**: Detects if an existing installation (manifest) exists and requires cleanup.

### Phase 2: Atomic Tracking
Every action taken is registered in a global `INSTALLED_ARTIFACTS` list.

### Phase 3: Commit or Rollback
*   **On Success**: A `manifest.json` is locked to disk.
*   **On Failure**: The `rollback()` method executes, iterating backward through the artifact list and surgically removing every folder and file created during the session.

---

## 📂 Data Structures & Manifests

### manifest.json Example
Located in `<project_root>/.librarian/manifest.json`.

```json
{
  "install_date": "2026-02-10 14:30:00",
  "install_artifacts": [
    "/Users/user/.mcp-tools/mcp-link-library",
    "/Users/user/Dev/project/.venv"
  ],
  "install_mode": "permanent",
  "remote_url": "https://github.com/...",
  "version": "0.5.0-hardened"
}
```

---

## ⚡ Phase 9: Permissions & Resolution

### Intelligent Entry-Point Resolution
When multiple candidates exist (e.g., `run.py` and `run.sh`), the system applies the following recommendation logic:

1.  **Preference**: `.sh` is always recommended over `.py` as it typically handles its own environment activation.
2.  **User Choice**: If ambiguous, the user is prompted to select the primary entry point via a numbered menu.
3.  **Hardening**: The selected file is run through `chmod +x` immediately.

### Auto-Chmod Logic
```python
def ensure_executable(path: Path):
    if not path.exists() or not path.is_file(): return
    # Apply execute bit (0o111) while preserving other bits
    path.chmod(path.stat().st_mode | 0o111)
```

---

## 🌐 Mutual Discovery (The Bootstrap Loop)

Each tool in the Nexus implements `bootstrap.py` with a recursive discovery loop:

1.  **Level 0**: Is the sibling repo already in the parent folder?
2.  **Level 1**: Is the tool already installed in `~/.mcp-tools`?
3.  **Level 2**: Fetch from GitHub.

This ensures that clicking "Install" on any one tool can safely and reliably bring the entire Workforce Nexus to life.

## 🧩 GUI Control Surface Architecture

The GUI scaffold (`repo-mcp-packager/gui/`) acts as an orchestration layer over CLI commands:

1. `widgets.json` defines the command model and tier availability (`lite`, `standard`, `permanent`).
2. `server.py` exposes allowlisted widget execution by `widget_id` and returns command behavior (stdout/stderr/exit code).
3. `app.js` renders visual unchecked widgets when a command is outside the selected tier.

---

## 📝 Metadata
*   **Status**: Production / Hardened (Phase 9)
*   **Developer**: l00p3rl00p
*   **Reference**: [USER_OUTCOMES.md](./USER_OUTCOMES.md) | [ENVIRONMENT.md](./ENVIRONMENT.md)
