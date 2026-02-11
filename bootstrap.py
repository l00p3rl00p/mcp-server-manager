#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

GITHUB_ROOT = "https://github.com/l00p3rl00p"
ACTIVATOR_REPO = f"{GITHUB_ROOT}/repo-mcp-packager.git"


def _home() -> Path:
    return Path(os.environ.get("HOME") or str(Path.home())).expanduser()


def _mcp_tools_home() -> Path:
    if sys.platform == "win32":
        return Path(os.environ["USERPROFILE"]) / ".mcp-tools"
    return _home() / ".mcp-tools"


def _candidate_activator_bootstraps() -> list[Path]:
    here = Path(__file__).resolve()
    sibling = here.parent.parent / "repo-mcp-packager" / "bootstrap.py"
    central = _mcp_tools_home() / "repo-mcp-packager" / "bootstrap.py"
    return [sibling, central]

def _git_available() -> bool:
    try:
        subprocess.run(["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return True
    except Exception:
        return False

def _maybe_fetch_activator_to_central() -> bool:
    if not sys.stdin.isatty():
        return False
    if not _git_available():
        return False
    central_repo_dir = _mcp_tools_home() / "repo-mcp-packager"
    if central_repo_dir.exists():
        return False
    r = input("Fetch Activator (repo-mcp-packager) into ~/.mcp-tools now? [y/N]: ").strip().lower()
    if r not in ("y", "yes"):
        return False
    try:
        _mcp_tools_home().mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", ACTIVATOR_REPO, str(central_repo_dir)], check=True)
        return True
    except Exception as e:
        print(f"❌ Failed to fetch Activator: {e}")
        return False


def main() -> int:
    for candidate in _candidate_activator_bootstraps():
        if candidate.exists():
            return subprocess.run([sys.executable, str(candidate), *sys.argv[1:]], check=False).returncode

    print("❌ Activator bootstrap.py not found.")
    print("This repo's bootstrap is a forwarder and will not scan your disk.")
    print("Expected one of:")
    for c in _candidate_activator_bootstraps():
        print(f"  - {c}")
    print()
    print("Standalone usage (no install required):")
    print("  python3 -m mcp_inventory.cli --help")
    print("  python3 -m mcp_inventory.cli gui")
    print()
    if _maybe_fetch_activator_to_central():
        central = _mcp_tools_home() / "repo-mcp-packager" / "bootstrap.py"
        if central.exists():
            return subprocess.run([sys.executable, str(central), *sys.argv[1:]], check=False).returncode

    print("Fix options:")
    print("- If you have the 4-repo workspace, run the Activator directly:")
    print("  python3 ../repo-mcp-packager/bootstrap.py --permanent")
    print("- Or install the full suite, then re-run:")
    print("  python3 ~/.mcp-tools/repo-mcp-packager/bootstrap.py --permanent")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
