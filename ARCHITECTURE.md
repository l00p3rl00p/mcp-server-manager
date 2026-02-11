# Architecture - Local MCP-Server Discovery + Inventory

## 📋 Table of Contents
1. [Core Design Principles](#-core-design-principles)
2. [Module Overview](#-module-overview)
3. [The MCP Gate Logic](#-the-mcp-gate-logic)
4. [GUI & CLI Communication (Contracts)](#-gui--cli-communication-contracts)

---

## 🔍 Nexus Application Context
The **Observer** is a core component of the **Workforce Nexus**. It provides the observability layer for the converged suite. For the full architectural roadmap, see the [Master Nexus Guide](../repo-mcp-packager/NEXUS_GUIDE.md).

## 🏗️ Core Design Principles
**Scan wide, accept strict.**

The system is designed to crawl large Directory trees efficiently while maintaining a high bar for what is considered an "MCP Server".

* **Wide Scan**: Finds candidates using cheap trigger files (.env, Dockerfile, etc.).
* **Strict Gate**: Decides if a candidate is Confirmed, Review-worthy, or Rejected.
* **Inventory Single Source of Truth**: The `inventory.yaml` is the authoritative list.

---

## 📂 Module Overview

* **`scan.py`**: Crawls scan roots, excludes noisy directories, and emits `Candidate` objects with evidence and scoring.
* **`gate.py`**: Applies the hard acceptance gate based on SDK imports, manifests, and Docker labels.
* **`inventory.py`**: Manages the lifecycle of `~/.mcpinv/inventory.yaml`.
* **`runtime.py`**: Observes running signals (Docker ps, OS processes) for heartbeat visibility.
* **`cli.py`**: The entry point for all operator commands (`scan`, `add`, `list`, `running`, `config`).

---

## ⚙️ The MCP Gate Logic

### Strong MCP Signals (Auto-Accept)
Any one of these triggers an automatic addition to the inventory:
* `mcp.server.json` or `mcp.json` manifest present.
* `package.json` depends on `@modelcontextprotocol/*`.
* Source code references `modelcontextprotocol` SDKs.
* Docker labels like `io.mcp.*` (future).

### Medium Signals (Flag for Review)
Sent to the GUI "Review" bucket:
* README explicitly mentions MCP.
* Docker Compose service name suggests MCP.
* `.env` contains specific LLM/Agentic keys.

### Weak Signals (Auto-Reject)
* `.env` file present without any other context.
* Common infrastructure services (Postgres, Redis, etc.) without MCP markers.

---

## 🔌 GUI & CLI Communication (Contracts)

To ensure the GUI is "thin" and the CLI is the source of truth, communication follows these health "lenses".

### 1. Application Health
* **GUI Shows**: Current state, last successful run, mode, project, and errors.
* **CLI Emits**: Status snapshots with severity levels, timestamps, and run identity (version, OS, timezone).

### 2. Command Execution Health
* **GUI Shows**: Timeline of commands, arguments, outcomes, and stderr summaries.
* **CLI Emits**: Record entries containing `command_id`, `exit_code`, `error_class`, and `human_hint`.

### 3. I/O & Artifact Observability
* **GUI Shows**: Inputs/outputs captured as artifacts (files, payload sizes, destinations).
* **CLI Emits**: Metadata for artifacts including `direction`, `ownership` (command linkage), and `retention_policy`.

### 4. Unified Data Strategy
All communication happens via a unified "App Data" directory:
* macOS: `~/Library/Application Support/mcp-manager/`
* Linux: `~/.local/share/mcp-manager/`
* Windows: `%AppData%/mcp-manager/`

**Storage Structure**:
* `/logs/`: Rotating human and machine-readable (JSONL) logs.
* `/state/`: Status snapshots and session registry.
* `/artifacts/`: Outputs, exports, and cached previews.
* `/config/`: Per-user and per-project configuration.

---

## 👤 Maintainers
Developed by the Git-Packager team.
