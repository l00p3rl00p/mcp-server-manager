from __future__ import annotations
import argparse
from pathlib import Path
from typing import List

from .config import load_config, save_config
from .inventory import load_inventory, save_inventory, add_manual, upsert_entry, make_entry_id
from .scan import scan_installed
from .gate import decide
from .models import InventoryEntry, InventoryRun, Evidence
from .runtime import running_snapshot
from .util import slugify


def _print_kv(title: str, value: str) -> None:
    print(f"{title}: {value}")


def cmd_config(args: argparse.Namespace) -> int:
    cfg = load_config()
    if args.show:
        print("config.json")
        print(Path.home() / ".mcpinv" / "config.json")
        print()
        print(cfg)
        return 0
    if args.add_root:
        roots = set(cfg.scan_roots)
        roots.add(str(Path(args.add_root).expanduser()))
        cfg.scan_roots = sorted(roots)
        save_config(cfg)
        print("Added scan root.")
        return 0
    if args.deep is not None:
        cfg.deep_scan = bool(args.deep)
        save_config(cfg)
        print("Updated deep_scan.")
        return 0
    return 0


def cmd_inventory_list(args: argparse.Namespace) -> int:
    inv = load_inventory()
    if not inv:
        print("(empty)")
        return 0
    for e in inv.values():
        print(f"- {e.id:24}  {e.status:8}  {e.confidence:9}  {e.run.kind:13}  {e.path or '(no path)'}")
    return 0


def cmd_inventory_add(args: argparse.Namespace) -> int:
    inv = load_inventory()
    name = args.name
    path = args.path
    e = add_manual(inv, name=name, path=path)
    # Optional: set run config if provided
    if args.compose:
        e.run = InventoryRun(kind="docker-compose", compose_file=args.compose, compose_service=args.service, workdir=path)
    if args.start_cmd or args.stop_cmd:
        e.run = InventoryRun(kind="local", start_cmd=args.start_cmd, stop_cmd=args.stop_cmd, workdir=path)
    save_inventory(inv)
    print(f"Added/updated: {e.id}")
    return 0


def _candidate_to_entry(c) -> InventoryEntry:
    eid = make_entry_id(c.inferred_name)
    run = InventoryRun(kind=c.run_kind)
    if c.run_kind == "docker-compose":
        run.compose_file = c.compose_file
        run.workdir = c.path
    entry = InventoryEntry(
        id=eid,
        name=c.inferred_name,
        path=c.path,
        confidence="confirmed" if any(ev.kind.startswith("manifest:") or ev.kind.startswith("dep:@modelcontextprotocol") or ev.kind.startswith("code:modelcontextprotocol") for ev in c.evidence) else "likely",
        transport=c.transport,
        ports=sorted(set(c.ports)),
        env_files=c.env_files,
        run=run,
        evidence=[{"kind": ev.kind, "detail": ev.detail, "weight": ev.weight} for ev in c.evidence],
    )
    return entry


def cmd_inventory_scan(args: argparse.Namespace) -> int:
    cfg = load_config()
    inv = load_inventory()

    cands = scan_installed(
        roots=cfg.scan_roots if not args.roots else args.roots,
        exclude_dir_names=cfg.exclude_dir_names,
        trigger_files=cfg.trigger_files,
        deep_scan=cfg.deep_scan if args.deep is None else bool(args.deep),
        max_candidates=cfg.max_candidates,
    )

    added = 0
    review = 0
    rejected = 0

    for c in cands:
        d = decide(c)
        if d.bucket == "confirmed":
            entry = _candidate_to_entry(c)
            # upsert
            inv[entry.id] = entry
            added += 1
        elif d.bucket == "review":
            review += 1
        else:
            rejected += 1

    save_inventory(inv)

    print(f"Scan complete.")
    print(f"- auto-added (confirmed): {added}")
    print(f"- review candidates:       {review}")
    print(f"- rejected:                {rejected}")
    print()
    print("Tip: use `mcpinv scan --show-review` to print review candidates.")
    if args.show_review:
        print()
        print("REVIEW CANDIDATES")
        for c in cands:
            d = decide(c)
            if d.bucket != "review":
                continue
            evs = ", ".join([e.kind for e in c.evidence[:5]])
            print(f"- {c.path}")
            print(f"  name={c.inferred_name} score={c.score} evidence=[{evs}]")
            print(f"  add: mcpinv add --name {c.inferred_name} --path \"{c.path}\"")
    return 0


def cmd_running(args: argparse.Namespace) -> int:
    snap = running_snapshot()
    if not snap:
        print("(no running observations found)")
        return 0
    for o in snap:
        ports = ",".join(map(str, o.ports)) if o.ports else "-"
        print(f"- {o.kind:8}  {o.name:18}  ports={ports:12}  {o.detail}")
        if o.path_hint:
            print(f"  path_hint={o.path_hint}")
    return 0


def cmd_bootstrap(args: argparse.Namespace) -> int:
    """
    Bootstrap the Git-Packager workspace by fetching missing components.
    
    This command runs the universal bootstrapper to check for and optionally
    fetch missing workspace components (mcp-injector, repo-mcp-packager).
    """
    try:
        # Import and run the universal bootstrapper
        import importlib.util
        
        bootstrap_path = Path(__file__).parent.parent / "bootstrap.py"
        if not bootstrap_path.exists():
            print("❌ bootstrap.py not found. Please download it from:")
            print("   https://github.com/l00p3rl00p/repo-mcp-packager/blob/main/bootstrap.py")
            return 1
        
        # Load and execute bootstrap module
        spec = importlib.util.spec_from_file_location("bootstrap", bootstrap_path)
        bootstrap = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bootstrap)
        bootstrap.main()
        return 0
    except Exception as e:
        print(f"❌ Bootstrap failed: {e}")
        return 1


def main() -> None:
    p = argparse.ArgumentParser(prog="mcpinv", description="Local MCP discovery + curated inventory.")
    sub = p.add_subparsers(dest="cmd", required=True)

    pcfg = sub.add_parser("config", help="Show/update config.")
    pcfg.add_argument("--show", action="store_true")
    pcfg.add_argument("--add-root", type=str)
    pcfg.add_argument("--deep", type=int, choices=[0, 1])
    pcfg.set_defaults(func=cmd_config)

    plist = sub.add_parser("list", help="List inventory.")
    plist.set_defaults(func=cmd_inventory_list)

    padd = sub.add_parser("add", help="Add/update inventory entry (manual).")
    padd.add_argument("--name", required=True)
    padd.add_argument("--path")
    padd.add_argument("--compose", help="compose file name (e.g., docker-compose.yml)")
    padd.add_argument("--service", help="compose service name")
    padd.add_argument("--start-cmd")
    padd.add_argument("--stop-cmd")
    padd.set_defaults(func=cmd_inventory_add)

    pscan = sub.add_parser("scan", help="Scan for MCP candidates; auto-add confirmed only.")
    pscan.add_argument("--roots", nargs="*", help="Override scan roots")
    pscan.add_argument("--deep", type=int, choices=[0, 1], help="Override deep_scan")
    pscan.add_argument("--show-review", action="store_true")
    pscan.set_defaults(func=cmd_inventory_scan)

    prun = sub.add_parser("running", help="Show running observations (docker + mcp-ish processes).")
    prun.set_defaults(func=cmd_running)

    pboot = sub.add_parser("bootstrap", help="Bootstrap the Git-Packager workspace (fetch missing components).")
    pboot.set_defaults(func=cmd_bootstrap)

    args = p.parse_args()
    rc = args.func(args)
    raise SystemExit(rc)
