import sys
import tempfile
import unittest
from pathlib import Path


class TestForgeEngineBaselineServer(unittest.TestCase):
    def test_ensure_server_entrypoint_does_not_eval_inner_fstrings(self) -> None:
        """
        Regression: ForgeEngine used an outer f-string to build mcp_server.py content.
        Any inner f-strings in the generated server must keep placeholders like {name}
        literally, otherwise forge time raises NameError.
        """
        repo_root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(repo_root / "mcp-server-manager"))
        from forge.forge_engine import ForgeEngine  # type: ignore

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            suite_root = td_path / "suite"
            (suite_root / "mcp-link-library").mkdir(parents=True)
            (suite_root / "mcp-link-library" / "mcp_wrapper.py").write_text("#wrapper", encoding="utf-8")
            (suite_root / "mcp-link-library" / "atp_sandbox.py").write_text("#sandbox", encoding="utf-8")

            engine = ForgeEngine(suite_root=suite_root, inventory_path=td_path / "inventory.yaml")
            target = td_path / "target"
            target.mkdir()

            engine._ensure_server_entrypoint(target)
            generated = (target / "mcp_server.py").read_text(encoding="utf-8")

            for needle in ("{name}", "{method}", "{e}"):
                self.assertIn(needle, generated)


if __name__ == "__main__":
    unittest.main()

