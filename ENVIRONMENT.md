# Environment

## Requirements
- Python 3.10+
- Docker CLI (optional, for running detection)
- macOS / Linux recommended (Windows may work but process/port behaviors vary)

## Files created
- `~/.mcpinv/config.json`
- `~/.mcpinv/inventory.yaml`

## Config
Defaults:
- Scan roots:
  - `~/Code`, `~/Projects`, `~/Dev`, `~/Documents`
- Exclusions:
  - `.git`, `node_modules`, `.venv`, caches, build outputs

## Optional conventions (to improve accuracy)
### 1) Manifest file
Place in any MCP folder:
- `mcp.server.json`

### 2) `.env` marker
Add:
- `MCP_SERVER_NAME=your-server-name`

This upgrades `.env` from weak to strong signal (scan can confirm).
