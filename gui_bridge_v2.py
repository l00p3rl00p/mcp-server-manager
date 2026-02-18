import os
import json
import sqlite3
import subprocess
from flask import Flask, jsonify
from flask_cors import CORS
from pathlib import Path

app = Flask(__name__)
CORS(app) # Allow Vite dev server to access

LOG_PATH = Path.home() / ".mcpinv" / "session.jsonl"

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/logs', methods=['GET'])
def get_logs():
    """Read the last 100 lines of the session log."""
    if not LOG_PATH.exists():
        return jsonify([])
    
    logs = []
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            # Simple tail implementation
            lines = f.readlines()[-100:]
            for line in lines:
                try:
                    logs.append(json.loads(line))
                except:
                    continue
        return jsonify(logs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Real status from Nexus inventory."""
    inventory_path = Path.home() / ".mcpinv" / "inventory.json"
    servers = []
    
    if inventory_path.exists():
        try:
            with open(inventory_path, "r") as f:
                data = json.load(f)
                # Map inventory to UI format
                for s_id, s_data in data.get("servers", {}).items():
                    # Simple heuristic for online state (can be refined with PID check)
                    servers.append({
                        "id": s_id,
                        "name": s_data.get("name", s_id),
                        "status": "online" if "runtime" in s_data else "stopped",
                        "type": s_data.get("type", "generic")
                    })
        except:
            pass

    def is_running(pattern):
        try:
            # Simple pgrep check
            result = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    # Check for core components
    # activator/observer/surgeon are CLI tools, so we define 'online' as 'installed'
    bin_dir = Path.home() / ".mcp-tools" / "bin"
    
    # Posture: check if watcher has been active in last 60 seconds
    db_path = Path.home() / ".mcp-tools" / "mcp-server-manager" / "knowledge.db"
    has_watcher = False
    if db_path.exists():
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM links WHERE categories = 'debug' AND url LIKE 'log://watcher/%'")
            count = c.fetchone()[0]
            if count > 0:
                has_watcher = True
            conn.close()
        except:
            pass

    return jsonify({
        "activator": "online" if (bin_dir / "mcp-activator").exists() else "missing",
        "observer": "online" if (bin_dir / "mcp-observer").exists() else "missing",
        "surgeon": "online" if (bin_dir / "mcp-surgeon").exists() else "missing",
        "librarian": "online" if is_running("mcp.py") or is_running("nexus-librarian") else "stopped",
        "posture": "Live Tracking" if has_watcher else "Standard Operation",
        "servers": servers
    })

@app.route('/artifacts', methods=['GET'])
def get_artifacts():
    """List recent artifacts and their disk locations."""
    artifact_dir = Path.home() / ".mcpinv" / "artifacts"
    if not artifact_dir.exists():
        return jsonify([])
    
    results = []
    for f in sorted(artifact_dir.glob("*"), key=os.path.getmtime, reverse=True)[:50]:
        results.append({
            "name": f.name,
            "path": str(f),
            "size": f.stat().st_size,
            "modified": os.path.getmtime(f)
        })
    return jsonify(results)

@app.route('/server/control', methods=['POST'])
def control_server():
    """Start or Stop an MCP server."""
    from flask import request
    data = request.json
    s_id = data.get("id")
    action = data.get("action") # "start" or "stop"
    runtime_path = Path.home() / ".mcpinv" / "runtime.json"
    
    inventory_path = Path.home() / ".mcpinv" / "inventory.json"
    if not inventory_path.exists():
        return jsonify({"error": "No inventory found"}), 404
    
    try:
        with open(inventory_path, "r") as f:
            inventory = json.load(f)
        
        server = inventory.get("servers", {}).get(s_id)
        if not server:
            return jsonify({"error": "Server not found"}), 404
        
        # Load running pids
        pids = {}
        if runtime_path.exists():
            with open(runtime_path, "r") as f:
                pids = json.load(f)

        if action == "start":
            cmd = server.get("command")
            if not cmd:
                return jsonify({"error": "No start command defined for this server"}), 400
            
            import subprocess
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            pids[s_id] = proc.pid
            
            with open(runtime_path, "w") as f:
                json.dump(pids, f)
                
            return jsonify({"status": "starting", "pid": proc.pid})
            
        elif action == "stop":
            pid = pids.get(s_id)
            if pid:
                import signal
                try:
                    os.kill(pid, signal.SIGTERM)
                    del pids[s_id]
                    with open(runtime_path, "w") as f:
                        json.dump(pids, f)
                    return jsonify({"status": "stopped"})
                except ProcessLookupError:
                    return jsonify({"status": "error", "message": "Process not found"}), 404
            return jsonify({"status": "error", "message": "No PID recorded for this server"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Running on 5001 to avoid conflict with standard Streamlit/Vite ports
    app.run(host='127.0.0.1', port=5001, debug=True)
