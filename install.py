#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _home() -> Path:
    return Path.home().expanduser()


def _mcp_tools_home() -> Path:
    if sys.platform == "win32":
        import os

        return Path(os.environ["USERPROFILE"]) / ".mcp-tools"
    return _home() / ".mcp-tools"


def _candidate_installers() -> list[Path]:
    here = Path(__file__).resolve()
    sibling = here.parent.parent / "repo-mcp-packager" / "serverinstaller" / "install.py"
    central = _mcp_tools_home() / "repo-mcp-packager" / "serverinstaller" / "install.py"
    return [sibling, central]


def main() -> int:
    installer = next((p for p in _candidate_installers() if p.exists()), None)
    if not installer:
        print("❌ Activator installer not found.")
        print("Expected one of:")
        for p in _candidate_installers():
            print(f"- {p}")
        print()
        print("Fix:")
        print("- From a full workspace clone, run: `./nexus.sh`")
        print("- Or install the suite centrally via: `python3 bootstrap.py --install-suite --permanent`")
        return 2
    return subprocess.run([sys.executable, str(installer), *sys.argv[1:]], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())

