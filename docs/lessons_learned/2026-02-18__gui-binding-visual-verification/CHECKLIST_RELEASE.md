
# GUI Binding Verification Failure (2026-02-18)

## Symptom
The MCP GUI frontend (running on port 5173 via Vite) loaded but displayed zero data. The Dashboard badge was stuck on "Initializing...", the server list was empty ("No servers detected"), and the Librarian showed "No artifacts indexed." This occurred despite the backend process (`gui_bridge.py`) running without crash logs.

## Root Cause
The Flask backend (`gui_bridge.py`) was configured to bind to `127.0.0.1`. In many modern development environments (especially those involving containers, proxies, or specific network namespaces like Docker Desktop or some VS Code setups), `127.0.0.1` is not universally accessible across the stack. The frontend's fetch requests to `http://localhost:5001` were failing with `net::ERR_CONNECTION_REFUSED` or `TIMED_OUT` because the backend was only listening on the loopback interface, effectively invisible to the frontend context.

## The Fix
Switch the binding host from `127.0.0.1` to `0.0.0.0` in `app.run()`. This universal binding ensures the service is accessible from all network interfaces, resolving the disconnect.
Additionally, `debug=True` was disabled to prevent potential reloader conflicts in non-interactive environments.

## Why It Passed Initial (Automated) Checks
Previous checks relied on `curl http://127.0.0.1:5001` from the *same* terminal session where the server was started. Since both were in the same network namespace, `curl` succeeded. The failure only manifested when the *browser* (User) tried to access it, highlighting a critical gap between "test connectivity" and "user connectivity."

## Prevention Rule
**"User-Centric Verification"**: Functional tests for GUIs must not rely solely on CLI tools like `curl`. They must utilize a browser-based agent (or `playwright`/`selenium` script) to render the actual frontend page. If the test doesn't see what the user sees, it's not a valid test.

## Tags
gui, network, flask, binding, 0.0.0.0, localhost, visualization-gap
