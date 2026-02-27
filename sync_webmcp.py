#!/usr/bin/env python3
"""
sync_webmcp.py — Post-build capability sync for webmcp_server.py
=================================================================
Called automatically by the `postbuild` npm hook in gui/package.json
immediately after `tsc -b && vite build` succeeds.

What it does
------------
1. Hits GET /capabilities on the running gui_bridge (port 5001).
2. Loads the current webmcp_capabilities.json registry.
3. Adds any Flask routes not yet in the registry.
4. Removes dynamic registry entries whose route no longer exists in Flask.
5. Writes the updated registry back to disk.
6. Prints a human-readable summary to stdout.

The webmcp_server.py MCP process loads the registry fresh on each
startup, so the next time any IDE restarts the MCP server it will
see the updated tool set.

Usage
-----
    python3 sync_webmcp.py [--dry-run] [--base-url http://127.0.0.1:5001]

Exit codes
----------
    0  Success (or dry-run with no errors)
    1  Could not reach gui_bridge (non-fatal warning, build still passes)
    2  Unexpected error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("[sync_webmcp] WARNING: 'requests' not installed — skipping sync.", file=sys.stderr)
    sys.exit(0)  # non-fatal: don't break the build

REGISTRY_PATH = Path(__file__).parent / "webmcp_capabilities.json"
DEFAULT_BASE  = "http://127.0.0.1:5001"

# Slugs that belong to built-in static tools — never auto-added as dynamic
STATIC_NAMES: frozenset[str] = frozenset([
    "gui_health", "gui_status", "gui_validate", "gui_system_drift",
    "gui_logs", "gui_server_logs",
    "gui_server_control", "gui_server_add", "gui_server_delete", "gui_server_update",
    "gui_nexus_catalog", "gui_nexus_run",
    "gui_injector_clients", "gui_injector_status",
    "gui_forge", "gui_forge_status",
    "gui_librarian_roots", "gui_librarian_add",
    "gui_project_history", "gui_project_snapshot",
    "gui_export_report",
    # meta-tools
    "gui_sync_capabilities", "gui_register_tool", "gui_unregister_tool", "gui_list_registry",
])


def _load_registry() -> dict[str, dict]:
    if not REGISTRY_PATH.exists():
        return {}
    try:
        raw = json.loads(REGISTRY_PATH.read_text())
        return raw.get("tools", {})
    except Exception as exc:
        print(f"[sync_webmcp] Warning: could not read registry: {exc}", file=sys.stderr)
        return {}


def _save_registry(tools: dict[str, dict]) -> None:
    data = {"version": 1, "tools": tools}
    REGISTRY_PATH.write_text(json.dumps(data, indent=2))


def _fetch_capabilities(base_url: str) -> list[dict] | None:
    try:
        r = requests.get(f"{base_url}/capabilities", timeout=8)
        r.raise_for_status()
        return r.json().get("routes", [])
    except requests.exceptions.ConnectionError:
        print(
            f"[sync_webmcp] gui_bridge not reachable at {base_url}. "
            "Skipping sync (backend must be running for a live sync).",
            file=sys.stderr,
        )
        return None
    except Exception as exc:
        print(f"[sync_webmcp] Error fetching capabilities: {exc}", file=sys.stderr)
        return None


def sync(base_url: str, dry_run: bool) -> int:
    print(f"[sync_webmcp] {'DRY RUN — ' if dry_run else ''}syncing capabilities from {base_url}")

    routes = _fetch_capabilities(base_url)
    if routes is None:
        return 1  # non-fatal

    registry = _load_registry()
    live_paths: set[str] = {r["path"] for r in routes}

    added:   list[str] = []
    removed: list[str] = []

    # ── Add new routes ───────────────────────────────────────────────────────
    for route in routes:
        slug = route.get("slug", "")
        if not slug or slug in STATIC_NAMES or slug in registry:
            continue
        entry = {
            "name":        slug,
            "description": f"Auto-synced: {route.get('description', slug)}",
            "method":      (route.get("methods") or ["GET"])[0],
            "path":        route["path"],
            "inputSchema": {"type": "object", "properties": {}, "required": []},
        }
        if not dry_run:
            registry[slug] = entry
        added.append(slug)

    # ── Remove stale dynamic tools ────────────────────────────────────────────
    stale = [
        name for name, entry in list(registry.items())
        if entry.get("path") and entry["path"] not in live_paths
    ]
    for name in stale:
        if not dry_run:
            del registry[name]
        removed.append(name)

    # ── Persist ───────────────────────────────────────────────────────────────
    if not dry_run and (added or removed):
        _save_registry(registry)

    # ── Summary ───────────────────────────────────────────────────────────────
    unchanged = len(registry) - len(added)

    if added:
        print(f"  ✓ Added   ({len(added)}): {', '.join(added)}")
    if removed:
        print(f"  ✗ Removed ({len(removed)}): {', '.join(removed)}")
    if not added and not removed:
        print(f"  ✓ No changes — {unchanged} dynamic tools already up to date.")
    else:
        print(f"  ● Total dynamic tools: {len(registry)}")

    if dry_run:
        print("  [dry-run] No files were written.")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync webmcp tool registry with live gui_bridge routes.")
    parser.add_argument("--dry-run",  action="store_true", help="Report changes without writing.")
    parser.add_argument("--base-url", default=DEFAULT_BASE, help=f"gui_bridge base URL (default: {DEFAULT_BASE})")
    args = parser.parse_args()

    try:
        code = sync(args.base_url, args.dry_run)
        sys.exit(code)
    except Exception as exc:
        print(f"[sync_webmcp] Unexpected error: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
