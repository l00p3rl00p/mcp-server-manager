import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestRedTeamCallChains(unittest.TestCase):
    def setUp(self):
        import gui_bridge  # type: ignore

        self.gui_bridge = gui_bridge
        self.client = gui_bridge.app.test_client()
        # Keep side-effects out of real user state (~/.mcp-tools, ~/.mcpinv).
        self._tmpdir = tempfile.TemporaryDirectory()
        tmp_path = Path(self._tmpdir.name)
        self.gui_bridge.pm.app_data_dir = tmp_path
        self.gui_bridge.pm.inventory_path = tmp_path / "inventory.yaml"
        self.gui_bridge.pm.log_path = tmp_path / "session.jsonl"
        self.gui_bridge.pm.bin_dir = tmp_path / "bin"
        # Ensure a clean forge task registry per test.
        self.gui_bridge.fm.tasks = {}

    def tearDown(self):
        try:
            self._tmpdir.cleanup()
        except Exception:
            pass

    def test_forge_route_registers_task_and_returns_id(self):
        gb = self.gui_bridge
        created = {}

        def _fake_start_task(source, name=None):
            # Avoid running ForgeEngine; we only need a deterministic task record.
            task_id = "task-redteam"
            gb.fm.tasks[task_id] = {
                "id": task_id,
                "status": "pending",
                "source": source,
                "logs": ["queued"],
                "result": None,
                "start_time": time.time(),
            }
            created["source"] = source
            created["name"] = name
            return task_id

        with patch.object(gb.fm, "start_task", side_effect=_fake_start_task):
            res = self.client.post("/forge", json={"source": "/tmp/src", "name": "demo"})

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertTrue(payload.get("success"))
        self.assertEqual(payload.get("task_id"), "task-redteam")
        self.assertEqual(created.get("source"), "/tmp/src")
        self.assertEqual(created.get("name"), "demo")
        self.assertIn("task-redteam", gb.fm.tasks)

    def test_forge_status_returns_task_payload(self):
        gb = self.gui_bridge
        task_id = "task-status"
        gb.fm.tasks[task_id] = {
            "id": task_id,
            "status": "running",
            "source": "/tmp/src",
            "logs": ["Starting Forge..."],
            "result": None,
            "start_time": time.time(),
        }

        res = self.client.get(f"/forge/status/{task_id}")
        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertEqual(payload.get("id"), task_id)
        self.assertEqual(payload.get("status"), "running")
        self.assertEqual(payload.get("logs"), ["Starting Forge..."])

    def test_system_update_nexus_invokes_git_pull(self):
        gb = self.gui_bridge
        repo = Path(self._tmpdir.name) / "repo"

        def _fake_exists(self_path: Path) -> bool:
            return str(self_path) == str(repo / ".git")

        with patch.object(gb.Path, "cwd", return_value=repo), patch.object(
            gb.Path, "exists", new=_fake_exists
        ), patch.object(gb.subprocess, "Popen") as popen_mock:
            res = self.client.post("/system/update/nexus")

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertTrue(payload.get("success"))
        popen_mock.assert_called_once()
        argv = popen_mock.call_args[0][0]
        self.assertEqual(argv[:2], ["git", "pull"])
        self.assertEqual(popen_mock.call_args.kwargs.get("cwd"), repo)

    def test_server_logs_latest_returns_tail(self):
        gb = self.gui_bridge
        log_dir = gb.pm.app_data_dir / "server_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        server_id = "sample"
        log_path = log_dir / f"{server_id}_123.log"
        log_path.write_text("line1\nline2\nline3\n", encoding="utf-8")

        res = self.client.get(f"/server/logs/{server_id}")
        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertEqual(payload.get("server_id"), server_id)
        self.assertEqual(payload.get("log_path"), str(log_path))
        self.assertEqual(payload.get("lines"), ["line1", "line2", "line3"])

    def test_status_pulse_red_when_core_missing(self):
        gb = self.gui_bridge
        gb.pm.inventory_path = Path(self._tmpdir.name) / "missing.yaml"

        orig_import = __import__

        def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            # Force psutil import to fail so health falls back to core component checks.
            if name == "psutil":
                raise ImportError("psutil blocked for test")
            return orig_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=_fake_import):
            res = self.client.get("/status")

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertEqual(payload.get("pulse"), "red")
        self.assertIn("Missing", payload.get("posture", ""))


if __name__ == "__main__":
    unittest.main()
