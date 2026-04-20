from __future__ import annotations

import subprocess
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

try:
    from scripts.git_orquestrador.helpers import load_module
except ModuleNotFoundError:
    from helpers import load_module


mod = load_module("drop_empty_commits_auto", "src/drop_empty_commits_auto.py")


class DropEmptyCommitsAutoTest(unittest.TestCase):
    def test_list_empty_commits_returns_only_empty_commits(self) -> None:
        repo_root = Path(".")

        def fake_run_git(_repo_root: Path, args: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
            if args and args[0] == "rev-list":
                return subprocess.CompletedProcess(["git"], 0, stdout="c1\nc2\n", stderr="")
            if args and args[0] == "diff-tree":
                if args[-1] == "c1":
                    return subprocess.CompletedProcess(["git"], 0, stdout="\n", stderr="")
                if args[-1] == "c2":
                    return subprocess.CompletedProcess(["git"], 0, stdout="file.txt\n", stderr="")
            return subprocess.CompletedProcess(["git"], 0, stdout="", stderr="")

        with patch.object(mod, "run_git", side_effect=fake_run_git):
            empties = mod.list_empty_commits(repo_root, "base")

        self.assertEqual(empties, ["c1"])

    def test_main_returns_zero_when_no_empty_commit(self) -> None:
        args = Namespace(
            repo_root=".",
            base="ORIG_HEAD",
            dry_run=False,
            no_backup_tag=True,
            backup_tag_prefix="backup-before-drop-empty",
        )
        ok = subprocess.CompletedProcess(["git"], 0, stdout="", stderr="")

        with patch.object(mod, "parse_args", return_value=args), \
            patch.object(mod, "run_git", return_value=ok), \
            patch.object(mod, "in_rebase_or_am_session", return_value=False), \
            patch.object(mod, "ensure_clean_worktree"), \
            patch.object(mod, "resolve_ref", return_value="base-sha"), \
            patch.object(mod, "ensure_base_is_ancestor"), \
            patch.object(mod, "list_empty_commits", return_value=[]):
            code = mod.main()

        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
