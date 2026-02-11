import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT.parent


class CommandsFlagsExistTests(unittest.TestCase):
    def test_uninstall_entrypoint_has_flags(self):
        result = subprocess.run(["python3", "uninstall.py", "--help"], cwd=REPO_ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout + result.stderr
        for flag in ("--kill-venv", "--purge-data"):
            self.assertIn(flag, out)

    def test_observer_help_has_documented_subcommands(self):
        result = subprocess.run(
            ["python3", "-m", "mcp_inventory.cli", "--help"],
            cwd=str(REPO_ROOT),
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout + result.stderr
        for sub in ("config", "list", "add", "scan", "running", "bootstrap", "health", "gui"):
            self.assertIn(sub, out)

    def test_packager_bootstrap_help_has_documented_flags(self):
        packager = WORKSPACE_ROOT / "repo-mcp-packager" / "bootstrap.py"
        result = subprocess.run(["python3", str(packager), "--help"], cwd=packager.parent, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout + result.stderr
        for flag in ("--lite", "--industrial", "--permanent", "--sync", "--update", "--gui"):
            self.assertIn(flag, out)


if __name__ == "__main__":
    unittest.main()

