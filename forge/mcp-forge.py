#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
from forge_engine import ForgeEngine

def main():
    parser = argparse.ArgumentParser(description="Workforce Nexus Forge: The Factory Release")
    parser.add_argument("--dir", type=str, help="Local directory to forge")
    parser.add_argument("--repo", type=str, help="Remote Git repository to clone and forge")
    parser.add_argument("--name", type=str, help="Optional name for the forged server")
    parser.add_argument("--stack", type=str, help="Tag forged server with a named librarian stack")

    args = parser.parse_args()

    # Determine suite root
    script_path = Path(__file__).resolve()
    suite_root = script_path.parent.parent.parent # /mcp-server-manager/forge/mcp-forge -> /mcp-creater-manager
    
    engine = ForgeEngine(suite_root)

    try:
        source = args.repo if args.repo else args.dir
        if not source:
            parser.print_help()
            sys.exit(1)
            
        target = engine.forge(source, args.name, stack=getattr(args, 'stack', None))
        print(f"\nSUCCESS: Forged server ready at: {target}")
    except Exception as e:
        print(f"\nERROR during forge: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
