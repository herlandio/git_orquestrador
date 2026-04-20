from __future__ import annotations

import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

try:
    from scripts.git_orquestrador.helpers import load_module
except ModuleNotFoundError:
    from helpers import load_module


mod = load_module("discard_generated_patches", "src/discard_generated_patches.py")


class DiscardGeneratedPatchesTest(unittest.TestCase):
    def test_main_returns_error_when_missing_patches_dir(self) -> None:
        args = Namespace(patches_dir=None, yes=False, dry_run=False)
        with patch.object(mod, "parse_args", return_value=args), \
            patch.dict(os.environ, {}, clear=True):
            code = mod.main()

        self.assertEqual(code, 1)

    def test_main_dry_run_keeps_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            patch_file = Path(tmpdir) / "0001-test.patch"
            patch_file.write_text("dummy", encoding="utf-8")
            args = Namespace(patches_dir=tmpdir, yes=False, dry_run=True)

            with patch.object(mod, "parse_args", return_value=args):
                code = mod.main()

            self.assertEqual(code, 0)
            self.assertTrue(patch_file.exists())

    def test_main_yes_removes_patch_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            patch_file = Path(tmpdir) / "0001-test.patch"
            patch_file.write_text("dummy", encoding="utf-8")
            args = Namespace(patches_dir=tmpdir, yes=True, dry_run=False)

            with patch.object(mod, "parse_args", return_value=args):
                code = mod.main()

            self.assertEqual(code, 0)
            self.assertFalse(patch_file.exists())


if __name__ == "__main__":
    unittest.main()
