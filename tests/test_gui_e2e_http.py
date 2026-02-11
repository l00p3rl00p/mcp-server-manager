import json
import os
import signal
import time
import unittest
from urllib.request import urlopen, Request


class TestGuiE2EHttp(unittest.TestCase):
    def test_gui_api_endpoints_and_action_log(self):
        # E2E: bind to ephemeral port; skip if binding is not permitted in environment.
        try:
            from mcp_inventory.gui import create_server
        except Exception as e:
            self.skipTest(f"GUI import failed: {e}")

        try:
            httpd = create_server(0)
        except OSError as e:
            self.skipTest(f"Binding not permitted: {e}")

        port = httpd.server_address[1]

        import threading

        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            # /api/system_status should return JSON
            with urlopen(f"http://127.0.0.1:{port}/api/system_status", timeout=2) as r:
                data = json.loads(r.read().decode("utf-8"))
            self.assertIn("observer", data)
            self.assertTrue(data["observer"])

            # /api/logs should return JSON
            with urlopen(f"http://127.0.0.1:{port}/api/logs", timeout=2) as r:
                logs = json.loads(r.read().decode("utf-8"))
            self.assertIn("logs", logs)

            # Trigger action: health
            req = Request(
                f"http://127.0.0.1:{port}/api/action/health",
                method="POST",
                data=b"",
            )
            with urlopen(req, timeout=2) as r:
                resp = json.loads(r.read().decode("utf-8"))
            self.assertTrue(resp.get("success"))
            log_name = resp.get("action_log_name")
            self.assertTrue(log_name)
            pid = resp.get("pid")

            # Poll the action log via API until it has content
            deadline = time.time() + 5.0
            lines = []
            while time.time() < deadline:
                with urlopen(f"http://127.0.0.1:{port}/api/logs/{log_name}", timeout=2) as r:
                    payload = json.loads(r.read().decode("utf-8"))
                lines = payload.get("lines") or []
                if any("COMMAND:" in ln for ln in lines):
                    break
                time.sleep(0.2)

            self.assertTrue(any("COMMAND:" in ln for ln in lines))

            # Best-effort cleanup: terminate the spawned subprocess if still running.
            if isinstance(pid, int):
                try:
                    os.kill(pid, signal.SIGTERM)
                    # Wait briefly for exit (avoid ResourceWarning)
                    deadline_kill = time.time() + 2.0
                    while time.time() < deadline_kill:
                        wpid, _ = os.waitpid(pid, os.WNOHANG)
                        if wpid == pid:
                            break
                        time.sleep(0.05)
                    else:
                        try:
                            os.kill(pid, signal.SIGKILL)
                            os.waitpid(pid, 0)
                        except Exception:
                            pass
                except Exception:
                    pass
        finally:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    unittest.main()
