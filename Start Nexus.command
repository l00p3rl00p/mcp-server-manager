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

# If port 5001 is already in use by a previous Nexus instance, stop it before relaunch.
# If it's not Nexus, refuse (don’t kill random services).
python3 - <<'PY'
import os, socket, subprocess, time
from pathlib import Path

port = int(os.environ.get("NEXUS_PORT","5001"))
host = os.environ.get("NEXUS_BIND","127.0.0.1")

def listening()->bool:
    s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.2)
    try:
        return s.connect_ex((host, port))==0
    finally:
        s.close()

if not listening():
    raise SystemExit(0)

pid_file = Path.home()/".mcpinv"/"nexus.pid"
pid = None
try:
    if pid_file.exists():
        pid = pid_file.read_text().strip().splitlines()[0].strip()
except Exception:
    pid = None

def cmdline(pid: str) -> str:
    try:
        return subprocess.check_output(["ps","-p",pid,"-o","command="], text=True).strip()
    except Exception:
        return ""

if pid:
    cmd = cmdline(pid)
    if ("nexus_tray.py" in cmd) or ("gui_bridge.py" in cmd):
        try:
            os.kill(int(pid), 15)
        except Exception:
            pass
        time.sleep(0.4)
        if listening():
            try:
                os.kill(int(pid), 9)
            except Exception:
                pass
            time.sleep(0.2)

if listening():
    raise SystemExit(2)
raise SystemExit(0)
PY
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "❌ Cannot launch Nexus because port 5001 is in use by a non-Nexus process."
  echo "💡 Fix: close the other app using port 5001, then try again."
  read -p "Press Enter to close..."
  exit 1
fi

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
