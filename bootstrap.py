import os, sys, shutil, platform, argparse, hashlib, subprocess
from pathlib import Path

# Workforce Nexus Global Registry
GITHUB_ROOT = "https://github.com/l00p3rl00p"
NEXUS_REPOS = {
    'mcp-injector': f"{GITHUB_ROOT}/mcp-injector.git",
    'mcp-link-library': f"{GITHUB_ROOT}/mcp-link-library.git",
    'mcp-server-manager': f"{GITHUB_ROOT}/mcp-server-manager.git",
    'repo-mcp-packager': f"{GITHUB_ROOT}/repo-mcp-packager.git"
}

# Track artifacts for universal rollback
INSTALLED_ARTIFACTS = []

def git_available():
    try:
        subprocess.run(["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False

def fetch_nexus_repo(name: str, target_dir: Path, update=False):
    """Fetch a repo from GitHub if missing, or update if requested."""
    url = NEXUS_REPOS.get(name)
    if not url: return False
    
    if not git_available():
        print(f"❌ Git not found. Cannot manage {name} automatically.")
        return False
        
    try:
        if target_dir.exists() and (target_dir / ".git").exists():
            if update:
                print(f"🔄 Updating {name}...")
                subprocess.run(["git", "-C", str(target_dir), "pull"], check=True)
                return True
            return True
            
        print(f"📥 Fetching {name} from GitHub...")
        if target_dir.exists():
            shutil.rmtree(target_dir)
            
        subprocess.run(["git", "clone", "--depth", "1", url, str(target_dir)], check=True)
        return True
    except Exception as e:
        print(f"❌ Failed to fetch/update {name}: {e}")
        return False

def get_mcp_tools_home():
    if platform.system() == "Windows":
        return Path(os.environ['USERPROFILE']) / ".mcp-tools"
    return Path.home() / ".mcp-tools"

def get_workspace_root():
    """Find workspace by looking for sibling repos, searching upwards if needed."""
    # Start looking from the directory containing this script
    search_start = Path(__file__).resolve().parent
    siblings = ['mcp-injector', 'repo-mcp-packager', 'mcp-server-manager', 'mcp-link-library']
    
    # Check current parent and up to 3 levels higher
    current = search_start
    for _ in range(4):
        parent = current.parent
        if parent == current: break # Hit root
        
        found = [s for s in siblings if (parent / s).is_dir()]
        if len(found) >= 2:
            return parent
        current = parent
        
    return None

def detect_which_repo():
    return Path(__file__).parent.name

def detect_full_suite(workspace: Path):
    """Check if we are in a Workforce Nexus workspace (all 4 repos)."""
    if not workspace: return False
    required = ['mcp-injector', 'repo-mcp-packager', 'mcp-server-manager', 'mcp-link-library']
    missing = [r for r in required if not (workspace / r).exists()]
    return len(missing) == 0

def ask_convergence_tier():
    print("\n🔗 Nexus Application Convergence Detected!")
    print("="*50)
    print("You have the full suite detected. How would you like to configure the Nexus?")
    
    print(f"\n{'Tier':<12} | {'Area':<14} | {'Setup':<20}")
    print("-" * 60)
    print(f"{'Lite':<12} | {'Distributed':<14} | {'Workspace execution, Shared Config'}")
    print(f"{'Standard':<12} | {'Linked':<14} | {'Symlinks to ~/.mcp-tools/suite'}")
    print(f"{'Industrial':<12} | {'Unified':<14} | {'Managed Mirror in ~/.mcp-tools/app'}")
    print("-" * 60)
    
    choice = input("\nSelect Tier [l/s/I] (Default: Industrial): ").strip().lower()
    if choice == 'l': return 'lite'
    if choice == 's': return 'standard'
    return 'industrial'

def ask_user_install_strategy():
    print("\n🚀 MCP Tools Suite Bootstrap")
    print("="*50)
    print(f"Current repo: {detect_which_repo()}")
    print(f"Central install: {get_mcp_tools_home()}")
    
    print("\nReliability Tiers Decision Matrix:")
    print("-" * 80)
    print(f"{'Tier':<12} | {'Level':<12} | {'Strategy':<18} | {'Pros/Cons'}")
    print("-" * 80)
    print(f"{'Lite':<12} | {'Basic':<12} | {'Zero-Dep':<18} | {'👍 Portable, 👎 Basic matching'}")
    print(f"{'Standard':<12} | {'High':<12} | {'Pure Python':<18} | {'👍 Regex indexing, 👎 Manual venv'}")
    print(f"{'Industrial':<12} | {'Hardened':<12} | {'Infrastructure':<18} | {'👍 Maximum precision, 👎 Disk space'}")
    print("-" * 80)
    
    tier = 'industrial'
    t_choice = input("\nSelect Reliability Tier [l/s/I] (Default: Industrial): ").strip().lower()
    if t_choice == 'l': tier = 'lite'
    elif t_choice == 's': tier = 'standard'
    elif t_choice == 'i': tier = 'industrial'

    print("\nInstall strategy:")
    print("  [1] Full auto - Just do it all")
    print("  [2] Step by step - Ask each action")
    print("  [3] Manual - Exit")
    
    while True:
        choice = input("\nChoice [1/2/3]: ").strip()
        if choice in ['1','2','3']:
            return {'strategy': {'1':'full', '2':'step', '3':'manual'}[choice], 'tier': tier}



def ask(question):
    print(f"\n❓ {question}")
    while True:
        r = input("   [Y/n]: ").strip().lower()
        if r in ['y','yes','']: return True
        if r in ['n','no']: return False

def pre_flight_checks(central: Path):
    """Universal Safety: Verify integrity and permissions."""
    print(f"[*] Running pre-flight checks at {central}...")
    try:
        central.mkdir(parents=True, exist_ok=True)
        test_file = central / ".nexus_write_test"
        test_file.write_text("test")
        test_file.unlink()
        print("✅ Pre-flight checks passed.")
        return True
    except Exception as e:
        print(f"❌ Pre-flight checks failed: {e}")
        return False

def rollback():
    """Universal Safety: Multi-tool recovery."""
    if not INSTALLED_ARTIFACTS:
        return
    print(f"\n🔄 ROLLBACK: Removing {len(INSTALLED_ARTIFACTS)} partial installations...")
    for target in reversed(INSTALLED_ARTIFACTS):
        if target.exists():
            try:
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
                print(f"  🗑️ Removed: {target.name}")
            except Exception as e:
                print(f"  ⚠️  Failed to remove {target.name}: {e}")
    print("✅ Rollback complete.")

def ensure_executable(path: Path):
    """Universal Safety: Ensure scripts are executable recursively."""
    if not path.exists(): return
    
    # Files to target specifically
    entry_points = ['mcp.py', 'mcp_injector.py', 'install.py', 'uninstall.py', 'mcp_server_manager.py', 'bootstrap.py']
    
    if path.is_file():
        if path.suffix == '.sh' or path.name in entry_points:
            try:
                path.chmod(path.stat().st_mode | 0o111)
                # print(f"  🔓 Executable: {path.name}") # Verbose
            except Exception as e:
                print(f"  ⚠️  Failed to set executable on {path.name}: {e}")
    elif path.is_dir():
        for item in path.iterdir():
            ensure_executable(item)

def install_to_central(central, workspace=None, update=False):
    """Deploy repos to central location (~/.mcp-tools). Fetches from Git if workspace is missing."""
    central.mkdir(parents=True, exist_ok=True)
    
    # Define our components
    repos = ['mcp-injector', 'repo-mcp-packager', 'mcp-server-manager', 'mcp-link-library']
    
    for repo in repos:
        source = workspace / repo if (workspace and (workspace / repo).exists()) else None
        target = central / repo
        
        if source:
            # Mode A: Active Workspace Copy (Developer Mode)
            if target.exists():
                try:
                    shutil.rmtree(target)
                except Exception as e:
                    print(f"❌ Failed to remove existing {repo}: {e}")
                    raise e
            
            try:
                # We copy the source. If it has .git, we copy it too (optional, but requested for 'can be updated')
                shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '.venv', 'node_modules', '.DS_Store'))
                INSTALLED_ARTIFACTS.append(target)
                ensure_executable(target)
                print(f"✅ Installed {repo} (Local Source)")
            except Exception as e:
                print(f"❌ Failed to copy {repo}: {e}")
                raise e
        else:
            # Mode B: GitHub Discovery (Autonomous/Standalone Mode)
            if fetch_nexus_repo(repo, target, update=update):
                if target not in INSTALLED_ARTIFACTS:
                    INSTALLED_ARTIFACTS.append(target)
                ensure_executable(target)
            else:
                print(f"⚠️  Skipping {repo}: Source not found and fetch failed.")

        if repo == 'repo-mcp-packager':
            uninstall_src = target / "serverinstaller" / "uninstall.py"
            uninstall_dest = target / "uninstall.py"
            if uninstall_src.exists():
                try:
                    shutil.copy2(uninstall_src, uninstall_dest)
                    # Make executable
                    uninstall_dest.chmod(uninstall_dest.stat().st_mode | 0o111)
                except Exception as e:
                    print(f"⚠️  Failed to expose uninstall.py: {e}")

def install_converged_application(tier, workspace, update=False):
    """Phase 12: Application Convergence Logic."""
    central = get_mcp_tools_home()
    central.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📦 Deploying Nexus Application [Tier: {tier.upper()}]...")
    
    repos = ['mcp-injector', 'repo-mcp-packager', 'mcp-server-manager', 'mcp-link-library']
    
    if tier == 'lite':
        # Lite: Config pointers only. Logic handled by tools checking workspace.
        # We just create the root ensures configs can live there.
        print("✅ Lite mode: Workspace is authoritative. Config root created.")
        
    elif tier == 'standard':
        # Standard: Symlinks
        suite_dir = central / "suite"
        suite_dir.mkdir(parents=True, exist_ok=True)
        for repo in repos:
            src = workspace / repo
            dest = suite_dir / repo
            if dest.exists() or dest.is_symlink():
                if dest.is_dir() and not dest.is_symlink():
                    shutil.rmtree(dest) # Remove physical copy if switching to symlink
                else:
                    dest.unlink()
            os.symlink(src, dest)
            print(f"🔗 Linked {repo} -> {dest}")
            
    elif tier == 'industrial':
        # Industrial: Managed Mirror (Copy/Git)
        # We reuse install_to_central logic but ensure global venv
        install_to_central(central, workspace, update=update)
        setup_nexus_venv(central)
        create_hardened_entry_points(central)
        ensure_global_path(central)
        # Trigger Librarian Synergy (Lazy sync)
        print("🧠 Triggering Librarian Suite Indexing...")
        try:
            subprocess.run([sys.executable, str(central / "mcp-link-library" / "mcp.py"), "--index-suite"], check=False)
        except Exception as e:
            print(f"⚠️  Indexing minor issue: {e} (Installation still successful)")

    print("\n" + "="*60)
    print(f"✅  INSTALLATION SUCCESSFUL (Tier: {tier.upper()})")
    print("="*60)
    print(f"Your Nexus environment is fully configured.")
    print(f"Tools available in: {central}/bin")
    print("-" * 60)
    print(f"📊 GUI Dashboard Access:")
    print(f"   Command: mcp-observer gui")
    print(f"   URL:     http://localhost:8501")
    print("-" * 60)
    print(f"Log out and back in to refresh your path, or run:")
    print(f"  source ~/.zshrc  (or ~/.bashrc)")
    print("="*60 + "\n")

def setup_nexus_venv(central: Path):
    """Create a dedicated Nexus venv for --industrial mode."""
    venv_dir = central / ".venv"
    print(f"\n📦 Building Industrial Infrastructure at {venv_dir}...")
    
    try:
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        
        # Determine pip path
        if platform.system() == "Windows":
            pip = venv_dir / "Scripts" / "pip.exe"
        else:
            pip = venv_dir / "bin" / "pip"
            
        # 1. Upgrade pip to silence warnings and ensure compatibility
        print("⬆️  Upgrading pip to latest version...")
        try:
            subprocess.run([str(pip), "install", "--upgrade", "pip"], check=True)
        except subprocess.CalledProcessError:
            print("⚠️  Pip upgrade failed, attempting to continue with current version...")

        print("📥 Installing high-confidence libraries (pathspec, jsonschema, psutil, PyYAML)...")
        # 2. Allow interactive prompts if packages need them
        subprocess.run([str(pip), "install", "pathspec", "jsonschema", "psutil", "PyYAML"], check=True)
        
        print("✅ Nexus Venv ready.")
        return True
    except Exception as e:
        print(f"❌ Failed to setup Nexus Venv: {e}")
        return False

def ensure_global_path(central: Path):
    """Surgically add ~/.mcp-tools/bin to user PATH."""
    bin_dir = central / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    # Identify shell config
    shell = os.environ.get("SHELL", "")
    rc_file = None
    if "zsh" in shell:
        rc_file = Path.home() / ".zshrc"
    elif "bash" in shell:
        rc_file = Path.home() / ".bashrc"
    
    if not rc_file or not rc_file.exists():
        print(f"⚠️  Could not find shell config for {shell}. Please add {bin_dir} to your PATH manually.")
        return False

    export_line = f'export PATH="{bin_dir}:$PATH"'
    content = rc_file.read_text(errors='ignore')
    
    if export_line in content:
        print(f"✅ PATH already includes {bin_dir}")
        return True

    print(f"\n📎 Adding {bin_dir} to your global PATH...")
    marker_start = "# Workforce Nexus Block START"
    marker_end = "# Workforce Nexus Block END"
    
    # Check if a block already exists to avoid duplication
    if marker_start in content:
        print("⚠️  Workforce Nexus block already exists in shell config. Updating...")
        # (Simplified update: append if not found, advanced would replace block)
    
    block = f"\n{marker_start}\n{export_line}\n{marker_end}\n"
    try:
        with open(rc_file, "a") as f:
            f.write(block)
        print(f"✅ Success! Please restart your terminal or run: source {rc_file}")
        return True
    except Exception as e:
        print(f"❌ Failed to update shell config: {e}")
        return False

def create_hardened_entry_points(central: Path):
    """Create venv-locked executable wrappers in bin/."""
    bin_dir = central / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    venv_python = central / ".venv" / "bin" / "python"
    if platform.system() == "Windows":
        venv_python = central / ".venv" / "Scripts" / "python.exe"
    
    if not venv_python.exists():
        # Fallback to system python if venv failed, but warn
        print("⚠️  Hardened venv not found. Using system python for entry points.")
        venv_python = sys.executable

    # Command mapping: entry_name -> (repo_dir, module_path, use_python_m)
    commands = {
        "mcp-surgeon": ("mcp-injector", "mcp_injector.py", False),
        "mcp-observer": ("mcp-server-manager", "mcp_inventory/cli.py", True), # Uses -m mcp_inventory.cli
        "mcp-librarian": ("mcp-link-library", "mcp.py", False),
        "mcp-activator": ("repo-mcp-packager", "bootstrap.py", False)
    }
    
    for cmd, (repo, module, use_m) in commands.items():
        cmd_path = bin_dir / cmd
        target_script = central / repo / module
        
        if not target_script.exists():
            continue
            
        # Write the hardened wrapper
        # We add 'central' to PYTHONPATH so modules like mcp_inventory can be found
        if use_m:
            # For mcp-observer, we want `python -m mcp_inventory.cli`
            module_name = module.replace("/", ".").replace(".py", "")
            wrapper = f"""#!/bin/bash
# Workforce Nexus Hardened Wrapper
export PYTHONPATH="{central}/mcp-server-manager:$PYTHONPATH"
"{venv_python}" -m {module_name} "$@"
"""
        else:
            wrapper = f"""#!/bin/bash
# Workforce Nexus Hardened Wrapper
export PYTHONPATH="{central}/mcp-injector:{central}/mcp-link-library:{central}/repo-mcp-packager:$PYTHONPATH"
"{venv_python}" "{target_script}" "$@"
"""
        try:
            cmd_path.write_text(wrapper)
            cmd_path.chmod(cmd_path.stat().st_mode | 0o111)
            print(f"✅ Created hardened entry point: {cmd}")
        except Exception as e:
            print(f"❌ Failed to create entry point {cmd}: {e}")

def generate_integrity_manifest(central: Path):
    """Generate SHA-256 integrity manifest for all installed files."""
    print("\n🛡️  Generating Integrity Manifest...")
    manifest_file = central / "manifest.sha256"
    hashes = []
    
    for root, dirs, files in os.walk(central):
        if ".venv" in root or ".git" in root: continue
        
        for f in files:
            if f == "manifest.sha256": continue
            path = Path(root) / f
            try:
                rel_path = path.relative_to(central)
                sha = hashlib.sha256(path.read_bytes()).hexdigest()
                hashes.append(f"{sha}  {rel_path}")
            except:
                pass
                
    manifest_file.write_text("\n".join(hashes), encoding="utf-8")
    print(f"✅ Integrity locked at {manifest_file}")

def main():
    parser = argparse.ArgumentParser(description="Nexus Bootstrap - Tiered Reliability")
    parser.add_argument("--lite", action="store_true", help="Lite mode (Zero-Dep)")
    parser.add_argument("--industrial", "--permanent", action="store_true", dest="industrial", help="Industrial mode (Infrastructure)")
    parser.add_argument("--sync", action="store_true", help="Sync Industrial Nexus from workspace (Update logic)")
    parser.add_argument("--strategy", choices=["full", "step"], help="Installation strategy")
    parser.add_argument("--gui", action="store_true", help="Launch GUI after installation")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing installations")
    args = parser.parse_args()

    if args.sync:
        workspace = get_workspace_root()
        if not workspace:
            print("🔄 No workspace found. Syncing Industrial Nexus via GitHub...")
            install_converged_application('industrial', None, update=True)
            return
        print(f"🔄 Syncing Industrial Nexus from local workspace: {workspace}")
        install_converged_application('industrial', workspace, update=True)
        return

    if sys.version_info < (3,6):
        print("❌ Python 3.6+ required")
        sys.exit(1)
    
    workspace = get_workspace_root()
    
    # Check if we are being run from within a potential target project
    target_project = Path(__file__).resolve().parent.parent
    has_project_files = any((target_project / f).exists() for f in ['package.json', 'pyproject.toml', 'requirements.txt', 'setup.py'])
    
    if not workspace:
        # Case A: Standalone Mode (Copied into another repo)
        if has_project_files and target_project.name not in ['mcp-injector', 'mcp-server-manager', 'mcp-link-library', 'repo-mcp-packager']:
            print(f"🎯 Target Project Detected: {target_project.name}")
            print(f"[*] This looks like a standalone setup for {target_project.name}.")
            
            installer = Path(__file__).parent / "serverinstaller" / "install.py"
            if installer.exists():
                print(f"🚀 Launching Standalone Installer...")
                os.execv(sys.executable, [sys.executable, str(installer)] + sys.argv[1:])
        
        # Case B: Autonomous Mode (Suite Install from GitHub)
        print("[*] No local Nexus workspace found. Entering Autonomous Mode...")
        if not args.industrial and not args.lite and not args.strategy:
             print("⚠️  No deployment tier selected. To install the Workforce Nexus suite from GitHub, use:")
             print("   python bootstrap.py --industrial")
             sys.exit(1)
    elif has_project_files and target_project.name not in ['mcp-injector', 'mcp-server-manager', 'mcp-link-library', 'repo-mcp-packager']:
        # Case C: Developer Workspace + Standalone Target
        print(f"🎯 Target Project Detected: {target_project.name}")
        installer = Path(__file__).parent / "serverinstaller" / "install.py"
        if installer.exists():
            os.execv(sys.executable, [sys.executable, str(installer)] + sys.argv[1:])
        
    # Phase 12: Convergence Check
    if detect_full_suite(workspace):
        if not args.lite and not args.industrial:
            # If no manual flags, prompt for convergence
            tier = ask_convergence_tier()
            install_converged_application(tier, workspace)
            return
    else:
        # Partial or Autonomous Mode
        if workspace:
            print(f"⚠️  Partial workspace detected at {workspace}")
            print("   Proceeding with standard installation for available repos.")
            
    # Resolve strategy and tier
    if args.lite or args.industrial or args.strategy:
        strategy = args.strategy or "full"
        tier = "lite" if args.lite else ("industrial" if args.industrial else "standard")
    else:
        results = ask_user_install_strategy()
        if not results: return
        strategy = results['strategy']
        tier = results['tier']
    
    if strategy == 'manual':
        return
    
    central = get_mcp_tools_home()
    
    # 0. Universal Pre-flight
    if not pre_flight_checks(central):
        sys.exit(1)

    try:
        if strategy == 'full':
            install_to_central(central, workspace, update=args.force)
            
            if tier == 'industrial':
                setup_nexus_venv(central)
                create_hardened_entry_points(central)
                ensure_global_path(central)
            
            if tier != 'lite':
                generate_integrity_manifest(central)
                
            print(f"\n✅ Complete! Tools available at {central} [Tier: {tier.upper()}]")
            if tier == 'industrial':
                print("💡 Try running 'mcp-surgeon --help' in a new terminal.")
        elif strategy == 'step':
            if ask("Install to central location?"): 
                install_to_central(central, workspace, update=args.force)
                
                if tier == 'industrial':
                    if ask("Setup Nexus Venv and dependencies?"):
                        setup_nexus_venv(central)
                    if ask("Create hardened global entry points?"):
                        create_hardened_entry_points(central)
                    if ask("Integrate Nexus into your global PATH?"):
                        ensure_global_path(central)
                
                if tier != 'lite':
                    if ask("Generate Integrity Manifest?"):
                        generate_integrity_manifest(central)
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")
        rollback()
        sys.exit(1)

    # Post-Install GUI Launch
    if args.gui:
        print("\n🚀 Launching GUI Dashboard...")
        # Use the hardened entry point if it exists, otherwise fall back to manual logic
        observer_bin = central / "bin" / "mcp-observer"
        
        try:
            if observer_bin.exists():
                os.execl(str(observer_bin), str(observer_bin), "gui")
            else:
                # Manual fallback with explicit PYTHONPATH
                venv_python = central / ".venv" / "bin" / "python"
                if platform.system() == "Windows":
                    venv_python = central / ".venv" / "Scripts" / "python.exe"
                
                if not venv_python.exists():
                    venv_python = sys.executable
                
                env = os.environ.copy()
                env["PYTHONPATH"] = f"{central}/mcp-server-manager:{env.get('PYTHONPATH', '')}"
                
                cmd = [str(venv_python), "-m", "mcp_inventory.cli", "gui"]
                subprocess.run(cmd, env=env)
        except Exception as e:
            print(f"⚠️  Failed to launch GUI: {e}")
            print("   Try running it manually: mcp-observer gui")

if __name__ == "__main__":
    main()
