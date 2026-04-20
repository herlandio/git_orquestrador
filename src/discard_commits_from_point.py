#!/usr/bin/env python3
"""Descarta commits a partir de um ponto usando git reset --hard."""

from __future__ import annotations

import argparse
import datetime as dt
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
        description="Descarta commits a partir de um ponto com git reset --hard."
    )
    parser.add_argument("--repo-root", default=".", help="Repositorio alvo (default: diretorio atual).")
    parser.add_argument(
        "--to",
        required=True,
        help="Commit/alvo para reset (ex.: f068ac4b ou HEAD~5).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirma execucao sem prompt interativo.",
    )
    parser.add_argument(
        "--no-backup-tag",
        action="store_true",
        help="Nao cria tag de backup antes do reset.",
    )
    parser.add_argument(
        "--backup-tag-prefix",
        default="backup-before-discard",
        help="Prefixo da tag de backup (default: backup-before-discard).",
    )
    parser.add_argument(
        "--expected-branch",
        default=None,
        help="Cancela a operacao se a branch atual for diferente deste valor.",
    )
    return parser.parse_args()


def create_backup_tag(repo_root: Path, prefix: str) -> str:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    tag = f"{prefix}-{stamp}"
    run_git(repo_root, ["tag", tag], check=True)
    return tag


def delete_backup_tag(repo_root: Path, tag: str) -> bool:
    proc = run_git(repo_root, ["tag", "-d", tag])
    if proc.returncode == 0:
        return True
    return False


def current_branch(repo_root: Path) -> str:
    proc = run_git(repo_root, ["symbolic-ref", "--short", "-q", "HEAD"])
    name = proc.stdout.strip()
    return name if name else "(detached HEAD)"


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve()
    run_git(repo_root, ["rev-parse", "--is-inside-work-tree"], check=True)

    target = run_git(repo_root, ["rev-parse", "--verify", args.to], check=True).stdout.strip()
    current = run_git(repo_root, ["rev-parse", "--verify", "HEAD"], check=True).stdout.strip()
    branch = current_branch(repo_root)

    print(f"[info] branch atual: {branch}")
    print(f"[info] HEAD atual: {current}")
    print(f"[info] alvo do reset: {target}")
    print("[aviso] o reset sera aplicado na branch/referencia atual acima.")

    expected_branch = (args.expected_branch or "").strip()
    if expected_branch and branch != expected_branch:
        print(
            f"[erro] branch atual '{branch}' difere da esperada '{expected_branch}'. Operacao cancelada.",
            file=sys.stderr,
        )
        return 4

    if target == current:
        print("[ok] alvo ja e o HEAD atual. Nada a fazer.")
        return 0

    backup_tag: str | None = None
    if not args.no_backup_tag:
        tag = create_backup_tag(repo_root, args.backup_tag_prefix)
        backup_tag = tag
        print(f"[info] tag de backup criada: {tag}")

    if not args.yes:
        confirm = input("Confirmar reset --hard para esse ponto? Digite 'RESET': ").strip()
        if confirm != "RESET":
            print("[info] operacao cancelada.")
            return 2

    result = run_git(repo_root, ["reset", "--hard", target])
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode == 0 and backup_tag:
        if delete_backup_tag(repo_root, backup_tag):
            print(f"[info] operacao concluida com sucesso; tag de backup removida: {backup_tag}")
        else:
            print(f"[warn] operacao concluida, mas nao foi possivel remover a tag: {backup_tag}", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as err:
        print(f"[erro] {err}", file=sys.stderr)
        raise SystemExit(1)
