# User Outcomes - Local MCP-Server Discovery + Inventory

This document defines the goals and success criteria for the `mcpinv` tool.

---

## ⚡ Quick Summary
* **Primary Goal**: Maintain a curated inventory of all MCP servers on a machine.
* **Secondary Goal**: Provide real-time visibility into the running state of discovered servers.

---

## 📋 Table of Contents
1. [Core Outcomes](#-core-outcomes)
2. [User Scenarios](#-user-scenarios)
3. [Success Metrics](#-success-metrics)

---

## 🔍 Core Outcomes

As a user, I want:

### 1. Curated Inventory
* **Single Source of Truth**: I want an authoritative list of all my MCP servers, regardless of where they are installed.
* **High-Precision Discovery**: I want to scan my machine and find servers without being flooded by random folders that happen to have a `.env` file.
* **Explainability**: I want to see *the evidence* (e.g., specific dependencies or markers) that led the system to identify a folder as an MCP server.

### 2. Operational Visibility
* **Heartbeat Monitoring**: I want to know at a glance which MCP servers are currently running (via Docker or OS processes).
* **Health Tracking**: I want to see if a server in my inventory is healthy, broken, or missing.

### 3. Operator Control
* **Manual Overrides**: If the automated scan misses something, I want to be able to add it manually and have it marked as a `manual` entry.
* **Flexible Configuration**: I want to define which parts of my machine are scanned and how deep the scan goes.

### 4. Operational Discipline
* **Simple Lifecycle**: Starting, stopping, and restarting the dashboard must be intuitive and zero-side-effect.
* **Non-Blocking Execution**: Stopping the GUI should not terminate background heartbeat monitors if they are running as system services (Industrial mode).

### 5. Universal Observability
* **Visual Status**: The user can see the health and connection status of all Nexus components (Observer, Librarian, Injector, Activator) in a single dashboard.
* **Graceful Degradation**: The system functions even if components are missing, clearly indicating what is available vs. what needs installation.

### 5. Resilient Lifecycle
* **Atomic Rollback**: If an installation fails at any step, the system automatically reverts to a clean state, leaving no partial artifacts.
* **Safe Upgrades**: The installer respects existing configurations and only applies necessary updates, preventing "config drift" or data loss.

---

## 🚀 Roadmap to 100% Compliance

To fully align with these outcomes, the following enhancements are planned:

*   **Observability**: The GUI must eventually show *live* metrics (CPU/Memory) for the industrial tier, not just static "Presence".
*   **Usability**: The "Librarian CRUD" tools need a UI frontend. Currently, they are "Headless Tools" only.
*   **Resilience**: While `start_gui.sh` exists, the Python entry point (`python -m mcp_inventory.cli`) is more cross-platform compatible and should be the primary recommendation in all docs.

---

## 💻 User Scenarios

### Scenario 1: Onboarding a New Machine
* **Action**: User clones several repos and wants to know which ones are MCP-ready.
* **Outcome**: User runs `mcpinv scan`. The tool correctly identifies 3 confirmed servers and flags 2 others for review. The user confirms the 2 candidates, and is now ready to attach them to their IDE.

### Scenario 2: Debugging "Missing" Tools
* **Action**: Claude Desktop says it can't find a tool, but the user is sure it's running.
* **Outcome**: User runs `mcpinv running`. They see that the relevant Docker container is stopped. They restart the container, and `mcpinv` shows it as active again.

---

## 📈 Success Metrics

* **S/N Ratio**: High signal-to-noise ratio in scans (minimum false positives).
* **Inventory Reliability**: The `inventory.yaml` remains consistent and survives machine restarts.
* **Integration Speed**: Reduced time to configure a new IDE by pulling from the curated inventory.
