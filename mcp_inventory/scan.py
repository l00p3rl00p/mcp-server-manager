from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from .models import Candidate, Evidence
from .util import slugify

READ_ME_FILES = {"README.md", "Readme.md", "readme.md"}
MCP_WORD_RE = re.compile(r"\bmcp\b|modelcontextprotocol", re.IGNORECASE)
LLM_KEY_RE = re.compile(r"\b(OPENAI|ANTHROPIC|AZURE_OPENAI|GOOGLE|GEMINI|COHERE|MISTRAL)_", re.IGNORECASE)

def iter_candidate_dirs(
    roots: List[str],
    exclude_dir_names: Set[str],
    trigger_files: Set[str],
    deep_scan: bool,
    max_candidates: int,
) -> Iterable[Path]:
    seen: Set[Path] = set()
    count = 0
    for r in roots:
        root = Path(r).expanduser()
        if not root.exists():
            continue
        # Shallow scan: only 4 levels deep by default
        max_depth = 9 if deep_scan else 4
        for p in root.rglob("*"):
            if count >= max_candidates:
                return
            if not p.is_dir():
                continue
            parts = set(p.parts)
            if any(name in parts for name in exclude_dir_names):
                continue
            # depth bound (relative)
            try:
                rel = p.relative_to(root)
                if len(rel.parts) > max_depth:
                    continue
            except Exception:
                pass

            # trigger file check
            for tf in trigger_files:
                if (p / tf).exists():
                    if p not in seen:
                        seen.add(p)
                        count += 1
                        yield p
                    break


def _read_text_safe(path: Path, max_bytes: int = 256_000) -> str:
    try:
        b = path.read_bytes()
        if len(b) > max_bytes:
            b = b[:max_bytes]
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _package_json_signals(dirpath: Path, c: Candidate) -> None:
    pj = dirpath / "package.json"
    if not pj.exists():
        return
    txt = _read_text_safe(pj)
    try:
        data = json.loads(txt)
    except Exception:
        return
    deps = {}
    for k in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        deps.update(data.get(k, {}) or {})
    if any(k.startswith("@modelcontextprotocol/") for k in deps.keys()):
        c.evidence.append(Evidence("dep:@modelcontextprotocol", "package.json includes @modelcontextprotocol/*", 50))
        # likely name
        name = data.get("name")
        if isinstance(name, str) and name.strip():
            c.inferred_name = slugify(name)


def _pyproject_signals(dirpath: Path, c: Candidate) -> None:
    pp = dirpath / "pyproject.toml"
    if not pp.exists():
        return
    txt = _read_text_safe(pp)
    if "modelcontextprotocol" in txt.lower():
        c.evidence.append(Evidence("code:modelcontextprotocol", "pyproject.toml mentions modelcontextprotocol", 40))


def _manifest_signals(dirpath: Path, c: Candidate) -> None:
    for mf in ("mcp.server.json", "mcp.json"):
        p = dirpath / mf
        if p.exists():
            c.evidence.append(Evidence(f"manifest:{mf}", f"{mf} present", 80))
            # name inference
            if mf == "mcp.server.json":
                try:
                    data = json.loads(_read_text_safe(p))
                    nm = data.get("name")
                    if isinstance(nm, str) and nm.strip():
                        c.inferred_name = slugify(nm)
                    tr = data.get("transport")
                    if isinstance(tr, str) and tr.strip():
                        c.transport = tr.strip().lower()
                except Exception:
                    pass

    # Librarian Manifest Detection
    lib_path = dirpath / ".librarian" / "manifest.json"
    if lib_path.exists():
        c.evidence.append(Evidence("librarian:manifest", "Nexus/Librarian manifest detected", 100))
        try:
            data = json.loads(_read_text_safe(lib_path))
            c.install_mode = data.get("install_mode", "dev")
            c.remote_url = data.get("remote_url")
        except (json.JSONDecodeError, KeyError):
            # Malformed manifest — proceed without install_mode/remote_url
            pass


def _readme_signals(dirpath: Path, c: Candidate) -> None:
    for rf in READ_ME_FILES:
        p = dirpath / rf
        if p.exists():
            txt = _read_text_safe(p)
            if MCP_WORD_RE.search(txt):
                c.evidence.append(Evidence("readme:mentions:mcp", f"{rf} mentions MCP", 15))
            return


def _env_signals(dirpath: Path, c: Candidate) -> None:
    envs = list(dirpath.glob(".env*"))
    if envs:
        c.env_files = [e.name for e in envs[:10]]
        # weak trigger
        if len(c.evidence) == 0:
            c.evidence.append(Evidence("trigger:.env_only", ".env present (weak alone)", 1))
        # medium: detect LLM keys
        for e in envs[:3]:
            txt = _read_text_safe(e, max_bytes=96_000)
            if LLM_KEY_RE.search(txt):
                c.evidence.append(Evidence("env:llm_keys", f"{e.name} contains LLM-ish keys", 10))
                break
        # better: operator marker
        for e in envs[:3]:
            txt = _read_text_safe(e, max_bytes=96_000)
            m = re.search(r"^\s*MCP_SERVER_NAME\s*=\s*(.+)\s*$", txt, re.MULTILINE)
            if m:
                name = m.group(1).strip().strip('"').strip("'")
                if name:
                    c.inferred_name = slugify(name)
                    c.evidence.append(Evidence("env:mcp_server_name", "MCP_SERVER_NAME present", 70))
                break


def _compose_signals(dirpath: Path, c: Candidate) -> None:
    for fn in ("docker-compose.yml", "compose.yaml", "compose.yml"):
        p = dirpath / fn
        if p.exists():
            c.run_kind = "docker-compose"
            c.compose_file = fn
            txt = _read_text_safe(p)
            # heuristic: service names containing mcp
            if re.search(r"^\s{0,4}\w.*mcp.*:\s*$", txt, re.IGNORECASE | re.MULTILINE):
                c.evidence.append(Evidence("compose:service:contains:mcp", f"{fn} has service name containing 'mcp'", 12))
            return


def _dockerfile_signals(dirpath: Path, c: Candidate) -> None:
    p = dirpath / "Dockerfile"
    if p.exists() and c.run_kind == "unknown":
        c.run_kind = "docker"


def _code_keyword_signals(dirpath: Path, c: Candidate) -> None:
    # Keep this cheap: sample a few likely files
    sample = []
    for fn in ("server.py", "main.py", "app.py", "index.js", "index.ts", "src/index.ts", "src/index.js"):
        p = dirpath / fn
        if p.exists():
            sample.append(p)
    if not sample:
        # fallback: look for one small file in src/
        src = dirpath / "src"
        if src.exists() and src.is_dir():
            for p in src.glob("**/*.*"):
                if p.suffix.lower() in (".py", ".ts", ".js") and p.is_file():
                    sample.append(p)
                    break

    for p in sample[:3]:
        txt = _read_text_safe(p)
        if "modelcontextprotocol" in txt.lower() or "@modelcontextprotocol" in txt.lower():
            c.evidence.append(Evidence("code:modelcontextprotocol", f"code references modelcontextprotocol ({p.name})", 35))
            return


def scan_installed(roots: List[str], exclude_dir_names: List[str], trigger_files: List[str], deep_scan: bool, max_candidates: int) -> List[Candidate]:
    cands: List[Candidate] = []
    for d in iter_candidate_dirs(
        roots=roots,
        exclude_dir_names=set(exclude_dir_names),
        trigger_files=set(trigger_files),
        deep_scan=deep_scan,
        max_candidates=max_candidates,
    ):
        c = Candidate(path=str(d))
        # infer name from folder initially
        c.inferred_name = slugify(d.name)

        _manifest_signals(d, c)
        _package_json_signals(d, c)
        _pyproject_signals(d, c)
        _readme_signals(d, c)
        _compose_signals(d, c)
        _dockerfile_signals(d, c)
        _env_signals(d, c)
        _code_keyword_signals(d, c)

        c.score = sum(e.weight for e in c.evidence)
        cands.append(c)

    # Sort by score descending
    cands.sort(key=lambda x: x.score, reverse=True)
    return cands
