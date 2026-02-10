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
