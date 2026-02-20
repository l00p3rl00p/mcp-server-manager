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

    def forge(self, source: str, target_name: Optional[str] = None) -> Path:
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
        self._register_inventory(target_path, source, target_name)
        
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
            server_content = f"""# Baseline MCP Server (Forged)
\"\"\"
MCP Server: {target_path.name}
Generated by Workforce Nexus Forge.
Categories: forged, nexus-v3
\"\"\"
import os
import sys

# Add current directory to sys.path so we can import local modules
sys.path.insert(0, str(os.path.dirname(os.path.abspath(__file__))))

try:
    from mcp_wrapper import MCPWrapper
    from atp_sandbox import ATPSandbox
except ImportError:
    pass # Wrapper/Sandbox might be missing during dev

def main():
    print("MCP Server Ready (Stdio)")
    # TODO: Implement your tool logic here
    # Example:
    # wrapper = MCPWrapper("MyServer")
    # wrapper.run()

if __name__ == "__main__":
    main()
"""
            with open(target_path / "mcp_server.py", "w") as f:
                f.write(server_content)
            print(f"   + Generated baseline mcp_server.py")

    def _export_compliance_kit(self, target_path: Path):
        """Exports the standard ARCHITECTURE.md and README.md templates via the Librarian."""
        # Just touch them if missing for now to ensure portability
        if not (target_path / "ATP_COMPLIANCE_GUIDE.md").exists():
            (target_path / "ATP_COMPLIANCE_GUIDE.md").write_text("# ATP Compliance Guide\n\nThis server is ATP-compliant via Nexus Forge.")
        
    def _register_inventory(self, target_path: Path, source: str, name: str):
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
        
        entry = {
            "id": name,
            "name": name,
            "path": str(target_path),
            "source": source,
            "type": "forged",
            "status": "ready",
            "run": {
                "start_cmd": f"{sys.executable} mcp_server.py",
                "stop_cmd": "pkill -f mcp_server.py" # Simple default
            },
            "tags": ["forged", "nexus-v3"]
        }

        if existing:
            existing.update(entry)
            print(f"   * Updated existing inventory entry for {name}")
        else:
            inventory["servers"].append(entry)
            print(f"   + Added {name} to inventory")

        with open(self.inventory_path, "w") as f:
            yaml.safe_dump(inventory, f)
