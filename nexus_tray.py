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
import sys
import os
from pathlib import Path

# ── Ensure the project root is on sys.path so gui_bridge imports cleanly ──
PROJECT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_DIR))

# ── Port must match gui_bridge.py ──
PORT = 5001
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
        # Import the 'app' object that gui_bridge.py already defines
        from gui_bridge import app
        # host=127.0.0.1 — only reachable from localhost (safer than 0.0.0.0)
        app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)
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

    try:
        import pystray
    except ImportError:
        print(
            "[nexus_tray] pystray not installed. Run: pip3 install pystray Pillow",
            file=sys.stderr,
        )
        # Fall back: just open browser and block on Flask thread
        webbrowser.open(DASHBOARD_URL)
        flask_thread.join()
        return

    icon_image = _make_icon()
    if icon_image is None:
        print("[nexus_tray] Pillow not installed — tray icon will be blank.", file=sys.stderr)

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

    print(f"[nexus_tray] Bridge running → {DASHBOARD_URL}")
    print("[nexus_tray] Use the tray icon menu to stop.")
    icon.run()   # blocks on main thread — this is correct behaviour


if __name__ == "__main__":
    main()
