import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
UNINSTALL = REPO_ROOT / "uninstall.py"


class UninstallEntrypointTests(unittest.TestCase):
    def test_help(self):
        result = subprocess.run(
            ["python3", str(UNINSTALL), "--help"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--purge-data", result.stdout)


if __name__ == "__main__":
    unittest.main()

