#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _home() -> Path:
    return Path(os.environ.get("HOME") or str(Path.home())).expanduser()


def _mcp_tools_home() -> Path:
    if sys.platform == "win32":
        return Path(os.environ["USERPROFILE"]) / ".mcp-tools"
    return _home() / ".mcp-tools"


def _central_packager_uninstall() -> Path:
    return _mcp_tools_home() / "repo-mcp-packager" / "serverinstaller" / "uninstall.py"

def _confirm(prompt: str) -> bool:
    if not sys.stdin.isatty():
        return False
    r = input(f"{prompt} [y/N]: ").strip().lower()
    return r in ("y", "yes")

def _fallback_central_uninstall(*, kill_venv: bool, purge_data: bool, verbose: bool, yes: bool) -> int:
    nexus = _mcp_tools_home()
    mcpinv = _home() / ".mcpinv"

    if not purge_data:
        print("Nothing to do (central-only uninstaller requires --purge-data).")
        print("Tip: use `python3 uninstall.py --purge-data --kill-venv` for a full wipe.")
        return 0

    planned: list[Path] = []
    if nexus.exists():
        if kill_venv:
            planned.append(nexus)
        else:
            for child in sorted(nexus.iterdir(), key=lambda p: p.name):
                if child.name == ".venv":
                    continue
                planned.append(child)
    if mcpinv.exists():
        planned.append(mcpinv)

    print("\n🧹 Nexus Uninstall (Central-Only Fallback)")
    print("=" * 60)
    if planned:
        print("Planned removals:")
        for p in planned:
            print(f"- {p}")
    else:
        print("Nothing found to remove.")

    print("\nSafety note:")
    print("- This tool will NOT scan your disk or walk up directories.")
    print("- It will NOT delete anything in your git workspace automatically.")

    if planned and not yes and not _confirm("Proceed with deleting the above items?"):
        print("Aborted.")
        return 2

    for p in planned:
        try:
            if p.is_dir():
                if verbose:
                    print(f"[-] Removing directory: {p}")
                import shutil
                shutil.rmtree(p, ignore_errors=True)
            else:
                if verbose:
                    print(f"[-] Removing file: {p}")
                p.unlink(missing_ok=True)
        except Exception as e:
            print(f"⚠️  Failed to remove {p}: {e}")

    print("Done.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Uninstall MCP Workforce Nexus (central-only; does not touch your git workspace)"
    )
    parser.add_argument("--kill-venv", action="store_true", help="Remove Nexus venvs created under ~/.mcp-tools")
    parser.add_argument("--purge-data", action="store_true", help="Remove central suite data (~/.mcp-tools) and observer state (~/.mcpinv)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--devlog", action="store_true", help="Write dev log (JSONL) with 90-day retention")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompts (DANGEROUS)")
    ns, passthrough = parser.parse_known_args()

    script = _central_packager_uninstall()
    forwarded = []
    if ns.kill_venv:
        forwarded.append("--kill-venv")
    if ns.purge_data:
        forwarded.append("--purge-data")
    if ns.verbose:
        forwarded.append("--verbose")
    if ns.devlog:
        forwarded.append("--devlog")
    if ns.yes:
        forwarded.append("--yes")
    forwarded.extend(passthrough)

    if script.exists():
        return subprocess.run([sys.executable, str(script), *forwarded], check=False).returncode

    print("⚠️  Central packager uninstaller not found at:")
    print(f"   {script}")
    print("   Falling back to a minimal central-only uninstall (no workspace deletes).")

    return _fallback_central_uninstall(
        kill_venv=ns.kill_venv,
        purge_data=ns.purge_data,
        verbose=ns.verbose,
        yes=ns.yes,
    )


if __name__ == "__main__":
    raise SystemExit(main())
