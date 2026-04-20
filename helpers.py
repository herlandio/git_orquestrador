from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


BASE_DIR = Path(__file__).resolve().parent


def load_module(name: str, relative_path: str) -> ModuleType:
    module_path = BASE_DIR / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Nao foi possivel carregar modulo: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
