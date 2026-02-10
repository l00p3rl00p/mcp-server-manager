from __future__ import annotations
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List

APP_DIR = Path.home() / ".mcpinv"
CONFIG_PATH = APP_DIR / "config.json"
INVENTORY_PATH = APP_DIR / "inventory.yaml"


@dataclass
class Config:
    scan_roots: List[str] = field(default_factory=lambda: [
        str(Path.home() / "Code"),
        str(Path.home() / "Projects"),
        str(Path.home() / "Dev"),
        str(Path.home() / "Documents"),
    ])
    deep_scan: bool = False
    max_candidates: int = 5000

    # Hard exclusions (directory names)
    exclude_dir_names: List[str] = field(default_factory=lambda: [
        ".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache",
        "dist", "build", ".cache", "Library",
    ])

    # Candidate trigger files (wide scan)
    trigger_files: List[str] = field(default_factory=lambda: [
        ".env", "docker-compose.yml", "compose.yaml", "compose.yml", "Dockerfile",
        "package.json", "pyproject.toml", "requirements.txt", "mcp.server.json", "mcp.json"
    ])


def ensure_app_dir() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Config:
    ensure_app_dir()
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cfg = Config()
        for k, v in data.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        return cfg
    cfg = Config()
    save_config(cfg)
    return cfg


def save_config(cfg: Config) -> None:
    ensure_app_dir()
    CONFIG_PATH.write_text(json.dumps(asdict(cfg), indent=2), encoding="utf-8")
