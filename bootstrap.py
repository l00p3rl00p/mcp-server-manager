#!/usr/bin/env python3
import os, sys, shutil, platform
from pathlib import Path

def get_mcp_tools_home():
    if platform.system() == "Windows":
        return Path(os.environ['USERPROFILE']) / ".mcp-tools"
    return Path.home() / ".mcp-tools"

def get_workspace_root():
    """Find workspace by looking for sibling repos."""
    current = Path(__file__).parent
    parent = current.parent
    siblings = ['mcp-injector', 'repo-mcp-packager', 'mcp-server-manager', 'mcp-link-library']
    found = [s for s in siblings if (parent / s).exists()]
    return parent if len(found) >= 2 else None

def detect_which_repo():
    return Path(__file__).parent.name

def ask_user_install_strategy():
    print("\n🚀 MCP Tools Suite Bootstrap")
    print("="*50)
    print(f"Current repo: {detect_which_repo()}")
    print(f"Central install: {get_mcp_tools_home()}")
    print("\nInstall strategy:")
    print("  [1] Full auto - Just do it all")
    print("  [2] Step by step - Ask each action")
    print("  [3] Manual - Exit")
    
    while True:
        choice = input("\nChoice [1/2/3]: ").strip()
        if choice in ['1','2','3']:
            return {'1':'full', '2':'step', '3':'manual'}[choice]

def ask(question):
    print(f"\n❓ {question}")
    while True:
        r = input("   [Y/n]: ").strip().lower()
        if r in ['y','yes','']: return True
        if r in ['n','no']: return False

def install_to_central(central, workspace):
    central.mkdir(parents=True, exist_ok=True)
    
    # Define our components
    repos = ['mcp-injector', 'repo-mcp-packager', 'mcp-server-manager', 'mcp-link-library']
    
    for repo in repos:
        source = workspace / repo
        target = central / repo
        
        if not source.exists():
            print(f"⚠️  Skipping {repo}: Not found in workspace")
            continue
            
        if target.exists():
            # If target exists, we update it by removing and re-copying
            # This is cleaner than merging for a "True to Itself" tool
            try:
                shutil.rmtree(target)
            except Exception as e:
                print(f"❌ Failed to remove existing {repo}: {e}")
                continue
        
        try:
            # Ignore __pycache__, .git, .venv, node_modules to keep it clean
            shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '.git', '.venv', 'node_modules', '.DS_Store'))
            print(f"✅ Installed {repo}")
        except Exception as e:
            print(f"❌ Failed to copy {repo}: {e}")

def main():
    if sys.version_info < (3,6):
        print("❌ Python 3.6+ required")
        sys.exit(1)
    
    workspace = get_workspace_root()
    if not workspace:
        print("❌ Cannot find workspace (need sibling repos)")
        sys.exit(1)
    
    strategy = ask_user_install_strategy()
    if strategy == 'manual':
        return
    
    central = get_mcp_tools_home()
    
    if strategy == 'full':
        install_to_central(central, workspace)
        print(f"\n✅ Complete! Tools at {central}")
    elif strategy == 'step':
        if ask("Install to central location?"): 
            install_to_central(central, workspace)

if __name__ == "__main__":
    main()
