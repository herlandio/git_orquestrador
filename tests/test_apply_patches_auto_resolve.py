from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from scripts.git_orquestrador.helpers import load_module
except ModuleNotFoundError:
    from helpers import load_module


mod = load_module("apply_patches_auto_resolve", "src/apply_patches_auto_resolve.py")


class ApplyPatchesAutoResolveTest(unittest.TestCase):
    def test_parse_simple_yaml_list_supports_key_and_inline_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            yml = Path(tmpdir) / "ignore.yml"
            yml.write_text("ignore_files: ['a.txt', 'b.txt']\n- c.txt\n", encoding="utf-8")
            items = mod.parse_simple_yaml_list(yml)

        self.assertIn("a.txt", items)
        self.assertIn("b.txt", items)
        self.assertIn("c.txt", items)

    def test_parse_rename_map_yaml_reads_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            yml = Path(tmpdir) / "rename.yml"
            yml.write_text("rename_map:\n  old/a.py: new/a.py\n", encoding="utf-8")
            mapping = mod.parse_rename_map_yaml(yml)

        self.assertEqual(mapping, {"old/a.py": "new/a.py"})

    def test_should_auto_skip_empty_patch_respects_conflict_markers(self) -> None:
        blocked = "CONFLICT (content): Merge conflict"
        eligible = "No changes - did you forget to use 'git add'?"

        self.assertFalse(mod.should_auto_skip_empty_patch(blocked))
        self.assertTrue(mod.should_auto_skip_empty_patch(eligible))

    def test_build_am_excludes_expands_basename_by_tracked_paths(self) -> None:
        tracked = subprocess.CompletedProcess(["git"], 0, stdout="a/readme.md\nb/readme.md\n", stderr="")
        with patch.object(mod, "run_git", return_value=tracked):
            excludes = mod.build_am_excludes(Path("."), {"readme.md", "foo/bar.py"})

        self.assertIn("a/readme.md", excludes)
        self.assertIn("b/readme.md", excludes)
        self.assertIn("foo/bar.py", excludes)


if __name__ == "__main__":
    unittest.main()
