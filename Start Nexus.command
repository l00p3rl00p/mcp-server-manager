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

# 1. Activate Environment (Central or Local)
NEXUS_VENV="$HOME/.mcp-tools/.venv"
if [ -f "$NEXUS_VENV/bin/activate" ]; then
    echo "🐍 Using Central Virtual Environment"
    source "$NEXUS_VENV/bin/activate"
elif [ -d "$PROJECT_DIR/.venv" ]; then
    echo "🐍 Using Local Virtual Environment"
    source "$PROJECT_DIR/.venv/bin/activate"
fi

cd "$PROJECT_DIR" || { echo "❌ ERROR: Directory not found"; exit 1; }

# 2. Launch Tray & Bridge (Backgrounded)
echo "🔗 URL: http://localhost:5001"
echo "📦 Look for the Indigo dot in your menu bar."
echo "------------------------------------------------"
echo "✅ Launching background process. You can close this window."

# Run in background, ignoring HUP signal so it survives terminal closure
mkdir -p "$HOME/.mcpinv"
nohup python3 nexus_tray.py > "$HOME/.mcpinv/nexus.log" 2>&1 &
PID=$!
disown $PID
echo "$PID" > "$HOME/.mcpinv/nexus.pid" 2>/dev/null || true

# Give it a moment to initialize
sleep 2

# Verify it's still running
if kill -0 $PID 2>/dev/null; then
    echo "✅ Success! Process $PID running in background."
    echo "👋 Shutting down terminal session..."
else
    echo "❌ Start failed! Check $HOME/.mcpinv/nexus.log for errors."
    cat "$HOME/.mcpinv/nexus.log"
    # Keep window open to show error
    read -p "Press Enter to close..."
    exit 1
fi

exit 0
