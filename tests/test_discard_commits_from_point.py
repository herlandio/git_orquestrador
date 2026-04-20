from __future__ import annotations

import subprocess
import unittest
from argparse import Namespace
from unittest.mock import patch

try:
    from scripts.git_orquestrador.helpers import load_module
except ModuleNotFoundError:
    from helpers import load_module


mod = load_module("discard_commits_from_point", "src/discard_commits_from_point.py")


class DiscardCommitsFromPointTest(unittest.TestCase):
    def test_main_returns_zero_when_target_is_current_head(self) -> None:
        args = Namespace(
            repo_root=".",
            to="HEAD",
            yes=True,
            no_backup_tag=True,
            backup_tag_prefix="backup",
            expected_branch=None,
        )

        responses = [
            subprocess.CompletedProcess(["git"], 0, stdout="true\n", stderr=""),
            subprocess.CompletedProcess(["git"], 0, stdout="abc\n", stderr=""),
            subprocess.CompletedProcess(["git"], 0, stdout="abc\n", stderr=""),
            subprocess.CompletedProcess(["git"], 0, stdout="develop\n", stderr=""),
        ]

        with patch.object(mod, "parse_args", return_value=args), \
            patch.object(mod, "run_git", side_effect=responses) as run_git:
            code = mod.main()

        self.assertEqual(code, 0)
        self.assertEqual(run_git.call_count, 4)

    def test_main_cancels_when_confirmation_is_not_reset(self) -> None:
        args = Namespace(
            repo_root=".",
            to="HEAD~1",
            yes=False,
            no_backup_tag=True,
            backup_tag_prefix="backup",
            expected_branch=None,
        )

        responses = [
            subprocess.CompletedProcess(["git"], 0, stdout="true\n", stderr=""),
            subprocess.CompletedProcess(["git"], 0, stdout="target\n", stderr=""),
            subprocess.CompletedProcess(["git"], 0, stdout="head\n", stderr=""),
            subprocess.CompletedProcess(["git"], 0, stdout="develop\n", stderr=""),
        ]

        with patch.object(mod, "parse_args", return_value=args), \
            patch.object(mod, "run_git", side_effect=responses), \
            patch("builtins.input", return_value="NOPE"):
            code = mod.main()

        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
