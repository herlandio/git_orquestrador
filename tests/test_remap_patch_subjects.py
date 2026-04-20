from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    from scripts.git_orquestrador.helpers import load_module
except ModuleNotFoundError:
    from helpers import load_module


mod = load_module("remap_patch_subjects", "src/remap_patch_subjects.py")


class RemapPatchSubjectsTest(unittest.TestCase):
    def setUp(self) -> None:
        mod.RemapPatchSubjects.configure_id_patterns(
            mod.RemapPatchSubjects.DEFAULT_ID_PATTERNS,
            4,
        )

    def test_extract_hu_ids_supports_hu_task_and_hash(self) -> None:
        text = "HU #33120 TASK 44550 e ajuste # 33088"
        ids = mod.RemapPatchSubjects.extract_hu_ids(text)
        self.assertEqual(ids, ["33120", "44550", "33088"])

    def test_extract_hu_ids_uses_external_patterns_when_configured(self) -> None:
        mod.RemapPatchSubjects.configure_id_patterns([r"(?:US|HUS)-([0-9]{5})"], 5)
        text = "ajuste HUS-33088 e US-44550"
        ids = mod.RemapPatchSubjects.extract_hu_ids(text)
        self.assertEqual(ids, ["33088", "44550"])

    def test_load_patterns_map_reads_patterns_and_min_digits(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            patterns_file = Path(tmpdir) / "hu-patterns.yml"
            patterns_file.write_text(
                "min_id_digits: 5\n"
                "id_patterns:\n"
                "  - '(?:US|HUS)-([0-9]{5})'\n",
                encoding="utf-8",
            )
            patterns, min_digits = mod.RemapPatchSubjects.load_patterns_map(patterns_file)

        self.assertEqual(min_digits, 5)
        self.assertEqual(patterns, [r"(?:US|HUS)-([0-9]{5})"])

    def test_strip_hu_suffix_replaces_hu_with_gitlab_id(self) -> None:
        subject = "[PATCH] Corrige fluxo HU #33120"
        result = mod.RemapPatchSubjects.strip_hu_suffix(subject, "99887")
        self.assertEqual(result, "[PATCH] Corrige fluxo #99887")

    def test_process_content_dryrun_updates_subject(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = mod.RemapPatchSubjects(
                mapfile=mod.Path(tmpdir) / "map.yml",
                patches_dir=mod.Path(tmpdir),
                dryrun=True,
            )
            runner.mapping = {"33120": "99887"}
            content = (
                "From 123 Mon Sep 17 00:00:00 2001\n"
                "Subject: [PATCH] Ajuste HU #33120\n"
                "\n"
                "Body\n"
                "---\n"
                "diff --git a/a.txt b/a.txt\n"
            )

            changed = runner.process_content(content, f"{tmpdir}/0001-ajuste.patch")

        self.assertTrue(changed)


if __name__ == "__main__":
    unittest.main()
