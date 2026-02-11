#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from nexus_devlog import prune_devlogs, devlog_path, log_event, run_capture

GITHUB_ROOT = "https://github.com/l00p3rl00p"
NEXUS_REPOS = {
    "mcp-injector": f"{GITHUB_ROOT}/mcp-injector.git",
    "mcp-link-library": f"{GITHUB_ROOT}/mcp-link-library.git",
    "mcp-server-manager": f"{GITHUB_ROOT}/mcp-server-manager.git",
    "repo-mcp-packager": f"{GITHUB_ROOT}/repo-mcp-packager.git",
}
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

def _clone_repo(name: str, target: Path, *, devlog: Path | None) -> bool:
    url = NEXUS_REPOS.get(name)
    if not url:
        return False
    try:
        if target.exists():
            return True
        target.parent.mkdir(parents=True, exist_ok=True)
        run_capture(["git", "clone", "--depth", "1", url, str(target)], devlog=devlog, check=True)
        return True
    except Exception as e:
        print(f"❌ Failed to fetch {name}: {e}")
        log_event(devlog, "clone_failed", {"repo": name, "target": str(target), "error": str(e)})
        return False

def _install_suite_to_central(*, devlog: Path | None) -> bool:
    if not sys.stdin.isatty():
        return False
    if not _git_available():
        print("❌ git not available; cannot install the full suite automatically.")
        return False
    central = _mcp_tools_home()
    print("\n📦 Suite install (central-only)")
    print(f"Target: {central}")
    r = input("Clone missing Nexus repos into ~/.mcp-tools now? [y/N]: ").strip().lower()
    if r not in ("y", "yes"):
        return False

    for repo in ("repo-mcp-packager", "mcp-injector", "mcp-server-manager", "mcp-link-library"):
        if not _clone_repo(repo, central / repo, devlog=devlog):
            return False
    return True


def main() -> int:
    devlog = None
    if "--devlog" in sys.argv:
        prune_devlogs(days=90)
        devlog = devlog_path()
        log_event(devlog, "bootstrap_forwarder_start", {"argv": sys.argv})

    # Always show forwarder help directly (even if Activator exists), so users can discover forwarder-only flags.
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Nexus Bootstrap Forwarder (Observer)")
        print()
        print("This is a safe forwarder. It will not scan your disk or walk up directories.")
        print("It forwards to the Activator (repo-mcp-packager/bootstrap.py) when available.")
        print()
        print("Common forwarded flags:")
        print("  --permanent / --industrial   Hardened install into ~/.mcp-tools")
        print("  --lite                       Lite install")
        print("  --sync / --update            Sync/update suite")
        print("  --gui                        Launch GUI after install")
        print()
        print("Forwarder-only flags:")
        print("  --install-suite              Clone missing Nexus repos into ~/.mcp-tools (no scanning)")
        print("  --devlog                     Write JSONL devlog (90-day retention)")
        return 0

    if "--install-suite" in sys.argv:
        sys.argv = [a for a in sys.argv if a != "--install-suite"]
        if not _git_available():
            print("❌ git not available; cannot install the full suite automatically.")
            return 2
        central = _mcp_tools_home()
        central.mkdir(parents=True, exist_ok=True)
        ok = True
        for repo in ("repo-mcp-packager", "mcp-injector", "mcp-server-manager", "mcp-link-library"):
            ok = ok and _clone_repo(repo, central / repo, devlog=devlog)
        if ok:
            central_boot = central / "repo-mcp-packager" / "bootstrap.py"
            if central_boot.exists():
                cmd = [sys.executable, str(central_boot), *sys.argv[1:]]
                if devlog:
                    cp = run_capture(cmd, devlog=devlog, check=False)
                    if cp.stdout:
                        sys.stdout.write(cp.stdout)
                    if cp.stderr:
                        sys.stderr.write(cp.stderr)
                    return cp.returncode
                return subprocess.run(cmd, check=False).returncode

    for candidate in _candidate_activator_bootstraps():
        if candidate.exists():
            cmd = [sys.executable, str(candidate), *sys.argv[1:]]
            if devlog:
                cp = run_capture(cmd, devlog=devlog, check=False)
                if cp.stdout:
                    sys.stdout.write(cp.stdout)
                if cp.stderr:
                    sys.stderr.write(cp.stderr)
                return cp.returncode
            return subprocess.run(cmd, check=False).returncode

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

    if _install_suite_to_central(devlog=devlog):
        central = _mcp_tools_home() / "repo-mcp-packager" / "bootstrap.py"
        if central.exists():
            cmd = [sys.executable, str(central), *sys.argv[1:]]
            if devlog:
                cp = run_capture(cmd, devlog=devlog, check=False)
                if cp.stdout:
                    sys.stdout.write(cp.stdout)
                if cp.stderr:
                    sys.stderr.write(cp.stderr)
                return cp.returncode
            return subprocess.run(cmd, check=False).returncode

    if _maybe_fetch_activator_to_central():
        central = _mcp_tools_home() / "repo-mcp-packager" / "bootstrap.py"
        if central.exists():
            cmd = [sys.executable, str(central), *sys.argv[1:]]
            if devlog:
                cp = run_capture(cmd, devlog=devlog, check=False)
                if cp.stdout:
                    sys.stdout.write(cp.stdout)
                if cp.stderr:
                    sys.stderr.write(cp.stderr)
                return cp.returncode
            return subprocess.run(cmd, check=False).returncode

    print("Fix options:")
    print("- If you have the 4-repo workspace, run the Activator directly:")
    print("  python3 ../repo-mcp-packager/bootstrap.py --permanent")
    print("- Or install the full suite, then re-run:")
    print("  python3 ~/.mcp-tools/repo-mcp-packager/bootstrap.py --permanent")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
