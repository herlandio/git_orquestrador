#!/usr/bin/env python3
"""Gera arquivos .patch via git format-patch com intervalo e pasta customizaveis."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_git(repo_root: Path, args: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    cmd = ["git", "-C", str(repo_root), *args]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"Falha ao executar: {' '.join(cmd)}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera patches com git format-patch."
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repositorio alvo (default: diretorio atual).",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Pasta de saida dos patches (default: <repo-root>/patches).",
    )
    parser.add_argument(
        "--interval",
        default="",
        help="Intervalo de commits (ex.: origin/main..HEAD). Vazio usa --root.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve()
    out_dir = (
        Path(args.out_dir).expanduser().resolve()
        if args.out_dir
        else (repo_root / "patches").resolve()
    )

    run_git(repo_root, ["rev-parse", "--is-inside-work-tree"], check=True)

    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["format-patch", args.interval if args.interval.strip() else "--root", "--output-directory", str(out_dir)]
    result = run_git(repo_root, cmd)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as err:
        print(f"[erro] {err}", file=sys.stderr)
        raise SystemExit(1)
