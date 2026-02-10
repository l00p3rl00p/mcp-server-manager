from __future__ import annotations
import json
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import psutil

from .models import utc_now_iso

@dataclass
class RunningObservation:
    kind: str  # docker | port | process
    name: str
    detail: str
    ports: List[int]
    path_hint: Optional[str] = None
    last_seen: str = utc_now_iso()


def _run(cmd: List[str]) -> Tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return p.returncode, p.stdout, p.stderr
    except Exception as e:
        return 1, "", str(e)


def docker_running() -> List[RunningObservation]:
    obs: List[RunningObservation] = []
    rc, out, err = _run(["docker", "ps", "--format", "{{json .}}"])
    if rc != 0 or not out.strip():
        return obs
    for line in out.splitlines():
        try:
            row = json.loads(line)
        except Exception:
            continue
        name = row.get("Names") or row.get("Image") or "docker"
        ports_field = row.get("Ports") or ""
        ports: List[int] = []
        # parse "0.0.0.0:7450->7450/tcp"
        for part in ports_field.split(","):
            part = part.strip()
            if "->" in part and ":" in part:
                left = part.split("->", 1)[0]
                if ":" in left:
                    try:
                        ports.append(int(left.rsplit(":", 1)[1]))
                    except Exception:
                        pass
        obs.append(RunningObservation(kind="docker", name=name, detail=f"container={row.get('Names')} image={row.get('Image')}", ports=sorted(set(ports))))
    return obs


def listening_ports_localhost() -> List[RunningObservation]:
    # Best-effort using psutil; will include many non-MCP listeners (we keep it as "running signals").
    obs: List[RunningObservation] = []
    try:
        conns = psutil.net_connections(kind="inet")
    except Exception:
        return obs
    port_map: Dict[int, List[int]] = {}  # port -> pids
    for c in conns:
        if c.status != psutil.CONN_LISTEN:
            continue
        if not c.laddr:
            continue
        ip = c.laddr.ip
        port = c.laddr.port
        if ip not in ("127.0.0.1", "0.0.0.0", "::1"):
            continue
        if c.pid:
            port_map.setdefault(port, []).append(c.pid)
    for port, pids in port_map.items():
        # attach a small process hint
        name = "listener"
        detail = f"port={port} pids={sorted(set(pids))}"
        obs.append(RunningObservation(kind="port", name=name, detail=detail, ports=[port]))
    return obs


def mcpish_processes() -> List[RunningObservation]:
    obs: List[RunningObservation] = []
    needles = ("modelcontextprotocol", "@modelcontextprotocol", " mcp", "MCP_")
    for p in psutil.process_iter(attrs=["pid", "name", "cmdline", "cwd"]):
        try:
            cmd = " ".join(p.info.get("cmdline") or [])
            if not cmd:
                continue
            low = cmd.lower()
            if any(n in low for n in needles):
                obs.append(RunningObservation(
                    kind="process",
                    name=p.info.get("name") or "process",
                    detail=f"pid={p.info.get('pid')} cmd={cmd[:220]}",
                    ports=[],
                    path_hint=p.info.get("cwd"),
                ))
        except Exception:
            continue
    return obs


def running_snapshot() -> List[RunningObservation]:
    # Keep it simple: docker + processes. Ports can be noisy; still useful for heartbeat.
    out = []
    out.extend(docker_running())
    out.extend(mcpish_processes())
    return out
