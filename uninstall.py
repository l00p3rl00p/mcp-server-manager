#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _workspace_root() -> Path | None:
    here = Path(__file__).resolve().parent
    cur = here
    for _ in range(6):
        candidate = cur.parent
        if candidate == cur:
            break
        if (candidate / "repo-mcp-packager" / "serverinstaller" / "uninstall.py").exists():
            return candidate
        cur = candidate
    return None


def _run_packager_uninstall(workspace: Path, args: list[str]) -> int:
    script = workspace / "repo-mcp-packager" / "serverinstaller" / "uninstall.py"
    return subprocess.run([sys.executable, str(script), *args], cwd=str(workspace), check=False).returncode


def _local_uninstall(kill_venv: bool, purge_data: bool) -> int:
    repo_root = Path(__file__).resolve().parent
    if kill_venv:
        shutil.rmtree(repo_root / ".venv", ignore_errors=True)
    if purge_data:
        shutil.rmtree(Path.home() / ".mcp-tools", ignore_errors=True)
        shutil.rmtree(Path.home() / ".mcpinv", ignore_errors=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Uninstall MCP Workforce Nexus (single-repo entrypoint)")
    parser.add_argument("--kill-venv", action="store_true", help="Remove the local .venv (if present)")
    parser.add_argument("--purge-data", action="store_true", help="Purge shared Nexus data (~/.mcp-tools and ~/.mcpinv)")
    ns, passthrough = parser.parse_known_args()

    ws = _workspace_root()
    if ws is not None:
        forwarded = []
        if ns.kill_venv:
            forwarded.append("--kill-venv")
        if ns.purge_data:
            forwarded.append("--purge-data")
        forwarded.extend(passthrough)
        return _run_packager_uninstall(ws, forwarded)

    return _local_uninstall(kill_venv=ns.kill_venv, purge_data=ns.purge_data)


if __name__ == "__main__":
    raise SystemExit(main())

