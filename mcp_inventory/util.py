from __future__ import annotations
import re
from pathlib import Path
from typing import Iterable, Optional

SAFE_ID_RE = re.compile(r"[^a-z0-9\-]+")

def slugify(s: str) -> str:
    s = s.strip().lower().replace("_", "-").replace(" ", "-")
    s = SAFE_ID_RE.sub("-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "unknown"

def first_existing(paths: Iterable[Path]) -> Optional[Path]:
    for p in paths:
        if p.exists():
            return p
    return None
