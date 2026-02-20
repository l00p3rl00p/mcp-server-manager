import unittest


class TestStatusPayload(unittest.TestCase):
    def test_status_includes_core_components(self):
        # Import lazily to avoid side effects during test discovery
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(repo_root / "mcp-server-manager"))
        import gui_bridge  # type: ignore

        client = gui_bridge.app.test_client()
        res = client.get("/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn("core_components", data)
        core = data["core_components"]
        self.assertIsInstance(core, dict)

        # These keys should always exist; values vary by environment.
        for k in ("activator", "observer", "surgeon", "librarian_bin", "librarian"):
            self.assertIn(k, core)
