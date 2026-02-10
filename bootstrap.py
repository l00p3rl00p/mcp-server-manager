#!/usr/bin/env python3
"""
Universal Bootstrapper for Git-Packager Workspace

This module enables any of the three Git-Packager repositories to act as a
complete installer/updater for the entire workspace. It implements a three-tier
resolution strategy:
  1. Local: Check if component exists in current project
  2. Sibling: Check if component exists in workspace sibling directory
  3. Remote: Offer to fetch from GitHub if missing

Design Philosophy:
- Entry Point Agnostic: Works from any repo (injector, manager, or packager)
- Explicit Opt-Out: Always prompts before remote fetches
- Zero Dependencies: Uses only Python stdlib (urllib, json, pathlib)
- Standalone Safe: Each tool remains 100% functional without siblings

Usage:
    python bootstrap.py                    # Interactive mode
    python bootstrap.py --headless         # Non-interactive (CI/CD)
    python bootstrap.py --check-only       # Just report status
"""

import sys
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


# GitHub repository configuration
GITHUB_ORG = "l00p3rl00p"
COMPONENTS = {
    "mcp-injector": {
        "repo": f"{GITHUB_ORG}/mcp-injector",
        "main_file": "mcp_injector.py",
        "description": "IDE config file manager (zero-dependency JSON injector)"
    },
    "mcp-server-manager": {
        "repo": f"{GITHUB_ORG}/mcp-server-manager",
        "main_file": "mcp_inventory/cli.py",
        "description": "MCP server discovery and inventory tool"
    },
    "repo-mcp-packager": {
        "repo": f"{GITHUB_ORG}/repo-mcp-packager",
        "main_file": "serverinstaller/install.py",
        "description": "Universal MCP server installer and packager"
    }
}


@dataclass
class ComponentStatus:
    """Status of a workspace component"""
    name: str
    found_local: bool
    found_sibling: bool
    sibling_path: Optional[Path]
    description: str


class WorkspaceResolver:
    """
    Resolves component locations using Local -> Sibling -> Remote strategy.
    
    This class is responsible for discovering where components exist in the
    workspace and offering to fetch missing ones from GitHub.
    """
    
    def __init__(self, current_dir: Path, headless: bool = False):
        """
        Initialize the resolver.
        
        Args:
            current_dir: The directory of the currently executing script
            headless: If True, skip all interactive prompts
        """
        self.current_dir = current_dir.resolve()
        self.headless = headless
        self.workspace_root = self._find_workspace_root()
    
    def _find_workspace_root(self) -> Path:
        """
        Find the workspace root by looking for sibling Git-Packager repos.
        
        Returns:
            Path to workspace root (parent of current repo)
        """
        # Check if we're in a Git-Packager repo by looking for known markers
        if (self.current_dir / "mcp_injector.py").exists():
            return self.current_dir.parent
        elif (self.current_dir / "mcp_inventory").exists():
            return self.current_dir.parent
        elif (self.current_dir / "serverinstaller").exists():
            return self.current_dir.parent
        
        # Default: assume current dir is workspace root
        return self.current_dir
    
    def identify_current_component(self) -> Optional[str]:
        """
        Identify which component we're currently running from.
        
        Returns:
            Component name or None if unknown
        """
        if (self.current_dir / "mcp_injector.py").exists():
            return "mcp-injector"
        elif (self.current_dir / "mcp_inventory").exists():
            return "mcp-server-manager"
        elif (self.current_dir / "serverinstaller").exists():
            return "repo-mcp-packager"
        return None
    
    def check_component(self, component_name: str) -> ComponentStatus:
        """
        Check if a component exists locally or in sibling directory.
        
        Args:
            component_name: Name of the component to check
            
        Returns:
            ComponentStatus with location information
        """
        config = COMPONENTS[component_name]
        main_file = config["main_file"]
        
        # Check local (current directory)
        found_local = (self.current_dir / main_file).exists()
        
        # Check sibling directory
        sibling_path = self.workspace_root / component_name
        found_sibling = (sibling_path / main_file).exists() if sibling_path.exists() else False
        
        return ComponentStatus(
            name=component_name,
            found_local=found_local,
            found_sibling=found_sibling,
            sibling_path=sibling_path if found_sibling else None,
            description=config["description"]
        )
    
    def check_all_components(self) -> Dict[str, ComponentStatus]:
        """
        Check status of all workspace components.
        
        Returns:
            Dict mapping component name to ComponentStatus
        """
        return {name: self.check_component(name) for name in COMPONENTS.keys()}
    
    def fetch_component(self, component_name: str, target_dir: Path) -> bool:
        """
        Fetch a component from GitHub using git clone.
        
        Args:
            component_name: Name of the component to fetch
            target_dir: Directory to clone into
            
        Returns:
            True if successful, False otherwise
        """
        import subprocess
        
        config = COMPONENTS[component_name]
        repo_url = f"https://github.com/{config['repo']}.git"
        
        print(f"\n📦 Fetching {component_name} from GitHub...")
        print(f"   URL: {repo_url}")
        print(f"   Target: {target_dir}")
        
        try:
            # Use git clone
            result = subprocess.run(
                ["git", "clone", repo_url, str(target_dir)],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✅ Successfully cloned {component_name}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to clone {component_name}")
            print(f"   Error: {e.stderr}")
            return False
        except FileNotFoundError:
            print(f"❌ Git not found. Please install git to fetch components.")
            return False


def print_status_report(statuses: Dict[str, ComponentStatus], current: Optional[str]):
    """
    Print a formatted status report of all components.
    
    Args:
        statuses: Dict of component statuses
        current: Name of current component (if known)
    """
    print("\n" + "="*60)
    print("Git-Packager Workspace Status".center(60))
    print("="*60 + "\n")
    
    if current:
        print(f"📍 Current Component: {current}\n")
    
    for name, status in statuses.items():
        marker = "🟢" if (status.found_local or status.found_sibling) else "⚪"
        current_marker = " ← YOU ARE HERE" if name == current else ""
        
        print(f"{marker} {name}{current_marker}")
        print(f"   {status.description}")
        
        if status.found_local:
            print(f"   ✓ Found in current directory")
        elif status.found_sibling:
            print(f"   ✓ Found in sibling: {status.sibling_path}")
        else:
            print(f"   ✗ Not found")
        print()


def interactive_bootstrap(resolver: WorkspaceResolver):
    """
    Run interactive bootstrap process.
    
    Args:
        resolver: WorkspaceResolver instance
    """
    current = resolver.identify_current_component()
    statuses = resolver.check_all_components()
    
    print_status_report(statuses, current)
    
    # Find missing components
    missing = [name for name, status in statuses.items() 
               if not (status.found_local or status.found_sibling)]
    
    if not missing:
        print("✅ All components are present in the workspace!")
        print("\nYou can use them together for enhanced functionality:")
        print("  • mcp-injector: Manage IDE configurations")
        print("  • mcp-server-manager: Discover and track MCP servers")
        print("  • repo-mcp-packager: Install and package MCP servers")
        return
    
    print(f"⚠️  Missing components: {', '.join(missing)}\n")
    print("Would you like to fetch the missing components from GitHub?")
    print("This will clone them as siblings in your workspace.\n")
    
    response = input("Fetch missing components? [y/N]: ").strip().lower()
    
    if response != 'y':
        print("\n❌ Bootstrap cancelled. Components remain standalone.")
        return
    
    # Fetch missing components
    success_count = 0
    for component_name in missing:
        target_dir = resolver.workspace_root / component_name
        
        if resolver.fetch_component(component_name, target_dir):
            success_count += 1
    
    print(f"\n📊 Bootstrap Summary: {success_count}/{len(missing)} components fetched")
    
    if success_count == len(missing):
        print("\n🎉 Workspace is now complete!")
        print("All three components are available and can work together.")


def main():
    """Main entry point for the bootstrapper."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Universal Bootstrapper for Git-Packager Workspace",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--headless", action="store_true", 
                       help="Non-interactive mode (skip prompts)")
    parser.add_argument("--check-only", action="store_true",
                       help="Only check status, don't fetch")
    
    args = parser.parse_args()
    
    # Initialize resolver
    current_dir = Path(__file__).parent.resolve()
    resolver = WorkspaceResolver(current_dir, headless=args.headless)
    
    if args.check_only:
        # Just print status and exit
        current = resolver.identify_current_component()
        statuses = resolver.check_all_components()
        print_status_report(statuses, current)
        return
    
    # Run interactive bootstrap
    interactive_bootstrap(resolver)


if __name__ == "__main__":
    main()
