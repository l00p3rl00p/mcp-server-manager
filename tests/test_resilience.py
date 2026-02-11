import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from mcp_inventory import inventory


class ObserverResilienceTests(unittest.TestCase):
    def test_malformed_inventory_parse_error_is_backed_up_and_reset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            inventory_path = Path(temp_dir) / "inventory.yaml"
            inventory_path.write_text("servers: [bad", encoding="utf-8")
            fake_yaml = SimpleNamespace(
                safe_load=lambda _: (_ for _ in ()).throw(ValueError("bad yaml")),
                safe_dump=lambda data, sort_keys=False: "servers: []\n",
            )
            with mock.patch.object(inventory, "yaml", fake_yaml):
                entries = inventory.load_inventory(inventory_path)
            self.assertEqual(entries, {})
            backups = list(Path(temp_dir).glob("inventory.yaml.corrupt.*"))
            self.assertTrue(backups)

    def test_malformed_inventory_is_backed_up_and_reset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            inventory_path = Path(temp_dir) / "inventory.yaml"
            inventory_path.write_text("servers: bad-shape", encoding="utf-8")
            fake_yaml = SimpleNamespace(
                safe_load=lambda _: {"servers": "bad-shape"},
                safe_dump=lambda data, sort_keys=False: "servers: []\n",
            )
            with mock.patch.object(inventory, "yaml", fake_yaml):
                entries = inventory.load_inventory(inventory_path)
            self.assertEqual(entries, {})
            self.assertIn("servers:", inventory_path.read_text(encoding="utf-8"))
            backups = list(Path(temp_dir).glob("inventory.yaml.corrupt.*"))
            self.assertTrue(backups)

    def test_missing_yaml_dependency_falls_back_to_json_save(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            inventory_path = Path(temp_dir) / "inventory.yaml"
            with mock.patch.object(inventory, "yaml", None):
                inventory.save_inventory({}, inventory_path)
            self.assertTrue((Path(temp_dir) / "inventory.json").exists())

    def test_config_dir_falls_back_when_home_unwritable(self):
        with tempfile.TemporaryDirectory() as temp_home, tempfile.TemporaryDirectory() as temp_cwd:
            os.chmod(temp_home, stat.S_IREAD | stat.S_IEXEC)
            try:
                code = (
                    "from mcp_inventory.config import APP_DIR\n"
                    "print(APP_DIR)\n"
                )
                env = dict(os.environ)
                env["HOME"] = temp_home
                env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
                result = subprocess.run(
                    ["python3", "-c", code],
                    cwd=temp_cwd,
                    text=True,
                    capture_output=True,
                    env=env,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(".mcpinv/mcp-server-manager", result.stdout.strip())
            finally:
                os.chmod(temp_home, stat.S_IRWXU)


if __name__ == "__main__":
    unittest.main()
