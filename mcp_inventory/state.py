from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import asdict

from .config import STATE_DIR
from .models import InventoryEntry

# Ensure state directory exists
STATE_DIR.mkdir(parents=True, exist_ok=True)

def _write_json(filename: str, data: Any) -> None:
    """
    atomic write to state directory
    """
    path = STATE_DIR / filename
    temp = path.with_suffix(".tmp")
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    temp.replace(path)

def write_inventory_snapshot(inventory: Dict[str, InventoryEntry]) -> None:
    """
    Writes the full inventory state to state/inventory.json
    """
    data = {
        "timestamp": time.time(),
        "entries": [asdict(e) for e in inventory.values()]
    }
    _write_json("inventory.json", data)

def write_runtime_snapshot(snapshot: List[Any]) -> None:
    """
    Writes the runtime (scan/running) snapshot to state/runtime.json.
    Currently 'snapshot' is a list of RuntimeObservation objects (or similar).
    """
    # Assuming snapshot items have an as_dict or are dataclasses
    data = {
        "timestamp": time.time(),
        "observations": [asdict(o) if hasattr(o, "__dataclass_fields__") else o for o in snapshot]
    }
    _write_json("runtime.json", data)

def write_health_snapshot(checks: List[Dict[str, Any]]) -> None:
    """
    Writes a health check report to state/health.json
    """
    data = {
        "timestamp": time.time(),
        "checks": checks
    }
    _write_json("health.json", data)
