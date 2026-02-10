# Contributing Guide

Welcome! We appreciate your interest in improving the Local MCP-Server Discovery + Inventory tool.

---

## 📋 Table of Contents

1. [Our Philosophy](#-our-philosophy)
2. [The Golden Rule](#-the-golden-rule)
3. [Ways to Contribute](#-ways-to-contribute)
4. [Getting Started](#-getting-started)
5. [Review Process](#-review-process)

---

## 🔍 Our Philosophy

We believe in radical improvement. We will accept **any edit that makes the project better**. Whether it's a bug fix, a new feature, a documentation update, or a performance improvement—if it adds value, we want it.

---

## 🔱 The Golden Rule: Maintain Package Linkage

This repository is part of a 3-repository suite that forms the **Git-Packager** workspace:

1. **mcp-injector**
2. **mcp-server-manager** (this tool)
3. **repo-mcp-packager**

> **CRITICAL**: You must ensure that your changes **do not break the link** between these three repositories. They are tightly integrated and depend on each other to function correctly as a whole.

* **Do** improve individual components and logic.
* **Do not** break the interoperability or the bootstrap/integration patterns between them.

If your change affects the integration, please ensure you have tested it across all three repositories.

---

## 🌟 Ways to Contribute

* **Report Bugs**: Open an issue if you find something broken (e.g., poor discovery on certain OS).
* **Suggest Features**: We're looking for better "Strong Signals" and Gating logic.
* **Submit PRs**: Direct improvements to scanning accuracy or CLI features.
* **Documentation**: Help us refine the Architecture and User Outcomes.

---

## ⚡ Getting Started

### Development Environment
1. Clone the repository.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install in editable mode:
   ```bash
   pip install -e .
   ```
4. Run `mcpinv --help` to verify.

### Project Structure
* `scan.py`: The core crawler logic.
* `gate.py`: The validation and gating logic.
* `inventory.py`: YAML persistence layer.
* `cli.py`: Command-line interface.

---

## 📝 Review Process

1. **Check for noise**: Does your change add too many false positives to scans?
2. **Validate connectivity**: Does this break the `bootstrap` link with the other tools?
3. **OS Compatibility**: Does the change work on macOS, Linux, and Windows (where possible)?

Once verified, we aim for a quick review and merge.
