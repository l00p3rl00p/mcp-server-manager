from __future__ import annotations

import json
import os
import subprocess
import datetime
from pathlib import Path
from typing import Any, Optional


def _home() -> Path:
    return Path(os.environ.get("HOME") or str(Path.home())).expanduser()


def devlog_dir() -> Path:
    return _home() / ".mcpinv" / "devlogs"


def prune_devlogs(days: int = 90) -> None:
    try:
        d = devlog_dir()
        d.mkdir(parents=True, exist_ok=True)
        cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
        for p in d.glob("nexus-*.jsonl"):
            try:
                mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime)
                if mtime < cutoff:
                    p.unlink(missing_ok=True)
            except Exception:
                continue
    except Exception:
        return


def devlog_path() -> Path:
    stamp = datetime.datetime.now().strftime("%Y-%m-%d")
    return devlog_dir() / f"nexus-{stamp}.jsonl"


def log_event(devlog: Optional[Path], event: str, data: dict[str, Any]) -> None:
    if not devlog:
        return
    try:
        devlog.parent.mkdir(parents=True, exist_ok=True)
        payload = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "event": event, **data}
        with open(devlog, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        return


def run_capture(
    cmd: list[str],
    *,
    devlog: Optional[Path] = None,
    cwd: Optional[str] = None,
    env: Optional[dict[str, str]] = None,
    timeout: Optional[float] = None,
    check: bool = False,
    capture_limit: int = 20000,
) -> subprocess.CompletedProcess:
    log_event(devlog, "subprocess_start", {"cmd": cmd, "cwd": cwd})
    try:
        cp = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except Exception as e:
        log_event(devlog, "subprocess_exception", {"cmd": cmd, "cwd": cwd, "error": str(e)})
        raise

    stdout = (cp.stdout or "")[:capture_limit]
    stderr = (cp.stderr or "")[:capture_limit]
    log_event(
        devlog,
        "subprocess_end",
        {"cmd": cmd, "cwd": cwd, "returncode": cp.returncode, "stdout": stdout, "stderr": stderr},
    )
    if check and cp.returncode != 0:
        raise subprocess.CalledProcessError(cp.returncode, cmd, output=cp.stdout, stderr=cp.stderr)
    return cp

