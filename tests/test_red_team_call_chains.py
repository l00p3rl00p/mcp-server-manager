import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import time
import types
import yaml

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
        (repo / ".git").mkdir(parents=True, exist_ok=True)

        with patch.object(gb.Path, "cwd", return_value=repo), patch.object(
            gb.subprocess, "Popen"
        ) as popen_mock:
            res = self.client.post("/system/update/nexus")

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertTrue(payload.get("success"))
        popen_mock.assert_called_once()
        argv = popen_mock.call_args[0][0]
        self.assertEqual(argv[:2], ["git", "pull"])
        self.assertEqual(Path(popen_mock.call_args.kwargs.get("cwd")).resolve(), repo.resolve())

    def test_system_update_nexus_dry_run_uses_git_repo(self):
        gb = self.gui_bridge
        repo = Path(self._tmpdir.name) / "repo"
        (repo / ".git").mkdir(parents=True, exist_ok=True)

        with patch.object(gb.Path, "cwd", return_value=repo), patch.object(
            gb.subprocess, "Popen"
        ) as popen_mock:
            res = self.client.post("/system/update/nexus", json={"dry_run": True})

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertTrue(payload.get("success"))
        self.assertTrue(payload.get("dry_run"))
        self.assertEqual(payload.get("cmd"), ["git", "pull"])
        self.assertEqual(Path(payload.get("cwd")).resolve(), repo.resolve())
        popen_mock.assert_not_called()

    def test_system_update_python_dry_run_prefers_pyproject(self):
        gb = self.gui_bridge
        repo = Path(self._tmpdir.name) / "repo"
        repo.mkdir(parents=True, exist_ok=True)
        (repo / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")

        # Mock NEXUS_HOME to be empty so it falls back to sys.executable for the test,
        # OR mock the exact executable we expect.
        with patch.object(gb.Path, "cwd", return_value=repo), patch.object(
            gb.subprocess, "Popen"
        ) as popen_mock, patch("gui_bridge.NEXUS_HOME", Path("/fake/nexus")):
            res = self.client.post("/system/update/python", json={"dry_run": True})

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertTrue(payload.get("success"))
        self.assertTrue(payload.get("dry_run"))
        # Should fallback to sys.executable because /fake/nexus/.venv does not exist
        self.assertEqual(payload.get("cmd"), [sys.executable, "-m", "pip", "install", "--upgrade", "-e", "."])
        self.assertEqual(Path(payload.get("cwd")).resolve(), repo.resolve())
        self.assertEqual(payload.get("mode"), "pyproject")
        popen_mock.assert_not_called()

    def test_system_update_python_dry_run_falls_back_to_requirements(self):
        gb = self.gui_bridge
        repo = Path(self._tmpdir.name) / "repo"
        repo.mkdir(parents=True, exist_ok=True)
        (repo / "requirements.txt").write_text("requests==2.0.0\n", encoding="utf-8")

        with patch.object(gb.Path, "cwd", return_value=repo), patch.object(
            gb.subprocess, "Popen"
        ) as popen_mock, patch("gui_bridge.NEXUS_HOME", Path("/fake/nexus")):
            res = self.client.post("/system/update/python", json={"dry_run": True})

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertTrue(payload.get("success"))
        self.assertTrue(payload.get("dry_run"))
        self.assertEqual(payload.get("cmd"), [sys.executable, "-m", "pip", "install", "--upgrade", "-r", "requirements.txt"])
        self.assertEqual(Path(payload.get("cwd")).resolve(), repo.resolve())
        self.assertEqual(payload.get("mode"), "requirements")
        popen_mock.assert_not_called()

    def test_server_control_start_writes_log_and_returns_resolved_cmd(self):
        gb = self.gui_bridge
        repo = Path(self._tmpdir.name)
        server_dir = repo / "srv"
        server_dir.mkdir(parents=True, exist_ok=True)
        inv_path = repo / "inventory.yaml"
        inv = {
            "servers": [
                {
                    "id": "demo-server",
                    "name": "demo-server",
                    "path": str(server_dir),
                    "run": {"start_cmd": "python3 mcp_server.py", "stop_cmd": "pkill -f demo-server"},
                }
            ]
        }
        inv_path.write_text(yaml.safe_dump(inv), encoding="utf-8")
        gb.pm.inventory_path = inv_path

        class _FakePopen:
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

            def poll(self):
                return None

            def wait(self, *args, **kwargs):
                return 0

        class _FakeThread:
            def __init__(self, *args, **kwargs):
                pass

            def start(self):
                return None

        with patch.object(gb.subprocess, "Popen", side_effect=_FakePopen) as popen_mock, patch.object(
            gb.threading, "Thread", side_effect=_FakeThread
        ), patch.object(gb.time, "sleep", return_value=None):
            res = self.client.post("/server/control", json={"id": "demo-server", "action": "start"})

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertTrue(payload.get("success"))
        self.assertIn("log_path", payload)
        self.assertEqual(payload.get("resolved_cmd"), ["python3", "mcp_server.py"])
        log_path = Path(payload.get("log_path"))
        self.assertTrue(log_path.exists())
        text = log_path.read_text(encoding="utf-8")
        self.assertIn("--- CMD: python3 mcp_server.py ---", text)
        popen_mock.assert_called_once()

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

    def test_llm_batch_calls_wrapper_and_returns_results(self):
        """
        Call-chain: HTTP /llm/batch -> imports mcp_wrapper.wrapper -> wrapper.call executed -> JSON response.
        Proves the endpoint is wired to the wrapper layer (no ghost response).
        """
        gb = self.gui_bridge

        fake = types.ModuleType("mcp_wrapper")
        wrapper_obj = MagicMock()
        wrapper_obj.call = MagicMock(side_effect=[{"ok": True}, {"ok": False}])
        fake.wrapper = wrapper_obj

        with patch.dict(sys.modules, {"mcp_wrapper": fake}):
            res = self.client.post("/llm/batch", json={"requests": [{"a": 1}, {"b": 2}]})

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertEqual(payload.get("total"), 2)
        self.assertEqual(len(payload.get("results") or []), 2)
        self.assertEqual(payload.get("efficiency_gain"), "PARALLEL_REAL_EXECUTION")
        self.assertEqual(wrapper_obj.call.call_count, 2)

    def test_os_pick_folder_returns_selected_path(self):
        gb = self.gui_bridge

        fake_tk = types.ModuleType("tkinter")
        fake_dialog = types.ModuleType("tkinter.filedialog")

        class _Root:
            def withdraw(self):  # pragma: no cover
                return None

            def attributes(self, *args, **kwargs):  # pragma: no cover
                return None

            def destroy(self):  # pragma: no cover
                return None

        fake_tk.Tk = _Root
        fake_dialog.askdirectory = MagicMock(return_value="/tmp/selected")

        with patch.dict(sys.modules, {"tkinter": fake_tk, "tkinter.filedialog": fake_dialog}), patch.dict(
            gb.os.environ, {"NEXUS_HEADLESS": "0"}, clear=False
        ), patch.object(gb.sys, "platform", "linux"):
            res = self.client.post("/os/pick_folder", json={})

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertTrue(payload.get("success"))
        self.assertEqual(payload.get("path"), "/tmp/selected")

    def test_system_python_info_returns_versions_and_packages(self):
        gb = self.gui_bridge

        def _fake_run(cmd, capture_output=False, text=False, timeout=None, **kwargs):
            joined = " ".join(cmd)
            p = MagicMock()
            if cmd[:2] == [gb.sys.executable, "--version"]:
                p.returncode = 0
                p.stdout = "Python 3.12.0"
                p.stderr = ""
                return p
            if cmd[:3] == [gb.sys.executable, "-m", "pip"] and cmd[3:] == ["--version"]:
                p.returncode = 0
                p.stdout = "pip 26.0.0"
                p.stderr = ""
                return p
            if cmd[:3] == [gb.sys.executable, "-m", "pip"] and cmd[3] == "show":
                pkg = cmd[4]
                p.returncode = 0
                p.stdout = f"Name: {pkg}\nVersion: 1.2.3\n"
                p.stderr = ""
                return p
            p.returncode = 1
            p.stdout = ""
            p.stderr = f"unexpected cmd: {joined}"
            return p

        with patch.object(gb.shutil, "which", side_effect=lambda x: f"/usr/bin/{x}"), patch.object(
            gb.subprocess, "run", side_effect=_fake_run
        ), patch.object(gb.Path, "exists", return_value=True):
            res = self.client.get("/system/python_info")

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertTrue(payload.get("success"))
        self.assertIn("bridge", payload)
        self.assertIn("packages", payload)
        self.assertTrue(payload["nexus"]["venv_exists"])
        self.assertEqual(payload["bridge"]["python_version"], "Python 3.12.0")
        self.assertEqual(payload["bridge"]["pip_version"], "pip 26.0.0")
        self.assertEqual(payload["packages"]["flask"]["version"], "1.2.3")


if __name__ == "__main__":
    unittest.main()
