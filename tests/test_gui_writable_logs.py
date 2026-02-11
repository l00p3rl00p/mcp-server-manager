import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestGuiWritableLogs(unittest.TestCase):
    def test_active_logs_dir_is_writable(self):
        # Importing logger should resolve and create ACTIVE_LOGS_DIR
        from mcp_inventory.logger import ACTIVE_LOGS_DIR

        ACTIVE_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        probe = ACTIVE_LOGS_DIR / ".write_test_gui"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)

    def test_config_ensure_app_dir_creates_subdirs(self):
        with TemporaryDirectory() as tmp:
            # Patch HOME for this test, then import config fresh by loading module from file path.
            import os
            import importlib
            import sys

            old_home = os.environ.get("HOME")
            os.environ["HOME"] = tmp
            try:
                sys.modules.pop("mcp_inventory.config", None)
                module = importlib.import_module("mcp_inventory.config")

                module.ensure_app_dir()
                self.assertTrue(module.STATE_DIR.exists())
                self.assertTrue(module.LOGS_DIR.exists())
                self.assertTrue(module.ARTIFACTS_DIR.exists())
            finally:
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home


if __name__ == "__main__":
    unittest.main()
