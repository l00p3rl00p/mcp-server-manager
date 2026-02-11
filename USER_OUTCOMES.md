# User Outcomes - Git Repo MCP Converter & Installer

This document defines what success looks like for the "Clean Room Installer" and ensures the technical path aligns with the mission of friction-less replication.

---

## ⚡ Quick Summary
* **Mission Statement**: To provide a "Just Works" installation experience that creates zero-leak, isolated environments allowing agents to replicate the packager stack without friction.

---

## 📋 Table of Contents
1. [Successful Outcomes](#-successful-outcomes)
2. [High-Fidelity Signals](#-high-fidelity-signals)
3. [Design Guardrails](#-design-guardrails)

---

## 🔍 Successful Outcomes

As a user, I want:

### 1. Portability & Isolation
* **Standalone Execution**: The `/serverinstaller` directory can be copied to any repo and execute correctly without external dependencies.
* **Environment Integrity**: The installer bootstraps from the host's existing tools and create isolated environments (e.g., `.venv`) to prevent leaks.
* **Zero-Touch Replication**: A real agent can execute `install.py --headless` and achieve a functional stack without human intervention.

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
* **Safe Upgrades**: The `mcp-activator --sync` command provides a unified update loop, ensuring all central tools stay synchronized with the latest security and feature patches.
* **Context-Locked Execution**: Entry points carry their own venv and PYTHONPATH, ensuring they work regardless of the user's active terminal environment.

---

## 🚀 Roadmap to 100% Compliance

To fully align with these outcomes, the following enhancements are planned:

*   **GUI Reliability (Target 95%+)**: Transition GUI from a blocking process to a background service with PID management.
*   **Librarian Synergy**: Implement a dynamic watcher so the Librarian indexes changes in real-time, not just on installation.
*   **Operational Awareness**: Add "version health" checks to the GUI dashboard to visually signal when a `--sync` is required.

### 2026-02-11 Alignment Update
* **Injector Startup Detect**: Added startup detection/prompt flow for common IDE clients, including `claude`, `codex`, and `aistudio` (plus `google-antigravity` alias).
* **Package-Created Component Injection Policy**: If full Nexus components are detected (`~/.mcp-tools/bin`), the injector now prompts injection per component (`nexus-activator`, `nexus-observer`, `nexus-surgeon`, `nexus-librarian`).
* **Tier-Aware GUI Control Surface**: GUI command widgets now map to command catalog behavior with visual unchecked state for unsupported tier actions.
* **Central-Only Uninstall Policy**: Full wipes only touch approved central locations (e.g. `~/.mcp-tools`, `~/.mcpinv`, and the Nexus PATH block). No disk scans or directory-tree climbing during uninstall.
* **Uninstall Safety + Diagnostics**: Uninstall now prints an explicit deletion plan and requires confirmation (unless `--yes`). Added `--verbose` and `--devlog` (JSONL) with 90-day retention for diagnostics.
* **Bootstrap Safety Policy**: Workspace detection avoids filesystem crawling (checks only `cwd` + script-sibling workspace). If a workspace `.env` is present, the installer warns about potential conflicts with the central install.

---

## 🚥 High-Fidelity Signals

* **Success**: `.librarian/manifest.json` correctly lists all artifacts, and `verify.py` reports `[VERIFIED]` for all items.
* **Failure**: Encountering an interactive prompt in `--headless` mode.
* **Success**: Running `uninstall.py` removes the `# Shesha Block` from `.zshrc` without deleting other aliases.

---

## 🛡 Design Guardrails

* **No Sudo**: Reject any feature that requires global `sudo` permissions if a local `.venv` alternative exists.
* **No Unmanaged Overwrites**: Reject any "auto-update" feature that replaces local configuration without a manifest-backed snapshot.
* **Respect Local Code**: Treatment of the current repository state as the "source of truth." Never overwrite local changes with upstream templates.
