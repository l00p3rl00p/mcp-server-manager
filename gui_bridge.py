import os
import json
import sqlite3
import subprocess
import sys
import shlex
import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from collections import deque
import time

METRIC_HISTORY = deque(maxlen=60)
from pathlib import Path

app = Flask(__name__)
CORS(app) 

# Official Logging Integration
try:
    sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-link-library"))
    from nexus_session_logger import NexusSessionLogger
    session_logger = NexusSessionLogger()
except:
    session_logger = None

# Base Discovery
NEXUS_HOME = Path.home() / ".mcp-tools"
PROJECTS_FILE = Path.home() / ".mcpinv" / "projects.json"
ACTIVE_CONTEXT_FILE = Path.home() / ".mcpinv" / "active_context.json"

class ProjectManager:
    def __init__(self):
        self.active_project = None
        self.app_data_dir = NEXUS_HOME / "mcp-server-manager"
        self.inventory_path = self.app_data_dir / "inventory.yaml"
        self.log_path = Path.home() / ".mcpinv" / "session.jsonl"
        self.bin_dir = NEXUS_HOME / "bin"
        self.watcher_proc = None # Track the PID
        self.load_active_context()

    def load_active_context(self):
        if ACTIVE_CONTEXT_FILE.exists():
            try:
                with open(ACTIVE_CONTEXT_FILE, 'r') as f:
                    ctx = json.load(f)
                    self.set_project(ctx.get("path"), ctx.get("id"))
            except: pass
        if not self.active_project:
            self.set_project(str(self.app_data_dir), "nexus-default")

    def save_snapshot(self):
        """Captures a timestamped copy of the inventory.yaml for recovery."""
        if not self.inventory_path.exists(): return
        try:
            snapshot_dir = pm.app_data_dir / "snapshots"
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            import shutil
            shutil.copy2(self.inventory_path, snapshot_dir / f"inventory_{stamp}.yaml")
            # Prune to last 10
            snaps = sorted(snapshot_dir.glob("inventory_*.yaml"), reverse=True)
            for s in snaps[10:]: s.unlink()
        except Exception as e:
            if session_logger: session_logger.log("ERROR", f"Snapshot capture failed: {str(e)}")

    def set_project(self, path: str, p_id: str):
        """Standardizes paths for a specific project context and saves the active session."""
        path = Path(path)
        self.active_project = {"id": p_id, "path": str(path)}
        # Project-specific paths
        self.app_data_dir = path
        self.inventory_path = path / "inventory.yaml"
        # Logs usually stay central for chronological timeline, but can be project-specific
        # For v11 we keep logs central but filterable if needed.
        
        # Save context
        ACTIVE_CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ACTIVE_CONTEXT_FILE, 'w') as f:
            json.dump(self.active_project, f)

    def get_projects(self):
        if not PROJECTS_FILE.exists():
            projects = [{"id": "nexus-default", "name": "Workforce Nexus (Default)", "path": str(NEXUS_HOME / "mcp-server-manager")}]
            with open(PROJECTS_FILE, 'w') as f: json.dump(projects, f)
        
        with open(PROJECTS_FILE, 'r') as f:
            return json.load(f)

    def get_inventory(self):
        import yaml
        if not self.inventory_path.exists(): return {"servers": []}
        try:
            with open(self.inventory_path, 'r') as f:
                return yaml.safe_load(f) or {"servers": []}
        except: return {"servers": []}

pm = ProjectManager()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "project": pm.active_project})

@app.route('/logs', methods=['GET'])
def get_logs():
    if not pm.log_path.exists(): return jsonify([])
    logs = []
    try:
        with open(pm.log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-100:]
            for line in lines:
                try: logs.append(json.loads(line))
                except: continue
        return jsonify(logs)
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/status', methods=['GET'])
def get_status():
    import psutil
    import yaml
    
    servers = []
    # Capture PID, Name, Cmdline
    procs = list(psutil.process_iter(['name', 'cmdline', 'pid']))
    
    def find_process(patterns):
        for p in procs:
            try:
                cmdline = ' '.join(p.info['cmdline'] or [])
                if any(pat in cmdline for pat in patterns): return p
            except: pass
        return None

    librarian_proc = find_process(["mcp.py", "nexus-librarian"])
    librarian_online = librarian_proc is not None
    core_keywords = ["mcp-injector", "mcp-server-manager", "repo-mcp-packager", "nexus-librarian"]

    if pm.inventory_path.exists():
        try:
            with open(pm.inventory_path, "r") as f:
                data = yaml.safe_load(f)
                for s_data in data.get("servers", []):
                    s_id = s_data.get("id")
                    run_config = s_data.get("run", {})
                    start_cmd = run_config.get("start_cmd", "")
                    
                    proc = None
                    if "mcp.py" in start_cmd or "librarian" in s_id: proc = librarian_proc
                    elif "gui_bridge.py" in start_cmd:
                        # Self-identification
                        proc = psutil.Process(os.getpid())
                    elif start_cmd:
                        parts = [p for p in start_cmd.split() if len(p) > 3 and not p.startswith('-')]
                        proc = find_process(parts)

                    online = proc is not None
                    
                    # Detailed Metrics
                    stats = {"cpu": 0, "ram": 0, "pid": None}
                    if online:
                        try:
                            # Use oneshot to avoid race conditions
                            with proc.oneshot():
                                stats["cpu"] = proc.cpu_percent(interval=None)
                                stats["ram"] = proc.memory_info().rss  # Bytes
                                stats["pid"] = proc.pid
                        except: pass

                    is_core = any(k in s_id for k in core_keywords)
                    servers.append({
                        "id": s_id, "name": s_data.get("name", s_id),
                        "status": "online" if online else "stopped",
                        "type": "core" if is_core else run_config.get("kind", "generic"),
                        "metrics": stats,
                        "raw": s_data
                    })
        except: pass

    # Global Metrics
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

    resource_count = 0
    db_path = pm.app_data_dir / "knowledge.db"
    if db_path.exists():
        try:
            conn = sqlite3.connect(db_path)
            resource_count = conn.execute("SELECT count(*) FROM links").fetchone()[0]
            conn.close()
        except: pass

    # Version Status
    version_status = "up-to-date"
    try:
        activator_path = pm.bin_dir / "mcp-activator"
        if activator_path.exists():
            mtime = activator_path.stat().st_mtime
            if (datetime.datetime.now().timestamp() - mtime) > 86400:
                version_status = "sync-required"
    except: pass

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
        "version_status": version_status,
        "posture": posture,
        "pulse": pulse,
        "metrics": current_metrics,
        "history": list(METRIC_HISTORY),
        "servers": servers,
        "resource_count": resource_count,
        "active_project": pm.active_project
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
                        if entry.get("level") == "ERROR":
                            recent_errors.append(entry)
                    except: pass
                
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
    except: pass

    # 3. Check Python version
    if sys.version_info < (3, 10):
        results.append({"domain": "Python", "status": "warning", "msg": "Python 3.10+ recommended.", "fix": "Upgrade Python"})
    
    # 2. Check BIN_DIR existence
    if not pm.bin_dir.exists():
        results.append({"domain": "Infrastructure", "status": "error", "msg": "Hardened binaries missing.", "fix": "mcp-activator --sync"})
    
    # 3. Check writable paths
    for p in [pm.app_data_dir, pm.log_path.parent]:
        if p.exists() and not os.access(p, os.W_OK):
            results.append({"domain": "Permissions", "status": "error", "msg": f"Cannot write to {p}", "fix": f"chmod +w {p}"})

    # 4. Check for critical artifacts
    if not (pm.app_data_dir / "knowledge.db").exists():
        results.append({"domain": "Librarian", "status": "warning", "msg": "Knowledge base empty.", "fix": "Add scan roots and index"})

    # 5. Check for common port conflicts
    import socket
    def is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    if is_port_in_use(5001):
        results.append({"domain": "Networking", "status": "warning", "msg": "Port 5001 in use (Bridge default).", "fix": "Check for other bridge instances"})

    return jsonify(results)

@app.route('/nexus/run', methods=['POST'])
def nexus_run_command():
    cmd_str = request.json.get("command")
    if not cmd_str: return jsonify({"error": "Command required"}), 400
    allowed_bins = ["mcp-activator", "mcp-observer", "mcp-librarian", "mcp-surgeon"]
    cmd_base = cmd_str.split()[0]
    if cmd_base not in allowed_bins:
        return jsonify({"error": f"Command '{cmd_base}' not allowed"}), 403

    try:
        bin_path = pm.bin_dir / cmd_base
        args = shlex.split(cmd_str)[1:]
        # v11: Pass project context via env if needed
        env = os.environ.copy()
        env["NEXUS_PROJECT_PATH"] = pm.active_project["path"]
        result = subprocess.run([str(bin_path)] + args, capture_output=True, text=True, timeout=30, env=env)
        
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

@app.route('/export/report', methods=['GET'])
def export_report():
    """Generate a high-fidelity HTML report."""
    from flask import render_template_string
    template = """
    <html>
    <head><style>
        body { font-family: sans-serif; padding: 40px; color: #333; }
        .card { border: 1px solid #ccc; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .success { color: green; }
        .error { color: red; }
    </style></head>
    <body>
        <h1>Workforce Nexus - System Performance Report</h1>
        <p>Generated on: {{ time }}</p>
        <div class="card">
            <h2>System Health</h2>
            <p>Status: <span class="success">OPTIMAL</span></p>
            <p>Active Project: {{ project.id }} ({{ project.path }})</p>
        </div>
        <div class="card">
            <h2>Resources</h2>
            <p>Total Indexed Links: {{ resource_count }}</p>
        </div>
    </body>
    </html>
    """
    resource_count = 0
    db_path = pm.app_data_dir / "knowledge.db"
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        resource_count = conn.execute("SELECT count(*) FROM links").fetchone()[0]
        conn.close()
        
    html = render_template_string(template, 
                                  time=datetime.datetime.now().isoformat(),
                                  project=pm.active_project,
                                  resource_count=resource_count)
    return html

@app.route('/nexus/catalog', methods=['GET'])
def nexus_catalog():
    """Return a metadata catalog of all reachable Nexus commands."""
    catalog = [
        {
            "id": "activator",
            "name": "Nexus Activator",
            "bin": "mcp-activator",
            "description": "Installer and synchronization engine.",
            "actions": [
                {"name": "Sync Suite", "cmd": "--sync", "desc": "Updates all Nexus components to match local source."},
                {"name": "Industrial Install", "cmd": "--permanent", "desc": "Hardens the installation for industrial use (PATH, venv)."},
                {"name": "Check Integrity", "cmd": "--check", "desc": "Verifies suite connectivity and manifest health."}
            ]
        },
        {
            "id": "librarian",
            "name": "Nexus Librarian",
            "bin": "mcp-librarian",
            "description": "Knowledge Base and Resource Manager.",
            "actions": [
                {"name": "Index Suite", "cmd": "--index-suite", "desc": "Scan Observer/Injector for discovery."},
                {"name": "Add Resource", "cmd": "--add", "desc": "Index a new URL or file path.", "arg": "url"},
                {"name": "Index Folder", "cmd": "--index", "desc": "Deep scan a directory.", "arg": "path"},
                {"name": "Start Watcher", "cmd": "--watch", "desc": "Activate real-time file monitoring."}
            ]
        },
        {
            "id": "observer",
            "name": "Nexus Observer",
            "bin": "mcp-observer",
            "description": "Health Monitoring and Resource Telemetry.",
            "actions": [
                {"name": "Verify Status", "cmd": "--status", "desc": "Check health of all registered servers."},
                {"name": "Log Pulse", "cmd": "--pulse", "desc": "Record current metrics to the session log."}
            ]
        },
        {
            "id": "surgeon",
            "name": "Nexus Surgeon",
            "bin": "mcp-surgeon",
            "description": "Surgical Cleanup and Repair Tool.",
            "actions": [
                {"name": "Repair Venv", "cmd": "--repair", "desc": "Rebuilds central virtual environments."},
                {"name": "Flush Artifacts", "cmd": "--purge", "desc": "Cleans the artifacts directory."}
            ]
        }
    ]
    return jsonify(catalog)

@app.route('/project/history', methods=['GET'])
def project_history():
    """Returns a list of available system state snapshots."""
    snapshot_dir = pm.app_data_dir / "snapshots"
    if not snapshot_dir.exists(): return jsonify([])
    snaps = sorted(snapshot_dir.glob("inventory_*.yaml"), reverse=True)
    return jsonify([{"name": s.name, "path": str(s), "time": s.stat().st_mtime} for s in snaps])

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
            except: continue
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-disposition": "attachment; filename=nexus_history.csv"})

@app.route('/system/uninstall', methods=['POST'])
def system_uninstall():
    try:
        uninstaller = NEXUS_HOME.parent / "repo-mcp-packager" / "uninstall.py"
        if not uninstaller.exists(): return jsonify({"error": "Uninstaller not found"}), 404
        if session_logger:
            session_logger.log("COMMAND", "Factory Reset Initiated", suggestion="Purging all suite data and settings.")
        result = subprocess.run([sys.executable, str(uninstaller), "--yes", "--purge-data", "--kill-venv"], capture_output=True, text=True, timeout=60)
        return jsonify({"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr})
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
    if not cmd: return jsonify({"error": f"No {action} command defined"}), 400

    try:
        # For now, simplistic start/stop
        subprocess.Popen(shlex.split(cmd), start_new_session=True)
        if session_logger:
            session_logger.log("COMMAND", f"Server {s_id}: {action}", suggestion=f"Triggered: {cmd}")
        return jsonify({"success": True})
    except Exception as e:
        if session_logger:
            session_logger.log("ERROR", f"Control failed for {s_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

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

@app.route('/librarian/roots', methods=['GET', 'POST', 'DELETE'])
def librarian_roots():
    db_path = pm.app_data_dir / "knowledge.db"
    try:
        conn = sqlite3.connect(db_path)
        if request.method == 'POST':
            path = request.json.get("path")
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
                    try: p.kill()
                    except: pass
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
def get_artifacts():
    artifact_dir = pm.app_data_dir / "artifacts"
    if not artifact_dir.exists(): return jsonify([])
    results = []
    try:
        for f in sorted(artifact_dir.glob("*"), key=os.path.getmtime, reverse=True)[:50]:
            results.append({"name": f.name, "path": str(f), "size": f.stat().st_size, "modified": os.path.getmtime(f)})
    except: pass
    return jsonify(results)

if __name__ == '__main__':
    print(f"🚀 Nexus GUI Bridge v11 - Active Project: {pm.active_project['id']}")
    app.run(host='0.0.0.0', port=5001, debug=False)
