#!/usr/bin/env python3
"""Descarta arquivos .patch gerados em uma pasta alvo."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove arquivos .patch de uma pasta alvo."
    )
    parser.add_argument(
        "--patches-dir",
        default=None,
        help="Pasta dos patches (obrigatorio via --patches-dir ou PATCHES_DIR).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirma remocao sem prompt.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas lista arquivos que seriam removidos.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    patches_dir_raw = args.patches_dir or ""
    if not patches_dir_raw.strip():
        patches_dir_raw = (os.environ.get("PATCHES_DIR") or "").strip()
    if not patches_dir_raw:
        print("[erro] informe --patches-dir ou defina PATCHES_DIR.", file=sys.stderr)
        return 1

    patches_dir = Path(patches_dir_raw).expanduser().resolve()

    if not patches_dir.is_dir():
        print(f"[erro] pasta de patches nao encontrada: {patches_dir}", file=sys.stderr)
        return 1

    patch_files = sorted(path for path in patches_dir.glob("*.patch") if path.is_file())
    if not patch_files:
        print(f"[ok] nenhum .patch encontrado em: {patches_dir}")
        return 0

    print(f"[info] .patch encontrados: {len(patch_files)}")
    for patch in patch_files:
        print(f"  - {patch}")

    if args.dry_run:
        print("[ok] dry-run concluido (sem remocao).")
        return 0

    if not args.yes:
        confirm = input("Confirmar remocao de TODOS os .patch listados? Digite 'DELETE': ").strip()
        if confirm != "DELETE":
            print("[info] operacao cancelada.")
            return 2

    removed = 0
    for patch in patch_files:
        patch.unlink(missing_ok=False)
        removed += 1

    print(f"[ok] arquivos .patch removidos: {removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
