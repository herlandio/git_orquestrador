#!/usr/bin/env python3
"""Gerenciamento de git worktrees para ambientes azure/gitlab.

Comandos compatíveis com a versão shell:
- init
- add <azure|gitlab> <ref-remota>
- list
- remove <caminho> [--branch <nome-branch-local>]
- remove-ref <azure|gitlab> <ref-remota>
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def die(message: str) -> None:
    print(f"[erro] {message}", file=sys.stderr)
    raise SystemExit(1)


def run_git(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        details = "\n".join(part for part in [stdout, stderr] if part)
        if details:
            die(f"falha ao executar git {' '.join(args)}\n{details}")
        die(f"falha ao executar git {' '.join(args)}")
    return proc


def is_inside_repo() -> bool:
    proc = run_git(["rev-parse", "--is-inside-work-tree"], check=False)
    return proc.returncode == 0


def need_git_repo() -> None:
    if not is_inside_repo():
        die("execute dentro de um repositório git")


def repo_root() -> Path:
    proc = run_git(["rev-parse", "--show-toplevel"])
    return Path(proc.stdout.strip())


def get_env_defaults() -> tuple[str, str, str, Path]:
    remote_azure = os.environ.get("REMOTE_AZURE", "azure")
    remote_gitlab = os.environ.get("REMOTE_GITLAB", "gitlab")
    default_branch = os.environ.get("DEFAULT_BRANCH", "develop")

    worktrees_root_env = os.environ.get("WORKTREES_ROOT")
    if worktrees_root_env:
        worktrees_root = Path(worktrees_root_env).expanduser().resolve()
    elif is_inside_repo():
        worktrees_root = repo_root() / "_worktrees"
    else:
        worktrees_root = Path("_worktrees").resolve()

    return remote_azure, remote_gitlab, default_branch, worktrees_root


def ensure_remote_exists(remote: str) -> None:
    proc = run_git(["remote", "get-url", remote], check=False)
    if proc.returncode != 0:
        die(f"remote '{remote}' não existe. Verifique com: git remote -v")


def fetch_remote(remote: str) -> None:
    proc = run_git(["fetch", "--prune", remote], check=False)
    if proc.returncode != 0:
        print(f"[warn] falha no fetch de {remote}; seguindo execução", file=sys.stderr)


def fetch_all(remote_azure: str, remote_gitlab: str) -> None:
    print("[info] executando fetch nos remotes...")
    fetch_remote(remote_azure)
    fetch_remote(remote_gitlab)


def local_branch_exists(local_branch: str) -> bool:
    proc = run_git(["show-ref", "--verify", "--quiet", f"refs/heads/{local_branch}"], check=False)
    return proc.returncode == 0


def remote_ref_exists(remote: str, remote_ref: str) -> bool:
    proc = run_git(
        ["show-ref", "--verify", "--quiet", f"refs/remotes/{remote}/{remote_ref}"],
        check=False,
    )
    return proc.returncode == 0


def ensure_tracking_branch(remote: str, remote_ref: str, local_branch: str) -> None:
    if local_branch_exists(local_branch):
        run_git(["branch", "--set-upstream-to", f"{remote}/{remote_ref}", local_branch], check=False)
        return

    if not remote_ref_exists(remote, remote_ref):
        die(f"branch remota não encontrada: {remote}/{remote_ref}")

    run_git(["branch", "--track", local_branch, f"{remote}/{remote_ref}"])


def worktree_path_by_branch(local_branch: str) -> str | None:
    proc = run_git(["worktree", "list", "--porcelain"])
    current_path = ""
    target_branch = f"refs/heads/{local_branch}"

    for line in proc.stdout.splitlines():
        if line.startswith("worktree "):
            current_path = line.split(" ", 1)[1].strip()
            continue
        if line.startswith("branch "):
            branch = line.split(" ", 1)[1].strip()
            if branch == target_branch:
                return current_path
    return None


def add_worktree(path: Path, local_branch: str) -> None:
    if path.exists():
        git_marker_file = path / ".git"
        if git_marker_file.exists():
            print(f"[info] worktree já existe em: {path}")
            return
        die(f"pasta '{path}' já existe mas não parece um worktree")

    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[info] criando worktree: {path} -> {local_branch}")
    run_git(["worktree", "add", str(path), local_branch])


def remove_worktree_hard(path_input: str) -> None:
    root = repo_root()
    raw_path = Path(path_input).expanduser()
    path = raw_path.resolve() if raw_path.exists() else raw_path

    cwd = Path.cwd().resolve()
    if str(cwd).startswith(str(path)):
        die("você está dentro do worktree a remover; saia dele e tente novamente")

    print(f"[info] removendo worktree: {path}")

    removed = False
    for flag in ["--force", "-f"]:
        proc = run_git(["-C", str(root), "worktree", "remove", flag, str(path)], check=False)
        if proc.returncode == 0:
            removed = True
            break

    if not removed:
        run_git(["-C", str(root), "worktree", "prune", "--expire", "now"], check=False)

    if path.exists() and path.is_dir():
        shutil.rmtree(path)

    run_git(["-C", str(root), "worktree", "prune", "--expire", "now"], check=False)
    print("[ok] worktree removido/limpo")


def branch_in_use_by_worktree(local_branch: str) -> bool:
    proc = run_git(["worktree", "list"])
    target = f"[{local_branch}]"
    return any(target in line for line in proc.stdout.splitlines())


def delete_local_branch(local_branch: str) -> None:
    if not local_branch_exists(local_branch):
        print(f"[info] branch local não existe: {local_branch}")
        return

    proc = run_git(["branch", "-d", local_branch], check=False)
    if proc.returncode == 0:
        print(f"[ok] branch removida: {local_branch}")
        return

    if branch_in_use_by_worktree(local_branch):
        die(f"branch '{local_branch}' está em uso por um worktree")

    run_git(["branch", "-D", local_branch])
    print(f"[ok] branch removida (forçada): {local_branch}")


def cmd_init() -> int:
    need_git_repo()
    remote_azure, remote_gitlab, default_branch, worktrees_root = get_env_defaults()

    ensure_remote_exists(remote_azure)
    ensure_remote_exists(remote_gitlab)
    fetch_all(remote_azure, remote_gitlab)

    worktrees_root.mkdir(parents=True, exist_ok=True)

    b1 = f"azure-{default_branch}"
    b2 = f"gitlab-{default_branch}"

    ensure_tracking_branch(remote_azure, default_branch, b1)
    ensure_tracking_branch(remote_gitlab, default_branch, b2)

    add_worktree(worktrees_root / b1, b1)
    add_worktree(worktrees_root / b2, b2)

    print("[ok] init concluído")
    print(f"  - {worktrees_root / b1} (track: {remote_azure}/{default_branch})")
    print(f"  - {worktrees_root / b2} (track: {remote_gitlab}/{default_branch})")
    return 0


def cmd_add(which: str, remote_ref: str) -> int:
    need_git_repo()
    remote_azure, remote_gitlab, _default_branch, worktrees_root = get_env_defaults()

    if which == "azure":
        remote = remote_azure
        local_branch = f"azure-{remote_ref.replace('/', '-')}"
    elif which == "gitlab":
        remote = remote_gitlab
        local_branch = f"gitlab-{remote_ref.replace('/', '-')}"
    else:
        die("remote inválido. Use: azure | gitlab")

    folder = worktrees_root / local_branch

    ensure_remote_exists(remote)
    fetch_all(remote_azure, remote_gitlab)

    ensure_tracking_branch(remote, remote_ref, local_branch)
    add_worktree(folder, local_branch)

    print(f"[ok] criado: {folder} (track: {remote}/{remote_ref})")
    return 0


def cmd_list() -> int:
    need_git_repo()
    proc = run_git(["worktree", "list"], check=True)
    print(proc.stdout, end="")
    return 0


def cmd_remove(path: str, branch: str | None) -> int:
    need_git_repo()
    if not Path(path).expanduser().exists():
        die(f"caminho não existe: {path}")

    remove_worktree_hard(path)

    if branch:
        delete_local_branch(branch)

    return 0


def cmd_remove_ref(which: str, remote_ref: str) -> int:
    need_git_repo()
    _remote_azure, _remote_gitlab, _default_branch, worktrees_root = get_env_defaults()

    if which == "azure":
        local_branch = f"azure-{remote_ref.replace('/', '-')}"
    elif which == "gitlab":
        local_branch = f"gitlab-{remote_ref.replace('/', '-')}"
    else:
        die("remote inválido. Use: azure | gitlab")

    folder = worktrees_root / local_branch

    if folder.exists():
        remove_worktree_hard(str(folder))
    else:
        wt_path = worktree_path_by_branch(local_branch)
        if wt_path:
            print(f"[info] pasta esperada não existe: {folder}")
            print(f"[info] worktree encontrado para '{local_branch}': {wt_path}")
            remove_worktree_hard(wt_path)
        else:
            print(f"[info] worktree não encontrado para: {folder}; removendo só branch local")
            run_git(["worktree", "prune", "--expire", "now"], check=False)

    delete_local_branch(local_branch)
    print(f"[ok] remoção por ref concluída: {which}/{remote_ref}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gerencia git worktrees para remotes azure/gitlab.")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="Cria worktrees padrão para develop/main dos dois remotes.")

    p_add = sub.add_parser("add", help="Cria worktree para remote/ref específica.")
    p_add.add_argument("which", choices=["azure", "gitlab"], help="remote alvo")
    p_add.add_argument("remote_ref", help="ref remota (ex: feature/30958)")

    sub.add_parser("list", help="Lista worktrees")

    p_remove = sub.add_parser("remove", help="Remove worktree por caminho")
    p_remove.add_argument("path", help="caminho do worktree")
    p_remove.add_argument("--branch", default=None, help="remove branch local após remover worktree")

    p_remove_ref = sub.add_parser("remove-ref", help="Remove por remote/ref (worktree + branch local espelho)")
    p_remove_ref.add_argument("which", choices=["azure", "gitlab"], help="remote alvo")
    p_remove_ref.add_argument("remote_ref", help="ref remota (ex: develop, feature/30958)")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init":
        return cmd_init()
    if args.command == "add":
        return cmd_add(args.which, args.remote_ref)
    if args.command == "list":
        return cmd_list()
    if args.command == "remove":
        return cmd_remove(args.path, args.branch)
    if args.command == "remove-ref":
        return cmd_remove_ref(args.which, args.remote_ref)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
