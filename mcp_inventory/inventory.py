from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional
import datetime
import json

try:
    import yaml
except ImportError:
    yaml = None

from .config import INVENTORY_PATH, ensure_app_dir
from .models import InventoryEntry, InventoryRun
from .util import slugify


def _backup_and_reset_inventory(path: Path, reason: str) -> Dict[str, List[dict]]:
    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup = path.with_suffix(f".yaml.corrupt.{stamp}")
    try:
        if path.exists():
            path.replace(backup)
    except Exception:
        pass
    if yaml is not None:
        path.write_text(yaml.safe_dump({"servers": []}, sort_keys=False), encoding="utf-8")
    else:
        path.write_text(json.dumps({"servers": []}, indent=2), encoding="utf-8")
    print(f"⚠️  Recovered malformed inventory ({reason}). Backup: {backup}")
    return {"servers": []}


def load_inventory(path: Path = INVENTORY_PATH) -> Dict[str, InventoryEntry]:
    ensure_app_dir()
    if yaml is None:
        print("⚠️  Missing dependency: pyyaml. Falling back to empty inventory.")
        return {}
    if not path.exists():
        path.write_text(yaml.safe_dump({"servers": []}, sort_keys=False), encoding="utf-8")
    raw = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(raw) or {"servers": []}
    except Exception:
        data = _backup_and_reset_inventory(path, "parse-error")
    if not isinstance(data, dict):
        data = _backup_and_reset_inventory(path, "root-not-mapping")
    servers = data.get("servers", [])
    if not isinstance(servers, list):
        data = _backup_and_reset_inventory(path, "servers-not-list")
        servers = data["servers"]
    out: Dict[str, InventoryEntry] = {}
    for item in servers:
        if not isinstance(item, dict) or "id" not in item:
            continue
        run = item.get("run", {}) or {}
        entry = InventoryEntry(
            id=item["id"],
            name=item.get("name", item["id"]),
            path=item.get("path"),
            confidence=item.get("confidence", "manual"),
            status=item.get("status", "unknown"),
            transport=item.get("transport", "unknown"),
            ports=item.get("ports", []) or [],
            env_files=item.get("env_files", []) or [],
            run=InventoryRun(**{k: run.get(k) for k in [
                "kind","compose_file","compose_service","docker_container","docker_image",
                "start_cmd","stop_cmd","workdir"
            ] if k in run}),
            tags=item.get("tags", []) or [],
            notes=item.get("notes", "") or "",
            added_on=item.get("added_on"),
            last_seen=item.get("last_seen"),
            evidence=item.get("evidence", []) or [],
        )
        out[entry.id] = entry
    return out


def save_inventory(entries: Dict[str, InventoryEntry], path: Path = INVENTORY_PATH) -> None:
    ensure_app_dir()
    if yaml is None:
        fallback = path.with_suffix(".json")
        servers = []
        for _, e in sorted(entries.items(), key=lambda kv: kv[0]):
            servers.append(asdict(e))
        fallback.write_text(json.dumps({"servers": servers}, indent=2), encoding="utf-8")
        return
    servers: List[dict] = []
    for _, e in sorted(entries.items(), key=lambda kv: kv[0]):
        d = asdict(e)
        servers.append(d)
    path.write_text(yaml.safe_dump({"servers": servers}, sort_keys=False), encoding="utf-8")


def upsert_entry(entries: Dict[str, InventoryEntry], entry: InventoryEntry) -> InventoryEntry:
    entries[entry.id] = entry
    return entry


def make_entry_id(name: str) -> str:
    return slugify(name)


def add_manual(entries: Dict[str, InventoryEntry], name: str, path: Optional[str] = None) -> InventoryEntry:
    eid = make_entry_id(name)
    if eid in entries:
        e = entries[eid]
        if path and not e.path:
            e.path = path
        return e
    e = InventoryEntry(id=eid, name=name, path=path, confidence="manual")
    entries[eid] = e
    return e
