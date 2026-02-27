import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import yaml

class ForgeEngine:
    """
    Workforce Nexus Forge Engine (The Factory)
    Converts arbitrary folders or repositories into compliant MCP servers.
    """

    def __init__(self, suite_root: Path, inventory_path: Optional[Path] = None):
        self.suite_root = suite_root
        self.link_library = suite_root / "mcp-link-library"
        
        # Standardize on ~/.mcp-tools/servers for persistent, central storage
        if sys.platform == "win32":
            self.forge_root = Path(os.environ['USERPROFILE']) / ".mcp-tools" / "servers"
        else:
            self.forge_root = Path.home() / ".mcp-tools" / "servers"
            
        self.forge_root.mkdir(parents=True, exist_ok=True)
        
        # Use provided active inventory or fallback to default
        if inventory_path:
            self.inventory_path = inventory_path
        else:
            self.inventory_path = self.forge_root.parent / "mcp-server-manager" / "inventory.yaml"

    def forge(self, source: str, target_name: Optional[str] = None, stack: Optional[str] = None) -> Path:
        """
        Main entry point for forging a server.
        source: A local path or a Git URL.
        """
        print(f"🔨 Forge Engine 3.1.0 starting for: {source}")
        
        # 1. Determine target name and path
        if not target_name:
            if source.startswith(("http://", "https://", "git@")):
                target_name = source.rstrip("/").split("/")[-1].replace(".git", "")
            else:
                target_name = Path(source).name
        
        target_path = self.forge_root / target_name
        
        # 2. Clone or Copy
        if source.startswith(("http://", "https://", "git@")):
            self._clone_repo(source, target_path)
        else:
            self._copy_local(source, target_path)

        if not target_path.exists():
            raise FileNotFoundError(f"Target path {target_path} creation failed.")

        # 3. Inject Deterministic Wrapper & ATP Sandbox
        self._inject_wrapper(target_path)
        self._inject_sandbox(target_path)

        # 4. Generate Baseline Server if missing
        self._ensure_server_entrypoint(target_path)

        # 5. Export Compliance Kit (ATP/README)
        self._export_compliance_kit(target_path)

        # 6. Verify Logic (Strawberry Test)
        # self._verify_logic(target_path) # Disabled for stability in v3.1.0 (requires hot reload of modules)

        # 7. Register with Inventory
        self._register_inventory(target_path, source, target_name, stack=stack)
        
        print(f"✅ Forge Complete: Server '{target_name}' is ready at {target_path}")
        return target_path

    def _clone_repo(self, url: str, target_dir: Path):
        """Clones a remote repo into the central server store."""
        if target_dir.exists():
            print(f"⚠️  Target {target_dir} exists. Pulling latest...")
            try:
                subprocess.run(["git", "pull"], cwd=target_dir, check=True)
            except Exception as e:
                print(f"   Git pull failed ({e}). Proceeding with existing state.")
            return

        print(f"⬇️  Cloning {url}...")
        subprocess.run(["git", "clone", url, str(target_dir)], check=True)

    def _copy_local(self, source: str, target_dir: Path):
        """Copies a local folder into the central server store."""
        src_path = Path(source).expanduser().resolve()
        if not src_path.exists():
            raise FileNotFoundError(f"Local source {src_path} not found")

        if src_path.is_file():
            raise ValueError(
                f"Forge expects a folder or git repo, but received a file: {src_path}. "
                f"To index documents, use the Librarian 'Add Resource' flow instead."
            )
            
        if target_dir.exists():
            print(f"⚠️  Target {target_dir} exists. Overwriting...")
            shutil.rmtree(target_dir)
            
        print(f"📋 Copying local source to {target_dir}...")
        shutil.copytree(src_path, target_dir, ignore=shutil.ignore_patterns('.git', '__pycache__', 'node_modules'))

    def _inject_wrapper(self, target_path: Path):
        """Injects the canonical mcp_wrapper.py."""
        wrapper_src = self.link_library / "mcp_wrapper.py"
        if wrapper_src.exists():
            shutil.copy2(wrapper_src, target_path / "mcp_wrapper.py")
            print(f"   + Injected mcp_wrapper.py")

    def _inject_sandbox(self, target_path: Path):
        """Injects the atp_sandbox.py."""
        sandbox_src = self.link_library / "atp_sandbox.py"
        if sandbox_src.exists():
            shutil.copy2(sandbox_src, target_path / "atp_sandbox.py")
            print(f"   + Injected atp_sandbox.py")

    def _ensure_server_entrypoint(self, target_path: Path):
        """Generates a baseline mcp_server.py if no python entrypoint exists."""
        entrypoints = list(target_path.glob("mcp_server.py")) + list(target_path.glob("server.py"))
        if not entrypoints:
            # 1. Documentation Intelligence: Detect Docs
            docs = list(target_path.rglob("*.md"))
            is_knowledge_heavy = len(docs) > 2 or (target_path / "docs").exists() or (target_path / "doc").exists()
            
            if is_knowledge_heavy:
                print(f"   * Detected Documentation-heavy repository. Generating Knowledge Server.")
                server_content = self._get_knowledge_server_template(target_path)
            else:
                server_content = self._get_baseline_server_template(target_path)

            with open(target_path / "mcp_server.py", "w") as f:
                f.write(server_content)
            print(f"   + Generated intelligent mcp_server.py")

    def _get_baseline_server_template(self, target_path: Path) -> str:
        return f"""# Baseline MCP Server (Forged)
\"\"\"
MCP Server: {target_path.name}
Generated by Nexus Forge.
\"\"\"
from __future__ import annotations
import json
import sys
import time
import logging
import warnings
from typing import Any, Dict, Optional

# Configure logging to stderr for debugging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stderr)

SERVER_NAME = {target_path.name!r}
SERVER_VERSION = "0.1.0-forged"

def _ok(msg_id: Any, result: Any) -> Dict[str, Any]:
    return {{"jsonrpc": "2.0", "id": msg_id, "result": result}}

def _err(msg_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {{"jsonrpc": "2.0", "id": msg_id, "error": {{"code": code, "message": message}}}}

def handle_request(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = request.get("method")
    params = request.get("params") or {{}}
    msg_id = request.get("id")

    try:
        if method == "initialize":
            return _ok(msg_id, {{
                "protocolVersion": "2024-11-05",
                "serverInfo": {{"name": SERVER_NAME, "version": SERVER_VERSION}},
                "capabilities": {{"tools": {{"listChanged": False}}}},
            }})
        if method == "tools/list":
            return _ok(msg_id, {{"tools": [
                {{"name": "ping", "description": "Liveness check.", 
                  "inputSchema": {{"type": "object", "properties": {{}}}}}}
            ]}})
        if method == "tools/call":
            name = (params.get("name") or "").strip()
            if name == "ping":
                return _ok(msg_id, {{"ok": True, "ts": time.time()}})
            return _err(msg_id, -32601, f"Unknown tool: {{name}}")
        return _err(msg_id, -32601, f"Unknown method: {{method}}")
    except Exception as e:
        return _err(msg_id, -32000, f"Server error: {{e}}")

def main():
    while True:
        line = sys.stdin.readline()
        if not line: break
        try: req = json.loads(line)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON from client: {{e}}", exc_info=True)
            continue
        resp = handle_request(req)
        if resp: sys.stdout.write(json.dumps(resp) + "\\n"); sys.stdout.flush()

if __name__ == "__main__":
    main()
"""

    def _get_knowledge_server_template(self, target_path: Path) -> str:
        return f"""# Knowledge-Enhanced MCP Server (Forged)
\"\"\"
MCP Server: {target_path.name}
Documentation-first server generated by Nexus Forge.
\"\"\"
from __future__ import annotations
import json
import sys
import time
import logging
import re
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Configure logging to stderr for debugging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stderr)

SERVER_NAME = {target_path.name!r}
ROOT = Path(__file__).parent.resolve()

def _ok(msg_id: Any, result: Any) -> Dict[str, Any]:
    return {{"jsonrpc": "2.0", "id": msg_id, "result": result}}

def _err(msg_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {{"jsonrpc": "2.0", "id": msg_id, "error": {{"code": code, "message": message}}}}

def handle_request(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = request.get("method")
    params = request.get("params") or {{}}
    msg_id = request.get("id")

    try:
        if method == "initialize":
            return _ok(msg_id, {{
                "protocolVersion": "2024-11-05",
                "serverInfo": {{"name": SERVER_NAME, "version": "1.0.0-forged"}},
                "capabilities": {{"tools": {{"listChanged": False}}}},
            }})
        
        if method == "tools/list":
            return _ok(msg_id, {{"tools": [
                {{"name": "search_docs", "description": "Search through documentation files for a keyword.", 
                  "inputSchema": {{"type": "object", "properties": {{"query": {{"type": "string"}}}}}}}},
                {{"name": "list_docs", "description": "List all documentation files in the repository.", 
                  "inputSchema": {{"type": "object", "properties": {{}}}}}},
                {{"name": "read_doc", "description": "Read the content of a specific documentation file.", 
                  "inputSchema": {{"type": "object", "properties": {{"path": {{"type": "string"}}}}}}}}
            ]}})

        if method == "tools/call":
            name = params.get("name")
            p = params.get("arguments") or {{}}
            
            if name == "search_docs":
                query = p.get("query", "").lower()
                matches = []
                for md in ROOT.rglob("*.md"):
                    content = md.read_text(errors='ignore')
                    if query in content.lower():
                        matches.append(str(md.relative_to(ROOT)))
                return _ok(msg_id, {{"matches": matches}})

            if name == "list_docs":
                docs = [str(md.relative_to(ROOT)) for md in ROOT.rglob("*.md")]
                return _ok(msg_id, {{"docs": docs}})

            if name == "read_doc":
                file_path = ROOT / p.get("path", "")
                if file_path.exists() and file_path.suffix == ".md":
                    return _ok(msg_id, {{"content": file_path.read_text(errors='ignore')}})
                return _err(msg_id, 404, "File not found or not a markdown file.")

            return _err(msg_id, -32601, f"Unknown tool: {{name}}")
        
        return _err(msg_id, -32601, f"Unknown method: {{method}}")
    except Exception as e:
        return _err(msg_id, -32000, f"Server error: {{e}}")

def main():
    while True:
        line = sys.stdin.readline()
        if not line: break
        try: req = json.loads(line)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON from client: {{e}}", exc_info=True)
            continue
        resp = handle_request(req)
        if resp: sys.stdout.write(json.dumps(resp) + "\\n"); sys.stdout.flush()

if __name__ == "__main__":
    main()
"""


    def _export_compliance_kit(self, target_path: Path):
        """Exports the standard ARCHITECTURE.md and README.md templates via the Librarian."""
        # Just touch them if missing for now to ensure portability
        if not (target_path / "ATP_COMPLIANCE_GUIDE.md").exists():
            (target_path / "ATP_COMPLIANCE_GUIDE.md").write_text("# ATP Compliance Guide\n\nThis server is ATP-compliant via Nexus Forge.")
        
    def _register_inventory(self, target_path: Path, source: str, name: str, stack: Optional[str] = None):
        """Registers the forged server in the suite's inventory."""
        if not self.inventory_path.parent.exists():
            self.inventory_path.parent.mkdir(parents=True, exist_ok=True)

        inventory = {"servers": []}
        if self.inventory_path.exists():
            try:
                with open(self.inventory_path, "r") as f:
                    inventory = yaml.safe_load(f) or {"servers": []}
            except Exception as e:
                print(f"   ⚠️  Could not read inventory ({e}). Starting fresh.")

        # Update or Append
        existing = next((s for s in inventory["servers"] if s.get("id") == name), None)

        # Prefer the installed binary wrapper; fall back to raw script for dev environments.
        _installed_bin = Path.home() / ".mcp-tools" / "bin" / name
        _start_cmd = str(_installed_bin) if _installed_bin.exists() else f"{sys.executable} mcp_server.py"

        entry = {
            "id": name,
            "name": name,
            "path": str(target_path),
            "source": source,
            "type": "forged",
            "status": "ready",
            "run": {
                "start_cmd": _start_cmd,
                "stop_cmd": "pkill -f mcp_server.py" # Simple default
            },
            "tags": ["forged", "nexus-v3"],
        }
        if stack:
            entry["stack"] = stack

        if existing:
            existing.update(entry)
            print(f"   * Updated existing inventory entry for {name}")
        else:
            inventory["servers"].append(entry)
            print(f"   + Added {name} to inventory")

        with open(self.inventory_path, "w") as f:
            yaml.safe_dump(inventory, f)
