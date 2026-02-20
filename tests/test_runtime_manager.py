import io
import os
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runtime_manager  # type: ignore


class RuntimeManagerTests(unittest.TestCase):
    def test_list_managed_pythons_empty_when_missing(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["NEXUS_RUNTIME_HOME"] = td
            self.assertEqual(runtime_manager.list_managed_pythons(), [])

    def test_choose_managed_python_at_least_picks_highest(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["NEXUS_RUNTIME_HOME"] = td
            base = Path(td) / "python"
            (base / "3.11.8" / "bin").mkdir(parents=True)
            (base / "3.12.1" / "bin").mkdir(parents=True)
            (base / "3.11.8" / "bin" / "python3").write_text("#!/bin/sh\n", encoding="utf-8")
            (base / "3.12.1" / "bin" / "python3").write_text("#!/bin/sh\n", encoding="utf-8")
            (base / "3.11.8" / "bin" / "python3").chmod(0o755)
            (base / "3.12.1" / "bin" / "python3").chmod(0o755)
            mp = runtime_manager.choose_managed_python_at_least(3, 11)
            self.assertIsNotNone(mp)
            self.assertEqual(mp.version, "3.12.1")

    def test_ensure_managed_python_installs_and_links(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["NEXUS_RUNTIME_HOME"] = td

            # Build a tiny tar.gz containing python/bin/python3
            fake_root = Path(td) / "fake"
            (fake_root / "python" / "bin").mkdir(parents=True, exist_ok=True)
            py = fake_root / "python" / "bin" / "python3"
            py.write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
            py.chmod(0o755)

            archive = Path(td) / "python.tgz"
            with tarfile.open(archive, "w:gz") as tf:
                tf.add(fake_root / "python", arcname="python")

            # Monkeypatch urlretrieve to copy our local archive.
            def _fake_urlretrieve(url, filename):
                Path(filename).write_bytes(archive.read_bytes())
                return (str(filename), None)

            orig = runtime_manager.urlretrieve
            runtime_manager.urlretrieve = _fake_urlretrieve  # type: ignore[assignment]
            try:
                mp = runtime_manager.ensure_managed_python("3.11.8", url="file:///ignored.tgz", force=True)
                self.assertTrue(mp.python.exists())
                self.assertTrue(mp.python.is_symlink())
            finally:
                runtime_manager.urlretrieve = orig  # type: ignore[assignment]

    def test_resolve_standalone_python_url_prefers_install_only(self):
        fake_releases = [
            {
                "assets": [
                    {
                        "name": "cpython-3.11.8+foo-aarch64-apple-darwin-install_only.tar.gz",
                        "browser_download_url": "https://example.com/install_only.tgz",
                    },
                    {
                        "name": "cpython-3.11.8+foo-aarch64-apple-darwin.tar.gz",
                        "browser_download_url": "https://example.com/other.tgz",
                    },
                ]
            }
        ]

        class _Resp:
            def __enter__(self):  # noqa: D401
                return self

            def __exit__(self, exc_type, exc, tb):  # noqa: D401
                return False

            def read(self):
                import json as _json

                return _json.dumps(fake_releases).encode("utf-8")

        with patch.object(runtime_manager.platform, "system", return_value="Darwin"), patch.object(
            runtime_manager.platform, "machine", return_value="arm64"
        ), patch.object(runtime_manager, "urlopen", return_value=_Resp()):
            url = runtime_manager.resolve_standalone_python_url("3.11.8")
            self.assertEqual(url, "https://example.com/install_only.tgz")

    def test_safe_extract_blocks_path_traversal(self):
        # Create a tarball with a member that attempts to escape extraction root.
        with tempfile.TemporaryDirectory() as td:
            tar_path = Path(td) / "evil.tgz"
            with tarfile.open(tar_path, "w:gz") as tf:
                info = tarfile.TarInfo(name="../pwned.txt")
                payload = b"nope"
                info.size = len(payload)
                tf.addfile(info, io.BytesIO(payload))

            out = Path(td) / "out"
            out.mkdir(parents=True, exist_ok=True)
            with tarfile.open(tar_path, "r:gz") as tf:
                with self.assertRaises(RuntimeError):
                    runtime_manager._safe_extract_tar_gz(tf, out)  # type: ignore[attr-defined]


if __name__ == "__main__":
    unittest.main()
