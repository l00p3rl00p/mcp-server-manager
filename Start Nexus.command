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

# 2. Launch Tray & Bridge (Backgrounded)
echo "🔗 URL: http://localhost:5001"
echo "📦 Look for the Indigo dot in your menu bar."
echo "------------------------------------------------"
echo "✅ Launching background process. You can close this window."

# Run in background, ignoring HUP signal so it survives terminal closure
nohup python3 nexus_tray.py > "$HOME/.mcpinv/nexus.log" 2>&1 &

# Give it a moment to initialize
sleep 2

exit 0

