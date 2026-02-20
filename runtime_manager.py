from __future__ import annotations

import json
import os
import platform
import shutil
import stat
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
from urllib.request import Request, urlopen, urlretrieve


def _indygreg_platform_matchers() -> tuple[str, str]:
    """
    Return (arch_token, os_token) for python-build-standalone asset selection.
    """
    sys_platform = platform.system().lower()
    machine = platform.machine().lower()

    if machine in ("arm64", "aarch64"):
        arch = "aarch64"
    elif machine in ("x86_64", "amd64"):
        arch = "x86_64"
    else:
        arch = machine

    if sys_platform == "darwin":
        os_token = "apple-darwin"
    elif sys_platform == "linux":
        os_token = "unknown-linux"
    elif sys_platform == "windows":
        os_token = "pc-windows"
    else:
        os_token = sys_platform

    return arch, os_token


def resolve_standalone_python_url(version: str, *, provider: str = "indygreg") -> str:
    """
    Resolve a download URL for a self-contained CPython runtime without requiring Homebrew/system changes.

    Default provider: python-build-standalone (indygreg).
    """
    provider = (provider or "").strip().lower()
    if provider != "indygreg":
        raise RuntimeError(f"Unsupported runtime provider: {provider}")

    arch, os_token = _indygreg_platform_matchers()
    want = f"cpython-{version}".lower()

    api = "https://api.github.com/repos/indygreg/python-build-standalone/releases"
    req = Request(
        api,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "nexus-runtime-manager",
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=20) as resp:
            releases = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as e:
        raise RuntimeError(f"Failed to resolve standalone Python URL (network required): {e}") from e

    best_url: Optional[str] = None
    best_score = -1
    for rel in releases or []:
        for asset in (rel.get("assets") or []):
            name = (asset.get("name") or "").lower()
            url = asset.get("browser_download_url") or ""
            if not name or not url:
                continue
            if want not in name:
                continue
            if os_token not in name:
                continue
            if arch not in name:
                continue
            if not name.endswith(".tar.gz"):
                continue

            score = 0
            if "install_only" in name:
                score += 10
            if "pgo" in name:
                score += 1
            if "lto" in name:
                score += 1

            if score > best_score:
                best_score = score
                best_url = url

    if not best_url:
        raise RuntimeError(
            f"No standalone Python asset found for {version} ({arch}-{os_token}). "
            "Provide an explicit --url."
        )

    return best_url


def _safe_extract_tar_gz(tf: tarfile.TarFile, dest_dir: Path) -> None:
    """
    Safely extract a tarball into dest_dir.

    Blocks path traversal (absolute paths, `..` segments, symlink tricks) by ensuring every
    extracted path resolves under dest_dir.
    """
    dest_dir = dest_dir.resolve()
    members = tf.getmembers()

    # Basic anti-zip-bomb guardrails (tunable). We keep these conservative to avoid surprising failures.
    if len(members) > 50000:
        raise RuntimeError("Refusing to extract tarball: too many members")

    for m in members:
        name = m.name or ""
        # tarfile can contain absolute paths.
        if name.startswith("/") or name.startswith("\\"):
            raise RuntimeError(f"Refusing to extract absolute tar member path: {name}")

        # Normalize and enforce extraction root.
        target = (dest_dir / name).resolve()
        if target == dest_dir or str(target).startswith(str(dest_dir) + os.sep):
            pass
        else:
            raise RuntimeError(f"Refusing to extract tar member outside dest: {name}")

        # Refuse links that could point outside root when followed.
        if m.issym() or m.islnk():
            raise RuntimeError(f"Refusing to extract tar link member: {name}")

    tf.extractall(dest_dir)  # noqa: S202 - validated members above


@dataclass(frozen=True)
class ManagedPython:
    version: str
    root: Path
    python: Path


def runtime_home() -> Path:
    """
    Managed runtimes live here. This must not touch Homebrew/system toolchains.
    """
    override = os.environ.get("NEXUS_RUNTIME_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / ".mcp-tools" / "runtime").resolve()


def _version_tuple(version: str) -> Optional[Tuple[int, int, int]]:
    try:
        parts = (version or "").strip().split(".")
        if len(parts) < 2:
            return None
        major = int(parts[0])
        minor = int(parts[1])
        patch = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 0
        return (major, minor, patch)
    except Exception:
        return None


def _is_executable(p: Path) -> bool:
    try:
        st = p.stat()
        return bool(st.st_mode & stat.S_IXUSR)
    except Exception:
        return False


def _find_python3(root: Path) -> Optional[Path]:
    """
    Best-effort locate a python3 executable inside an extracted archive.
    Keeps search bounded to avoid scanning huge trees.
    """
    try:
        # Search a few common locations first.
        for cand in [
            root / "bin" / "python3",
            root / "python" / "bin" / "python3",
            root / "python3" / "bin" / "python3",
        ]:
            if cand.exists() and cand.is_file() and _is_executable(cand):
                return cand

        # Bounded walk (depth <= 6)
        max_depth = 6
        base_parts = len(root.parts)
        for p in root.rglob("python3"):
            try:
                if not p.is_file():
                    continue
                depth = len(p.parts) - base_parts
                if depth > max_depth:
                    continue
                if _is_executable(p):
                    return p
            except Exception:
                continue
        return None
    except Exception:
        return None


def managed_python_dir(version: str) -> Path:
    return runtime_home() / "python" / version


def managed_python_meta_path(version: str) -> Path:
    return managed_python_dir(version) / "meta.json"


def list_managed_pythons() -> list[ManagedPython]:
    out: list[ManagedPython] = []
    root = runtime_home() / "python"
    if not root.exists():
        return out
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        py = d / "bin" / "python3"
        if py.exists():
            out.append(ManagedPython(version=d.name, root=d, python=py))
    return out


def choose_managed_python_at_least(min_major: int, min_minor: int) -> Optional[ManagedPython]:
    best: Optional[ManagedPython] = None
    for mp in list_managed_pythons():
        vt = _version_tuple(mp.version)
        if not vt:
            continue
        if (vt[0], vt[1]) < (min_major, min_minor):
            continue
        if not best:
            best = mp
            continue
        bvt = _version_tuple(best.version)
        if bvt and vt > bvt:
            best = mp
    return best


def ensure_managed_python(
    version: str, *, url: str | None, provider: str = "indygreg", force: bool = False
) -> ManagedPython:
    """
    Download and install a self-contained Python runtime into ~/.mcp-tools/runtime
    (or NEXUS_RUNTIME_HOME). This is isolated from Homebrew/system Python.

    The installed runtime must expose <root>/bin/python3.
    """
    dest = managed_python_dir(version)
    python_link = dest / "bin" / "python3"
    if python_link.exists() and not force:
        return ManagedPython(version=version, root=dest, python=python_link)

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    url = (url or "").strip()
    if not url:
        url = resolve_standalone_python_url(version, provider=provider)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        archive = tmp / "python.tgz"
        urlretrieve(url, archive)  # nosec - controlled by CLI input / internal mapping

        extract_dir = tmp / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive, "r:gz") as tf:
            _safe_extract_tar_gz(tf, extract_dir)

        found = _find_python3(extract_dir)
        if not found:
            raise RuntimeError("Managed Python install failed: python3 executable not found in archive")

        # Move extracted payload into dest/payload for transparency.
        payload = dest / "payload"
        payload.mkdir(parents=True, exist_ok=True)
        # If archive has a single top-level dir, preserve it.
        top = [p for p in extract_dir.iterdir()]
        if len(top) == 1 and top[0].is_dir():
            shutil.move(str(top[0]), str(payload / top[0].name))
            found = _find_python3(payload)
        else:
            shutil.copytree(extract_dir, payload, dirs_exist_ok=True)
            found = _find_python3(payload)

        if not found:
            raise RuntimeError("Managed Python install failed after payload move: python3 not found")

        (dest / "bin").mkdir(parents=True, exist_ok=True)
        if python_link.exists() or python_link.is_symlink():
            python_link.unlink()
        python_link.symlink_to(found)

        meta = {
            "version": version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "source_url": url,
            "python": str(python_link),
        }
        managed_python_meta_path(version).write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return ManagedPython(version=version, root=dest, python=python_link)
