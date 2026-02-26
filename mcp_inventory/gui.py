from __future__ import annotations
import http.server
import json
import logging
import os
import socketserver
import subprocess
import threading
from pathlib import Path
from typing import Optional
from typing import Any, Dict
from urllib.parse import urlparse

from .config import STATE_DIR, APP_DIR
from .logger import ACTIVE_LOGS_DIR
from .nexus_devlog import prune_devlogs, devlog_path, log_event

logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).parent / "web"

_ACTIVE_PROCS: dict[int, subprocess.Popen] = {}
_REAPER_STARTED = False

def _start_reaper() -> None:
    """
    Prevent ResourceWarnings by retaining spawned Popen handles and reaping them.
    """
    global _REAPER_STARTED
    if _REAPER_STARTED:
        return
    _REAPER_STARTED = True

    def _reap_loop():
        import time
        while True:
            try:
                dead = []
                for pid, proc in list(_ACTIVE_PROCS.items()):
                    rc = proc.poll()
                    if rc is not None:
                        try:
                            proc.wait(timeout=0.1)
                        except Exception:
                            pass
                        dead.append(pid)
                for pid in dead:
                    _ACTIVE_PROCS.pop(pid, None)
            except Exception:
                pass
            time.sleep(0.2)

    t = threading.Thread(target=_reap_loop, daemon=True)
    t.start()

def _maybe_devlog() -> Optional[Path]:
    # Best-effort shared devlog capture for GUI-triggered subprocess runs.
    # Enabled by default if writable; never blocks GUI.
    try:
        prune_devlogs(days=90)
        return devlog_path()
    except Exception:
        return None

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

        # API: Get Antigravity Config State
        if path == "/api/config_state":
            self.api_get_config_state()
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
            
        # API: Full State Aggregation (Optimization)
        if path == "/api/state/full":
            self.api_get_full_state()
            return

        # Serve Static Files
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # API: Toggle Server (Enable/Disable in Antigravity config)
        if path == "/api/toggle_server":
            self.api_toggle_server()
            return

        # API: Trigger Action (health/scan/etc)
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

        file_path = ACTIVE_LOGS_DIR / log_name
        if not file_path.exists():
            self.send_json_response({"lines": []})
            return

        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
            self.send_json_response({"lines": lines})
        except Exception as e:
            self.send_error(500, str(e))
    def api_get_config_state(self):
        """Fetch the current disabled/enabled state from Antigravity config."""
        config_path = Path.home() / ".gemini" / "antigravity" / "mcp_config.json"
        if not config_path.exists():
            self.send_json_response({"mcpServers": {}})
            return
        
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.send_json_response(config)
        except Exception as e:
            self.send_error(500, str(e))

    def api_toggle_server(self):
        """Enable or disable a server in the Antigravity mcp_config.json."""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length <= 0:
            self.send_error(400, "Missing payload")
            return

        try:
            raw_data = self.rfile.read(content_length)
            data = json.loads(raw_data)
            server_id = data.get("name")
            disabled = data.get("disabled")

            if server_id is None or disabled is None:
                self.send_error(400, f"Missing name or disabled state in {data}")
                return

            config_path = Path.home() / ".gemini" / "antigravity" / "mcp_config.json"
            if not config_path.exists():
                self.send_error(404, f"Config not found at {config_path}")
                return

            # Atomic read-modify-write
            config_text = config_path.read_text(encoding="utf-8")
            config = json.loads(config_text)
            
            if "mcpServers" not in config:
                config["mcpServers"] = {}
            
            if server_id not in config["mcpServers"]:
                self.send_error(404, f"Server {server_id} not found in config")
                return

            config["mcpServers"][server_id]["disabled"] = disabled
            config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

            log_event(_maybe_devlog(), "server_toggled", {"server": server_id, "disabled": disabled})
            self.send_json_response({"success": True, "message": f"Server {server_id} {'disabled' if disabled else 'enabled'}"})

        except Exception as e:
            self.send_error(500, str(e))

    def api_get_logs(self):
        try:
            logs = self._get_logs_internal(limit=100)
            self.send_json_response({"logs": logs})
        except Exception as e:
            self.send_error(500, str(e))

    def _get_system_status_data(self):
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
        
        return status

    def api_system_status(self):
        """Check for presence of Nexus components."""
        status = self._get_system_status_data()
        self.send_json_response(status)

    def api_get_full_state(self):
        """Aggregated endpoint for Zero-Token Optimization (1 call vs 5 calls)."""
        try:
            # 1. Config
            config_path = Path.home() / ".gemini" / "antigravity" / "mcp_config.json"
            config_data = {"mcpServers": {}}
            if config_path.exists():
                 try:
                    config_data = json.loads(config_path.read_text(encoding="utf-8"))
                 except: pass

            # 2. Filesystem State (Inventory & Health)
            inventory_data = {"entries": []}
            health_data = None
            
            inv_path = STATE_DIR / "inventory.json"
            if inv_path.exists():
                try: inventory_data = json.loads(inv_path.read_text(encoding="utf-8"))
                except: pass
                
            health_path = STATE_DIR / "health.json"
            if health_path.exists():
                try: health_data = json.loads(health_path.read_text(encoding="utf-8"))
                except: pass
            
            # 3. Logs (Limit 50)
            logs_data = self._get_logs_internal(limit=50)
            
            # 4. System Status
            system_status = self._get_system_status_data()
            
            full_state = {
                "configState": config_data,
                "inventory": inventory_data.get("entries", []),
                "health": health_data,
                "logs": logs_data,
                "system": system_status
            }
            self.send_json_response(full_state)
            
        except Exception as e:
            self.send_error(500, f"Aggregation failed: {e}")

    def _get_logs_internal(self, limit=100):
        parsed_logs = []
        log_file = ACTIVE_LOGS_DIR / "mcpinv.jsonl"
        
        if log_file.exists():
            try:
                lines = log_file.read_text(encoding="utf-8").splitlines()[-limit:]
                for line in lines:
                    try:
                        parsed_logs.append(json.loads(line))
                    except json.JSONDecodeError:
                        parsed_logs.append({"message": line, "level": "RAW"})
            except: pass
            
        # Librarian Logs
        lib_log_file = ACTIVE_LOGS_DIR / "librarian_errors.log"
        if lib_log_file.exists():
            try:
                lib_lines = lib_log_file.read_text(encoding="utf-8").splitlines()[-50:]
                for line in lib_lines:
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
                        except: pass
            except: pass
            
        # Sort
        parsed_logs.sort(key=lambda x: x.get("timestamp", ""))
        return parsed_logs

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
            action_log_path = ACTIVE_LOGS_DIR / f"action_{int(time.time())}.log"
            action_log_path.parent.mkdir(parents=True, exist_ok=True)
            devlog = _maybe_devlog()
            _start_reaper()
            
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
                        # SECURITY: avoid shell=True. Use `cmd.exe /c start ...` (start is a cmd builtin).
                        subprocess.run(["cmd", "/c", "start", "cmd", "/K", f"cd /d {root_dir}"])
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
                    # System Update: Update the suite via the Activator bootstrapper.
                    # (Avoids relying on a non-existent repo-mcp-packager/install.py.)
                    nexus_root = APP_DIR.parent
                    bootstrap = nexus_root / "repo-mcp-packager" / "bootstrap.py"
                    if not bootstrap.exists():
                        self.send_error(404, f"Activator bootstrap.py not found at {bootstrap}")
                        return
                    cmd = [sys.executable, str(bootstrap), "--repair"]

            else:
                cmd = [sys.executable, "-m", "mcp_inventory.cli", command]
            
            # Start process and pipe output to a file so it's accessible during/after
            with open(action_log_path, "w") as f:
                f.write(f"--- COMMAND: {' '.join(cmd)} ---\n")
                process = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, text=True)
                _ACTIVE_PROCS[process.pid] = process

            log_event(devlog, "gui_action_spawned", {"command": command, "cmd": cmd, "action_log": str(action_log_path), "pid": process.pid})
                
            response = {
                "success": True,
                "command": command,
                "action_log_name": action_log_path.name,
                "pid": process.pid
            }
            self.send_json_response(response)
            

        except Exception as e:
            self.send_error(500, f"Action failed: {e}")

    def send_json_response(self, data: Any):
        content = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(content)

def start_server(port: int = 8501):
    # Ensure WEB_DIR exists
    WEB_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVE_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    handler = MCPInvHandler
    # SECURITY: Bind only to local loopback to prevent external access
    _start_reaper()
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Serving GUI at http://localhost:{port} (Local Only)")
        httpd.serve_forever()


def create_server(port: int = 0) -> socketserver.TCPServer:
    """
    Create (but do not start) a GUI HTTP server. Used by E2E tests.
    """
    WEB_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVE_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    handler = MCPInvHandler

    class _ReuseTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    _start_reaper()
    return _ReuseTCPServer(("127.0.0.1", port), handler)
