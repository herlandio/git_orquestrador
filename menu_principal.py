#!/usr/bin/env python3
"""Menu operacional para fluxo de patches.

Opcoes:
1) Gerenciar worktrees (chama worktrees.py)
2) Gerar patches (git format-patch) com intervalo e pasta customizaveis
3) Reescrever HUs/TASKs no Subject (chama remap_patch_subjects.py)
4) Aplicar patches com auto-resolucao de conflitos (chama apply_patches_auto_resolve.py)
5) Descartar patches gerados (chama discard_generated_patches.py)
6) Remover commits vazios (chama drop_empty_commits_auto.py)
7) Descartar commits a partir de um ponto (chama discard_commits_from_point.py)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
SRC_DIR = APP_DIR / "src"
PYTHON_BIN = sys.executable or "python3"
USE_COLOR = sys.stdout.isatty()

COLOR_RED = "\033[31m" if USE_COLOR else ""
COLOR_YELLOW = "\033[33m" if USE_COLOR else ""
COLOR_GREEN = "\033[32m" if USE_COLOR else ""
COLOR_CYAN = "\033[36m" if USE_COLOR else ""
COLOR_BLUE = "\033[34m" if USE_COLOR else ""
COLOR_BOLD = "\033[1m" if USE_COLOR else ""
COLOR_DIM = "\033[2m" if USE_COLOR else ""
COLOR_RESET = "\033[0m" if USE_COLOR else ""


def critical_label(text: str) -> str:
    return f"{COLOR_RED}{COLOR_BOLD}[!]{COLOR_RESET} {text}"


def info_label(text: str) -> str:
    return f"{COLOR_YELLOW}{text}{COLOR_RESET}"


def normal_option_label(text: str) -> str:
    return f"{COLOR_CYAN}{text}{COLOR_RESET}"


def draw_header() -> None:
    width = 58
    line = "=" * width
    git_logo = [
        "   ____ ___ _____ ",
        "  / ___|_ _|_   _|",
        " | |  _ | |  | |  ",
        " | |_| || |  | |  ",
        "  \\____|___| |_|  ",
    ]
    mascot = [
        "",
        "      /\\_/\\  ",
        "     ( o.o ) ",
        "      > ^ <  ",
        "",
    ]
    for logo_row, mascot_row in zip(git_logo, mascot):
        right = f"{COLOR_CYAN}{COLOR_BOLD}{mascot_row}{COLOR_RESET}" if mascot_row else ""
        print(f"{COLOR_RED}{COLOR_BOLD}{logo_row}{COLOR_RESET}   {right}")
    print(f"{COLOR_BLUE}{line}{COLOR_RESET}")
    print(f"{COLOR_BLUE}{COLOR_BOLD} Patch Operations Menu{COLOR_RESET}{COLOR_DIM} | Criadores: Herlandio | Glauco{COLOR_RESET}")
    print(f"{COLOR_BLUE}{line}{COLOR_RESET}")
    print(
        f"{COLOR_RED}{COLOR_BOLD}[OBS] 'AZURE-DEVELOP' E 'GITLAB-DEVELOP' SAO APENAS EXEMPLOS "
        f"DE NOMES DE WORKTREE/BRANCH. USE OS NOMES DO SEU AMBIENTE.{COLOR_RESET}"
    )
    print(f"{COLOR_DIM}Use as opcoes abaixo para executar o fluxo completo.{COLOR_RESET}")


def prompt(message: str, default: str | None = None) -> str:
    print(f"{message}:")
    if default is not None:
        default_text = str(default)
        if default_text:
            preview = default_text
            if len(preview) > 100:
                preview = f"{preview[:47]} ... {preview[-47:]}"
            print(f"  {COLOR_DIM}[padrao] {preview}{COLOR_RESET}")
            print(f"  {COLOR_DIM}(Enter usa o padrao){COLOR_RESET}")
        else:
            print(f"  {COLOR_DIM}[padrao] <vazio>{COLOR_RESET}")
            print(f"  {COLOR_DIM}(Enter mantem vazio){COLOR_RESET}")

    value = input("  > ").strip()
    if not value and default is not None:
        return str(default)
    return value


def prompt_yes_no(message: str, default_yes: bool = True) -> bool:
    default = "s" if default_yes else "n"
    value = input(f"{message} [s/n] ({default}): ").strip().lower()
    if not value:
        value = default
    return value in {"s", "sim", "y", "yes"}


def run_command(cmd: list[str], env: dict[str, str] | None = None) -> int:
    print(f"\n{COLOR_GREEN}[exec]{COLOR_RESET} " + " ".join(cmd))
    proc = subprocess.run(cmd, env=env)
    print(f"{info_label('[info]')} codigo de saida: {proc.returncode}\n")
    return proc.returncode


def option_generate_patches() -> None:
    print("\n== Gerar patches ==")
    script_path = SRC_DIR / "generate_patches.py"
    if not script_path.is_file():
        print(f"[erro] script nao encontrado: {script_path}")
        return

    repo_root = Path(prompt("Repositorio alvo (repo-root)", str(Path.cwd()))).expanduser().resolve()
    out_dir = Path(prompt("Pasta de saida dos patches", str(repo_root / "patches"))).expanduser().resolve()
    interval = prompt("Intervalo (ex: origin/main..HEAD). Vazio usa --root", "")

    cmd = [
        PYTHON_BIN,
        str(script_path),
        "--repo-root",
        str(repo_root),
        "--out-dir",
        str(out_dir),
        "--interval",
        interval,
    ]
    run_command(cmd)


def option_remap_subjects() -> None:
    print("\n== Reescrever HUs/TASKs no Subject ==")
    script_path = SRC_DIR / "remap_patch_subjects.py"
    if not script_path.is_file():
        print(f"[erro] script nao encontrado: {script_path}")
        return

    map_raw = prompt("Arquivo de mapa (MAP)", os.environ.get("MAP"))
    patches_raw = prompt("Pasta de patches (PATCHES_DIR)", os.environ.get("PATCHES_DIR"))
    patterns_default = os.environ.get("PATTERNS_MAP") or str(APP_DIR / "map" / "hu-patterns.yml")
    patterns_raw = prompt("Arquivo de padroes (PATTERNS_MAP, vazio=padrao)", patterns_default)
    if not map_raw.strip() or not patches_raw.strip():
        print("[erro] MAP e PATCHES_DIR sao obrigatorios.")
        return
    map_path = Path(map_raw).expanduser().resolve()
    patches_dir = Path(patches_raw).expanduser().resolve()
    patterns_path = Path(patterns_raw).expanduser().resolve() if patterns_raw.strip() else None
    dry_run = prompt_yes_no("Rodar em dry-run?", default_yes=True)

    env = os.environ.copy()
    env["MAP"] = str(map_path)
    env["PATCHES_DIR"] = str(patches_dir)
    if patterns_path is not None:
        env["PATTERNS_MAP"] = str(patterns_path)

    cmd = [PYTHON_BIN, str(script_path)]
    if patterns_path is not None:
        cmd.extend(["--patterns-map", str(patterns_path)])
    if dry_run:
        cmd.append("--dry-run")
    run_command(cmd, env=env)


def option_apply_with_conflict_resolution() -> None:
    print("\n== Aplicar patches com auto-resolucao de conflitos ==")
    script_path = SRC_DIR / "apply_patches_auto_resolve.py"
    if not script_path.is_file():
        print(f"[erro] script nao encontrado: {script_path}")
        return

    repo_root = Path(
        prompt(
            "Repo de destino onde os patches serao aplicados (--repo-root)",
            str(Path.cwd()),
        )
    ).expanduser().resolve()
    azure_root_raw = prompt("Worktree de origem (--azure-root)", os.environ.get("AZURE_ROOT"))
    patches_dir_raw = prompt("Pasta de patches (--patches-dir)", os.environ.get("PATCHES_DIR"))
    if not azure_root_raw.strip() or not patches_dir_raw.strip():
        print("[erro] --azure-root e --patches-dir sao obrigatorios.")
        return

    ignore_yml_raw = prompt("YAML de ignorados (--ignore-yml, vazio=nao usar)", "")
    rename_map_raw = prompt("YAML de renome (--rename-map-yml, vazio=nao usar)", "")
    apply_branch_raw = prompt("Branch de aplicacao (--apply-branch, vazio=nao usar)", "")
    derive_from_raw = prompt("Base para criar branch (--derive-from-branch, vazio=nao usar)", "")

    cmd = [
        PYTHON_BIN,
        str(script_path),
        "--repo-root",
        str(repo_root),
        "--azure-root",
        str(Path(azure_root_raw).expanduser().resolve()),
        "--patches-dir",
        str(Path(patches_dir_raw).expanduser().resolve()),
    ]
    if ignore_yml_raw.strip():
        cmd.extend(["--ignore-yml", str(Path(ignore_yml_raw).expanduser().resolve())])
    if rename_map_raw.strip():
        cmd.extend(["--rename-map-yml", str(Path(rename_map_raw).expanduser().resolve())])
    if apply_branch_raw.strip():
        cmd.extend(["--apply-branch", apply_branch_raw.strip()])
    if derive_from_raw.strip():
        cmd.extend(["--derive-from-branch", derive_from_raw.strip()])

    run_command(cmd)


def option_drop_empty_commits() -> None:
    print(f"\n== {critical_label('Remover commits vazios')} ==")
    script_path = SRC_DIR / "drop_empty_commits_auto.py"
    if not script_path.is_file():
        print(f"[erro] script nao encontrado: {script_path}")
        return

    repo_root = Path(prompt("Repo alvo (--repo-root)", str(Path.cwd()))).expanduser().resolve()
    base = prompt("Base do intervalo (--base)", "ORIG_HEAD")
    dry_run = prompt_yes_no("Rodar em dry-run?", default_yes=True)
    backup = prompt_yes_no("Criar tag de backup automatica?", default_yes=True)

    cmd = [
        PYTHON_BIN,
        str(script_path),
        "--repo-root",
        str(repo_root),
        "--base",
        base,
    ]
    if dry_run:
        cmd.append("--dry-run")
    if not backup:
        cmd.append("--no-backup-tag")

    run_command(cmd)


def option_discard_commits_from_point() -> None:
    print(f"\n== {critical_label('Descartar commits a partir de um ponto')} ==")
    script_path = SRC_DIR / "discard_commits_from_point.py"
    if not script_path.is_file():
        print(f"[erro] script nao encontrado: {script_path}")
        return

    repo_root = Path(prompt("Repo alvo (--repo-root)", str(Path.cwd()))).expanduser().resolve()
    target = prompt("Ponto alvo do reset (--to, ex: f068ac4b ou HEAD~5)", "")
    if not target.strip():
        print("[erro] ponto alvo obrigatorio.")
        return
    expected_branch = prompt("Branch esperada (--expected-branch, vazio=nao validar)", "")
    backup = prompt_yes_no("Criar tag de backup automatica?", default_yes=True)

    cmd = [
        PYTHON_BIN,
        str(script_path),
        "--repo-root",
        str(repo_root),
        "--to",
        target.strip(),
    ]
    if expected_branch.strip():
        cmd.extend(["--expected-branch", expected_branch.strip()])
    if not backup:
        cmd.append("--no-backup-tag")

    run_command(cmd)


def option_discard_generated_patches() -> None:
    print(f"\n== {critical_label('Descartar patches gerados (.patch)')} ==")
    script_path = SRC_DIR / "discard_generated_patches.py"
    if not script_path.is_file():
        print(f"[erro] script nao encontrado: {script_path}")
        return

    patches_dir_raw = prompt("Pasta de patches (--patches-dir)", os.environ.get("PATCHES_DIR"))
    if not patches_dir_raw.strip():
        print("[erro] --patches-dir obrigatorio.")
        return
    patches_dir = Path(patches_dir_raw).expanduser().resolve()
    dry_run = prompt_yes_no("Rodar em dry-run?", default_yes=True)

    cmd = [
        PYTHON_BIN,
        str(script_path),
        "--patches-dir",
        str(patches_dir),
    ]
    if dry_run:
        cmd.append("--dry-run")

    run_command(cmd)


def option_manage_worktrees() -> None:
    print("\n== Gerenciar worktrees ==")
    script_path = SRC_DIR / "worktrees.py"
    if not script_path.is_file():
        print(f"[erro] script nao encontrado: {script_path}")
        return

    print("Comandos:")
    print("1) init")
    print("2) add")
    print("3) list")
    print("4) remove")
    print("5) remove-ref")
    sub = prompt("Escolha o comando", "1")

    cmd = [PYTHON_BIN, str(script_path)]

    if sub == "1":
        cmd.append("init")
    elif sub == "2":
        which = prompt("Remote (azure|gitlab)", "azure").strip().lower()
        remote_ref = prompt("Ref remota (ex: feature/30958)", "")
        if which not in {"azure", "gitlab"} or not remote_ref.strip():
            print("[erro] parametros invalidos para add.")
            return
        cmd.extend(["add", which, remote_ref.strip()])
    elif sub == "3":
        cmd.append("list")
    elif sub == "4":
        path = prompt("Caminho do worktree para remover", "")
        if not path.strip():
            print("[erro] caminho obrigatorio para remove.")
            return
        cmd.extend(["remove", path.strip()])
        remove_branch = prompt_yes_no("Remover branch local tambem?", default_yes=False)
        if remove_branch:
            branch_name = prompt("Nome da branch local (--branch)", "")
            if not branch_name.strip():
                print("[erro] nome de branch obrigatorio quando --branch for usado.")
                return
            cmd.extend(["--branch", branch_name.strip()])
    elif sub == "5":
        which = prompt("Remote (azure|gitlab)", "azure").strip().lower()
        remote_ref = prompt("Ref remota (ex: feature/30958 ou develop)", "")
        if which not in {"azure", "gitlab"} or not remote_ref.strip():
            print("[erro] parametros invalidos para remove-ref.")
            return
        cmd.extend(["remove-ref", which, remote_ref.strip()])
    else:
        print("[erro] comando invalido.")
        return

    env = os.environ.copy()
    remote_azure = prompt("REMOTE_AZURE (vazio=default)", "")
    remote_gitlab = prompt("REMOTE_GITLAB (vazio=default)", "")
    default_branch = prompt("DEFAULT_BRANCH (vazio=default)", "")
    worktrees_root = prompt("WORKTREES_ROOT (vazio=default)", "")

    if remote_azure.strip():
        env["REMOTE_AZURE"] = remote_azure.strip()
    if remote_gitlab.strip():
        env["REMOTE_GITLAB"] = remote_gitlab.strip()
    if default_branch.strip():
        env["DEFAULT_BRANCH"] = default_branch.strip()
    if worktrees_root.strip():
        env["WORKTREES_ROOT"] = worktrees_root.strip()

    run_command(cmd, env=env)


def main() -> int:
    actions = {
        "1": option_manage_worktrees,
        "2": option_generate_patches,
        "3": option_remap_subjects,
        "4": option_apply_with_conflict_resolution,
        "5": option_discard_generated_patches,
        "6": option_drop_empty_commits,
        "7": option_discard_commits_from_point,
    }

    while True:
        print()
        draw_header()
        print(f"1) {normal_option_label('Gerenciar worktrees (init/add/list/remove/remove-ref)')}")
        print(f"2) {normal_option_label('Gerar patches (intervalo + pasta)')}")
        print(f"3) {normal_option_label('Reescrever HUs/TASKs no Subject')}")
        print(f"4) {normal_option_label('Aplicar patches com auto-resolucao')}")
        print(f"5) {critical_label('Descartar patches gerados (.patch)')}")
        print(f"6) {critical_label('Remover commits vazios')}")
        print(f"7) {critical_label('Descartar commits a partir de um ponto')}")
        print(f"0) {normal_option_label('Sair')}")
        print(f"{COLOR_DIM}Legenda: [!] operacao critica{COLOR_RESET}")
        choice = input(f"{COLOR_BOLD}Escolha uma opcao{COLOR_RESET}: ").strip()

        if choice == "0":
            print("Encerrado.")
            return 0

        action = actions.get(choice)
        if action is None:
            print("[erro] opcao invalida.\n")
            continue

        try:
            action()
        except KeyboardInterrupt:
            print("\n[info] operacao cancelada pelo usuario.\n")
        except Exception as err:  # pragma: no cover - fallback operacional
            print(f"[erro] {err}\n")


if __name__ == "__main__":
    raise SystemExit(main())
