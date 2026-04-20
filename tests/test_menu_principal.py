from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

try:
    from scripts.git_orquestrador.helpers import load_module
except ModuleNotFoundError:
    from helpers import load_module


mod = load_module("menu_principal", "menu_principal.py")


class MenuPrincipalTest(unittest.TestCase):
    def test_prompt_returns_default_on_empty_input(self) -> None:
        with patch("builtins.input", return_value=""):
            value = mod.prompt("Mensagem", "padrao")
        self.assertEqual(value, "padrao")

    def test_prompt_uses_compact_entry_cursor(self) -> None:
        with patch("builtins.input", return_value="valor") as mocked_input:
            value = mod.prompt("Mensagem", "padrao")
        self.assertEqual(value, "valor")
        mocked_input.assert_called_with("  > ")

    def test_prompt_yes_no_accepts_default_yes(self) -> None:
        with patch("builtins.input", return_value=""):
            value = mod.prompt_yes_no("Confirmar?", default_yes=True)
        self.assertTrue(value)

    def test_run_command_returns_subprocess_exit_code(self) -> None:
        proc = subprocess.CompletedProcess(["python"], 7, stdout="", stderr="")
        with patch.object(mod.subprocess, "run", return_value=proc):
            rc = mod.run_command(["python", "script.py"])
        self.assertEqual(rc, 7)


if __name__ == "__main__":
    unittest.main()
