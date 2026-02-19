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

# Send macOS Notification
osascript -e 'display notification "Launching Dashboard..." with title "Workforce Nexus"'

echo "🚀 Starting Workforce Nexus..."
echo "📍 Project: $PROJECT_DIR"

# 1. Activate Environment
if [ -d "$PROJECT_DIR/.venv" ]; then
    echo "🐍 Using Virtual Environment"
    source "$PROJECT_DIR/.venv/bin/activate"
fi

cd "$PROJECT_DIR" || { echo "❌ ERROR: Directory not found"; exit 1; }

# 2. Launch Tray & Bridge
# We use 'exec' to replace the terminal session with the python process.
# nexus_tray.py will handle opening the browser automatically.
echo "🔗 URL: http://localhost:5001"
echo "📦 Look for the Indigo dot in your menu bar."
echo "------------------------------------------------"

exec python3 nexus_tray.py

