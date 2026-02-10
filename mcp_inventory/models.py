from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


@dataclass
class Evidence:
    kind: str
    detail: str
    weight: int


@dataclass
class Candidate:
    path: str
    inferred_name: str = "unknown"
    evidence: List[Evidence] = field(default_factory=list)
    run_kind: str = "unknown"  # docker-compose | docker | local | unknown
    compose_file: Optional[str] = None
    compose_services: List[str] = field(default_factory=list)
    docker_images: List[str] = field(default_factory=list)
    ports: List[int] = field(default_factory=list)
    env_files: List[str] = field(default_factory=list)
    transport: str = "unknown"  # http|ws|stdio|unknown
    install_mode: str = "dev"
    remote_url: Optional[str] = None
    score: int = 0


@dataclass
class GateDecision:
    accept: bool
    bucket: str  # confirmed | review | rejected
    reason: str


@dataclass
class InventoryRun:
    kind: str  # docker-compose | docker | local | unknown
    compose_file: Optional[str] = None
    compose_service: Optional[str] = None
    docker_container: Optional[str] = None
    docker_image: Optional[str] = None
    start_cmd: Optional[str] = None
    stop_cmd: Optional[str] = None
    workdir: Optional[str] = None


@dataclass
class InventoryEntry:
    id: str
    name: str
    path: Optional[str] = None
    confidence: str = "manual"  # confirmed|likely|manual
    status: str = "unknown"     # running|stopped|broken|unknown|orphan
    transport: str = "unknown"
    ports: List[int] = field(default_factory=list)
    env_files: List[str] = field(default_factory=list)
    run: InventoryRun = field(default_factory=lambda: InventoryRun(kind="unknown"))
    tags: List[str] = field(default_factory=list)
    install_mode: str = "dev"  # managed | dev
    remote_url: Optional[str] = None
    notes: str = ""
    added_on: str = field(default_factory=utc_now_iso)
    last_seen: Optional[str] = None
    evidence: List[Dict[str, Any]] = field(default_factory=list)  # serialized Evidence


@dataclass
class VerifyResult:
    entry_id: str
    ok: bool
    status: str
    problems: List[str] = field(default_factory=list)
