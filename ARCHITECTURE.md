# Architecture

## Core idea
**Scan wide, accept strict.**

- Wide scan finds candidates using cheap trigger files.
- Gate decides:
  - Confirmed = auto-add
  - Review = show candidate (user can add)
  - Rejected = ignore

Inventory remains the source of truth.

## Modules

- `scan.py`
  - Crawls scan roots, excludes noisy dirs, emits `Candidate` objects with evidence + score.

- `gate.py`
  - Hard acceptance gate:
    - Strong signals → confirmed
    - Medium signals → review
    - Weak/no signals → reject

- `inventory.py`
  - Reads/writes `~/.mcpinv/inventory.yaml`.
  - Manual add/update support.

- `runtime.py`
  - Running observations for heartbeat:
    - Docker `ps`
    - MCP-ish process commandlines

- `cli.py`
  - Operator commands:
    - `scan`, `add`, `list`, `running`, `config`

## Strong MCP signals (auto-accept)
Any one of:
- `mcp.server.json` or `mcp.json` present
- `package.json` depends on `@modelcontextprotocol/*`
- code references `modelcontextprotocol`
- docker labels `io.mcp.*` (future extension)

## Medium signals (review)
- README mentions MCP
- compose service name suggests MCP
- `.env` contains LLM-ish keys

## Weak signals (reject)
- `.env` alone
