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
        
        # API: Get Logs
        if path == "/api/logs":
            self.api_get_logs()
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
            
            self.send_json_response({"logs": parsed_logs})
        except Exception as e:
            self.send_error(500, str(e))

    def api_trigger_action(self, command: str):
        # Allowed commands whitelist for security
        ALLOWED_COMMANDS = ["scan", "health", "running"]
        
        if command not in ALLOWED_COMMANDS:
            self.send_error(403, "Command not allowed")
            return

        # Run in a separate thread/process to not block server
        # For simplicity, we run blocking here but ideally this should be async or backgrounded
        # Triggering the CLI command via checking main? Or just subprocess
        try:
            # We call the CLI via subprocess to ensure full environment is used
            # Assuming 'mcpinv' is in path, or use sys.executable
            import sys
            cmd = [sys.executable, "-m", "mcp_inventory.cli", command]
            
            # Reset args if needed? No, subprocess.run is fresh.
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            response = {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": command
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
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Serving GUI at http://localhost:{port}")
        httpd.serve_forever()
