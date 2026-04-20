from __future__ import annotations

import subprocess
import unittest
from argparse import Namespace
from unittest.mock import patch

try:
    from scripts.git_orquestrador.helpers import load_module
except ModuleNotFoundError:
    from helpers import load_module


mod = load_module("generate_patches", "src/generate_patches.py")


class GeneratePatchesTest(unittest.TestCase):
    def test_run_git_raises_runtime_error_when_check_fails(self) -> None:
        failed = subprocess.CompletedProcess(["git"], 1, stdout="out", stderr="err")
        with patch.object(mod.subprocess, "run", return_value=failed):
            with self.assertRaises(RuntimeError):
                mod.run_git(mod.Path("."), ["status"], check=True)

    def test_main_uses_root_when_interval_is_empty(self) -> None:
        args = Namespace(repo_root=".", out_dir=None, interval="   ")
        ok = subprocess.CompletedProcess(["git"], 0, stdout="", stderr="")
        done = subprocess.CompletedProcess(["git"], 0, stdout="patch-1\n", stderr="")

        with patch.object(mod, "parse_args", return_value=args), \
            patch.object(mod, "run_git", side_effect=[ok, done]) as run_git:
            code = mod.main()

        self.assertEqual(code, 0)
        self.assertEqual(run_git.call_count, 2)
        second_call_args = run_git.call_args_list[1].args[1]
        self.assertIn("--root", second_call_args)


if __name__ == "__main__":
    unittest.main()
