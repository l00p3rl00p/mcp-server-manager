# Workforce Nexus: Unified Guide & Command Reference

This is the master guide for the **Workforce Nexus** suite. It covers all commands, directory contexts, and management procedures for the industrial-grade MCP environment.

---

## 🛠️ Master Command Reference

| Tool | Global Command | Responsibility | Primary Directory Context |
| :--- | :--- | :--- | :--- |
| **Activator** | `mcp-activator` | Installation, Workspace Sync, Bootstrapping | `repo-mcp-packager/` |
| **Observer** | `mcp-observer` | GUI Dashboard, Health Monitoring, Inventory | Anywhere (Global) |
| **Surgeon** | `mcp-surgeon` | IDE Config Injection (Claude, Cursor, etc.) | Anywhere (Global) |
| **Librarian** | `mcp-librarian` | Knowledge Indexing, SQLite URL Storage | Anywhere (Global) |

---

## 🚀 Getting Started

### 1. Installation (The "Industrial" Path)
To set up the full suite with global commands and a managed environment:

1.  **Navigate to the Activator root**:
    ```bash
    cd repo-mcp-packager
    ```
2.  **Run the Bootstrap**:
    ```bash
    python3 bootstrap.py --permanent
    ```
3.  **Refresh your Shell**:
    ```bash
    source ~/.zshrc  # or ~/.bashrc
    ```

### 2. Standalone Packaging (The "Portable" Path)
If you want to package a *single* repository without installing the full Nexus:

1.  **Copy the `serverinstaller/` folder** into your target repository.
2.  **Navigate to the target repository root**.
3.  **Run the Installer**:
    ```bash
    python3 serverinstaller/install.py
    ```

---

## 🖥️ Management (GUI & Services)

### Launching the Dashboard
The **Observer GUI** provides a visual overview of all your AI tools.

```bash
mcp-observer gui
```
*   **URL**: [http://localhost:8501](http://localhost:8501)
*   **Context**: Can be run from ANY directory once installed.

### Stopping the GUI
To terminate the dashboard server:
1.  Go to the terminal window where the command is running.
2.  Press **`Ctrl + C`**.

### Restarting the GUI
Simply run the launch command again. The Observer will automatically re-scan the inventory and active heartbeats.

---

## 🌍 Directory & PATH Rules

### Directory Context
*   **`mcp-activator`**: Must be run from the `repo-mcp-packager` directory if syncing from source, or any directory if running a global command.
*   **`mcp-observer` / `mcp-surgeon` / `mcp-librarian`**: These are shell-aware and can be run from **anywhere** in your terminal.

### PATH Configuration
The Nexus requires `~/.mcp-tools/bin` to be in your system PATH. If the installer failed to add it automatically, add the following to your `~/.zshrc` or `~/.bashrc`:

```bash
# Workforce Nexus Path
export PATH="$HOME/.mcp-tools/bin:$PATH"
```

---

## 📋 Standard Multi-Tool Procedures

### Adding a new MCP Server to Claude
```bash
mcp-surgeon add claude my-new-server "python3 /path/to/server.py"
```

### Indexing a directory into the Librarian
```bash
mcp-librarian --index /path/to/my-docs --category "Technical"
```

### Checking Suite Synergy
```bash
mcp-observer check-synergy
```

---

## ⚖️ Troubleshooting

*   **"Command not found"**: Run `source ~/.zshrc` or verify the PATH export exists in your shell config.
*   **"Cannot find workspace"**: Ensure you are running `bootstrap.py` from within the `repo-mcp-packager` folder, and that sibling repositories (mcp-injector, etc.) are in the parent directory.
*   **GUI Failure**: Ensure your Python version is 3.11+ and that `streamlit` is installed (Industrial mode handles this automatically).
