import sys
import unittest
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestUiCallChains(unittest.TestCase):
    def setUp(self):
        import gui_bridge  # type: ignore

        self.gui_bridge = gui_bridge
        self.client = gui_bridge.app.test_client()
        # Prevent tests from polluting real user logs under ~/.mcp-tools.
        self._tmpdir = tempfile.TemporaryDirectory()
        self.gui_bridge.pm.app_data_dir = Path(self._tmpdir.name)

    def tearDown(self):
        try:
            self._tmpdir.cleanup()
        except Exception:
            pass

    def test_nexus_run_rejects_disallowed_bin(self):
        res = self.client.post("/nexus/run", json={"command": "rm -rf /"})
        self.assertEqual(res.status_code, 403)
        payload = res.get_json()
        self.assertIn("not allowed", payload.get("error", "").lower())

    def test_nexus_run_mcp_surgeon_arg_split_and_bin_resolution(self):
        gb = self.gui_bridge

        fake_bin = gb.pm.bin_dir / "mcp-surgeon"
        cmd = "mcp-surgeon --add foo --client claude"

        with patch.object(type(fake_bin), "exists", return_value=True), patch.object(
            gb.subprocess, "run"
        ) as run_mock:
            run_mock.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            res = self.client.post("/nexus/run", json={"command": cmd})

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertTrue(payload.get("success"))

        called_argv = run_mock.call_args[0][0]
        self.assertEqual(called_argv[0], str(fake_bin))
        self.assertEqual(called_argv[1:], ["--add", "foo", "--client", "claude"])

    def test_server_control_start_calls_resolver_and_writes_log(self):
        gb = self.gui_bridge

        server_id = "test-server"
        inv = {"servers": [{"id": server_id, "run": {"start_cmd": "python3 -c 'print(1)'"}}]}

        resolved_argv = ["python3", "-c", "print('hi')"]
        resolved_cwd = "/tmp"
        resolved_env = {"X": "1"}

        with patch.object(gb.pm, "get_inventory", return_value=inv), patch.object(
            gb, "_resolve_server_run", return_value=(resolved_argv, resolved_cwd, resolved_env, "note", None)
        ), patch.object(gb.subprocess, "Popen") as popen_mock:
            popen_mock.return_value = MagicMock(pid=1234, poll=lambda: None)
            with patch.object(time, "sleep", return_value=None):
                res = self.client.post("/server/control", json={"id": server_id, "action": "start"})

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertTrue(payload.get("success"))
        self.assertEqual(payload.get("resolved_cmd"), resolved_argv)
        self.assertEqual(payload.get("cwd"), resolved_cwd)

        popen_mock.assert_called()
        argv = popen_mock.call_args[0][0]
        self.assertEqual(argv, resolved_argv)
        self.assertEqual(popen_mock.call_args.kwargs.get("cwd"), resolved_cwd)
        self.assertEqual(popen_mock.call_args.kwargs.get("env"), resolved_env)

        # follow-on action: start log file path is returned and should exist on disk
        log_path = payload.get("log_path")
        self.assertTrue(log_path)
        self.assertTrue(Path(log_path).exists())

    def test_server_control_start_reports_immediate_exit(self):
        gb = self.gui_bridge

        server_id = "crashy"
        inv = {"servers": [{"id": server_id, "run": {"start_cmd": "python3 -c 'print(1)'"}}]}

        resolved_argv = ["python3", "-c", "print('hi')"]

        crashing_proc = MagicMock(pid=2222)
        crashing_proc.poll = MagicMock(return_value=1)

        with patch.object(gb.pm, "get_inventory", return_value=inv), patch.object(
            gb, "_resolve_server_run", return_value=(resolved_argv, None, None, "", None)
        ), patch.object(gb.subprocess, "Popen", return_value=crashing_proc), patch.object(
            time, "sleep", return_value=None
        ):
            res = self.client.post("/server/control", json={"id": server_id, "action": "start"})

        self.assertEqual(res.status_code, 500)
        payload = res.get_json()
        self.assertFalse(payload.get("success"))
        self.assertIn("exited", (payload.get("error") or "").lower())
        self.assertEqual(payload.get("returncode"), 1)
        self.assertTrue(payload.get("log_path"))

    def test_server_control_auto_retries_with_python310_on_union_error(self):
        gb = self.gui_bridge

        server_id = "notebooklm"
        inv = {"servers": [{"id": server_id, "run": {"start_cmd": "python3 mcp_server.py"}, "path": "/tmp"}]}

        resolved_argv = ["/usr/bin/python3.9", "-m", "notebooklm_mcp"]
        # first launch exits immediately
        proc1 = MagicMock(pid=4444)
        proc1.poll = MagicMock(return_value=1)

        # second launch stays alive
        proc2 = MagicMock(pid=5555)
        proc2.poll = MagicMock(return_value=None)

        popen_mock = MagicMock(side_effect=[proc1, proc2])

        union_signature = "TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'"

        with patch.object(gb.pm, "get_inventory", return_value=inv), patch.object(
            gb, "_resolve_server_run", return_value=(resolved_argv, "/tmp", {}, "note", None)
        ), patch.object(gb, "_find_python_at_least", return_value="/usr/bin/python3.11"), patch.object(
            gb.subprocess, "Popen", popen_mock
        ), patch.object(time, "sleep", return_value=None), patch.object(
            gb.Path, "read_text", return_value=union_signature
        ):
            res = self.client.post("/server/control", json={"id": server_id, "action": "start"})

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertTrue(payload.get("success"))
        self.assertIn("retry", payload)
        self.assertEqual(payload["retry"]["reason"], "python<3.10 union crash signature")

        # ensure the second spawn used the fallback python
        self.assertEqual(popen_mock.call_count, 2)
        second_argv = popen_mock.call_args_list[1][0][0]
        self.assertEqual(second_argv[0], "/usr/bin/python3.11")

    def test_server_control_start_reports_traceback_in_log(self):
        gb = self.gui_bridge

        server_id = "tracey"
        inv = {"servers": [{"id": server_id, "run": {"start_cmd": "python3 -c 'print(1)'"}}]}

        resolved_argv = ["python3", "-c", "print('hi')"]

        running_proc = MagicMock(pid=3333)
        running_proc.poll = MagicMock(return_value=None)

        with patch.object(gb.pm, "get_inventory", return_value=inv), patch.object(
            gb, "_resolve_server_run", return_value=(resolved_argv, None, None, "", None)
        ), patch.object(gb.subprocess, "Popen", return_value=running_proc), patch.object(
            time, "sleep", return_value=None
        ), patch.object(Path, "read_text", return_value="Traceback (most recent call last):\nboom"):
            res = self.client.post("/server/control", json={"id": server_id, "action": "start"})

        self.assertEqual(res.status_code, 500)
        payload = res.get_json()
        self.assertFalse(payload.get("success"))
        self.assertIn("traceback", (payload.get("error") or "").lower())

    def test_server_control_blocks_python_requires_mismatch(self):
        gb = self.gui_bridge

        server_id = "pyreq"
        inv = {"servers": [{"id": server_id, "run": {"start_cmd": "python3 mcp_server.py"}, "path": "/tmp"}]}

        resolved_argv = ["/fake/python3", "-m", "x"]
        # requires-python higher than the fake interpreter version we return
        requires_python = ">=3.10"

        with patch.object(gb.pm, "get_inventory", return_value=inv), patch.object(
            gb, "_resolve_server_run", return_value=(resolved_argv, "/tmp", {}, "", requires_python)
        ), patch.object(gb, "_python_version_tuple", return_value=(3, 9, 6)):
            res = self.client.post("/server/control", json={"id": server_id, "action": "start"})

        self.assertEqual(res.status_code, 409)
        payload = res.get_json()
        self.assertFalse(payload.get("success"))
        self.assertIn("mismatch", (payload.get("error") or "").lower())
        self.assertEqual(payload.get("requires_python"), requires_python)

    def test_librarian_add_url_calls_subprocess_run(self):
        gb = self.gui_bridge
        url = "https://example.com"

        with patch.object(gb.subprocess, "run") as run_mock:
            run_mock.return_value = MagicMock(returncode=0, stdout="indexed", stderr="")
            res = self.client.post("/librarian/add", json={"resource": url})

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertTrue(payload.get("success"))
        self.assertEqual(payload.get("resource"), url)

        called = run_mock.call_args[0][0]
        self.assertIn("--add", called)
        self.assertEqual(called[-1], url)

    def test_system_uninstall_passes_selected_flags(self):
        gb = self.gui_bridge

        with patch.object(gb.Path, "exists", return_value=True), patch.object(gb.subprocess, "run") as run_mock:
            run_mock.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            res = self.client.post(
                "/system/uninstall",
                json={
                    "purge_data": True,
                    "kill_venv": False,
                    "detach_clients": True,
                    "remove_path_block": True,
                    "remove_wrappers": True,
                },
            )

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertTrue(payload.get("success"))

        argv = run_mock.call_args[0][0]
        self.assertIn("--yes", argv)
        self.assertIn("--purge-data", argv)
        self.assertNotIn("--kill-venv", argv)
        self.assertIn("--detach-clients", argv)
        self.assertIn("--remove-path-block", argv)
        self.assertIn("--remove-wrappers", argv)

    def test_system_uninstall_dry_run_passes_flag(self):
        gb = self.gui_bridge

        with patch.object(gb.Path, "exists", return_value=True), patch.object(gb.subprocess, "run") as run_mock:
            run_mock.return_value = MagicMock(returncode=0, stdout="plan", stderr="")
            res = self.client.post(
                "/system/uninstall",
                json={
                    "purge_data": True,
                    "kill_venv": True,
                    "dry_run": True,
                },
            )

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertTrue(payload.get("success"))

        argv = run_mock.call_args[0][0]
        self.assertIn("--dry-run", argv)

    def test_system_update_python_uses_editable_install_when_pyproject_present(self):
        gb = self.gui_bridge

        repo = gb.Path("/tmp/repo")

        def _fake_exists(self_path: gb.Path) -> bool:
            s = str(self_path)
            if s == str(repo / "pyproject.toml"):
                return True
            if s == str(repo / "requirements.txt"):
                return False
            return False

        with patch.object(gb.Path, "cwd", return_value=repo), patch.object(
            gb.Path, "exists", new=_fake_exists
        ), patch.object(gb.subprocess, "Popen") as popen_mock:
            res = self.client.post("/system/update/python")

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertTrue(payload.get("success"))
        popen_mock.assert_called()
        argv = popen_mock.call_args[0][0]
        self.assertIn("-e", argv)
        self.assertEqual(argv[-1], ".")

    def test_system_update_python_dry_run_returns_cmd_without_spawning(self):
        gb = self.gui_bridge
        repo = gb.Path("/tmp/repo")

        def _fake_exists(self_path: gb.Path) -> bool:
            s = str(self_path)
            if s == str(repo / "pyproject.toml"):
                return True
            if s == str(repo / "requirements.txt"):
                return False
            return False

        with patch.object(gb.Path, "cwd", return_value=repo), patch.object(
            gb.Path, "exists", new=_fake_exists
        ), patch.object(gb.subprocess, "Popen") as popen_mock:
            res = self.client.post("/system/update/python", json={"dry_run": True})

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertTrue(payload.get("success"))
        self.assertTrue(payload.get("dry_run"))
        self.assertTrue(payload.get("cmd"))
        popen_mock.assert_not_called()

    def test_injector_clients_parses_list_clients_output(self):
        gb = self.gui_bridge

        fake_output = "✅ Claude\n✅ VSCode\n"
        with patch.object(gb.subprocess, "run") as run_mock:
            run_mock.return_value = MagicMock(returncode=0, stdout=fake_output, stderr="")
            res = self.client.get("/injector/clients")

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertEqual(sorted(payload.get("clients", [])), ["claude", "vscode"])

    def test_os_pickers_return_501_in_headless(self):
        gb = self.gui_bridge
        with patch.dict(gb.os.environ, {"NEXUS_HEADLESS": "1"}):
            res1 = self.client.post("/os/pick_file")
            res2 = self.client.post("/os/pick_folder")

        self.assertEqual(res1.status_code, 501)
        self.assertEqual(res2.status_code, 501)


if __name__ == "__main__":
    unittest.main()
