#!/usr/bin/env python3
"""Remove commits vazios automaticamente no intervalo BASE..HEAD.

Estratégia:
- identifica commits vazios no range (sem arquivos alterados)
- remove um por vez com `git rebase --onto <empty>^ <empty>`
- repete até não restar commit vazio no intervalo

Segurança:
- exige working tree limpa
- exige ausência de rebase/am em andamento
- cria tag de backup antes de alterar histórico (padrão)
"""

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


def in_rebase_or_am_session(repo_root: Path) -> bool:
    def git_path(rel: str) -> Path:
        proc = run_git(repo_root, ["rev-parse", "--git-path", rel], check=True)
        return Path(proc.stdout.strip())

    return (
        git_path("rebase-apply").is_dir()
        or git_path("rebase-merge").is_dir()
    )


def ensure_clean_worktree(repo_root: Path) -> None:
    status = run_git(repo_root, ["status", "--porcelain"], check=True).stdout.strip()
    if status:
        raise RuntimeError(
            "Working tree nao esta limpa. Faça commit/stash/reset antes de remover commits vazios."
        )


def resolve_ref(repo_root: Path, ref: str) -> str:
    proc = run_git(repo_root, ["rev-parse", "--verify", ref], check=True)
    return proc.stdout.strip()


def ensure_base_is_ancestor(repo_root: Path, base: str) -> None:
    proc = run_git(repo_root, ["merge-base", "--is-ancestor", base, "HEAD"])
    if proc.returncode != 0:
        raise RuntimeError(f"Base '{base}' nao e ancestral de HEAD.")


def list_empty_commits(repo_root: Path, base: str) -> list[str]:
    revs = run_git(repo_root, ["rev-list", "--reverse", f"{base}..HEAD"], check=True).stdout.splitlines()
    empties: list[str] = []
    for commit in [item.strip() for item in revs if item.strip()]:
        files = run_git(repo_root, ["diff-tree", "--no-commit-id", "--name-only", "-r", commit], check=True)
        if not files.stdout.strip():
            empties.append(commit)
    return empties


def create_backup_tag(repo_root: Path, prefix: str) -> str:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    tag_name = f"{prefix}-{stamp}"
    run_git(repo_root, ["tag", tag_name], check=True)
    return tag_name


def delete_backup_tag(repo_root: Path, tag_name: str) -> bool:
    proc = run_git(repo_root, ["tag", "-d", tag_name])
    if proc.returncode == 0:
        return True
    return False


def remove_empty_commits(repo_root: Path, base: str, dry_run: bool) -> int:
    removed = 0
    while True:
        empties = list_empty_commits(repo_root, base)
        if not empties:
            return removed

        current = empties[0]
        parent = resolve_ref(repo_root, f"{current}^")
        short = run_git(repo_root, ["show", "-s", "--format=%h %s", current], check=True).stdout.strip()
        print(f"[auto] removendo commit vazio: {short}")

        if dry_run:
            removed += 1
            # Mantido por compatibilidade de assinatura; o dry-run real é tratado em main.
            return removed

        rebase = run_git(repo_root, ["rebase", "--onto", parent, current])
        sys.stdout.write(rebase.stdout)
        sys.stderr.write(rebase.stderr)
        if rebase.returncode != 0:
            raise RuntimeError(
                "Falha no rebase ao remover commit vazio. "
                "Resolva conflitos e use 'git rebase --continue' ou 'git rebase --abort'."
            )
        removed += 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove commits vazios automaticamente no intervalo BASE..HEAD."
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repositorio alvo (default: diretorio atual).",
    )
    parser.add_argument(
        "--base",
        default="ORIG_HEAD",
        help="Commit base do intervalo (default: ORIG_HEAD).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas mostra a primeira remocao que seria feita, sem alterar historico.",
    )
    parser.add_argument(
        "--no-backup-tag",
        action="store_true",
        help="Nao cria tag de backup antes de reescrever historico.",
    )
    parser.add_argument(
        "--backup-tag-prefix",
        default="backup-before-drop-empty",
        help="Prefixo da tag de backup (default: backup-before-drop-empty).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()

    run_git(repo_root, ["rev-parse", "--is-inside-work-tree"], check=True)

    if in_rebase_or_am_session(repo_root):
        print(
            "[erro] Existe sessao de rebase/am em andamento. Finalize com --continue/--abort antes.",
            file=sys.stderr,
        )
        return 2

    ensure_clean_worktree(repo_root)
    base_sha = resolve_ref(repo_root, args.base)
    ensure_base_is_ancestor(repo_root, base_sha)

    empties_before = list_empty_commits(repo_root, base_sha)
    if not empties_before:
        print("[ok] Nenhum commit vazio encontrado no intervalo BASE..HEAD.")
        return 0

    print(f"[info] commits vazios encontrados: {len(empties_before)}")
    if args.dry_run:
        print("[dry-run] commits vazios no intervalo BASE..HEAD:")
        for commit in empties_before:
            short = run_git(repo_root, ["show", "-s", "--format=%h %s", commit], check=True).stdout.strip()
            print(f"  - {short}")
        print("[ok] dry-run concluido (sem alteracao de historico).")
        return 0

    backup_tag: str | None = None
    if not args.dry_run and not args.no_backup_tag:
        tag = create_backup_tag(repo_root, args.backup_tag_prefix)
        backup_tag = tag
        print(f"[info] tag de backup criada: {tag}")

    removed = remove_empty_commits(repo_root, base_sha, args.dry_run)

    print(f"[ok] commits vazios removidos: {removed}")
    if backup_tag:
        if delete_backup_tag(repo_root, backup_tag):
            print(f"[info] operacao concluida com sucesso; tag de backup removida: {backup_tag}")
        else:
            print(f"[warn] operacao concluida, mas nao foi possivel remover a tag: {backup_tag}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as err:
        print(f"[erro] {err}", file=sys.stderr)
        raise SystemExit(1)
