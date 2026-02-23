import os
import json
import sqlite3
import subprocess
import sys
import shlex
import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from collections import deque
import time
import re
import shutil
import threading
__version__ = "3.3.4"

METRIC_HISTORY = deque(maxlen=60)
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse
import yaml

from runtime_manager import ManagedPython, choose_managed_python_at_least, list_managed_pythons

# Determine the directory where this script lives
BASE_DIR = Path(__file__).parent.resolve()

app = Flask(__name__, static_folder=str(BASE_DIR / "gui" / "dist"), static_url_path="")
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://localhost:5001", "http://127.0.0.1:5001"])

@app.route("/")
def serve_index():
    """Serve the built React frontend's index.html."""
    return send_from_directory(app.static_folder, "index.html")

@app.route("/<path:path>")
def serve_static(path):
    """Serve assets and other static files from gui/dist."""
    # Check if the requested path exists in static_folder
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    # Default to index.html for React Router compatibility
    return send_from_directory(app.static_folder, "index.html")

# OS navigation helpers (native dialogs). These are best-effort and will not work in headless/CI.
@app.route('/os/pick_file', methods=['POST'])
def os_pick_file():
    if os.environ.get("NEXUS_HEADLESS") == "1":
        return jsonify({"success": False, "error": "OS file picker not available in headless mode."}), 501
    try:
        # macOS: prefer AppleScript chooser (more reliable than tkinter in tray/threaded contexts)
        if sys.platform == "darwin":
            script = 'POSIX path of (choose file with prompt "Pick a file to index")'
            r = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if r.returncode != 0:
                err = (r.stderr or "").strip()
                # User canceled: osascript typically returns non-zero with a user-canceled message.
                if "User canceled" in err or "User cancelled" in err:
                    return jsonify({"success": False, "error": "Canceled"}), 400
                return jsonify({"success": False, "error": err or "Picker failed"}), 500
            path = (r.stdout or "").strip()
            if not path:
                return jsonify({"success": False, "error": "Canceled"}), 400
            return jsonify({"success": True, "path": path})

        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename()
        try:
            root.destroy()
        except Exception:
            pass
        if not path:
            return jsonify({"success": False, "error": "Canceled"}), 400
        return jsonify({"success": True, "path": path})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/os/pick_folder', methods=['POST'])
def os_pick_folder():
    if os.environ.get("NEXUS_HEADLESS") == "1":
        return jsonify({"success": False, "error": "OS folder picker not available in headless mode."}), 501
    # UAT/CI escape hatch: never pop a native dialog. Return a deterministic path.
    # This keeps the call-chain testable without human interaction.
    uat_path = os.environ.get("NEXUS_UAT_PICK_FOLDER")
    if uat_path:
        return jsonify({"success": True, "path": uat_path})
    try:
        # macOS: prefer AppleScript chooser (more reliable than tkinter in tray/threaded contexts)
        if sys.platform == "darwin":
            script = 'POSIX path of (choose folder with prompt "Pick a folder to index")'
            r = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if r.returncode != 0:
                err = (r.stderr or "").strip()
                if "User canceled" in err or "User cancelled" in err:
                    return jsonify({"success": False, "error": "Canceled"}), 400
                return jsonify({"success": False, "error": err or "Picker failed"}), 500
            path = (r.stdout or "").strip()
            if not path:
                return jsonify({"success": False, "error": "Canceled"}), 400
            return jsonify({"success": True, "path": path})

        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        path = filedialog.askdirectory()
        try:
            root.destroy()
        except Exception:
            pass
        if not path:
            return jsonify({"success": False, "error": "Canceled"}), 400
        return jsonify({"success": True, "path": path})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Official Logging Integration
try:
    sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-link-library"))
    from nexus_session_logger import NexusSessionLogger
    try:
        session_logger = NexusSessionLogger()
    except Exception:
        # In restricted/sandboxed environments we may not be allowed to write to ~/.mcpinv.
        session_logger = None
except:
    session_logger = None

if session_logger is not None:
    _orig_log = getattr(session_logger, "log", None)
    if callable(_orig_log):
        def _safe_log(*args, **kwargs):
            try:
                return _orig_log(*args, **kwargs)
            except Exception:
                return None
        session_logger.log = _safe_log

# Base Discovery (portable + test-friendly)
# Allow overriding state directories so tests/CI never write to the real home folder.
NEXUS_HOME = Path(os.environ.get("NEXUS_HOME") or (Path.home() / ".mcp-tools")).expanduser()
MCPINV_HOME = Path(os.environ.get("MCPINV_HOME") or (Path.home() / ".mcpinv")).expanduser()
PROJECTS_FILE = MCPINV_HOME / "projects.json"
ACTIVE_CONTEXT_FILE = MCPINV_HOME / "active_context.json"

class ProjectManager:
    def __init__(self):
        self.active_project = None
        self.app_data_dir = NEXUS_HOME / "mcp-server-manager"
        self.inventory_path = self.app_data_dir / "inventory.yaml"
        self.log_path = MCPINV_HOME / "session.jsonl"
        self.bin_dir = NEXUS_HOME / "bin"
        self.watcher_proc = None # Track the PID
        self.last_server_cmd: Dict[str, list[str]] = {}  # Best-effort: track actual started argv per server id
        self.last_server_exit: Dict[str, Dict[str, Any]] = {}  # Best-effort: last exit metadata per server id
        self.last_server_start: Dict[str, float] = {}  # Best-effort: last start timestamp per server id
        self.acknowledged_errors = 0.0 # Timestamp of last error clear
        self.last_forge_result = None # Persist the last successful forge
        self.load_active_context()
        self.ensure_core_services()

    def core_components(self) -> Dict[str, str]:
        """
        Suite-level components that should always be visible on the dashboard
        (even if not present in inventory.yaml as "servers").
        """
        def bin_status(name: str) -> str:
            return "online" if (self.bin_dir / name).exists() else "missing"

        return {
            "activator": bin_status("mcp-activator"),
            "observer": bin_status("mcp-observer"),
            "surgeon": bin_status("mcp-surgeon"),
            "librarian_bin": bin_status("mcp-librarian"),
        }

    def ensure_core_services(self):
        """Auto-starts Type-0 Core Dependencies (Librarian) if not running."""
        try:
            import psutil
            # Check for Librarian
            librarian_running = False
            for p in psutil.process_iter(['name', 'cmdline']):
                try:
                    cmd = ' '.join(p.info['cmdline'] or [])
                    if "nexus-librarian" in cmd or "mcp-librarian" in cmd:
                        librarian_running = True
                        break
                except Exception:
                    # Best-effort process inspection; permission/race failures are non-fatal.
                    continue
            
            if not librarian_running:
                librarian_bin = self.bin_dir / "mcp-librarian"
                if librarian_bin.exists():
                    if session_logger: 
                        session_logger.log("LIFECYCLE", "Auto-Starting Core Service: Librarian", suggestion="Core dependency missing.")
                    # Launch detached, inheriting environment to ensure PATH is correct
                    subprocess.Popen([str(librarian_bin), "--server"], start_new_session=True, env=os.environ.copy())
                else:
                    if session_logger:
                        session_logger.log("ERROR", "Core Service Missing: mcp-librarian binary not found.")
        except Exception as e:
            if session_logger: session_logger.log("ERROR", f"Core Service Auto-Start Failed: {e}")

    def load_active_context(self):
        """Restores the last active project and session state (like acknowledged errors)."""
        if ACTIVE_CONTEXT_FILE.exists():
            try:
                with open(ACTIVE_CONTEXT_FILE, 'r') as f:
                    ctx = json.load(f)
                    self.acknowledged_errors = ctx.get("acknowledged_errors", 0.0)
                    self.last_forge_result = ctx.get("last_forge_result")
                    self.set_project(ctx.get("path"), ctx.get("id"), reset_ack=False)
            except Exception as e:
                if session_logger:
                    session_logger.log("WARNING", f"Failed to load active context: {e}")
        if not self.active_project:
            self.set_project(str(self.app_data_dir), "nexus-default")

    def save_snapshot(self):
        """Captures a timestamped copy of the inventory.yaml for recovery."""
        if not self.inventory_path.exists(): return
        try:
            # Ensure snapshot directory exists
            snapshot_dir = self.app_data_dir / "snapshots"
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            
            # Create timestamped filename
            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            target_file = snapshot_dir / f"inventory_{stamp}.yaml"
            
            # Copy file
            import shutil
            shutil.copy2(self.inventory_path, target_file)

            # Prune old snapshots (keep last 10)
            snaps = sorted(snapshot_dir.glob("inventory_*.yaml"))
            while len(snaps) > 10:
                oldest = snaps.pop(0)
                try:
                    oldest.unlink()
                except Exception as e:
                    if session_logger:
                        session_logger.log("WARNING", f"Failed to prune snapshot {oldest.name}: {e}")
        except Exception as e:
            if session_logger: session_logger.log("ERROR", f"Snapshot capture failed: {str(e)}")

    def set_project(self, path: str, p_id: str, reset_ack: bool = True):
        """Standardizes paths for a specific project context and saves the active session."""
        path = Path(path)
        self.active_project = {"id": p_id, "path": str(path)}
        # Project-specific paths
        self.app_data_dir = path
        self.inventory_path = path / "inventory.yaml"
        
        # Reset acknowledged errors when switching projects so history is fresh
        if reset_ack:
            self.acknowledged_errors = 0.0
            
        self.save_context()

    def save_context(self):
        """Saves current project and session markers."""
        ACTIVE_CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ACTIVE_CONTEXT_FILE, 'w') as f:
            json.dump({
                **self.active_project,
                "acknowledged_errors": self.acknowledged_errors,
                "last_forge_result": self.last_forge_result
            }, f)

    def get_projects(self):
        if not PROJECTS_FILE.exists():
            projects = [{"id": "nexus-default", "name": "Nexus Commander (Default)", "path": str(NEXUS_HOME / "mcp-server-manager")}]
            with open(PROJECTS_FILE, 'w') as f: json.dump(projects, f)
        
        with open(PROJECTS_FILE, 'r') as f:
            return json.load(f)

    def get_inventory(self):
        if not self.inventory_path.exists(): return {"servers": []}
        try:
            with open(self.inventory_path, 'r') as f:
                return yaml.safe_load(f) or {"servers": []}
        except: return {"servers": []}

def _parse_pyproject_scripts(pyproject_path: Path) -> Dict[str, str]:
    """
    Best-effort extraction of [project.scripts] from a pyproject.toml.
    Avoids adding new runtime dependencies for TOML parsing.
    """
    try:
        lines = pyproject_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return {}

    scripts: Dict[str, str] = {}
    in_scripts = False
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            in_scripts = (line == "[project.scripts]")
            continue
        if not in_scripts:
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().strip('"').strip("'")
        value = value.strip().strip('"').strip("'")
        if key and value:
            scripts[key] = value
    return scripts

def _parse_pyproject_requires_python(pyproject_path: Path) -> Optional[str]:
    """
    Best-effort extraction of `requires-python` from [project] in pyproject.toml.
    Avoids adding runtime dependencies for TOML parsing.
    """
    try:
        lines = pyproject_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return None

    in_project = False
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            in_project = (line == "[project]")
            continue
        if not in_project:
            continue
        if line.startswith("requires-python"):
            if "=" not in line:
                continue
            _, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            return value or None
    return None

def _min_python_from_spec(spec: Optional[str]) -> Optional[Tuple[int, int]]:
    """
    Extract a minimum version tuple from a spec like ">=3.10" or ">=3.10,<4".
    Conservative: only understands >=X.Y.
    """
    if not spec:
        return None
    s = spec.strip()
    # find first occurrence of >=X.Y
    m = re.search(r">=\s*(\d+)\.(\d+)", s)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)))

def _python_version_tuple(python_exe: str, cwd: Optional[str], env: Dict[str, str]) -> Optional[Tuple[int, int, int]]:
    """
    Determine interpreter version for the specific python executable being used to launch a server.
    """
    try:
        res = subprocess.run(
            [python_exe, "-c", "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}')"],
            capture_output=True,
            text=True,
            timeout=3,
            cwd=cwd,
            env=env,
        )
        if res.returncode != 0:
            return None
        v = (res.stdout or "").strip()
        parts = v.split(".")
        if len(parts) < 2:
            return None
        major = int(parts[0])
        minor = int(parts[1])
        patch = int(parts[2]) if len(parts) > 2 else 0
        return (major, minor, patch)
    except Exception:
        return None

def _find_python_at_least(min_version: Tuple[int, int], cwd: Optional[str], env: Dict[str, str], exclude: Optional[str] = None) -> Optional[str]:
    """
    Best-effort discovery of a Python interpreter that satisfies min_version (major, minor).
    Returns an executable path or None.
    """
    candidates = [
        "python3.13",
        "python3.12",
        "python3.11",
        "python3.10",
        "python3",
        "python",
    ]
    for name in candidates:
        exe = shutil.which(name)
        if not exe:
            continue
        if exclude and os.path.abspath(exe) == os.path.abspath(exclude):
            continue
        ver = _python_version_tuple(exe, cwd, env)
        if not ver:
            continue
        if (ver[0], ver[1]) >= min_version:
            return exe
    return None

def _looks_like_python_lt_310_union_error(log_tail: str) -> bool:
    """
    Detect the common signature when Python<3.10 executes code using PEP604 unions (X | None).
    """
    t = (log_tail or "").lower()
    return "unsupported operand type(s) for |" in t and "nonetype" in t

def _ensure_server_venv(server_dir: Path, base_python: str, log_dir: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Best-effort: ensure a per-server venv exists and has deps installed (editable).
    Returns (venv_python, setup_log_path).
    """
    venv_dir = server_dir / ".venv"
    venv_py = venv_dir / "bin" / "python"
    setup_log = log_dir / f"{server_dir.name}_setup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    try:
        setup_log.parent.mkdir(parents=True, exist_ok=True)
        with open(setup_log, "w", encoding="utf-8") as f:
            f.write(f"--- SERVER_DIR: {server_dir} ---\n")
            f.write(f"--- BASE_PYTHON: {base_python} ---\n")
            f.write("\n")

            if not venv_py.exists():
                f.write(f"--- ACTION: create venv ({venv_dir}) ---\n")
                res = subprocess.run([base_python, "-m", "venv", str(venv_dir)], cwd=str(server_dir), stdout=f, stderr=subprocess.STDOUT, text=True, timeout=180)
                f.write(f"\n--- VENV_CREATE_RC: {res.returncode} ---\n")
                if res.returncode != 0:
                    return (None, str(setup_log))

            f.write("\n--- ACTION: pip install -e . ---\n")
            res2 = subprocess.run([str(venv_py), "-m", "pip", "install", "-e", "."], cwd=str(server_dir), stdout=f, stderr=subprocess.STDOUT, text=True, timeout=300)
            f.write(f"\n--- PIP_INSTALL_RC: {res2.returncode} ---\n")
            if res2.returncode != 0:
                return (str(venv_py), str(setup_log))

        return (str(venv_py), str(setup_log))
    except Exception:
        return (str(venv_py) if venv_py.exists() else None, str(setup_log))

def _normalize_user_path(raw: str) -> str:
    """
    Normalize a user-provided path string:
    - strips surrounding quotes
    - expands '~'
    - resolves to an absolute path
    """
    s = (raw or "").strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()
    return str(Path(s).expanduser().resolve())

def _is_url(s: str) -> bool:
    try:
        u = urlparse(s)
        return u.scheme in ("http", "https") and bool(u.netloc)
    except Exception:
        return False

def _resolve_server_run(target: Dict[str, Any]) -> Tuple[list[str], Optional[str], Dict[str, str], Optional[str], Optional[str]]:
    """
    Resolve how to run a server entry deterministically.
    Returns: (argv, cwd, env, resolution_note, requires_python)
    """
    run_cfg = (target.get("run") or {})
    cmd = run_cfg.get("start_cmd", "")
    if not cmd:
        return ([], None, {}, None)

    argv = shlex.split(cmd)
    cwd = target.get("path")
    env: Dict[str, str] = os.environ.copy()
    note: Optional[str] = None
    requires_python: Optional[str] = None

    cwd_path: Optional[Path] = None
    if cwd:
        try:
            cwd_path = Path(cwd)
        except Exception:
            cwd_path = None

    # If the project has a pyproject.toml, capture requires-python for runtime gating.
    if cwd_path and (cwd_path / "pyproject.toml").exists():
        try:
            requires_python = _parse_pyproject_requires_python(cwd_path / "pyproject.toml")
        except Exception:
            requires_python = None

    # Heuristic for forged Python repos that have a real MCP entrypoint in pyproject.toml.
    # If the inventory start_cmd is the generic forge stub `python3 mcp_server.py`, prefer the project MCP script.
    if (
        cwd_path
        and len(argv) >= 2
        and argv[0].endswith("python3")
        and Path(str(argv[1])).name == "mcp_server.py"
        and (cwd_path / "pyproject.toml").exists()
    ):
        pyproject = cwd_path / "pyproject.toml"
        scripts = _parse_pyproject_scripts(pyproject)
        mcp_script = scripts.get("notebooklm-mcp")
        if mcp_script:
            module = mcp_script.split(":", 1)[0]
            argv = [argv[0], "-m", module]
            src_dir = cwd_path / "src"
            if src_dir.exists():
                env["PYTHONPATH"] = str(src_dir) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
            note = f"Resolved MCP entrypoint from pyproject.toml: notebooklm-mcp -> -m {module}"

    return (argv, str(cwd_path) if cwd_path else None, env, note, requires_python)

def _forged_entrypoint_needs_repair(entrypoint: Path) -> bool:
    """
    Older forged servers emitted human banners to stdout (e.g. 'MCP Server Ready (Stdio)'),
    which breaks MCP clients that expect JSON on stdout.
    """
    try:
        if not entrypoint.exists() or not entrypoint.is_file():
            return False
        txt = entrypoint.read_text(encoding="utf-8", errors="ignore")
        # If the file doesn't even compile, it can't be safely executed as an MCP-stdio server.
        # This catches historical forge bugs where `"\n"` was written as a literal newline inside
        # a Python string, producing a SyntaxError at runtime.
        try:
            compile(txt, str(entrypoint), "exec")
        except SyntaxError:
            return True

        return ("MCP Server Ready" in txt) or ("Nexus-Forged MCP Server Ready" in txt) or ("print(\"MCP Server" in txt)
    except Exception:
        return False

def _repair_forged_entrypoint(entrypoint: Path, server_name: str) -> bool:
    """
    Rewrite the baseline forged entrypoint to a minimal MCP stdio JSON-RPC server.
    Returns True if repaired (or already compliant), False if repair failed.
    """
    try:
        if not entrypoint.parent.exists():
            return False
        if entrypoint.exists() and not _forged_entrypoint_needs_repair(entrypoint):
            return True

        # NOTE: This is intentionally not an f-string because the generated code itself must not
        # contain accidental outer-string interpolation (e.g., "{name}") which would raise here.
        content = """# Baseline MCP Server (Repaired)
\"\"\"
MCP Server: {server_name}
Repaired by Nexus Server Manager to be MCP-stdio compliant.
\"\"\"
from __future__ import annotations

import json
import sys
import time
from typing import Any, Dict, Optional


SERVER_NAME = {server_name_repr}
SERVER_VERSION = "0.0.1-forged"


def _ok(msg_id: Any, result: Any) -> Dict[str, Any]:
    return {{"jsonrpc": "2.0", "id": msg_id, "result": result}}


def _err(msg_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {{"jsonrpc": "2.0", "id": msg_id, "error": {{"code": code, "message": message}}}}


def handle_request(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = request.get("method")
    params = request.get("params") or {{}}
    msg_id = request.get("id")

    if msg_id is None and isinstance(method, str) and method.startswith("notifications/"):
        return None

    try:
        if method == "initialize":
            return _ok(
                msg_id,
                {{
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {{"name": SERVER_NAME, "version": SERVER_VERSION}},
                    "capabilities": {{"tools": {{"listChanged": False}}}},
                }},
            )
        if method in ("notifications/initialized",):
            return None
        if method == "tools/list":
            return _ok(
                msg_id,
                {{
                    "tools": [
                        {{
                            "name": "ping",
                            "description": "Liveness check (forged baseline).",
                            "inputSchema": {{"type": "object", "properties": {{}}, "additionalProperties": False}},
                        }}
                    ]
                }},
            )
        if method == "tools/call":
            name = (params.get("name") or "").strip()
            if name == "ping":
                return _ok(msg_id, {{"ok": True, "ts": time.time(), "server": SERVER_NAME}})
            return _err(msg_id, -32601, "Unknown tool: " + str(name))
        return _err(msg_id, -32601, "Unknown method: " + str(method))
    except Exception as e:
        return _err(msg_id, -32000, "Server error: " + str(e))


def main() -> None:
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            req = json.loads(line)
        except Exception:
            continue
        resp = handle_request(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
"""
        content = content.format(server_name=server_name, server_name_repr=repr(server_name))
        entrypoint.write_text(content, encoding="utf-8")
        return True
    except Exception:
        return False

pm = ProjectManager()

@app.route('/health', methods=['GET'])
def health():
    """Returns the basic health status and active project context."""
    return jsonify({"status": "ok", "project": pm.active_project})

@app.route('/logs', methods=['GET'])
def get_logs():
    """Retrieves the last 100 log entries from the session log file."""
    if not pm.log_path.exists(): return jsonify([])
    logs = []
    try:
        with open(pm.log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-100:]
            for line in lines:
                try: logs.append(json.loads(line))
                except Exception as e:
                    if session_logger: session_logger.log("ERROR", f"Log line corruption: {str(e)}")
                    continue
        return jsonify(logs)
    except Exception as e: return jsonify({"error": str(e)}), 500



def _log_policy() -> dict:
    # Industry-default local retention: 30 days, 500MB cap.
    try:
        days = int(os.environ.get('NEXUS_LOG_RETENTION_DAYS', '30'))
    except Exception:
        days = 30
    try:
        max_mb = int(os.environ.get('NEXUS_LOG_MAX_MB', '500'))
    except Exception:
        max_mb = 500
    return {"retention_days": max(1, days), "max_mb": max(50, max_mb)}


def _log_dir_stats(log_dir: Path) -> dict:
    total = 0
    files = []
    try:
        for p in log_dir.glob('*.log'):
            try:
                st = p.stat()
                total += int(st.st_size)
                files.append({"path": str(p), "mtime": float(st.st_mtime), "size": int(st.st_size)})
            except Exception:
                continue
    except Exception:
        pass
    return {"dir": str(log_dir), "bytes": total, "files": len(files), "entries": files}


def _prune_log_dir(log_dir: Path) -> dict:
    policy = _log_policy()
    stats = _log_dir_stats(log_dir)
    entries = list(stats.get('entries') or [])

    now = time.time()
    max_age_s = float(policy['retention_days']) * 86400.0

    removed = []
    kept = []

    # 1) Age-based deletion
    for e in sorted(entries, key=lambda x: x.get('mtime', 0.0)):
        try:
            if (now - float(e.get('mtime', now))) > max_age_s:
                Path(e['path']).unlink(missing_ok=True)
                removed.append({"path": e['path'], "reason": "age"})
            else:
                kept.append(e)
        except Exception:
            kept.append(e)

    # 2) Size-cap deletion (oldest first)
    cap_bytes = int(policy['max_mb']) * 1024 * 1024
    kept_sorted = sorted(kept, key=lambda x: x.get('mtime', 0.0))
    cur = sum(int(x.get('size', 0)) for x in kept_sorted)
    for e in list(kept_sorted):
        if cur <= cap_bytes:
            break
        try:
            Path(e['path']).unlink(missing_ok=True)
            removed.append({"path": e['path'], "reason": "size_cap"})
            cur -= int(e.get('size', 0))
        except Exception:
            continue

    final = _log_dir_stats(log_dir)
    final.pop('entries', None)
    return {"policy": policy, "removed": removed, "final": final}

@app.route('/status', methods=['GET'])
def get_status():
    """
    Compiles a comprehensive system status report including:
    - Process liveness check (Librarian, Bridge, Servers)
    - Resource usage metrics (CPU, RAM, PID)
    - MCP Server inventory status
    """
    import yaml

    servers = []
    procs = []
    psutil = None
    # Capture PID, Name, Cmdline (best-effort; may be blocked in sandboxed environments)
    try:
        import psutil as _psutil
        psutil = _psutil
        procs = list(psutil.process_iter(['name', 'cmdline', 'pid']))
    except Exception as e:
        # Degrade gracefully: still return inventory + core component presence.
        if session_logger:
            session_logger.log("WARNING", f"Status degraded: process inspection unavailable ({e})")
    
    def find_process(patterns):
        for p in procs:
            try:
                cmdline = ' '.join(p.info['cmdline'] or [])
                if any(pat in cmdline for pat in patterns): return p
            except Exception as e:
                # Silently ignore 404/connection errors for pings to avoid log bloat, but log system exceptions
                pass
        return None

    librarian_proc = find_process(["mcp.py", "nexus-librarian"]) if psutil else None
    librarian_online = librarian_proc is not None
    core_keywords = ["mcp-injector", "mcp-server-manager", "repo-mcp-packager", "nexus-librarian"]
    core_components = pm.core_components()
    core_components["librarian"] = "online" if librarian_online else "stopped"

    if pm.inventory_path.exists():
        try:
            with open(pm.inventory_path, "r") as f:
                data = yaml.safe_load(f)
                for s_data in data.get("servers", []):
                    s_id = s_data.get("id")
                    run_config = s_data.get("run", {})
                    start_cmd = run_config.get("start_cmd", "")
                    
                    proc = None
                    # If we previously started this server with an auto-resolved command (e.g., python fallback),
                    # use that argv to find the running process, otherwise fall back to inventory start_cmd patterns.
                    last_argv = pm.last_server_cmd.get(s_id)
                    if last_argv:
                        parts = [p for p in last_argv if p and len(p) > 2 and not str(p).startswith("-")]
                        proc = find_process(parts)
                    if "mcp.py" in start_cmd or "librarian" in s_id: proc = librarian_proc
                    elif "gui_bridge.py" in start_cmd:
                        # Self-identification
                        proc = psutil.Process(os.getpid())
                    elif start_cmd:
                        parts = [p for p in start_cmd.split() if len(p) > 3 and not p.startswith('-')]
                        proc = find_process(parts)

                    online = proc is not None
                    if not online and psutil is None:
                        # Degraded mode: without process inspection, treat "started this session"
                        # as online unless we have recorded an exit.
                        if s_id in pm.last_server_cmd and s_id not in pm.last_server_exit:
                            online = True
                    
                    # Detailed Metrics
                    stats = {"cpu": 0, "ram": 0, "pid": None}
                    if online:
                        try:
                            # Use oneshot to avoid race conditions
                            with proc.oneshot():
                                stats["cpu"] = proc.cpu_percent(interval=None)
                                stats["ram"] = proc.memory_info().rss  # Bytes
                                stats["pid"] = proc.pid
                        except Exception:
                            # Best-effort metrics; do not fail status on missing permissions / races.
                            pass

                    is_core = any(k in s_id for k in core_keywords)
                    servers.append({
                        "id": s_id, "name": s_data.get("name", s_id),
                        "status": "online" if online else "stopped",
                        "type": "core" if is_core else run_config.get("kind", "generic"),
                        "metrics": stats,
                        "last_exit": pm.last_server_exit.get(s_id),
                        "raw": s_data
                    })
        except Exception as e:
            if session_logger: session_logger.log("ERROR", f"Inventory sync failed: {str(e)}")
            pass

    # Global Metrics (best-effort; may be blocked)
    current_metrics = {"cpu": 0, "memory": 0, "ram_total": 0, "ram_used": 0, "disk": 0, "disk_total": 0, "disk_used": 0, "disk_free": 0, "ts": time.time()}
    if psutil:
        try:
            d = psutil.disk_usage('/')
            current_metrics = {
                "cpu": psutil.cpu_percent(interval=None),
                "memory": psutil.virtual_memory().percent,
                "ram_total": psutil.virtual_memory().total,
                "ram_used": psutil.virtual_memory().used,
                "disk": d.percent,
                "disk_total": d.total,
                "disk_used": d.used,
                "disk_free": d.free,
                "ts": time.time()
            }
            METRIC_HISTORY.append(current_metrics)
        except Exception:
            pass

    resource_count = 0
    db_path = pm.app_data_dir / "knowledge.db"
    if db_path.exists():
        try:
            conn = sqlite3.connect(db_path)
            try:
                resource_count = conn.execute("SELECT count(*) FROM links").fetchone()[0]
            except sqlite3.OperationalError as e:
                # Common in fresh installs / partial restores: DB exists but schema not initialized yet.
                # Do not spam ERROR logs in status/report surfaces.
                msg = str(e).lower()
                if "no such table" in msg or "no such column" in msg:
                    resource_count = 0
                else:
                    if session_logger:
                        session_logger.log("WARNING", f"Resource count unavailable: {e}")
            conn.close()
        except Exception as e:
            if session_logger:
                session_logger.log("WARNING", f"Resource count unavailable: {str(e)}")
            pass

    # Version Status
    version_status = "up-to-date"
    try:
        activator_path = pm.bin_dir / "mcp-activator"
        if activator_path.exists():
            mtime = activator_path.stat().st_mtime
            if (datetime.datetime.now().timestamp() - mtime) > 86400:
                version_status = "sync-required"
    except Exception as e:
        if session_logger:
            session_logger.log("WARNING", f"Version status check failed: {e}")

    missing_cores = []
    if not (pm.bin_dir / "mcp-activator").exists(): missing_cores.append("activator")
    if not librarian_online: missing_cores.append("librarian")

    if missing_cores:
        pulse = "red"; posture = f"Degraded: Missing {', '.join(missing_cores)}"
    elif current_metrics["cpu"] > 80:
        pulse = "yellow"; posture = "Resource Pressure"
    else:
        pulse = "green"; posture = "Optimal"

    return jsonify({
        "activator": "online" if (pm.bin_dir / "mcp-activator").exists() else "missing",
        "librarian": "online" if librarian_online else "stopped",
        "core_components": core_components,
        "version_status": version_status,
        "posture": posture,
        "pulse": pulse,
        "metrics": current_metrics,
        "history": list(METRIC_HISTORY),
        "servers": servers,
        "resource_count": resource_count,
        "active_project": pm.active_project,
        "version": __version__,
        "log_stats": {**_log_dir_stats(pm.app_data_dir / "server_logs"), **_log_policy()}
    })

@app.route('/validate', methods=['GET'])
def validate_env():
    """Deep environment validation with ranked fixes."""
    results = []
    
    # 1. Critical: Scan session logic for recent errors
    try:
        log_path = pm.log_path
        if log_path.exists():
            with open(log_path, "r") as f:
                # Read last 50 lines for better coverage
                lines = f.readlines()
                recent_errors = []
                for line in lines[-50:]:
                    try:
                        entry = json.loads(line)
                        # Only show errors that haven't been acknowledged
                        if entry.get("level") == "ERROR" and entry.get("timestamp", 0) > pm.acknowledged_errors:
                            recent_errors.append(entry)
                    except Exception:
                        continue
                
                if recent_errors:
                    # Group by message to avoid spam
                    unique_msgs = set([e.get("message") for e in recent_errors])
                    for msg in unique_msgs:
                        results.append({
                            "domain": "Runtime", 
                            "status": "error", 
                            "msg": f"Last Error: {msg}", 
                            "fix": "Re-run command with --debug"
                        })
    except Exception as e:
        print(f"Validator error: {e}")

    # 2. Check Server Health
    try:
        inventory = pm.get_inventory()
        for server_id, cfg in inventory.get("mcp_servers", {}).items():
            # Basic process check if possible
            pass
    except Exception as e:
        if session_logger:
            session_logger.log("WARNING", f"Server health validation degraded: {e}")

    # 3. Check Python version
    if sys.version_info < (3, 10):
        results.append({"domain": "Python", "status": "warning", "msg": "Python 3.10+ recommended.", "fix": "Upgrade Python"})
    
    # 2. Check BIN_DIR existence
    if not pm.bin_dir.exists():
        results.append({"domain": "Infrastructure", "status": "fatal", "msg": "Hardened binaries missing.", "fix": "mcp-activator --sync"})
    
    # 3. Check writable paths
    for p in [pm.app_data_dir, pm.log_path.parent]:
        if p.exists() and not os.access(p, os.W_OK):
            results.append({"domain": "Permissions", "status": "fatal", "msg": f"Cannot write to {p}", "fix": f"chmod +w {p}"})

    # 4. Check for critical artifacts
    if not (pm.app_data_dir / "knowledge.db").exists():
        results.append({"domain": "Librarian", "status": "warning", "msg": "Knowledge base empty.", "fix": "Add scan roots and index"})

    # 5. Check for common port conflicts - REMOVED (self-check causes false positive)
    # import socket
    # def is_port_in_use(port):
    #     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    #         return s.connect_ex(('localhost', port)) == 0
    # if is_port_in_use(5001):
    #     results.append({"domain": "Networking", "status": "warning", "msg": "Port 5001 in use (Bridge default).", "fix": "Check for other bridge instances"})

    return jsonify(results)

@app.route('/nexus/acknowledge', methods=['GET', 'POST', 'OPTIONS'])
def acknowledge_errors():
    """Silence current error notifications in the GUI."""
    pm.acknowledged_errors = time.time()
    pm.save_context() # RED TEAM: Persist dismissal
    if session_logger:
        session_logger.log("INFO", "GUI Error Notifications Cleared", suggestion="Logs remain accessible in the Terminal tab.")
    return jsonify({"success": True, "ts": pm.acknowledged_errors})

@app.route('/nexus/run', methods=['POST'])
def nexus_run_command():
    cmd_str = request.json.get("command")
    if not cmd_str: return jsonify({"error": "Command required"}), 400
    allowed_bins = ["mcp-activator", "mcp-observer", "mcp-librarian", "mcp-surgeon", "python3", "npx"] # Allow python3 for injector
    cmd_base = cmd_str.split()[0]
    if cmd_base not in allowed_bins:
        return jsonify({"error": f"Command '{cmd_base}' not allowed"}), 403

    try:
        # Use system command if not found in bin_dir
        binary_path = pm.bin_dir / cmd_base
        if not binary_path.exists():
            binary_path = cmd_base # Fallback to PATH for system commands
        
        # SPECIAL HANDLING: mcp-surgeon needs strict argument parsing
        # The frontend sends "mcp-surgeon --add foo --client claude"
        # We must ensure this splits into ["--add", "foo", "--client", "claude"]
        if cmd_base == "mcp-surgeon":
             # Force clean split, removing any potential weird quote handling if frontend sent raw string
             parts = shlex.split(cmd_str)
             if len(parts) > 1:
                 args = parts[1:]
             else:
                 args = []
        else:
             args = shlex.split(cmd_str)[1:]
        # v11: Pass project context via env if needed
        env = os.environ.copy()
        env["NEXUS_PROJECT_PATH"] = pm.active_project["path"]
        result = subprocess.run([str(binary_path)] + args, capture_output=True, text=True, timeout=30, env=env)
        
        if session_logger:
            status = "SUCCESS" if result.returncode == 0 else "FAILED"
            # Log with full stdout/stderr in metadata
            session_logger.log_command(
                cmd_str, 
                status, 
                result=result.stdout if result.returncode == 0 else result.stderr
            )

        return jsonify({"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr})
    except Exception as e: 
        if session_logger:
            session_logger.log("ERROR", f"Command execution failed: {cmd_str}", metadata={"error": str(e)})
        return jsonify({"error": str(e)}), 500

@app.route('/llm/batch', methods=['POST'])
def llm_batch_process():
    """
    Sub-Agent Supervisor: Executes multiple LLM extractions in parallel.
    Reduces total token round-trips by aggregating results on the server.
    """
    requests_data = request.json.get("requests", [])
    if not requests_data: return jsonify({"error": "No requests provided"}), 400
    
    from concurrent.futures import ThreadPoolExecutor
    
    import sys
    from pathlib import Path
    lib_path = str(Path(__file__).parent.parent / "mcp-link-library")
    if lib_path not in sys.path: sys.path.append(lib_path)
    try:
        from mcp_wrapper import wrapper
    except ImportError:
        return jsonify({"error": "MCPWrapper not found"}), 500
    # Real parallel loop

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(wrapper.call, requests_data))
        
    return jsonify({
        "total": len(results),
        "results": results,
        "efficiency_gain": "PARALLEL_REAL_EXECUTION"
    })

@app.route('/mcp/sse', methods=['GET'])
def mcp_sse():
    """Server-Sent Events endpoint for MCP clients."""
    from flask import Response
    def event_stream():
        # Instructions for the web client
        yield f"data: {json.dumps({'type': 'info', 'msg': 'Nexus Librarian SSE Connected'})}\n\n"
        while True:
            # We would normally wait for actual MCP events here
            # For now, keep connection alive
            import time
            time.sleep(15)
            yield f"data: {json.dumps({'type': 'ping'})}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")



@app.route('/logs/prune', methods=['POST'])
def logs_prune():
    # Prune lifecycle logs by age and total size cap.
    try:
        log_dir = pm.app_data_dir / 'server_logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        result = _prune_log_dir(log_dir)
        if session_logger:
            session_logger.log('INFO', 'Logs pruned', metadata=result)
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/export/report', methods=['GET'])
def export_report():
    """Generate a high-fidelity HTML report."""
    from flask import render_template_string
    server_id = request.args.get("server")
    log_payload = None
    if server_id:
        try:
            resp = server_logs_latest(server_id)
            # If server_logs_latest returned an error response, pass it through as None.
            if isinstance(resp, tuple):
                log_payload = None
            else:
                log_payload = resp.get_json()
        except Exception:
            log_payload = None
    template = """
    <html>
    <head><style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 40px; color: #333; background: #f4f4f9; }
        .card { background: white; border: 1px solid #ddd; padding: 25px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        h1 { color: #2c3e50; }
        h2 { color: #34495e; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        .success { color: #2ecc71; font-weight: bold; }
        .error { color: #e74c3c; font-weight: bold; }
        .warning { color: #f1c40f; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; color: #7f8c8d; font-size: 12px; text-transform: uppercase; }
        code { background: #f1f2f6; padding: 2px 6px; border-radius: 4px; font-family: monospace; color: #e74c3c; }
        .log-entry { font-family: monospace; font-size: 12px; border-bottom: 1px solid #eee; padding: 8px 0; }
        pre { background: #0b1020; color: #e2e8f0; padding: 14px; border-radius: 10px; overflow: auto; white-space: pre-wrap; }
        details > summary { cursor: pointer; font-weight: 600; }
    </style></head>
    <body>
        <h1>Nexus Server Report</h1>
        <p><strong>Generated:</strong> {{ time }}</p>
        <div class="card">
          <h2>Target Server</h2>
          <form>
            <label for="server" style="font-size:12px;color:#7f8c8d;">Select server</label><br/>
            <select id="server" name="server" onchange="this.form.submit()" style="margin-top:8px;padding:10px;border-radius:10px;border:1px solid #ddd;min-width:260px;">
              <option value="">(system-wide report)</option>
              {% for s in servers %}
                <option value="{{ s.id }}" {% if server_id == s.id %}selected{% endif %}>{{ s.name }} ({{ s.id }})</option>
              {% endfor %}
            </select>
          </form>
          {% if server_id %}
            <p style="margin-top:10px;"><strong>Target Server:</strong> <code>{{ server_id }}</code></p>
          {% endif %}
          {% if server_id and not target %}
            <p class="warning">Requested server id was not found in inventory: <code>{{ server_id }}</code></p>
            <p style="font-size:12px;color:#7f8c8d;">Tip: choose a server from the dropdown above.</p>
          {% endif %}
        </div>
        
        {% if target %}
        <div class="card">
            <h2>Target Server Details</h2>
            <table>
                <tr><th>Field</th><th>Value</th></tr>
                <tr><td>Name</td><td>{{ target.name }}</td></tr>
                <tr><td>Status</td><td><span class="{{ 'success' if target.status == 'online' else 'error' }}">{{ target.status }}</span></td></tr>
                <tr><td>Type</td><td>{{ target.type }}</td></tr>
                <tr><td>PID</td><td>{{ target.metrics.pid or '-' }}</td></tr>
                <tr><td>Path</td><td><code>{{ target.raw.path or '' }}</code></td></tr>
                <tr><td>Start Cmd</td><td><code>{{ (target.raw.run.start_cmd if target.raw.run and target.raw.run.start_cmd else '') }}</code></td></tr>
                <tr><td>Last Start Log</td><td><code>/server/logs/{{ server_id }}/view</code></td></tr>
            </table>
            {% if log_payload and log_payload.lines %}
              <h3 style="margin-top:18px;margin-bottom:8px;">Last Start Log (tail)</h3>
              <div style="font-size:12px;margin-bottom:8px;">
                <div><strong>File:</strong> <code>{{ log_payload.log_path }}</code></div>
              </div>
              <pre>{{ "\n".join(log_payload.lines) }}</pre>
            {% else %}
              <p class="warning" style="margin-top:18px;">No per-server start log found. Try starting the server once and re-open this report.</p>
            {% endif %}
        </div>
        {% endif %}

        <div class="card">
          <details>
            <summary>System context (optional)</summary>
            <div style="margin-top:12px;">
              <p><strong>Overall Posture:</strong> <span class="{{ 'success' if status.pulse == 'green' else 'error' }}">{{ status.posture }}</span></p>
              <p><strong>Project:</strong> {{ project.id }}</p>
              <p><strong>Location:</strong> <code>{{ project.path }}</code></p>
              <table>
                  <tr><th>Component</th><th>Status</th></tr>
                  <tr><td>Activator</td><td class="{{ 'success' if status.activator == 'online' else 'error' }}">{{ status.activator }}</td></tr>
                  <tr><td>Librarian</td><td class="{{ 'success' if status.librarian == 'online' else 'error' }}">{{ status.librarian }}</td></tr>
              </table>
            </div>
          </details>
        </div>

        <div class="card">
            <h2>Recent Activity Logs</h2>
            {% for log in logs[-20:] %}
            <div class="log-entry">
                <span style="color: #95a5a6">{{ log.iso }}</span>
                <span style="font-weight: bold; color: {{ '#e74c3c' if log.level == 'ERROR' else '#3498db' }}">{{ log.level }}</span>
                {{ log.message }}
            </div>
            {% endfor %}
        </div>
    </body>
    </html>
    """
    
    # Gather data
    status_data = get_status().get_json()
    logs_data = get_logs().get_json()
    servers_list = []
    try:
        servers_list = status_data.get("servers") or []
    except Exception:
        servers_list = []
    target = None
    if server_id:
        try:
            for s in (status_data.get("servers") or []):
                if s.get("id") == server_id:
                    target = s
                    break
        except Exception:
            target = None
    
    html = render_template_string(template, 
                                  time=datetime.datetime.now().isoformat(),
                                  project=pm.active_project,
                                  status=status_data,
                                  logs=logs_data,
                                  servers=servers_list,
                                  server_id=server_id,
                                  target=target,
                                  log_payload=log_payload)
    return html

@app.route('/export/report.json', methods=['GET'])
def export_report_json():
    """
    JSON version of /export/report for in-app log browsing.
    Designed for GUI inspection (raw), not for MCP stdio.
    """
    server_id = request.args.get("server")
    try:
        status_data = get_status().get_json()
    except Exception:
        status_data = {}
    try:
        logs_data = get_logs().get_json()
    except Exception:
        logs_data = []

    servers_list = []
    try:
        servers_list = status_data.get("servers") or []
    except Exception:
        servers_list = []

    target = None
    if server_id:
        for s in servers_list:
            if s.get("id") == server_id:
                target = s
                break

    payload = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "server_id": server_id,
        "target": target,
        "servers": servers_list,
        "recent_activity": (logs_data[-200:] if isinstance(logs_data, list) else logs_data),
        "active_project": status_data.get("active_project"),
        "core_components": status_data.get("core_components"),
        "posture": status_data.get("posture"),
    }
    if server_id and target is None:
        return jsonify({**payload, "error": f"Requested server id was not found in inventory: {server_id}"}), 404
    return jsonify(payload)

@app.route('/nexus/catalog', methods=['GET'])
def nexus_catalog():
    """Return a metadata catalog of all reachable Nexus commands."""
    catalog = [
        {
            "id": "observer",
            "name": "Nexus Observer",
            "bin": "mcp-observer",
            "description": "Health Monitoring and Resource Telemetry.",
            "actions": [
                {"name": "Health Check",  "cmd": "health",   "desc": "Active probe of system components."},
                {"name": "List Servers",  "cmd": "list",     "desc": "Show all registered MCP servers."},
                {"name": "Running Procs", "cmd": "running",  "desc": "Check running server processes."},
                {"name": "Custom Run",    "cmd": "",         "desc": "Run observer with custom flags (e.g. --verbose, --export)."}
            ]
        },
        {
            "id": "activator",
            "name": "Nexus Activator",
            "bin": "mcp-activator",
            "description": "Installer and synchronization engine.",
            "actions": [
                {"name": "Sync Suite",    "cmd": "--sync",   "desc": "Updates all Nexus components to match local source."},
                {"name": "Repair Suite",  "cmd": "--repair", "desc": "Fixes missing dependencies and permissions."},
                {"name": "Custom Run",    "cmd": "",         "desc": "Run activator with custom flags (e.g. --lite, --permanent)."}
            ]
        },
        {
            "id": "librarian",
            "name": "Nexus Librarian",
            "bin": "mcp-librarian",
            "description": "Knowledge Base and Resource Manager.",
            "actions": [
                {"name": "Index Suite",    "cmd": "--index-suite", "desc": "Scan Observer/Injector for discovery."},
                {"name": "Add Resource",   "cmd": "--add",         "desc": "Index a new URL.", "arg": "url"},
                {"name": "Start Watcher",  "cmd": "--watch",       "desc": "Activate real-time file monitoring."},
                {"name": "Custom Run",     "cmd": "",              "desc": "Run librarian with custom flags (e.g. --search, --prune)."}
            ]
        },
        {
            "id": "injector",
            "name": "MCP Injector (Surgeon)",
            "bin": "mcp-surgeon",
            "description": "Output management for IDE configurations.",
            "actions": [
                {"name": "List Clients",   "cmd": "--list-clients", "desc": "Show locations of detected IDE configs."},
                {"name": "List Detected",  "cmd": "--list-clients", "desc": "[Requires Client] Use Custom Run for --list."},
                {"name": "Custom Run",     "cmd": "",               "desc": "Run injector with custom flags (e.g. --client claude --list)."}
            ]
        }
    ]
    return jsonify(catalog)

@app.route('/injector/clients', methods=['GET'])
def injector_clients():
    """Returns a list of installed/detected MCP clients (IDEs)."""
    clients = []
    try:
        cmd = [str(pm.bin_dir / "mcp-surgeon"), "--list-clients"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            # Parse output: "✅ CLIENT_NAME"
            for line in res.stdout.splitlines():
                if "✅" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        # parts[0] is emoji, parts[1] is name
                        clients.append(parts[1].lower())
    except Exception as e:
        if session_logger: session_logger.log("ERROR", f"Client detection failed: {e}")
    
    return jsonify({"clients": clients})

@app.route('/injector/status', methods=['POST'])
def injector_status():
    """
    Checks where a specific server is currently injected.
    It scrapes `mcp-surgeon --list-clients` then checks individual configs.
    NOTE: Ideally this should leverage mcp-surgeon internal API, but running CLI is safer for now.
    """
    target_name = request.json.get("name")
    if not target_name: return jsonify({"error": "Name required"}), 400
    
    injected_into = []
    
    # 1. Get detected clients dynamically
    clients = []
    try:
        cmd = [str(pm.bin_dir / "mcp-surgeon"), "--list-clients"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
             for line in res.stdout.splitlines():
                if "✅" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        clients.append(parts[1].lower())
    except:
        # Fallback if detection fails
        clients = ["claude", "vscode", "cursor", "windsurf"]

    try:
        for c in clients:
            # We run listing for each client.
            check_cmd = [str(pm.bin_dir / "mcp-surgeon"), "--client", c, "--list"]
            # Allow failure if client not found
            res = subprocess.run(check_cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                # Surgeon outputs "  - name: my-server" or similar
                if f"name: {target_name}" in res.stdout.lower() or f"- {target_name}" in res.stdout.lower():
                    injected_into.append(c)
    except Exception as e:
        if session_logger: session_logger.log("ERROR", f"Injection check failed: {e}")

    return jsonify({"server": target_name, "injected_into": injected_into})

@app.route('/project/history', methods=['GET'])
def project_history():
    """Returns a list of available system state snapshots."""
    snapshot_dir = pm.app_data_dir / "snapshots"
    if not snapshot_dir.exists(): return jsonify([])
    snaps = sorted(snapshot_dir.glob("inventory_*.yaml"), reverse=True)
    return jsonify([{"name": s.name, "path": str(s), "time": s.stat().st_mtime} for s in snaps])

def _candidate_repo_dirs() -> list[Path]:
    # Dual-state aware: prefer explicit, non-crawling candidates only.
    candidates: list[Path] = []
    try:
        candidates.append(Path.cwd())
    except Exception:
        pass
    # Test harness hint: allow unit tests to inject a deterministic project root.
    # (Keeps production behavior unchanged unless explicitly set.)
    try:
        hinted = os.environ.get("NEXUS_PROJECT_PATH")
        if hinted:
            candidates.append(Path(hinted).expanduser())
    except Exception:
        pass
    try:
        if isinstance(pm.active_project, dict) and pm.active_project.get("path"):
            candidates.append(Path(pm.active_project["path"]))
    except Exception:
        pass
    try:
        candidates.append(BASE_DIR)
    except Exception:
        pass
    try:
        candidates.append(NEXUS_HOME / "mcp-server-manager")
    except Exception:
        pass

    seen = set()
    uniq: list[Path] = []
    for c in candidates:
        # Do not resolve symlinks here. Some environments (notably macOS) can
        # canonicalize `/tmp` to `/private/tmp`, which breaks deterministic
        # path-based tests and can cause false "not found" results for callers
        # that provide explicit paths.
        try:
            c = c.expanduser()
        except Exception:
            pass
        key = str(c)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(c)
    return uniq

def _select_git_repo_dir() -> Tuple[Optional[Path], list[str]]:
    candidates = _candidate_repo_dirs()
    for c in candidates:
        if (c / ".git").exists():
            return c, [str(x) for x in candidates]
    return None, [str(x) for x in candidates]

def _select_python_project_dir() -> Tuple[Optional[Path], list[str], Optional[str]]:
    candidates = _candidate_repo_dirs()
    for c in candidates:
        try:
            pyp = (c / "pyproject.toml")
        except Exception:
            pyp = None
        if pyp is not None and pyp.exists():
            return c, [str(x) for x in candidates], "pyproject"
        try:
            req = (c / "requirements.txt")
        except Exception:
            req = None
        if req is not None and req.exists():
            return c, [str(x) for x in candidates], "requirements"
    return None, [str(x) for x in candidates], None

@app.route('/system/update/nexus', methods=['POST'])
def system_update_nexus():
    """Update the Nexus Suite (git pull + reinstall)."""
    try:
        payload = request.get_json(silent=True) or {}
        repo_dir, candidates = _select_git_repo_dir()
        if not repo_dir:
            return jsonify({
                "success": False,
                "error": "No git repository found for Nexus update. Run from a workspace repo or re-sync the managed mirror.",
                "candidates": candidates,
            }), 400

        if bool(payload.get("dry_run")):
            return jsonify({
                "success": True,
                "dry_run": True,
                "cmd": ["git", "pull"],
                "cwd": str(repo_dir),
                "candidates": candidates,
            })

        subprocess.Popen(["git", "pull"], cwd=repo_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # We might need to restart the bridge?
        return jsonify({
            "success": True,
            "message": "Git pull initiated. Please restart the bridge to apply changes.",
            "cwd": str(repo_dir),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/nexus/help', methods=['POST'])
def nexus_help():
    """Fetches help output for a given binary."""
    bin_str = request.json.get("bin")
    if not bin_str: return jsonify({"error": "Binary required"}), 400
    
    allowed = ["mcp-activator", "mcp-observer", "mcp-librarian", "python3"]
    cmd_parts = shlex.split(bin_str)
    if cmd_parts[0] not in allowed:
         return jsonify({"error": "Command not allowed"}), 403
         
    try:
        # Append --help. Handle python scripts correctly by appending to the end.
        full_cmd = cmd_parts + ["--help"]
        env = os.environ.copy()
        env["NEXUS_PROJECT_PATH"] = pm.active_project["path"]
        
        res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=5, env=env)
        output = res.stdout if res.stdout else res.stderr
        return jsonify({"help": output, "success": True})
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Command timed out", "success": False})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/system/update/python', methods=['POST'])
def system_update_python():
    """
    Upgrade the *bridge* Python environment (the interpreter running this server).

    NOTE: MCP servers generally have their own environments; use `/server/update/<id>`
    to upgrade a specific managed server.
    """
    try:
        payload = request.get_json(silent=True) or {}
        dry_run = bool(payload.get("dry_run"))
        bridge_python = sys.executable
        cmd = [bridge_python, "-m", "pip", "install", "--upgrade", "pip"]

        if dry_run:
            return jsonify({
                "success": True,
                "dry_run": True,
                "cmd": cmd,
                "cwd": None,
                "mode": "bridge-env",
                "note": "Upgrades pip for the running bridge interpreter.",
            })

        log_root = _home() / ".mcpinv" / "upgrades"
        log_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
        log_path = log_root / f"bridge_pip_upgrade_{stamp}.log"
        with open(log_path, "w") as f:
            f.write("=== Nexus Bridge Pip Upgrade ===\n")
            f.write(f"python: {bridge_python}\n")
            f.write(f"cmd: {' '.join(shlex.quote(x) for x in cmd)}\n\n")
        with open(log_path, "a") as f:
            subprocess.Popen(cmd, cwd=str(Path.cwd()), stdout=f, stderr=subprocess.STDOUT, text=True)
        if session_logger:
            session_logger.log(
                "COMMAND",
                "Bridge pip upgrade initiated",
                suggestion="Upgrade running in background. Open Log Browser → Audit report (JSON) or view the upgrade log.",
                metadata={"cmd": cmd, "log_path": str(log_path)},
            )
        return jsonify(
            {
                "success": True,
                "message": "Bridge pip upgrade initiated in background.",
                "cmd": cmd,
                "log_path": str(log_path),
                "mode": "bridge-env",
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/server/update/<server_id>', methods=['POST'])
def server_update_python(server_id: str):
    """Upgrade a specific managed MCP server's Python environment (server-scoped, not global)."""
    import yaml

    try:
        payload = request.get_json(silent=True) or {}
        dry_run = bool(payload.get("dry_run"))

        inv = pm.get_inventory()
        servers = list(inv.get("servers") or [])
        target = next((s for s in servers if str(s.get("id")) == str(server_id)), None)
        if not target:
            return jsonify({"success": False, "error": f"Server id not found: {server_id}"}), 404

        server_path = Path(str(target.get("path") or "")).expanduser()
        if not server_path:
            return jsonify({"success": False, "error": f"Server path missing for id: {server_id}"}), 400

        # Determine interpreter preference:
        # 1) server-local venv
        # 2) Nexus venv
        # 3) current bridge python
        candidates = [
            server_path / ".venv" / "bin" / "python3",
            server_path / "venv" / "bin" / "python3",
            NEXUS_HOME / ".venv" / "bin" / "python3",
            Path(sys.executable),
        ]
        py = next((p for p in candidates if p.exists()), Path(sys.executable))

        if (server_path / "pyproject.toml").exists():
            cmd = [str(py), "-m", "pip", "install", "--upgrade", "-e", "."]
            mode = "pyproject"
        elif (server_path / "requirements.txt").exists():
            cmd = [str(py), "-m", "pip", "install", "--upgrade", "-r", "requirements.txt"]
            mode = "requirements"
        else:
            cmd = [str(py), "-m", "pip", "install", "--upgrade", "pip"]
            mode = "pip-only"

        if dry_run:
            return jsonify(
                {
                    "success": True,
                    "dry_run": True,
                    "server_id": server_id,
                    "server_path": str(server_path),
                    "python": str(py),
                    "cmd": cmd,
                    "mode": mode,
                }
            )

        log_root = _home() / ".mcpinv" / "upgrades"
        log_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
        log_path = log_root / f"server_{server_id}_upgrade_{stamp}.log"
        with open(log_path, "w") as f:
            f.write("=== Nexus Server Upgrade ===\n")
            f.write(f"server_id: {server_id}\n")
            f.write(f"server_path: {server_path}\n")
            f.write(f"python: {py}\n")
            f.write(f"mode: {mode}\n")
            f.write(f"cmd: {' '.join(shlex.quote(x) for x in cmd)}\n\n")

        with open(log_path, "a") as f:
            subprocess.Popen(cmd, cwd=str(server_path), stdout=f, stderr=subprocess.STDOUT, text=True)

        if session_logger:
            session_logger.log(
                "COMMAND",
                f"Server pip upgrade initiated: {server_id}",
                suggestion="Upgrade running in background. View logs in Log Browser → lifecycle (server) or audit.",
                metadata={"server_id": server_id, "cmd": cmd, "cwd": str(server_path), "log_path": str(log_path)},
            )

        return jsonify(
            {
                "success": True,
                "message": f"Server upgrade initiated in background: {server_id}",
                "server_id": server_id,
                "server_path": str(server_path),
                "python": str(py),
                "cmd": cmd,
                "mode": mode,
                "log_path": str(log_path),
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/system/python_info', methods=['GET'])
def system_python_info():
    """
    Return Python/runtime visibility for the Command Center UI:
    - which interpreter the bridge is running under (truth for server-side behavior)
    - whether Nexus venvs exist
    - a small set of package versions used by the suite
    """

    def _probe(cmd: list[str]) -> Tuple[int, str, str]:
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            return (p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip())
        except Exception as e:
            return (1, "", str(e))

    bridge_python = sys.executable
    which_python3 = shutil.which("python3") or ""
    which_pip3 = shutil.which("pip3") or ""

    nexus_venv_python = str(NEXUS_HOME / ".venv" / "bin" / "python")
    nexus_venv_exists = Path(nexus_venv_python).exists()

    pkgs = [
        "flask",
        "flask-cors",
        "psutil",
        "pyyaml",
        "requests",
        "pillow",
        "pypdf",
        "openpyxl",
        "python-docx",
    ]

    pkg_versions: Dict[str, Any] = {}
    for name in pkgs:
        rc, out, err = _probe([bridge_python, "-m", "pip", "show", name])
        if rc != 0 or not out:
            pkg_versions[name] = {"present": False, "version": None, "error": err or None}
            continue
        version = None
        for line in out.splitlines():
            if line.lower().startswith("version:"):
                version = line.split(":", 1)[1].strip()
                break
        pkg_versions[name] = {"present": True, "version": version, "error": None}

    rc_v, out_v, err_v = _probe([bridge_python, "--version"])
    rc_p, out_p, err_p = _probe([bridge_python, "-m", "pip", "--version"])

    return jsonify(
        {
            "success": True,
            "bridge": {
                "python": bridge_python,
                "python_version": out_v or err_v,
                "pip_version": out_p or err_p,
            },
            "system": {"python3": which_python3, "pip3": which_pip3},
            "nexus": {"venv_python": nexus_venv_python, "venv_exists": nexus_venv_exists},
            "packages": pkg_versions,
        }
    )

@app.route('/project/rollback', methods=['POST'])
def project_rollback():
    """Restores a previous inventory state. Sanitizes input to prevent path traversal."""
    snapshot_name = request.json.get("name")
    if not snapshot_name: return jsonify({"error": "Snapshot name required"}), 400
    
    # Path Traversal Guard: Ensure name is just a filename
    safe_name = os.path.basename(snapshot_name)
    snapshot_path = pm.app_data_dir / "snapshots" / safe_name
    
    if not snapshot_path.exists(): return jsonify({"error": "Snapshot not found"}), 404
    try:
        import shutil
        pm.save_snapshot() # Save current state before rollback
        shutil.copy2(snapshot_path, pm.inventory_path)
        if session_logger:
            session_logger.log("COMMAND", f"System Rollback: {snapshot_name}", suggestion="System state restored to previous snapshot.")
        return jsonify({"success": True})
    except Exception as e:
        if session_logger:
            session_logger.log("ERROR", f"Rollback failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/nexus/projects', methods=['GET', 'POST'])
def nexus_projects():
    if request.method == 'POST':
        p_id = request.json.get("id")
        path = request.json.get("path")
        if not path: return jsonify({"error": "Path required"}), 400
        pm.set_project(path, p_id)
        return jsonify({"success": True, "active_id": p_id})
    return jsonify(pm.get_projects())

@app.route('/project/snapshot', methods=['POST'])
def project_snapshot():
    """Manually triggers a state snapshot."""
    try:
        pm.save_snapshot()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/export/logs', methods=['GET'])
def export_logs():
    import csv, io
    from flask import Response
    if not pm.log_path.exists(): return jsonify({"error": "No logs found"}), 404
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "Level", "Message", "Suggestion"])
    with open(pm.log_path, "r") as f:
        for line in f:
            try:
                log = json.loads(line)
                writer.writerow([datetime.datetime.fromtimestamp(log.get("timestamp", 0)).isoformat(), log.get("level"), log.get("message"), log.get("suggestion", "")])
            except Exception:
                continue
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-disposition": "attachment; filename=nexus_history.csv"})

@app.route('/system/uninstall', methods=['POST'])
def system_uninstall():
    try:
        def _candidate_uninstallers() -> list[Path]:
            out: list[Path] = []
            # Workspace (developer truth): suite root is parent of mcp-server-manager
            try:
                suite_root = Path(__file__).resolve().parent.parent
                p_ws = (suite_root / "repo-mcp-packager" / "uninstall.py").resolve()
                if p_ws.exists():
                    out.append(p_ws)
            except Exception:
                pass

            # Managed mirror (runtime truth)
            p_mirror = (NEXUS_HOME / "repo-mcp-packager" / "uninstall.py").resolve()
            if p_mirror.exists():
                out.append(p_mirror)

            # de-dupe by real path
            seen: set[Path] = set()
            uniq: list[Path] = []
            for p in out:
                rp = p.resolve()
                if rp in seen:
                    continue
                seen.add(rp)
                uniq.append(rp)
            return uniq

        def _supports_flags(p: Path, flags: list[str]) -> bool:
            try:
                r = subprocess.run([sys.executable, str(p), "--help"], capture_output=True, text=True, timeout=5)
                help_txt = (r.stdout or "") + "\n" + (r.stderr or "")
                return all(f in help_txt for f in flags)
            except Exception:
                return False

        payload = request.json or {}
        needs = []
        if payload.get("detach_clients"):
            needs.append("--detach-clients")
        if payload.get("purge_env"):
            needs.append("--purge-env")
        if payload.get("detach_managed_servers"):
            needs.append("--detach-managed-servers")
        if payload.get("detach_suite_tools"):
            needs.append("--detach-suite-tools")
        if payload.get("remove_path_block"):
            needs.append("--remove-path-block")
        if payload.get("remove_wrappers"):
            needs.append("--remove-wrappers")

        candidates = _candidate_uninstallers()
        uninstaller = None
        for c in candidates:
            if needs and not _supports_flags(c, needs):
                continue
            uninstaller = c
            break

        if not uninstaller:
            # Fall back to any candidate, but return a clear error if it can't support requested flags.
            if candidates:
                return jsonify(
                    {
                        "success": False,
                        "error": "Uninstaller found, but it does not support requested options. Run sync/update, or use the workspace version.",
                        "candidates": [str(p) for p in candidates],
                        "requested_flags": needs,
                    }
                ), 409
            uninstaller = None

        if not uninstaller:
            return jsonify({"success": False, "error": "Uninstaller not found"}), 404
        if session_logger:
            session_logger.log("COMMAND", "Factory Reset Initiated", suggestion="Purging all suite data and settings.")
        purge_data = bool(payload.get("purge_data", True))
        purge_env = bool(payload.get("purge_env", False))
        kill_venv = bool(payload.get("kill_venv", True))
        detach_clients = bool(payload.get("detach_clients", False))
        detach_managed_servers = bool(payload.get("detach_managed_servers", False))
        detach_suite_tools = bool(payload.get("detach_suite_tools", False))
        remove_path_block = bool(payload.get("remove_path_block", False))
        remove_wrappers = bool(payload.get("remove_wrappers", False))
        dry_run = bool(payload.get("dry_run", False))

        cmd = [sys.executable, str(uninstaller), "--yes"]
        if purge_data:
            cmd.append("--purge-data")
        if purge_env:
            cmd.append("--purge-env")
        if kill_venv:
            cmd.append("--kill-venv")
        if detach_clients:
            cmd.append("--detach-clients")
        if detach_managed_servers:
            cmd.append("--detach-managed-servers")
        if detach_suite_tools:
            cmd.append("--detach-suite-tools")
        if remove_path_block:
            cmd.append("--remove-path-block")
        if remove_wrappers:
            cmd.append("--remove-wrappers")
        if dry_run:
            cmd.append("--dry-run")

        # Guardrail: avoid running an older uninstaller that doesn't support requested flags.
        # Even if the "supports_flags" preflight misses something, detect argparse failures
        # and return a deterministic remediation message (instead of surfacing a scary stack).
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        stderr = result.stderr or ""
        if "unrecognized arguments:" in stderr:
            try:
                help_res = subprocess.run([sys.executable, str(uninstaller), "--help"], capture_output=True, text=True, timeout=5)
                help_head = "\n".join(((help_res.stdout or "") + "\n" + (help_res.stderr or "")).splitlines()[:6])
            except Exception:
                help_head = ""
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Installed uninstaller is out of date and does not support the selected reset options. Run suite sync/update, then retry Preview.",
                        "uninstaller": str(uninstaller),
                        "cmd": cmd,
                        "stderr": stderr,
                        "help_head": help_head,
                    }
                ),
                409,
            )
        return jsonify({"success": result.returncode == 0, "stdout": result.stdout, "stderr": stderr, "cmd": cmd, "uninstaller": str(uninstaller)})
    except Exception as e:
        if session_logger:
            session_logger.log("ERROR", f"Uninstall failure: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/server/control', methods=['POST'])
def server_control():
    s_id = request.json.get("id")
    action = request.json.get("action")
    inv = pm.get_inventory()
    target = next((s for s in inv.get("servers", []) if s.get("id") == s_id), None)
    if not target: return jsonify({"error": "Server not found"}), 404

    cmd = target.get("run", {}).get("start_cmd" if action == "start" else "stop_cmd")

    def _sanitize_run_cmd(raw: str) -> str:
        # Commands come from inventory and are executed without a shell (via shlex.split).
        # Strip common shell operators to avoid confusing pkill/argv parsing (e.g. 'pkill -f x || true').
        for op in ('||', '&&', ';'):
            if op in raw:
                raw = raw.split(op, 1)[0].strip()
        return raw
    if not cmd: return jsonify({"error": f"No {action} command defined"}), 400

    try:
        log_dir = pm.app_data_dir / "server_logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        def _write_action_log(action_name: str, lines: list[str]) -> Optional[str]:
            try:
                stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                lp = log_dir / f"{s_id}_{stamp}.log"
                with open(lp, "w", encoding="utf-8") as f:
                    f.write(f"--- SERVER: {s_id} ---\n")
                    f.write(f"--- ACTION: {action_name} ---\n")
                    for ln in lines:
                        f.write(f"{ln}\n")
                    f.write("\n")
                return str(lp)
            except Exception:
                return None

        if action != "start":
            stop_cmd = _sanitize_run_cmd(str(cmd))
            stop_log = _write_action_log("stop", [f"--- CMD: {stop_cmd}", f"--- TS: {datetime.datetime.now().isoformat()}"])
            subprocess.Popen(shlex.split(stop_cmd), start_new_session=True)
            if session_logger:
                session_logger.log("COMMAND", f"Server {s_id}: {action}", suggestion=f"Triggered: {cmd}")
            return jsonify({"success": True, "log_path": stop_log})

        argv, cwd, env, note, requires_python = _resolve_server_run(target)
        if not argv:
            return jsonify({"error": f"No start command resolved for '{s_id}'"}), 400
        if env is None:
            env = os.environ.copy()

        # Auto-repair older forged stub entrypoints that print human banners to stdout.
        # This prevents MCP clients (Claude, Cursor, etc.) from failing JSON parsing.
        try:
            if len(argv) >= 2 and Path(str(argv[1])).name == "mcp_server.py":
                server_path = target.get("path")
                if server_path:
                    ep = Path(server_path) / "mcp_server.py"
                    if _forged_entrypoint_needs_repair(ep):
                        ok = _repair_forged_entrypoint(ep, s_id)
                        if ok:
                            note = (note + " | " if note else "") + "Auto-repaired forged entrypoint for MCP-stdio compliance"
        except Exception:
            pass

        # Runtime gating: if pyproject declares requires-python and the chosen interpreter
        # does not satisfy it, block start with a deterministic error (no "Start lies").
        min_py = _min_python_from_spec(requires_python)
        if min_py:
            py_exe = str(argv[0])
            ver = _python_version_tuple(py_exe, cwd, env)
            if ver and (ver[0], ver[1]) < min_py:
                fallback = _find_python_at_least((min_py[0], min_py[1]), cwd, env, exclude=str(argv[0]))
                if fallback:
                    old = argv[0]
                    argv = [fallback] + list(argv[1:])
                    note = (note + " | " if note else "") + f"Auto-selected {fallback} to satisfy requires-python {requires_python} (was {old})"
                else:
                    # Prefer managed per-suite runtimes before telling the user to change their system toolchain.
                    managed: Optional[ManagedPython] = None
                    try:
                        pin = None
                        rt_cfg = target.get("runtime") or {}
                        if isinstance(rt_cfg, dict):
                            pin = rt_cfg.get("python")
                        if isinstance(pin, str) and pin.strip():
                            # Exact pin: use only if installed.
                            for mp in list_managed_pythons():
                                if mp.version == pin.strip():
                                    managed = mp
                                    break
                        if not managed:
                            managed = choose_managed_python_at_least(min_py[0], min_py[1])
                    except Exception:
                        managed = None

                    if managed:
                        old = argv[0]
                        argv = [str(managed.python)] + list(argv[1:])
                        note = (note + " | " if note else "") + f"Using managed python {managed.version} to satisfy requires-python {requires_python} (was {old})"
                    else:
                        msg = f"Python {ver[0]}.{ver[1]}.{ver[2]} is too old for requires-python '{requires_python}'."
                        if session_logger:
                            session_logger.log("ERROR", f"Blocked start for {s_id}: python mismatch", metadata={"requires_python": requires_python, "python": ver, "cmd": argv, "cwd": cwd})
                        fail_log = _write_action_log(
                            "start_failed",
                            [
                                f"--- CWD: {cwd or '(none)'} ---",
                                f"--- CMD: {' '.join(argv)} ---",
                                f"--- REQUIRES_PYTHON: {requires_python} ---",
                                f"--- ERROR: Runtime mismatch: Python version too old ---",
                                f"--- DETAIL: {msg} ---",
                            ],
                        )
                        return jsonify({
                            "success": False,
                            "error": "Runtime mismatch: Python version too old",
                            "detail": msg,
                            "requires_python": requires_python,
                            "python": {"major": ver[0], "minor": ver[1], "patch": ver[2]},
                            "resolved_cmd": argv,
                            "cwd": cwd,
                            "note": note,
                            "next_step": f"mcp-observer runtime ensure --python {min_py[0]}.{min_py[1]}.0",
                            "log_path": fail_log,
                        }), 409

        setup_log_path = None

        # If this is a real server project directory, prefer a per-server venv so dependencies
        # exist even when we auto-select a newer system Python to satisfy requires-python.
        try:
            server_path = target.get("path")
            server_dir = Path(server_path) if server_path else None
            if server_dir and server_dir.exists() and (server_dir / "pyproject.toml").exists():
                venv_python, setup_log_path = _ensure_server_venv(server_dir, str(argv[0]), log_dir)
                if venv_python:
                    old = argv[0]
                    argv = [venv_python] + list(argv[1:])
                    note = (note + " | " if note else "") + f"Using per-server venv python ({venv_python}) (was {old})"
        except Exception:
            pass

        def _spawn_with_log(spawn_argv: list[str], spawn_note: Optional[str]) -> Tuple[subprocess.Popen, Path]:
            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            lp = log_dir / f"{s_id}_{stamp}.log"
            with open(lp, "w", encoding="utf-8") as f:
                f.write(f"--- SERVER: {s_id} ---\n")
                f.write("--- ACTION: start ---\n")
                f.write(f"--- CWD: {cwd or '(none)'} ---\n")
                f.write(f"--- CMD: {' '.join(spawn_argv)} ---\n")
                if requires_python:
                    f.write(f"--- REQUIRES_PYTHON: {requires_python} ---\n")
                if setup_log_path:
                    f.write(f"--- SETUP_LOG: {setup_log_path} ---\n")
                if spawn_note:
                    f.write(f"--- RESOLVE: {spawn_note} ---\n")
                f.write("\n")
                p = subprocess.Popen(
                    spawn_argv,
                    start_new_session=True,
                    cwd=cwd,
                    env=env,
                    # MCP servers are stdio-based; if stdin is inherited from a closed/non-tty parent,
                    # many servers will detect EOF and exit. Keep stdin open to prevent immediate shutdown.
                    stdin=subprocess.PIPE,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
            def _monitor_exit(proc: subprocess.Popen, log_path: Path, argv_snapshot: list[str]) -> None:
                try:
                    rc = proc.wait()
                except Exception:
                    return
                meta = {
                    "returncode": rc,
                    "ts": time.time(),
                    "cmd": argv_snapshot,
                    "log_path": str(log_path),
                }
                pm.last_server_exit[s_id] = meta
                # Operational truthfulness: if a server stops after start, emit a COMMAND log entry
                # so the UI timeline shows the failure and links to the exact lifecycle log.
                try:
                    started_at = pm.last_server_start.get(s_id)
                    age = (time.time() - float(started_at)) if started_at else None
                except Exception:
                    age = None
                if session_logger and (rc != 0 or (age is not None and age < 15.0)):
                    try:
                        session_logger.log_command(
                            f"Server {s_id}: exited",
                            'FAILED' if rc != 0 else 'SUCCESS',
                            result=f"returncode={rc} log={log_path}" + (f" age_s={age:.1f}" if age is not None else ''),
                        )
                    except Exception:
                        pass
                try:
                    with open(log_path, "a", encoding="utf-8") as f2:
                        when = datetime.datetime.now().isoformat()
                        f2.write("\n")
                        f2.write(f"--- EXIT: {rc} ---\n")
                        f2.write(f"--- EXIT_TS: {when} ---\n")
                except Exception:
                    pass

            t = threading.Thread(target=_monitor_exit, args=(p, lp, list(spawn_argv)), daemon=True)
            t.start()
            return p, lp

        proc, log_path = _spawn_with_log(argv, note)
        pm.last_server_cmd[s_id] = argv
        pm.last_server_start[s_id] = time.time()

        def _retry_with_newer_python(first_log_path: Path, reason: str) -> Optional[Tuple[subprocess.Popen, Path, list[str], str]]:
            fallback = _find_python_at_least((3, 10), cwd, env, exclude=str(argv[0]))
            if not fallback:
                return None
            retry_argv = [fallback] + list(argv[1:])
            retry_note = (note + " | " if note else "") + f"Auto-retry with {fallback} due to {reason}"
            if session_logger:
                session_logger.log("WARNING", f"Retrying start for {s_id} with newer python", metadata={"from": str(argv[0]), "to": fallback, "first_log": str(first_log_path), "reason": reason})
            p2, lp2 = _spawn_with_log(retry_argv, retry_note)
            return (p2, lp2, retry_argv, retry_note)

        # Fast failure detection: if the process exits immediately, return an error
        # so the UI doesn't claim "started" when it actually crashed.
        try:
            # Poll a few times to avoid a race where the child exits just after a single sleep.
            rc = None
            for _ in range(12):
                time.sleep(0.2)
                rc = proc.poll()
                if rc is not None:
                    break
            if rc is not None:
                # If the log indicates a Python<3.10 crash due to PEP604 unions, attempt a deterministic relaunch
                # with a Python>=3.10 interpreter (if present). This fixes common "starts then stops" cases like notebooklm.
                try:
                    tail = log_path.read_text(encoding="utf-8", errors="replace")[-8000:]
                except Exception:
                    tail = ""
                if _looks_like_python_lt_310_union_error(tail):
                    retried = _retry_with_newer_python(log_path, "Python<3.10 union crash signature")
                    if retried:
                        proc2, log_path2, retry_argv, retry_note = retried
                        pm.last_server_cmd[s_id] = retry_argv
                        pm.last_server_start[s_id] = time.time()
                        # Wait for immediate exit again
                        rc2 = None
                        for _ in range(12):
                            time.sleep(0.2)
                            rc2 = proc2.poll()
                            if rc2 is not None:
                                break
                        if rc2 is None:
                            if session_logger:
                                session_logger.log("COMMAND", f"Server {s_id}: start", suggestion=f"Started via fallback python. Logs: {log_path2}")
                            return jsonify({
                                "success": True,
                                "log_path": str(log_path2),
                                "resolved_cmd": retry_argv,
                                "cwd": cwd,
                                "note": retry_note,
                                "retry": {"reason": "python<3.10 union crash signature", "first_log_path": str(log_path)},
                            })
                        if session_logger:
                            session_logger.log("ERROR", f"Server {s_id} exited immediately after retry", metadata={"returncode": rc2, "log_path": str(log_path2)})
                            return jsonify({
                                "success": False,
                                "error": "Server exited immediately after start (python retry attempted)",
                                "returncode": rc2,
                                "log_path": str(log_path2),
                                "resolved_cmd": retry_argv,
                                "cwd": cwd,
                                "note": retry_note,
                                "retry": {"reason": "python<3.10 union crash signature", "first_log_path": str(log_path)},
                            }), 500

                if session_logger:
                    session_logger.log("ERROR", f"Server {s_id} exited immediately", metadata={"returncode": rc, "log_path": str(log_path)})
                return jsonify({"success": False, "error": "Server exited immediately after start", "returncode": rc, "log_path": str(log_path), "resolved_cmd": argv, "cwd": cwd, "note": note}), 500

            # If the process is still running but the log already contains a fatal traceback,
            # fail fast so the UI doesn't claim "started" while the child is crashing.
            try:
                # Give the child a moment to flush stderr/stdout to the file.
                # This is intentionally >1s to catch import-time crashes that occur after dependency loading.
                time.sleep(1.5)
                tail = log_path.read_text(encoding="utf-8", errors="replace")[-8000:]
                if "Traceback (most recent call last):" in tail:
                    if _looks_like_python_lt_310_union_error(tail):
                        retried = _retry_with_newer_python(log_path, "Python<3.10 union crash signature")
                        if retried:
                            proc2, log_path2, retry_argv, retry_note = retried
                            pm.last_server_cmd[s_id] = retry_argv
                            pm.last_server_start[s_id] = time.time()
                            rc2 = None
                            for _ in range(12):
                                time.sleep(0.2)
                                rc2 = proc2.poll()
                                if rc2 is not None:
                                    break
                            if rc2 is None:
                                if session_logger:
                                    session_logger.log("COMMAND", f"Server {s_id}: start", suggestion=f"Started via fallback python. Logs: {log_path2}")
                                return jsonify({
                                    "success": True,
                                    "log_path": str(log_path2),
                                    "resolved_cmd": retry_argv,
                                    "cwd": cwd,
                                    "note": retry_note,
                                    "retry": {"reason": "python<3.10 union crash signature", "first_log_path": str(log_path)},
                                })
                            if session_logger:
                                session_logger.log("ERROR", f"Server {s_id} exited immediately after retry", metadata={"returncode": rc2, "log_path": str(log_path2)})
                            return jsonify({
                                "success": False,
                                "error": "Server produced traceback during start (python retry attempted)",
                                "returncode": rc2,
                                "log_path": str(log_path2),
                                "resolved_cmd": retry_argv,
                                "cwd": cwd,
                                "note": retry_note,
                                "retry": {"reason": "python<3.10 union crash signature", "first_log_path": str(log_path)},
                            }), 500
                    if session_logger:
                        session_logger.log("ERROR", f"Server {s_id} produced traceback on start", metadata={"log_path": str(log_path)})
                    return jsonify({"success": False, "error": "Server produced traceback during start", "log_path": str(log_path), "resolved_cmd": argv, "cwd": cwd, "note": note}), 500
            except Exception:
                pass
        except Exception:
            pass

        if session_logger:
            session_logger.log("COMMAND", f"Server {s_id}: {action}", suggestion=f"Started. Logs: {log_path}")

        return jsonify({"success": True, "log_path": str(log_path), "resolved_cmd": argv, "cwd": cwd, "note": note})
    except Exception as e:
        if session_logger:
            session_logger.log("ERROR", f"Control failed for {s_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/server/logs/<server_id>', methods=['GET'])
def server_logs_latest(server_id: str):
    """
    Returns the most recent captured start log for a server (tail only).
    Intended for quick debugging when a forged server immediately exits.
    """
    # Basic traversal guard
    if ".." in server_id or "/" in server_id:
        return jsonify({"error": "Bad server id"}), 400

    log_dir = pm.app_data_dir / "server_logs"
    if not log_dir.exists():
        return jsonify({"error": "No server logs directory"}), 404

    candidates = sorted(log_dir.glob(f"{server_id}_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return jsonify({"error": "No logs found"}), 404

    log_path = candidates[0]
    try:
        # Tail last N lines to keep payload bounded
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = lines[-200:]
        return jsonify({
            "server_id": server_id,
            "log_path": str(log_path),
            "mtime": log_path.stat().st_mtime,
            "lines": tail,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/server/logs/<server_id>/view', methods=['GET'])
def server_logs_latest_view(server_id: str):
    """
    Human-friendly view of the latest server log.
    """
    data = server_logs_latest(server_id)
    # If server_logs_latest returned an error response, pass it through.
    try:
        status_code = data[1]
        payload = data[0].get_json()
        return jsonify(payload), status_code
    except Exception:
        pass

    payload = data.get_json()
    lines = payload.get("lines", [])
    escaped = "\n".join(lines)
    return f"<pre style='white-space:pre-wrap;font-family:ui-monospace,Menlo,monospace'>{escaped}</pre>"

# Server Management endpoints (passing through PM paths)
@app.route('/server/add', methods=['POST'])
def add_server():
    import yaml
    new_server = request.json
    if not new_server.get("id"): return jsonify({"error": "ID required"}), 400
    try:
        pm.save_snapshot()
        inv = {"servers": []}
        if pm.inventory_path.exists():
            with open(pm.inventory_path, "r") as f: inv = yaml.safe_load(f) or {"servers": []}
        if any(s.get("id") == new_server["id"] for s in inv["servers"]): return jsonify({"error": "ID already exists"}), 400
        inv["servers"].append(new_server)
        with open(pm.inventory_path, "w") as f: yaml.dump(inv, f)
        if session_logger:
            session_logger.log("COMMAND", f"Added new server to inventory: {new_server.get('id')}", suggestion="Server is now available in the Dashboard.")
        return jsonify({"success": True})
    except Exception as e:
        if session_logger:
            session_logger.log("ERROR", f"Failed to add server: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/server/delete', methods=['POST'])
def delete_server():
    import yaml
    s_id = request.json.get("id")
    
    # Core Protection Guard
    core_ids = ["mcp-injector", "mcp-server-manager", "repo-mcp-packager", "nexus-librarian"]
    if s_id in core_ids:
        if session_logger:
            session_logger.log("WARNING", f"Blocked deletion attempt of core component: {s_id}", suggestion="Use 'Purge Entire Suite' in Lifecycle for full removal.")
        return jsonify({"error": f"Cannot delete core component '{s_id}'. Use Lifecycle > Purge for full uninstallation."}), 403

    if not pm.inventory_path.exists(): return jsonify({"error": "Inventory not found"}), 404
    try:
        pm.save_snapshot()
        with open(pm.inventory_path, "r") as f: inv = yaml.safe_load(f)
        before_count = len(inv.get("servers", []))
        inv["servers"] = [s for s in inv.get("servers", []) if s.get("id") != s_id]
        after_count = len(inv["servers"])
        
        if before_count == after_count:
            return jsonify({"error": "Server ID not found"}), 404

        with open(pm.inventory_path, "w") as f: yaml.dump(inv, f)
        if session_logger:
            session_logger.log("COMMAND", f"Deleted server: {s_id}", suggestion="Inventory updated.")
        return jsonify({"success": True})
    except Exception as e:
        if session_logger:
            session_logger.log("ERROR", f"Failed to delete server {s_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/librarian/resource/delete', methods=['POST'])
def delete_link():
    link_id = request.json.get("id")
    db_path = pm.app_data_dir / "knowledge.db"
    if not db_path.exists(): return jsonify({"error": "DB not found"}), 404
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM links WHERE id = ?", (link_id,))
        conn.commit()
        conn.close()
        if session_logger:
            session_logger.log("COMMAND", f"Deleted Librarian resource ID: {link_id}", suggestion="Librarian index updated.")
        return jsonify({"success": True})
    except Exception as e:
        if session_logger:
            session_logger.log("ERROR", f"Failed to delete Librarian resource: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/librarian/resource/open', methods=['POST'])
def open_resource():
    link_id = request.json.get("id")
    root = Path(__file__).parent.parent
    librarian_script = root / "mcp-link-library" / "mcp.py"
    if not librarian_script.exists():
         return jsonify({"error": "Librarian script not found"}), 500
    
    try:
        # Run mcp.py --open <id>
        subprocess.Popen([sys.executable, str(librarian_script), "--open", str(link_id)])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/librarian/resource/edit', methods=['POST'])
def edit_resource():
    link_id = request.json.get("id")
    root = Path(__file__).parent.parent
    librarian_script = root / "mcp-link-library" / "mcp.py"
    if not librarian_script.exists():
         return jsonify({"error": "Librarian script not found"}), 500
    
    try:
        # Run mcp.py --edit <id>
        subprocess.Popen([sys.executable, str(librarian_script), "--edit", str(link_id)])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/librarian/roots', methods=['GET', 'POST', 'DELETE'])
def librarian_roots():
    db_path = pm.app_data_dir / "knowledge.db"
    try:
        conn = sqlite3.connect(db_path)
        if request.method == 'POST':
            path_raw = request.json.get("path")
            if not path_raw:
                return jsonify({"error": "Path required"}), 400
            path = _normalize_user_path(path_raw)
            if Path(path).is_file():
                return jsonify({"error": "Scan roots must be directories. Use 'Add Resource' for files."}), 400
            conn.execute("INSERT OR IGNORE INTO scan_roots (path) VALUES (?)", (path,))
            conn.commit()
            if session_logger:
                session_logger.log("COMMAND", f"Added scan root: {path}")
            return jsonify({"success": True})
        elif request.method == 'DELETE':
            root_id = request.args.get("id")
            conn.execute("DELETE FROM scan_roots WHERE id = ?", (root_id,))
            conn.commit()
            if session_logger:
                session_logger.log("COMMAND", f"Removed scan root ID: {root_id}")
            return jsonify({"success": True})
        
        rows = conn.execute("SELECT id, path, created_at FROM scan_roots").fetchall()
        conn.close()
        return jsonify([{"id": r[0], "path": r[1], "created_at": r[2]} for r in rows])
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/librarian/add', methods=['POST'])
def librarian_add_resource():
    """
    Index a single resource (local file path or URL) via the Librarian.
    Accepts paths with spaces and '~' and avoids shell splitting.
    """
    body = request.json or {}
    resource_raw = body.get("resource") or body.get("url") or body.get("path")
    if not resource_raw:
        return jsonify({"error": "resource required"}), 400

    resource = str(resource_raw).strip()
    if not _is_url(resource):
        resource = _normalize_user_path(resource)
        p = Path(resource)
        if not p.exists():
            return jsonify({"error": f"File not found: {resource}"}), 404

    librarian_script = BASE_DIR.parent / "mcp-link-library" / "mcp.py"
    if not librarian_script.exists():
        return jsonify({"error": f"Librarian script not found at {librarian_script}"}), 500

    try:
        cmd = [sys.executable, str(librarian_script), "--add", resource]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if session_logger:
            session_logger.log_command(" ".join(cmd), "SUCCESS" if res.returncode == 0 else "FAILED", result=(res.stdout or res.stderr))
        return jsonify({"success": res.returncode == 0, "stdout": res.stdout, "stderr": res.stderr, "resource": resource})
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Indexing timed out"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/librarian/watcher', methods=['GET', 'POST'])
def librarian_watcher():
    if request.method == 'POST':
        action = request.json.get("action")
        if action == 'start':
            if pm.watcher_proc and pm.watcher_proc.poll() is None:
                return jsonify({"status": "already running"})
            
            bin_path = NEXUS_HOME.parent / "mcp-link-library" / "mcp.py"
            pm.watcher_proc = subprocess.Popen([sys.executable, str(bin_path), "--watch"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return jsonify({"status": "starting", "pid": pm.watcher_proc.pid})
        elif action == 'stop':
            if pm.watcher_proc:
                pm.watcher_proc.terminate()
                pm.watcher_proc = None
            # Aggressive kill without shell=True for security
            import psutil
            for p in psutil.process_iter(['cmdline']):
                if "mcp.py --watch" in " ".join(p.info['cmdline'] or []):
                    try:
                        p.kill()
                    except Exception as e:
                        if session_logger:
                            session_logger.log("WARNING", f"Failed to kill watcher process: {e}")
            return jsonify({"status": "stopped"})
            
    is_alive = pm.watcher_proc is not None and pm.watcher_proc.poll() is None
    if not is_alive:
        # Check system proc list just in case
        import psutil
        for p in psutil.process_iter(['cmdline']):
            if "mcp.py --watch" in " ".join(p.info['cmdline'] or []):
                is_alive = True
                break
                
    return jsonify({"status": "online" if is_alive else "offline"})

@app.route('/librarian/links', methods=['GET'])
def get_links():
    db_path = pm.app_data_dir / "knowledge.db"
    if not db_path.exists(): return jsonify([])
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, url, title, categories, description, domain, created_at FROM links ORDER BY id DESC").fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/artifacts', methods=['GET'])
@app.route('/artifact/list', methods=['GET'])  # v16 alias — resolves 404 gap
def get_artifacts():
    artifact_dir = pm.app_data_dir / "artifacts"
    if not artifact_dir.exists(): return jsonify([])
    results = []
    try:
        for f in sorted(artifact_dir.glob("*"), key=os.path.getmtime, reverse=True)[:50]:
            results.append({"name": f.name, "path": str(f), "size": f.stat().st_size, "modified": os.path.getmtime(f)})
    except Exception as e:
        if session_logger:
            session_logger.log("WARNING", f"Artifact listing failed: {e}")
    return jsonify(results)

import threading
import uuid

class ForgeManager:
    """Manages asynchronous Forge tasks.

    Thread safety: self._lock must be held for all reads/writes of self.tasks
    because start_task (HTTP thread) and _run_forge (background thread)
    both mutate the dict concurrently.
    """
    MAX_TASKS = 50  # Evict oldest terminal tasks beyond this cap

    def __init__(self):
        self.tasks = {}
        self._lock = threading.Lock()  # Guards all self.tasks mutations

    def _evict(self):
        """Remove oldest completed/failed tasks when cap is exceeded. Caller must hold self._lock."""
        if len(self.tasks) < self.MAX_TASKS:
            return
        terminal = [
            (tid, t) for tid, t in self.tasks.items()
            if t["status"] in ("completed", "failed")
        ]
        # Sort by start_time ascending and drop oldest half to stay under cap
        terminal.sort(key=lambda x: x[1].get("start_time", 0))
        for tid, _ in terminal[: len(terminal) // 2 + 1]:
            del self.tasks[tid]

    def start_task(self, source, name=None):
        """Register a new forge task and return its ID. Thread-safe."""
        with self._lock:
            self._evict()
            task_id = str(uuid.uuid4())
            self.tasks[task_id] = {
                "id": task_id,
                "status": "pending",
                "source": source,
                "logs": [],
                "result": None,
                "start_time": time.time()
            }
        thread = threading.Thread(target=self._run_forge, args=(task_id, source, name))
        thread.daemon = True
        thread.start()
        return task_id

    def _run_forge(self, task_id, source, name):
        task = self.tasks[task_id]
        task["status"] = "running"
        try:
            import sys, io as _io
            project_root = Path(__file__).parent
            if str(project_root / "forge") not in sys.path:
                sys.path.insert(0, str(project_root / "forge"))

            from forge_engine import ForgeEngine

            engine = ForgeEngine(pm.app_data_dir.parent, inventory_path=pm.inventory_path)

            task["logs"].append(f"Starting Forge for: {source}")
            task["logs"].append(f"Target Inventory: {pm.inventory_path}")

            # Redirect stdout so ForgeEngine's print() lines flow into task logs
            class _LogCapture(_io.TextIOBase):
                def write(self_inner, s):
                    if s.strip():
                        task["logs"].append(s.rstrip())
                    return len(s)
                def flush(self_inner): pass

            _orig_stdout = sys.stdout
            sys.stdout = _LogCapture()
            try:
                target_path = engine.forge(source, name)
            finally:
                sys.stdout = _orig_stdout  # always restore

            task["logs"].append(f"Server available at: {target_path}")
            task["status"] = "completed"
            task["result"] = {
                "success": True,
                "stdout": "\n".join(task["logs"]),
                "server_path": str(target_path)
            }

            if session_logger:
                session_logger.log_command(f"FORGE: {source}", "SUCCESS", result=str(target_path))
            
            # Persist for recovery in GUI
            pm.last_forge_result = task["result"]
            pm.save_context()

        except Exception as e:
            sys.stdout = _orig_stdout if '_orig_stdout' in dir() else sys.stdout
            task["status"] = "failed"
            task["logs"].append(f"ERROR: {str(e)}")
            import traceback
            task["logs"].append(traceback.format_exc())
            task["result"] = {"success": False, "error": str(e)}
            if session_logger:
                session_logger.log("ERROR", f"Forge failed: {str(e)}")

fm = ForgeManager()

@app.route('/forge', methods=['POST'])
def forge_server():
    """Triggers the Nexus Forge Engine asynchronously."""
    source = request.json.get("source")
    name = request.json.get("name")
    if not source: return jsonify({"error": "Source path or URL required"}), 400
    
    task_id = fm.start_task(source, name)
    
    if session_logger:
        session_logger.log("COMMAND", f"Forge Initiated (Async): {source}", suggestion="Check Progress tab for status.")

    return jsonify({"success": True, "task_id": task_id})

@app.route('/forge/status/<task_id>', methods=['GET'])
def forge_status(task_id):
    task = fm.tasks.get(task_id)
    if not task: return jsonify({"error": "Task not found"}), 404
    return jsonify(task)

@app.route('/forge/last', methods=['GET'])
def forge_last():
    """Returns the last persisted forge result."""
    return jsonify(pm.last_forge_result or {})

if __name__ == '__main__':
    # ── Do not run gui_bridge.py directly ──────────────────────────────────
    # The canonical entry point is nexus_tray.py, which starts Flask in a
    # daemon thread and provides a macOS/Windows system-tray icon.
    # Double-click "Start Nexus.command" on your Desktop instead.
    #
    # This fallback exists for CI / headless environments only.
    import os
    if os.environ.get("NEXUS_HEADLESS") == "1":
        print(f"🚀 Nexus GUI Bridge (headless) — port 5001")
        host = os.environ.get("NEXUS_BIND", "127.0.0.1")
        port = int(os.environ.get("NEXUS_PORT", "5001"))
        app.run(host=host, port=port, debug=False)
    else:
        print("⚠️  Use  'python3 nexus_tray.py'  or double-click 'Start Nexus.command' on your Desktop.")
        print("   Set NEXUS_HEADLESS=1 to force terminal mode (CI/servers only).")
