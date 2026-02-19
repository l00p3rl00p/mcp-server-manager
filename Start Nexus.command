#!/bin/bash
# ============================================================
#  Start Nexus.command
#  Double-click this file in Finder to launch the Nexus GUI.
#  You can move or copy this file anywhere — it always finds
#  the project via the embedded path below.
#
#  Stop the server: click the menu-bar icon → "Stop & Quit"
#  Closing the browser window does NOT stop the server.
# ============================================================

PROJECT_DIR="/Users/almowplay/Developer/Github/mcp-creater-manager/mcp-server-manager"

# Activate venv if present, otherwise use system python3
VENV="$PROJECT_DIR/.venv/bin/activate"
if [ -f "$VENV" ]; then
    source "$VENV"
fi

cd "$PROJECT_DIR" || { echo "ERROR: project dir not found: $PROJECT_DIR"; exit 1; }

# Launch tray app (no terminal stays open after this — .command files
# keep their own window but nexus_tray.py moves to the menu bar)
exec python3 nexus_tray.py
