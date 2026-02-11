# Environment Specification - Git Repo MCP Converter & Installer

**Unified Environment Requirements & Audit Logic.**

This document provides a low-density technical manual for the host environment requirements, dependency resolution logic, and OS-specific configurations used by the Workforce Nexus Activator.

---

## 🔍 Core Dependency Rules

### 1. Python Runtimes
*   **The Orchestrator (`install.py`)**: Requires **Python 3.9+**.
*   **The Application Engine**: The core workforce tools are optimized for **Python 3.11+**.
*   **Isolation Policy**: The installer will always prioritize the creation of a local `.venv` within the project root to prevent global package conflicts.

### 2. Node.js & NPM
*   **Requirement**: Node.js v18+ and NPM v9+ are required only if the `gui/` directory is present.
*   **Isolation Policy**: Use `--npm-policy local` to ensure binaries are installed in a project-private context.

### 3. Docker Ecosystem
*   **Requirement**: A running Docker Desktop or Engine daemon is required for sandbox operations.
*   **Validation**: The installer executes `docker info` to verify daemon status. If inaccessible, the `--docker-policy` determines whether to skip or fail.

---

## 🛠 OS-Specific Path Matrix

The Workforce Nexus centralizes all artifacts in a predictable location based on the host OS.

| Platform | Nexus Home Root | Config Path |
| :--- | :--- | :--- |
| **macOS** | `~/.mcp-tools` | `~/Library/Application Support/Cloud/claude_desktop_config.json` |
| **Linux** | `~/.mcp-tools` | `~/.config/Claude/claude_desktop_config.json` |
| **Windows** | `%USERPROFILE%\.mcp-tools` | `%APPDATA%\Claude\claude_desktop_config.json` |

Additional common MCP client paths used by injector discovery include:
* `codex`: `~/Library/Application Support/Codex/mcp_servers.json` (plus OS-specific fallbacks)
* `aistudio`: `~/.config/aistudio/mcp_servers.json` (plus OS-specific fallbacks)
* `google-antigravity`: alias of AI Studio path set

---

## 🛠 Environment Audit Logic: The Pre-flight Probe

The `audit.py` module performs a multi-stage probe to build a system capabilities map.

### Stage 1: Shell Detection
The probe identifies the active shell via the `SHELL` environment variable.
*   **Targets**: `.zshrc` (macOS default), `.bashrc`, `.bash_profile`.
*   **Action**: Captures the path to the primary RC file for future PATH modifications.

### Stage 2: Binary Path Discovery
Uses `shutil.which` to find system binaries for:
*   `python3`
*   `npm`
*   `node`
*   `docker`
*   `git`

### Stage 3: Feature Inventory
Scans the current project root for identifying markers:
1.  **`pyproject.toml`**: Triggers full Python packaging logic.
2.  **`requirements.txt`**: Triggers legacy pip dependency installation.
3.  **`package.json`**: Triggers NPM installation.
4.  **`Dockerfile`**: Enables containerization features.

---

## ⚙️ Configuration Policies

### PATH Management (Surgical Injection)
The installer adds the project's bin directory to the host PATH using unique markers to ensure zero-risk uninstallation.

**Example Injection Block:**
```bash
# Shesha Block START
export PATH="/Users/user/project/.venv/bin:$PATH"
# Shesha Block END
```
*The uninstall script specifically targets everything between these markers.*

### IDE Injection Policy (Startup Detect)
*   The injector supports startup client discovery (`--startup-detect`) and prompts before mutation.
*   `claude` is always included in the common prompt set.
*   If full Nexus-created binaries exist (`~/.mcp-tools/bin`), the injector prompts for each created component instead of blind bulk injection.

### Permissions Hardening (Phase 9)
The environment must support `chmod` (POSIX) or equivalent ACL modifications.
*   **Logic**: During the installation phase, the `ensure_executable` method iterates through all entry points and shell scripts, setting the `0o111` (execute) bits.
*   **Enforcement**: This applies to all internal Nexus tools and discovered user repository scripts.

---

## 🛡 Network & Proxy Requirements
*   **Discovery**: Requires outbound access to `github.com` for bootstrapping sibling repos.
*   **Installation**: Requires access to `pypi.org` and `registry.npmjs.org`.
*   **Air-gap Mode**: If dependencies are pre-cached, the `--lite` mode can be used without active network connections.

---

## 📝 Metadata
*   **Status**: Production / Hardened (Phase 9)
*   **Developer**: l00p3rl00p
*   **Reference**: [ARCHITECTURE.md](./ARCHITECTURE.md) | [USER_OUTCOMES.md](./USER_OUTCOMES.md)
