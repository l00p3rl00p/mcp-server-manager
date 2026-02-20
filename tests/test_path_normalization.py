import unittest


class TestPathNormalization(unittest.TestCase):
    def test_normalize_user_path_expands_home_and_strips_quotes(self):
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(repo_root / "mcp-server-manager"))
        import gui_bridge  # type: ignore

        raw = '"~/Some Folder/File With Spaces.pdf"'
        norm = gui_bridge._normalize_user_path(raw)

        self.assertNotIn('"', norm)
        self.assertNotIn("~", norm)
        self.assertTrue(norm.startswith(str(Path.home())))

