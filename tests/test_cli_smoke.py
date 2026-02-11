import subprocess
import tempfile
import unittest
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = REPO_ROOT / "bootstrap.py"


def run_cmd(*args, cwd=None):
    return subprocess.run(
        ["python3"] + [str(arg) for arg in args],
        cwd=cwd or REPO_ROOT,
        text=True,
        capture_output=True,
    )


class ObserverSmokeTests(unittest.TestCase):
    def test_bootstrap_help(self):
        result = run_cmd(BOOTSTRAP, "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--sync", result.stdout)

    def test_installed_wrapper_help_if_available(self):
        wrapper = Path.home() / ".mcp-tools" / "bin" / "mcp-observer"
        if not wrapper.exists():
            self.skipTest("installed mcp-observer wrapper not available")
        with tempfile.TemporaryDirectory() as temp_home:
            env = dict(os.environ)
            env["HOME"] = temp_home
            result = subprocess.run([str(wrapper), "--help"], text=True, capture_output=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_installed_wrapper_list_if_available(self):
        wrapper = Path.home() / ".mcp-tools" / "bin" / "mcp-observer"
        if not wrapper.exists():
            self.skipTest("installed mcp-observer wrapper not available")
        with tempfile.TemporaryDirectory() as temp_home:
            env = dict(os.environ)
            env["HOME"] = temp_home
            result = subprocess.run([str(wrapper), "list"], text=True, capture_output=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
