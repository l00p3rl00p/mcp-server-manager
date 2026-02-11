from __future__ import annotations
import http.server
import json
import logging
import socketserver
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

from .config import STATE_DIR, APP_DIR, LOGS_DIR

logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).parent / "web"

class MCPInvHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # API: Get State
        if path.startswith("/api/state/"):
            resource = path[len("/api/state/"):]
            self.api_get_state(resource)
            return
        
        # API: Get Specific Action Log
        if path.startswith("/api/logs/"):
            log_name = path[len("/api/logs/"):]
            self.api_get_specific_log(log_name)
            return

        # API: Get Logs
        if path == "/api/logs":
            self.api_get_logs()
            return

        # API: System Status
        if path == "/api/system_status":
            self.api_system_status()
            return

        # Serve Static Files
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # API: Trigger Action
        if path.startswith("/api/action/"):
            command = path[len("/api/action/"):]
            self.api_trigger_action(command)
            return

        self.send_error(404, "Not Found")

    def api_get_state(self, resource: str):
        # Prevent traversal
        if ".." in resource or "/" in resource:
            self.send_error(400, "Bad Request")
            return

        file_path = STATE_DIR / f"{resource}.json"
        if not file_path.exists():
            self.send_error(404, f"State not found: {resource}")
            return

        try:
            content = file_path.read_text(encoding="utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        except Exception as e:
            self.send_error(500, str(e))

    def api_get_specific_log(self, log_name: str):
        # Prevent traversal
        if ".." in log_name or "/" in log_name:
            self.send_error(400, "Bad Request")
            return

        file_path = LOGS_DIR / log_name
        if not file_path.exists():
            self.send_json_response({"lines": []})
            return

        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
            self.send_json_response({"lines": lines})
        except Exception as e:
            self.send_error(500, str(e))

    def api_get_logs(self):
        # Read latest lines from the log file
        log_file = LOGS_DIR / "mcpinv.jsonl"
        if not log_file.exists():
             self.send_json_response({"logs": []})
             return

        try:
            # Read last 100 lines (naive approach)
            lines = log_file.read_text(encoding="utf-8").splitlines()[-100:]
            # Wrap in checking if they are valid json
            parsed_logs = []
            for line in lines:
                try:
                    parsed_logs.append(json.loads(line))
                except json.JSONDecodeError:
                    parsed_logs.append({"message": line, "level": "RAW"})
            
            # Read Librarian logs
            lib_log_file = LOGS_DIR / "librarian_errors.log"
            if lib_log_file.exists():
                lib_lines = lib_log_file.read_text(encoding="utf-8").splitlines()[-50:] # Last 50 errors
                for line in lib_lines:
                    # Format: [ISO_TIMESTAMP] Message
                    if line.startswith("["):
                        try:
                            ts_end = line.find("]")
                            if ts_end != -1:
                                ts = line[1:ts_end]
                                msg = line[ts_end+1:].strip()
                                parsed_logs.append({
                                    "timestamp": ts,
                                    "level": "ERROR",
                                    "message": f"[Librarian] {msg}",
                                    "source": "librarian"
                                })
                        except:
                            pass

            # Sort by timestamp
            def parse_ts(entry):
                return entry.get("timestamp", "")
            
            parsed_logs.sort(key=parse_ts)
            
            self.send_json_response({"logs": parsed_logs})
        except Exception as e:
            self.send_error(500, str(e))

    def api_system_status(self):
        """Check for presence of Nexus components."""
        import sys
        import os
        from pathlib import Path
        
        status = {
            "observer": True, # Self
            "librarian": False,
            "injector": False,
            "activator": False
        }
        
        # Locate Nexus Root
        if sys.platform == "win32":
            nexus_root = Path(os.environ['USERPROFILE']) / ".mcp-tools"
        else:
            nexus_root = Path.home() / ".mcp-tools"
            
        # Check components (Heartbeat)
        def check_heartbeat(path, args=["--help"]):
            try:
                # Active check: Run the tool with --help to verify it loads and runs
                subprocess.run(
                    [sys.executable, str(path)] + args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=1,
                    check=True
                )
                return True
            except Exception:
                return False

        # Librarian
        lib_path = nexus_root / "mcp-link-library" / "mcp.py"
        if lib_path.exists():
            status["librarian"] = check_heartbeat(lib_path)
            
        # Injector
        inj_path = nexus_root / "mcp-injector" / "mcp_injector.py"
        if inj_path.exists():
            status["injector"] = check_heartbeat(inj_path)
            
        # Activator
        act_path = nexus_root / "repo-mcp-packager" / "bootstrap.py"
        if act_path.exists():
            status["activator"] = check_heartbeat(act_path)
            
        self.send_json_response(status)

    def api_trigger_action(self, command: str):
        # Allowed commands whitelist for security
        # Allowed commands whitelist for security
        ALLOWED_COMMANDS = ["scan", "health", "running", "update", "attach", "terminal"]
        
        if command not in ALLOWED_COMMANDS:
            self.send_error(403, "Command not allowed")
            return

        # For update, we need a server_id or path
        server_id = None
        server_path = None
        
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            try:
                post_data = json.loads(self.rfile.read(content_length))
                server_id = post_data.get("server_id")
                server_path = post_data.get("path")
                
                # SECURITY: Validate path injection
                if server_path:
                    p = Path(server_path).resolve()
                    if not p.exists():
                        self.send_error(400, "Invalid server path")
                        return
                    server_path = str(p)
            except:
                pass

        # Run in a separate thread/process to not block server
        # For simplicity, we run blocking here but ideally this should be async or backgrounded
        # Triggering the CLI command via checking main? Or just subprocess
        try:
            # Decide on the command to run
            import sys
            import time
            import os
            from .config import LOGS_DIR
            
            action_log_path = LOGS_DIR / f"action_{int(time.time())}.log"
            
            if command == "attach":
                # Locate mcp-injector in Nexus
                if sys.platform == "win32":
                    injector = Path(os.environ['USERPROFILE']) / ".mcp-tools" / "mcp-injector" / "mcp_injector.py"
                else:
                    injector = Path.home() / ".mcp-tools" / "mcp-injector" / "mcp_injector.py"
                
                if not injector.exists():
                    self.send_error(404, f"mcp-injector not found at {injector}")
                    return

                # Run recursively to attach all known servers
                cmd = [sys.executable, str(injector), "--recursive"]
            
            elif command == "terminal":
                # Open system terminal at ~/.mcp-tools
                # We return immediately because this is a GUI action, not a long-running CLI process we stream
                root_dir = APP_DIR.parent
                try:
                    if sys.platform == "darwin":
                        subprocess.run(["open", "-a", "Terminal", str(root_dir)])
                    elif sys.platform == "win32":
                        # Open new cmd window
                        subprocess.run(["start", "cmd", "/K", f"cd /d {root_dir}"], shell=True)
                    else:
                        # Linux/other - simplified fallback
                        subprocess.run(["x-terminal-emulator", "--working-directory", str(root_dir)])
                    
                    self.send_json_response({"success": True, "message": "Terminal opened"})
                    return
                except Exception as e:
                    self.send_error(500, f"Failed to open terminal: {e}")
                    return

            elif command == "update":
                if server_path:
                     # Update specific server
                    installer = Path(server_path) / "serverinstaller" / "install.py"
                    if not installer.exists():
                        installer = Path(server_path) / "install.py"
                    
                    if not installer.exists():
                        self.send_error(400, f"No installer found in {server_path}")
                        return
                    
                    cmd = [sys.executable, str(installer), "--update", "--machine", "--headless"]
                else:
                    # System Update: Update the Packager itself (and thus the suite)
                    packager = APP_DIR.parent / "repo-mcp-packager" / "install.py"
                    if not packager.exists():
                        self.send_error(404, "Packager not found for system update")
                        return
                    cmd = [sys.executable, str(packager), "--update", "--machine", "--headless"]

            else:
                cmd = [sys.executable, "-m", "mcp_inventory.cli", command]
            
            # Start process and pipe output to a file so it's accessible during/after
            with open(action_log_path, "w") as f:
                f.write(f"--- COMMAND: {' '.join(cmd)} ---\n")
                process = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, text=True)
                
            response = {
                "success": True,
                "command": command,
                "action_log_name": action_log_path.name,
                "pid": process.pid
            }
            self.send_json_response(response)
            
        except Exception as e:
            self.send_error(500, str(e))

    def send_json_response(self, data: Any):
        content = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(content)

def start_server(port: int = 8501):
    # Ensure WEB_DIR exists
    WEB_DIR.mkdir(parents=True, exist_ok=True)
    
    # If no index.html, create a placeholder
    if not (WEB_DIR / "index.html").exists():
        (WEB_DIR / "index.html").write_text("<h1>MCP Inventory GUI Placeholder</h1>")

    handler = MCPInvHandler
    # SECURITY: Bind only to local loopback to prevent external access
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Serving GUI at http://localhost:{port} (Local Only)")
        httpd.serve_forever()
