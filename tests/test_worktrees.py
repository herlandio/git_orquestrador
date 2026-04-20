from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from scripts.git_orquestrador.helpers import load_module
except ModuleNotFoundError:
    from helpers import load_module


mod = load_module("worktrees", "src/worktrees.py")


class WorktreesTest(unittest.TestCase):
    def test_ensure_tracking_branch_sets_upstream_when_local_branch_exists(self) -> None:
        with patch.object(mod, "local_branch_exists", return_value=True), \
            patch.object(mod, "run_git") as run_git:
            mod.ensure_tracking_branch("azure", "develop", "azure-develop")

        run_git.assert_called_once_with(
            ["branch", "--set-upstream-to", "azure/develop", "azure-develop"], check=False
        )

    def test_ensure_tracking_branch_fails_when_remote_ref_does_not_exist(self) -> None:
        with patch.object(mod, "local_branch_exists", return_value=False), \
            patch.object(mod, "remote_ref_exists", return_value=False):
            with self.assertRaises(SystemExit):
                mod.ensure_tracking_branch("azure", "missing", "azure-missing")

    def test_cmd_add_normalizes_branch_name_and_calls_add_worktree(self) -> None:
        root = Path("/tmp/worktrees")
        with patch.object(mod, "need_git_repo"), \
            patch.object(mod, "get_env_defaults", return_value=("azure", "gitlab", "develop", root)), \
            patch.object(mod, "ensure_remote_exists"), \
            patch.object(mod, "fetch_all"), \
            patch.object(mod, "ensure_tracking_branch") as tracking, \
            patch.object(mod, "add_worktree") as add_worktree:
            rc = mod.cmd_add("azure", "feature/123")

        self.assertEqual(rc, 0)
        tracking.assert_called_once_with("azure", "feature/123", "azure-feature-123")
        add_worktree.assert_called_once_with(root / "azure-feature-123", "azure-feature-123")

    def test_branch_in_use_by_worktree_true_when_branch_marker_exists(self) -> None:
        output = subprocess.CompletedProcess(
            ["git"],
            0,
            stdout="/repo/path  abcd [azure-develop]\n",
            stderr="",
        )
        with patch.object(mod, "run_git", return_value=output):
            in_use = mod.branch_in_use_by_worktree("azure-develop")

        self.assertTrue(in_use)


if __name__ == "__main__":
    unittest.main()
