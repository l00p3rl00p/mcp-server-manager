#!/usr/bin/env python3
"""
nexus_tray.py — Nexus GUI system tray entry point.

Starts the Flask bridge in a daemon thread and lives as a
macOS menu-bar / Windows system-tray icon.  Double-click the
Desktop launcher (Start Nexus.command / Start Nexus.bat) to
launch this — never run gui_bridge.py directly from a terminal.

Stop the server via the tray menu: "Stop & Quit".
Closing the browser tab does NOT stop the server.
"""

import threading
import webbrowser
import platform
import time
import sys
import os
from pathlib import Path

# ── Ensure the project root is on sys.path so gui_bridge imports cleanly ──
PROJECT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_DIR))

# ── Port must match gui_bridge.py ──
PORT = int(os.environ.get("NEXUS_PORT", "5001"))
HOST = os.environ.get("NEXUS_BIND", "127.0.0.1")
DASHBOARD_URL = f"http://localhost:{PORT}"

# ────────────────────────────────────────────────────────────────────────────
# Icon — generate a simple coloured dot; replace with a real .png if desired
# ────────────────────────────────────────────────────────────────────────────
def _make_icon():
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Indigo filled circle
        draw.ellipse([4, 4, 60, 60], fill=(99, 102, 241, 255))
        # Small white dot in centre (status indicator)
        draw.ellipse([26, 26, 38, 38], fill=(255, 255, 255, 220))
        return img
    except ImportError:
        # pystray will use a blank icon — Pillow is expected to be present
        return None


# ────────────────────────────────────────────────────────────────────────────
# Flask runner — runs on a daemon thread so it exits when main thread exits
# ────────────────────────────────────────────────────────────────────────────
def _run_flask():
    """Import and start the Flask app from gui_bridge.py."""
    try:
        from gui_bridge import app, session_logger
        if session_logger:
            session_logger.log(
                "LIFECYCLE",
                "System Tray GUI Started",
                suggestion=f"Dashboard now available at {DASHBOARD_URL}",
            )
        app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
    except Exception as exc:
        # Log to stderr; don't crash the tray
        print(f"[nexus_tray] Flask error: {exc}", file=sys.stderr)


# ────────────────────────────────────────────────────────────────────────────
# Tray menu callbacks
# ────────────────────────────────────────────────────────────────────────────
def _on_open(icon, item):
    webbrowser.open(DASHBOARD_URL)


def _on_quit(icon, item):
    """Stop the tray icon; daemon Flask thread dies automatically."""
    icon.stop()


# ────────────────────────────────────────────────────────────────────────────
# Main — tray icon owns the main thread
# ────────────────────────────────────────────────────────────────────────────
def main():
    # ── Start Flask in background daemon thread ──
    flask_thread = threading.Thread(target=_run_flask, daemon=True, name="nexus-flask")
    flask_thread.start()

    print(f"🚀 Nexus GUI Bridge Starting...")
    print(f"🔗 URL: {DASHBOARD_URL}")
    print(f"📦 Tray: Indigo dot in menu bar")
    
    # Give Flask a moment to bind, then open browser immediately
    time.sleep(1.5)
    webbrowser.open(DASHBOARD_URL)

    try:
        import pystray
    except ImportError:
        print("[nexus_tray] pystray not installed. Run: pip3 install pystray Pillow", file=sys.stderr)
        flask_thread.join()
        return

    icon_image = _make_icon()
    icon = pystray.Icon(
        name="Nexus MCP Bridge",
        icon=icon_image,
        title="Nexus MCP Bridge",
        menu=pystray.Menu(
            pystray.MenuItem("Open Dashboard", _on_open, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Stop & Quit", _on_quit),
        ),
    )

    icon.run()   # blocks on main thread



if __name__ == "__main__":
    main()
