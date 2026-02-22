from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "cleanup_zone_identifier.py"
SPEC = importlib.util.spec_from_file_location("cleanup_zone_identifier", SCRIPT_PATH)
cleanup_zone_identifier = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(cleanup_zone_identifier)


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")


class CleanupZoneIdentifierTests(unittest.TestCase):
    def test_iter_target_files_skips_virtualenv_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _touch(root / "keep" / "sample.Zone.Identifier")
            _touch(root / ".venv" / "ignored.Zone.Identifier")
            _touch(root / "venv39" / "ignored.Zone.Identifier")

            detected_env = root / "detected_env"
            detected_env.mkdir()
            _touch(detected_env / "pyvenv.cfg")
            _touch(detected_env / "ignored.Zone.Identifier")

            targets = cleanup_zone_identifier.iter_target_files(root, skip_dirs=set())
            target_rel_paths = sorted(p.relative_to(root).as_posix() for p in targets)

            self.assertEqual(target_rel_paths, ["keep/sample.Zone.Identifier"])

    def test_iter_target_files_respects_custom_skip_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _touch(root / "scan_me" / "remove.Zone.Identifier")
            _touch(root / "skip_me" / "do_not_remove.Zone.Identifier")

            targets = cleanup_zone_identifier.iter_target_files(root, skip_dirs={"skip_me"})
            target_rel_paths = sorted(p.relative_to(root).as_posix() for p in targets)

            self.assertEqual(target_rel_paths, ["scan_me/remove.Zone.Identifier"])

    def test_parser_defaults_to_repository_root(self) -> None:
        parser = cleanup_zone_identifier.build_parser()
        args = parser.parse_args([])

        self.assertEqual(Path(args.root).resolve(), cleanup_zone_identifier.REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
