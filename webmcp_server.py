#!/usr/bin/env python3
"""
webmcp_server.py — MCP Stdio Wrapper for the Nexus GUI Backend
================================================================
Exposes the mcp-server-manager Flask bridge (gui_bridge.py, port 5001)
as a proper MCP stdio server so agents can test and manipulate the GUI
without a browser.

Protocol : JSON-RPC 2.0 over stdin/stdout  (MCP spec 2024-11-05)
Backend  : http://127.0.0.1:5001            (gui_bridge.py)
Registry : webmcp_capabilities.json         (next to this file)

── Dynamic capability registry ───────────────────────────────────────
Tools are split into two tiers:

  STATIC  — hard-coded in STATIC_TOOLS; always present; cannot be
             removed via gui_unregister_tool.

  DYNAMIC — stored in webmcp_capabilities.json; added / removed at
             runtime via gui_register_tool / gui_unregister_tool; or
             bulk-synced from the live Flask route map via
             gui_sync_capabilities (called automatically after every
             `npm run build` via the postbuild hook).

── Post-build auto-sync ──────────────────────────────────────────────
  gui/package.json  "postbuild": "python3 ../sync_webmcp.py"
  sync_webmcp.py    Calls gui_bridge GET /capabilities, diffs against
                    the current registry, and patches the JSON file so
                    the next MCP session picks up the changes.

── Usage (stdio transport) ───────────────────────────────────────────
  python3 webmcp_server.py

── Claude / Antigravity / Codex settings entry ───────────────────────
  "nexus-gui": {
      "command": "python3",
      "args": ["/path/to/mcp-server-manager/webmcp_server.py"],
      "env": { "GUI_BASE_URL": "http://127.0.0.1:5001" }
  }
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

import requests

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

GUI_BASE        = os.environ.get("GUI_BASE_URL", "http://127.0.0.1:5001").rstrip("/")
DEFAULT_TIMEOUT = 15  # seconds
SERVER_NAME     = "nexus-gui"
SERVER_VERSION  = "2.0.0"

# Persisted dynamic registry — lives next to this file so it's version-controlled
REGISTRY_PATH   = Path(__file__).parent / "webmcp_capabilities.json"

# ──────────────────────────────────────────────────────────────────────────────
# HTTP helpers
# ──────────────────────────────────────────────────────────────────────────────

def _get(path: str, params: dict | None = None) -> dict:
    url = f"{GUI_BASE}{path}"
    try:
        r = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        return {"ok": r.ok, "status": r.status_code, "data": _safe_json(r)}
    except requests.RequestException as exc:
        return {"ok": False, "status": 0, "error": str(exc)}


def _post(path: str, body: dict | None = None) -> dict:
    url = f"{GUI_BASE}{path}"
    try:
        r = requests.post(url, json=body or {}, timeout=DEFAULT_TIMEOUT)
        return {"ok": r.ok, "status": r.status_code, "data": _safe_json(r)}
    except requests.RequestException as exc:
        return {"ok": False, "status": 0, "error": str(exc)}


def _delete(path: str, body: dict | None = None) -> dict:
    url = f"{GUI_BASE}{path}"
    try:
        r = requests.delete(url, json=body or {}, timeout=DEFAULT_TIMEOUT)
        return {"ok": r.ok, "status": r.status_code, "data": _safe_json(r)}
    except requests.RequestException as exc:
        return {"ok": False, "status": 0, "error": str(exc)}


def _safe_json(r: requests.Response) -> Any:
    try:
        return r.json()
    except Exception:
        return r.text[:2000]


# ──────────────────────────────────────────────────────────────────────────────
# Static tool definitions  (always present; cannot be removed)
# ──────────────────────────────────────────────────────────────────────────────

STATIC_TOOLS: list[dict] = [
    # ── Health / Status ──────────────────────────────────────────────────────
    {
        "name": "gui_health",
        "description": "Check that the Nexus GUI backend is alive.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "gui_status",
        "description": (
            "Get full system status: all registered MCP servers, CPU/mem metrics, "
            "Python environments, and drift alerts."
        ),
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "gui_validate",
        "description": "Validate the current MCP configuration.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "gui_system_drift",
        "description": "Detect config drift — servers that have changed on disk vs the inventory.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    # ── Logs ─────────────────────────────────────────────────────────────────
    {
        "name": "gui_logs",
        "description": "Retrieve the Nexus session log (last N entries).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max entries (default 100).", "default": 100}
            },
            "required": [],
        },
    },
    {
        "name": "gui_server_logs",
        "description": "Retrieve stdout/stderr logs for a specific running MCP server.",
        "inputSchema": {
            "type": "object",
            "properties": {"server_id": {"type": "string"}},
            "required": ["server_id"],
        },
    },
    # ── Server lifecycle ──────────────────────────────────────────────────────
    {
        "name": "gui_server_control",
        "description": "Start, stop, or restart a registered MCP server.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "server_id": {"type": "string"},
                "action": {"type": "string", "enum": ["start", "stop", "restart"]},
            },
            "required": ["server_id", "action"],
        },
    },
    {
        "name": "gui_server_add",
        "description": "Register a new MCP server into the Nexus inventory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name":        {"type": "string"},
                "server_id":   {"type": "string"},
                "start_cmd":   {"type": "string"},
                "description": {"type": "string"},
                "auto_start":  {"type": "boolean"},
            },
            "required": ["name", "server_id", "start_cmd"],
        },
    },
    {
        "name": "gui_server_delete",
        "description": "Remove a server from the Nexus inventory.",
        "inputSchema": {
            "type": "object",
            "properties": {"server_id": {"type": "string"}},
            "required": ["server_id"],
        },
    },
    {
        "name": "gui_server_update",
        "description": "Update a server's metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "server_id":   {"type": "string"},
                "name":        {"type": "string"},
                "start_cmd":   {"type": "string"},
                "description": {"type": "string"},
                "auto_start":  {"type": "boolean"},
            },
            "required": ["server_id"],
        },
    },
    # ── Catalog / Injector / Forge / Librarian / Project / Export ────────────
    {
        "name": "gui_nexus_catalog",
        "description": "Browse the Nexus server catalog.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "gui_nexus_run",
        "description": "Run a Nexus CLI command against the catalog.",
        "inputSchema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "gui_injector_clients",
        "description": "List all detected MCP clients on this machine.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "gui_injector_status",
        "description": "Get or set a server's enabled state in a specific MCP client.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string"},
                "server_id": {"type": "string"},
                "enabled":   {"type": "boolean"},
            },
            "required": ["client_id", "server_id", "enabled"],
        },
    },
    {
        "name": "gui_forge",
        "description": "Scaffold a new MCP server from a template.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name":        {"type": "string"},
                "template":    {"type": "string"},
                "description": {"type": "string"},
                "output_dir":  {"type": "string"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "gui_forge_status",
        "description": "Poll the status of an in-progress Forge task.",
        "inputSchema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
        },
    },
    {
        "name": "gui_librarian_roots",
        "description": "List, add, or remove watched root directories for the Librarian.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "add", "remove"], "default": "list"},
                "path":   {"type": "string"},
            },
            "required": ["action"],
        },
    },
    {
        "name": "gui_librarian_add",
        "description": "Index a URL or file path into the knowledge base.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url":        {"type": "string"},
                "stack":      {"type": "string"},
                "categories": {"type": "string"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "gui_project_history",
        "description": "Retrieve recent project change history.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "gui_project_snapshot",
        "description": "Take a snapshot of the current project state.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "gui_export_report",
        "description": "Generate the full Nexus HTML status report.",
        "inputSchema": {
            "type": "object",
            "properties": {"server_id": {"type": "string"}},
            "required": [],
        },
    },

    # ── Registry meta-tools ───────────────────────────────────────────────────
    {
        "name": "gui_sync_capabilities",
        "description": (
            "Fetch the live route map from GET /capabilities on the GUI backend and "
            "reconcile the dynamic tool registry. Adds routes that are not yet "
            "registered; removes dynamic tools whose route no longer exists. "
            "Call this after every `npm run build` (the postbuild hook does it "
            "automatically). Returns a summary of added/removed/unchanged tools."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, report changes without writing them. Default false.",
                    "default": False,
                }
            },
            "required": [],
        },
    },
    {
        "name": "gui_register_tool",
        "description": (
            "Manually register a new dynamic tool that proxies an arbitrary "
            "gui_bridge endpoint. The tool is persisted to webmcp_capabilities.json "
            "and is immediately available in the current session."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name":        {"type": "string",  "description": "MCP tool name (must be unique, prefix 'gui_' recommended)."},
                "description": {"type": "string",  "description": "Human-readable description."},
                "method":      {"type": "string",  "enum": ["GET", "POST", "DELETE"], "description": "HTTP method."},
                "path":        {"type": "string",  "description": "Flask route path, e.g. /analytics/summary"},
                "input_schema": {
                    "type": "object",
                    "description": "JSON Schema for the tool's arguments (optional).",
                },
            },
            "required": ["name", "description", "method", "path"],
        },
    },
    {
        "name": "gui_unregister_tool",
        "description": (
            "Remove a dynamic tool from the registry. "
            "Static (built-in) tools cannot be removed."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Exact tool name to remove."}
            },
            "required": ["name"],
        },
    },
    {
        "name": "gui_list_registry",
        "description": "List all registered tools, showing which are static vs dynamic.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
]

STATIC_NAMES: frozenset[str] = frozenset(t["name"] for t in STATIC_TOOLS)


# ──────────────────────────────────────────────────────────────────────────────
# Dynamic registry  (loaded from / persisted to webmcp_capabilities.json)
# ──────────────────────────────────────────────────────────────────────────────

def _load_registry() -> dict[str, dict]:
    """Load the persisted dynamic tool registry.

    Schema of webmcp_capabilities.json:
    {
      "version": 1,
      "tools": {
        "<tool_name>": {
          "name": "...",
          "description": "...",
          "method": "GET|POST|DELETE",
          "path": "/some/flask/route",
          "inputSchema": { ... }   ← MCP input schema
        }
      }
    }
    """
    if not REGISTRY_PATH.exists():
        return {}
    try:
        raw = json.loads(REGISTRY_PATH.read_text())
        return raw.get("tools", {})
    except Exception as exc:
        print(f"[webmcp] Warning: could not read registry ({exc}), starting empty.", file=sys.stderr)
        return {}


def _save_registry(tools: dict[str, dict]) -> None:
    data = {"version": 1, "tools": tools}
    REGISTRY_PATH.write_text(json.dumps(data, indent=2))


# Mutable in-process registry  {name: tool_definition}
_DYNAMIC: dict[str, dict] = _load_registry()


def _all_tools() -> list[dict]:
    """Return static tools + dynamic tools as a single list (static first)."""
    dynamic_as_mcp = []
    for entry in _DYNAMIC.values():
        dynamic_as_mcp.append({
            "name": entry["name"],
            "description": entry["description"],
            "inputSchema": entry.get("inputSchema", {"type": "object", "properties": {}, "required": []}),
        })
    return STATIC_TOOLS + dynamic_as_mcp


# ──────────────────────────────────────────────────────────────────────────────
# Static tool dispatch
# ──────────────────────────────────────────────────────────────────────────────

def _dispatch_static(name: str, args: dict) -> Any:
    if name == "gui_health":
        return _get("/health")
    if name == "gui_status":
        return _get("/status")
    if name == "gui_validate":
        return _get("/validate")
    if name == "gui_system_drift":
        return _get("/system/drift")
    if name == "gui_logs":
        return _get("/logs", params={"limit": args.get("limit", 100)})
    if name == "gui_server_logs":
        return _get(f"/server/logs/{args['server_id']}")
    if name == "gui_server_control":
        return _post("/server/control", {"server_id": args["server_id"], "action": args["action"]})
    if name == "gui_server_add":
        return _post("/server/add", args)
    if name == "gui_server_delete":
        return _post("/server/delete", {"server_id": args["server_id"]})
    if name == "gui_server_update":
        sid = args.pop("server_id")
        return _post(f"/server/update/{sid}", args)
    if name == "gui_nexus_catalog":
        return _get("/nexus/catalog")
    if name == "gui_nexus_run":
        return _post("/nexus/run", {"command": args["command"]})
    if name == "gui_injector_clients":
        return _get("/injector/clients")
    if name == "gui_injector_status":
        return _post("/injector/status", args)
    if name == "gui_forge":
        return _post("/forge", args)
    if name == "gui_forge_status":
        return _get(f"/forge/status/{args['task_id']}")
    if name == "gui_librarian_roots":
        action = args.get("action", "list")
        if action == "list":
            return _get("/librarian/roots")
        if action == "add":
            return _post("/librarian/roots", {"path": args.get("path")})
        if action == "remove":
            return _delete("/librarian/roots", {"path": args.get("path")})
        return {"ok": False, "error": f"Unknown action: {action}"}
    if name == "gui_librarian_add":
        return _post("/librarian/add", args)
    if name == "gui_project_history":
        return _get("/project/history")
    if name == "gui_project_snapshot":
        return _post("/project/snapshot")
    if name == "gui_export_report":
        params = {"server": args["server_id"]} if "server_id" in args else None
        return _get("/export/report", params=params)

    # ── Registry meta-tools ───────────────────────────────────────────────────
    if name == "gui_list_registry":
        return {
            "ok": True,
            "static": sorted(STATIC_NAMES),
            "dynamic": {k: v for k, v in _DYNAMIC.items()},
            "total": len(STATIC_NAMES) + len(_DYNAMIC),
        }

    if name == "gui_register_tool":
        return _op_register(args)

    if name == "gui_unregister_tool":
        return _op_unregister(args["name"])

    if name == "gui_sync_capabilities":
        return _op_sync(dry_run=args.get("dry_run", False))

    return None  # signal: not a static tool


# ──────────────────────────────────────────────────────────────────────────────
# Registry operations
# ──────────────────────────────────────────────────────────────────────────────

def _op_register(args: dict) -> dict:
    tool_name = args["name"]
    if tool_name in STATIC_NAMES:
        return {"ok": False, "error": f"'{tool_name}' is a static tool and cannot be overridden."}

    entry = {
        "name":        tool_name,
        "description": args["description"],
        "method":      args.get("method", "GET").upper(),
        "path":        args["path"],
        "inputSchema": args.get("input_schema") or {"type": "object", "properties": {}, "required": []},
    }
    _DYNAMIC[tool_name] = entry
    _save_registry(_DYNAMIC)
    return {"ok": True, "registered": tool_name, "entry": entry}


def _op_unregister(tool_name: str) -> dict:
    if tool_name in STATIC_NAMES:
        return {"ok": False, "error": f"'{tool_name}' is a static (built-in) tool and cannot be removed."}
    if tool_name not in _DYNAMIC:
        return {"ok": False, "error": f"'{tool_name}' is not in the dynamic registry."}
    del _DYNAMIC[tool_name]
    _save_registry(_DYNAMIC)
    return {"ok": True, "unregistered": tool_name}


def _op_sync(dry_run: bool = False) -> dict:
    """Fetch GET /capabilities from the bridge and reconcile the registry.

    - Routes that exist in Flask but not in the registry → added.
    - Dynamic tools whose Flask route no longer exists → removed.
    - Static tools are never touched.
    Returns { ok, added: [...], removed: [...], unchanged: int, dry_run: bool }
    """
    resp = _get("/capabilities")
    if not resp.get("ok"):
        return {"ok": False, "error": "Could not reach /capabilities", "detail": resp}

    live_routes: list[dict] = resp["data"].get("routes", [])
    live_paths: set[str] = {r["path"] for r in live_routes}

    # Build a slug → route map from what Flask reported
    live_by_slug: dict[str, dict] = {}
    for route in live_routes:
        slug = route.get("slug", "")
        if slug and slug not in STATIC_NAMES:
            live_by_slug[slug] = route

    added:   list[str] = []
    removed: list[str] = []

    # 1. Add routes that are live in Flask but missing from the registry
    for slug, route in live_by_slug.items():
        if slug not in _DYNAMIC and slug not in STATIC_NAMES:
            entry = {
                "name":        slug,
                "description": f"Auto-synced: {route['description']}",
                "method":      route["methods"][0] if route["methods"] else "GET",
                "path":        route["path"],
                "inputSchema": {"type": "object", "properties": {}, "required": []},
            }
            if not dry_run:
                _DYNAMIC[slug] = entry
            added.append(slug)

    # 2. Remove dynamic tools whose Flask route no longer exists
    stale = [
        name for name, entry in list(_DYNAMIC.items())
        if entry.get("path") and entry["path"] not in live_paths
    ]
    for name in stale:
        if not dry_run:
            del _DYNAMIC[name]
        removed.append(name)

    if not dry_run and (added or removed):
        _save_registry(_DYNAMIC)

    unchanged = len(_DYNAMIC) - len(added) if not dry_run else len(_DYNAMIC)
    return {
        "ok":       True,
        "dry_run":  dry_run,
        "added":    added,
        "removed":  removed,
        "unchanged": unchanged,
        "total_dynamic": len(_DYNAMIC),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Dynamic tool dispatch (routes stored in _DYNAMIC)
# ──────────────────────────────────────────────────────────────────────────────

def _dispatch_dynamic(name: str, args: dict) -> dict:
    entry = _DYNAMIC.get(name)
    if entry is None:
        return {"ok": False, "error": f"Unknown tool: {name}"}

    method = entry.get("method", "GET").upper()
    path   = entry["path"]

    if method == "GET":
        return _get(path, params=args or None)
    if method == "POST":
        return _post(path, args or None)
    if method == "DELETE":
        return _delete(path, args or None)

    return {"ok": False, "error": f"Unsupported HTTP method: {method}"}


# ──────────────────────────────────────────────────────────────────────────────
# Unified dispatch
# ──────────────────────────────────────────────────────────────────────────────

def _dispatch(name: str, args: dict) -> Any:
    result = _dispatch_static(name, args)
    if result is not None:
        return result
    return _dispatch_dynamic(name, args)


# ──────────────────────────────────────────────────────────────────────────────
# MCP JSON-RPC stdio protocol
# ──────────────────────────────────────────────────────────────────────────────

def _send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _ok(req_id: Any, result: Any) -> None:
    _send({"jsonrpc": "2.0", "id": req_id, "result": result})


def _err(req_id: Any, code: int, message: str, data: Any = None) -> None:
    err: dict = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    _send({"jsonrpc": "2.0", "id": req_id, "error": err})


def _handle(msg: dict) -> None:
    method  = msg.get("method", "")
    req_id  = msg.get("id")
    params  = msg.get("params") or {}

    if method == "initialize":
        _ok(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        })
        return

    if method == "notifications/initialized":
        return

    if method == "ping":
        _ok(req_id, {})
        return

    if method == "tools/list":
        _ok(req_id, {"tools": _all_tools()})
        return

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = dict(params.get("arguments") or {})
        try:
            result = _dispatch(tool_name, arguments)
        except Exception:
            _err(req_id, -32603, f"Tool error: {tool_name}",
                 {"traceback": traceback.format_exc()})
            return
        _ok(req_id, {
            "content":  [{"type": "text", "text": json.dumps(result, indent=2)}],
            "isError":  not result.get("ok", True),
        })
        return

    if req_id is not None:
        _err(req_id, -32601, f"Method not found: {method}")


def main() -> None:
    n_dynamic = len(_DYNAMIC)
    n_static  = len(STATIC_TOOLS)
    print(
        f"[webmcp] Nexus GUI MCP server v{SERVER_VERSION} ready. "
        f"Backend: {GUI_BASE}  |  "
        f"Static: {n_static}  Dynamic: {n_dynamic}  Total: {n_static + n_dynamic}",
        file=sys.stderr,
    )

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError as exc:
            _send({"jsonrpc": "2.0", "id": None,
                   "error": {"code": -32700, "message": f"Parse error: {exc}"}})
            continue
        try:
            _handle(msg)
        except Exception:
            _send({"jsonrpc": "2.0", "id": msg.get("id"),
                   "error": {"code": -32603, "message": "Internal server error",
                             "data": traceback.format_exc()}})


if __name__ == "__main__":
    main()
