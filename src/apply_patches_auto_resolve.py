#!/usr/bin/env python3
"""Aplica patches com auto-resolucao por copia do worktree Azure.

Fluxo:
- inicia `git am --3way` com todos os patches (ordem alfabetica)
- quando houver conflito, tenta resolver cada arquivo por `rename_map` e,
  na falta dele, por nome de arquivo (basename) no worktree Azure
- para nomes repetidos, aplica desempate seguro por similaridade de caminho
  e evita `vendor` quando possivel
- executa `git add` e `git am --continue`
- usa `git am --skip` automaticamente para patch sem diff util ja aplicado
- tenta novamente operacoes de git em falhas transitórias de `index.lock`
- interrompe quando nao consegue resolver com seguranca

Retomada:
- se houver sessao `git am` em andamento, ao executar novamente o script ele
  continua do ponto atual usando `git am --continue`.

Ignorar arquivos:
- permite ignorar um ou mais arquivos via `--ignore-file`
- permite carregar lista de ignorados via `--ignore-yml`
- para arquivo ignorado em conflito, mantem a versao local do gitlab (`--ours`)
  e continua.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def run_git(repo_root: Path, args: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    cmd = ["git", "-C", str(repo_root), *args]
    retries = 3
    delay_seconds = 0.25
    proc = subprocess.run(cmd, capture_output=True, text=True)
    for _ in range(retries):
        if proc.returncode == 0:
            break
        stderr = (proc.stderr or "").lower()
        lock_contention = (
            "index.lock" in stderr
            and (
                "file exists" in stderr
                or "resource temporarily unavailable" in stderr
            )
        )
        if not lock_contention:
            break
        time.sleep(delay_seconds)
        proc = subprocess.run(cmd, capture_output=True, text=True)

    if check and proc.returncode != 0:
        raise RuntimeError(
            f"Falha ao executar: {' '.join(cmd)}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc


def get_git_path(repo_root: Path, relative_path: str) -> Path:
    proc = run_git(repo_root, ["rev-parse", "--git-path", relative_path], check=True)
    return Path(proc.stdout.strip())


def in_am_session(repo_root: Path) -> bool:
    # Em worktree, .git e um arquivo ponteiro. O caminho correto deve vir do
    # proprio git.
    return get_git_path(repo_root, "rebase-apply").is_dir()


def get_unmerged_paths(repo_root: Path) -> list[str]:
    # Mais confiavel para conflitos durante git am/rebase em worktree.
    proc = run_git(repo_root, ["ls-files", "-u"], check=True)
    paths: list[str] = []
    seen: set[str] = set()
    for line in proc.stdout.splitlines():
        # Formato: <mode> <sha> <stage>\t<path>
        if "\t" not in line:
            continue
        path = line.split("\t", 1)[1].strip()
        if path and path not in seen:
            seen.add(path)
            paths.append(path)
    return paths


def is_path_unmerged(repo_root: Path, rel: str) -> bool:
    proc = run_git(repo_root, ["ls-files", "-u", "--", rel], check=True)
    return bool(proc.stdout.strip())


def read_stage_blob(repo_root: Path, stage: int, rel: str) -> str | None:
    proc = run_git(repo_root, ["show", f":{stage}:{rel}"])
    if proc.returncode != 0:
        return None
    return proc.stdout


def parse_simple_yaml_list(yml_path: Path) -> list[str]:
    """Parser simples para listas YAML.

    Suporta:
    - lista direta:
        - arquivo1
        - pasta/arquivo2
    - chave ignore_files/ignored_files/files:
        ignore_files:
          - arquivo1
          - pasta/arquivo2
    """
    items: list[str] = []
    in_supported_key_block = False

    with yml_path.open("r", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            if ":" in line and not line.startswith("-"):
                key, _, value = line.partition(":")
                key = key.strip().lower()
                value = value.strip()
                in_supported_key_block = key in {"ignore_files", "ignored_files", "files"}

                # suporte para lista inline: ignore_files: [a, b]
                if in_supported_key_block and value.startswith("[") and value.endswith("]"):
                    content = value[1:-1]
                    for part in content.split(","):
                        item = part.strip().strip("'\"")
                        if item:
                            items.append(item)
                continue

            if line.startswith("-"):
                item = line[1:].strip().strip("'\"")
                if item:
                    items.append(item)

    return items


def parse_rename_map_yaml(yml_path: Path) -> dict[str, str]:
    """Parser simples para mapa de renome.

    Formato esperado:
      rename_map:
        caminho/antigo.php: caminho/novo.php
        outro/antigo.vue: outro/novo.vue
    """
    mapping: dict[str, str] = {}
    in_block = False

    with yml_path.open("r", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            if line.endswith(":") and not line.startswith("-"):
                key = line[:-1].strip().lower()
                in_block = key in {"rename_map", "renames", "rename"}
                continue

            if not in_block or ":" not in line:
                continue

            src, _, dst = line.partition(":")
            src = src.strip().strip("'\"")
            dst = dst.strip().strip("'\"")
            if src and dst:
                mapping[src] = dst

    return mapping


def build_ignored_specs(ignore_files: list[str], ignore_yml: str | None) -> set[str]:
    specs = {item.strip() for item in ignore_files if item and item.strip()}
    if ignore_yml:
        yml_path = Path(ignore_yml).resolve()
        if not yml_path.is_file():
            raise RuntimeError(f"Arquivo YAML de ignorados nao encontrado: {yml_path}")
        yml_items = parse_simple_yaml_list(yml_path)
        specs.update(item.strip() for item in yml_items if item and item.strip())
    return specs


def build_rename_map(rename_map_yml: str | None) -> dict[str, str]:
    if not rename_map_yml:
        return {}
    yml_path = Path(rename_map_yml).resolve()
    if not yml_path.is_file():
        raise RuntimeError(f"Arquivo YAML de renome nao encontrado: {yml_path}")
    return parse_rename_map_yaml(yml_path)


def is_ignored_path(rel_path: str, ignored_specs: set[str]) -> bool:
    if not ignored_specs:
        return False

    rel = rel_path.strip()
    name = Path(rel).name

    for spec in ignored_specs:
        if rel == spec or name == spec:
            return True
    return False


def build_azure_basename_index(azure_root: Path) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    for path in azure_root.rglob("*"):
        if path.is_file():
            index.setdefault(path.name, []).append(path)
    return index


def suffix_match_score(left_parts: list[str], right_parts: list[str]) -> int:
    score = 0
    i = 1
    while i <= len(left_parts) and i <= len(right_parts):
        if left_parts[-i] != right_parts[-i]:
            break
        score += 1
        i += 1
    return score


def choose_best_candidate_by_name(azure_root: Path, rel: str, candidates: list[Path]) -> Path | None:
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    rel_parts = Path(rel).parts
    scored: list[tuple[int, bool, Path]] = []
    for candidate in candidates:
        candidate_rel = candidate.relative_to(azure_root)
        candidate_parts = candidate_rel.parts
        score = suffix_match_score(list(candidate_parts), list(rel_parts))
        is_vendor = "vendor" in candidate_parts
        scored.append((score, is_vendor, candidate))

    scored.sort(key=lambda item: (item[0], not item[1]), reverse=True)
    best_score, best_is_vendor, best_candidate = scored[0]
    same_best = [item for item in scored if item[0] == best_score and item[1] == best_is_vendor]
    # Em caso de nomes repetidos, só aceita auto-match quando há
    # alinhamento mínimo de caminho (>= 2 segmentos finais), para evitar
    # escolher arquivo errado apenas por nome.
    if len(same_best) == 1 and best_score >= 2:
        return best_candidate

    non_vendor = [item for item in scored if not item[1]]
    if len(non_vendor) == 1 and non_vendor[0][0] >= 2:
        return non_vendor[0][2]

    return None


def find_source_in_azure_by_name(
    azure_root: Path, rel: str, basename_index: dict[str, list[Path]] | None
) -> tuple[Path | None, dict[str, list[Path]] | None, bool]:
    """Localiza arquivo no Azure somente pelo nome (basename).

    Estratégia segura:
    - ignora caminho relativo
    - só aceita quando houver correspondência única
    """
    if basename_index is None:
        basename_index = build_azure_basename_index(azure_root)

    name = Path(rel).name
    candidates = basename_index.get(name, [])
    chosen = choose_best_candidate_by_name(azure_root, rel, candidates)
    if chosen is not None:
        return chosen, basename_index, False
    if len(candidates) > 1:
        return None, basename_index, True
    return None, basename_index, False


def resolve_conflicts_with_azure(
    repo_root: Path, azure_root: Path, ignored_specs: set[str], rename_map: dict[str, str]
) -> bool:
    """Resolve conflitos sempre priorizando o estado do Azure."""
    unmerged = get_unmerged_paths(repo_root)
    if not unmerged:
        return True

    basename_index: dict[str, list[Path]] | None = None

    for rel in unmerged:
        if is_ignored_path(rel, ignored_specs):
            run_git(repo_root, ["checkout", "--ours", "--", rel])
            run_git(repo_root, ["add", "--", rel])

            # Alguns conflitos continuam em UU mesmo após --ours.
            # Fallback: força o conteúdo do stage 2 (ours) no arquivo.
            if is_path_unmerged(repo_root, rel):
                stage2 = read_stage_blob(repo_root, 2, rel)
                dst = repo_root / rel
                if stage2 is not None:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_text(stage2, encoding="utf-8", errors="replace")
                    run_git(repo_root, ["add", "--", rel], check=True)
                else:
                    # Sem stage 2: tenta manter ausência no índice.
                    run_git(repo_root, ["rm", "-f", "--ignore-unmatch", "--", rel])

            if is_path_unmerged(repo_root, rel):
                print(f"[stop] nao foi possivel resolver arquivo ignorado: {rel}", file=sys.stderr)
                return False

            print(f"[ignore] mantendo versao local (gitlab): {rel}")
            continue

        dst = repo_root / rel
        src: Path | None = None

        mapped = rename_map.get(rel)
        if mapped:
            mapped_src = azure_root / mapped
            if mapped_src.is_file():
                src = mapped_src
                print(f"[auto] renome via mapa: {rel} <- {src}")
            else:
                print(
                    f"[warn] mapa de renome aponta para arquivo inexistente: {rel} -> {mapped}",
                    file=sys.stderr,
                )

        if src is None:
            exact_src = azure_root / rel
            if exact_src.is_file():
                src = exact_src
                print(f"[auto] resolvido por caminho exato: {rel} <- {src}")

        if src is None:
            by_name_src, basename_index, ambiguous_name = find_source_in_azure_by_name(
                azure_root, rel, basename_index
            )
            if by_name_src is None:
                if ambiguous_name:
                    print(
                        f"[stop] nome de arquivo ambiguo no Azure para: {rel}. "
                        "Use --rename-map-yml para mapear o caminho correto.",
                        file=sys.stderr,
                    )
                    return False
                # Se nao existe no Azure, considera exclusao no destino.
                run_git(repo_root, ["rm", "-f", "--ignore-unmatch", "--", rel], check=True)
                if is_path_unmerged(repo_root, rel):
                    print(f"[stop] conflito permaneceu apos exclusao automatica: {rel}", file=sys.stderr)
                    return False
                print(f"[auto] resolvido por exclusao (nome ausente no Azure): {rel}")
                continue
            src = by_name_src
            print(f"[auto] resolvido por nome de arquivo: {rel} <- {src}")

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        run_git(repo_root, ["add", "--", rel], check=True)
        if is_path_unmerged(repo_root, rel):
            print(f"[stop] conflito permaneceu apos copia do Azure: {rel}", file=sys.stderr)
            return False
        print(f"[auto] resolvido por copia: {rel}")

    remaining = get_unmerged_paths(repo_root)
    if remaining:
        print("[stop] conflitos restantes apos tentativa automatica:", file=sys.stderr)
        for rel in remaining:
            print(f"  - {rel}", file=sys.stderr)
        return False

    return True


def collect_patches(patches_dir: Path) -> list[Path]:
    patches = sorted(patches_dir.glob("*.patch"))
    return [p for p in patches if p.is_file()]


def build_am_excludes(repo_root: Path, ignored_specs: set[str]) -> list[str]:
    excludes: list[str] = []
    if not ignored_specs:
        return excludes

    tracked = run_git(repo_root, ["ls-files"], check=True).stdout.splitlines()
    tracked_set = {item.strip() for item in tracked if item.strip()}

    for spec in sorted(ignored_specs):
        if "/" in spec:
            excludes.append(spec)
            continue

        matched = [path for path in tracked_set if Path(path).name == spec]
        if matched:
            excludes.extend(sorted(matched))
        else:
            excludes.append(spec)

    dedup: list[str] = []
    seen: set[str] = set()
    for item in excludes:
        if item not in seen:
            seen.add(item)
            dedup.append(item)
    return dedup


def start_am_session(repo_root: Path, patches: list[Path], ignored_specs: set[str]) -> int:
    excludes = build_am_excludes(repo_root, ignored_specs)
    exclude_args: list[str] = []
    for path in excludes:
        exclude_args.extend(["--exclude", path])

    cmd = [
        "git",
        "-C",
        str(repo_root),
        "am",
        "--3way",
        "--empty=drop",
        *exclude_args,
        *[str(p) for p in patches],
    ]
    proc = subprocess.run(cmd, text=True)
    return proc.returncode


def should_auto_skip_empty_patch(output: str) -> bool:
    text = output.lower()
    # Nunca tentar skip automático quando há indício de conflito real.
    hard_blockers = [
        "conflict (content)",
        "patch failed at",
        "failed to merge in the changes",
    ]
    if any(marker in text for marker in hard_blockers):
        return False

    markers = [
        "no changes - did you forget to use 'git add'?",
        "already introduced the same changes",
        "patch already applied",
    ]
    return any(marker in text for marker in markers)


def has_staged_changes(repo_root: Path) -> bool:
    proc = run_git(repo_root, ["diff", "--cached", "--name-only"], check=True)
    return bool(proc.stdout.strip())


def auto_continue_loop(
    repo_root: Path, azure_root: Path, ignored_specs: set[str], rename_map: dict[str, str]
) -> int:
    while in_am_session(repo_root):
        pending = get_unmerged_paths(repo_root)
        if pending:
            print(f"[info] conflitos detectados ({len(pending)}). Resolvendo por copia do Azure antes de continuar...")
            if not resolve_conflicts_with_azure(repo_root, azure_root, ignored_specs, rename_map):
                print(
                    "[info] sessao mantida por conflito nao resolvido automaticamente. Ajuste manualmente e rode novamente.",
                    file=sys.stderr,
                )
                return 2

            pending_after = get_unmerged_paths(repo_root)
            if pending_after:
                print(
                    "[info] ainda existem conflitos apos tentativa automatica. Nao vou executar git am --continue.",
                    file=sys.stderr,
                )
                return 2

        cont = run_git(repo_root, ["am", "--continue"])
        sys.stdout.write(cont.stdout)
        sys.stderr.write(cont.stderr)
        if cont.returncode != 0:
            # Se ainda existem conflitos U, nao tenta skip aqui.
            # Volta para o inicio do loop para resolver por copia do Azure.
            unmerged_now = get_unmerged_paths(repo_root)
            if in_am_session(repo_root) and unmerged_now:
                print(
                    "[info] git am --continue ainda com conflitos; tentando nova rodada de auto-resolucao..."
                )
                continue

            combined_output = f"{cont.stdout}\n{cont.stderr}"
            if (
                in_am_session(repo_root)
                and not unmerged_now
                and not has_staged_changes(repo_root)
                and should_auto_skip_empty_patch(combined_output)
            ):
                print("[auto] patch sem diff util (ja aplicado). Executando git am --skip...")
                skip = run_git(repo_root, ["am", "--skip"])
                sys.stdout.write(skip.stdout)
                sys.stderr.write(skip.stderr)
                if skip.returncode != 0:
                    unmerged_after_skip = get_unmerged_paths(repo_root) if in_am_session(repo_root) else []
                    if in_am_session(repo_root) and unmerged_after_skip:
                        print(
                            "[info] git am --skip pulou o patch atual e encontrou novo conflito "
                            "no proximo patch; continuando auto-resolucao..."
                        )
                        continue
                    if not in_am_session(repo_root):
                        print("[info] sessao git am encerrada apos tentativa de skip.")
                        return 0
                    print(
                        "[erro] falha ao executar git am --skip automaticamente. "
                        "Verifique a mensagem do git acima para o motivo exato.",
                        file=sys.stderr,
                    )
                    return skip.returncode
                continue

            # Se ainda estiver em sessao, houve novo conflito e o loop tenta de novo.
            if not in_am_session(repo_root):
                print("[erro] git am --continue falhou fora de sessao ativa.", file=sys.stderr)
                return cont.returncode

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aplica patches com auto-resolucao de conflitos por copia do Azure."
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repositorio destino (se omitido, usa o diretorio atual).",
    )
    parser.add_argument(
        "--azure-root",
        default=None,
        help="Worktree Azure para copiar arquivos em conflito (obrigatorio via --azure-root ou AZURE_ROOT).",
    )
    parser.add_argument(
        "--patches-dir",
        default=None,
        help="Pasta dos .patch (obrigatorio para iniciar aplicacao; aceite --patches-dir ou PATCHES_DIR).",
    )
    parser.add_argument(
        "--ignore-file",
        action="append",
        default=[],
        help="Arquivo a ignorar em conflitos (pode repetir; aceita nome ou caminho relativo).",
    )
    parser.add_argument(
        "--ignore-yml",
        default=None,
        help="YAML com lista de arquivos ignorados (chave ignore_files/ignored_files/files ou lista direta).",
    )
    parser.add_argument(
        "--rename-map-yml",
        default=None,
        help="YAML com mapa de renome (antigo_rel_path: novo_rel_path no Azure).",
    )
    parser.add_argument(
        "--apply-branch",
        default=None,
        help=(
            "Branch local onde os patches serao aplicados. "
            "Se nao existir, sera criada a partir de --derive-from-branch."
        ),
    )
    parser.add_argument(
        "--derive-from-branch",
        default=None,
        help="Branch/ref base para derivar --apply-branch quando ela ainda nao existir.",
    )
    return parser.parse_args()


def branch_exists(repo_root: Path, branch_name: str) -> bool:
    proc = run_git(repo_root, ["show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"])
    return proc.returncode == 0


def checkout_or_create_apply_branch(
    repo_root: Path, apply_branch: str, derive_from_branch: str | None
) -> None:
    if branch_exists(repo_root, apply_branch):
        run_git(repo_root, ["checkout", apply_branch], check=True)
        print(f"[info] usando branch de aplicacao existente: {apply_branch}")
        return

    if not derive_from_branch:
        raise RuntimeError(
            "branch de aplicacao inexistente. Informe --derive-from-branch para criar a nova branch."
        )

    run_git(repo_root, ["rev-parse", "--verify", derive_from_branch], check=True)
    run_git(repo_root, ["checkout", "-b", apply_branch, derive_from_branch], check=True)
    print(f"[info] branch criada para aplicacao: {apply_branch} (derivada de {derive_from_branch})")


def main() -> int:
    args = parse_args()
    repo_root_raw = (args.repo_root or "").strip()
    if repo_root_raw:
        repo_root = Path(repo_root_raw).expanduser().resolve()
    else:
        repo_root = Path.cwd().resolve()
        print(
            "[aviso] --repo-root nao informado. Usando diretorio atual como destino: "
            f"{repo_root}",
            file=sys.stderr,
        )
        print(
            "[aviso] informe --repo-root explicitamente para garantir aplicacao no repo/worktree GitLab.",
            file=sys.stderr,
        )

    azure_root_raw = (args.azure_root or "").strip() or (os.environ.get("AZURE_ROOT") or "").strip()
    patches_dir_raw = (args.patches_dir or "").strip() or (os.environ.get("PATCHES_DIR") or "").strip()

    if not azure_root_raw:
        print("[erro] informe --azure-root ou defina AZURE_ROOT.", file=sys.stderr)
        return 1

    azure_root = Path(azure_root_raw).expanduser().resolve()
    patches_dir = Path(patches_dir_raw).expanduser().resolve() if patches_dir_raw else None
    ignored_specs = build_ignored_specs(args.ignore_file, args.ignore_yml)
    rename_map = build_rename_map(args.rename_map_yml)

    run_git(repo_root, ["rev-parse", "--is-inside-work-tree"], check=True)

    if not azure_root.is_dir():
        print(f"[erro] worktree Azure nao encontrado: {azure_root}", file=sys.stderr)
        return 1

    # Cenário de segurança: conflitos já abertos sem sessao de git am ativa.
    # Nesse caso, tenta resolver por cópia para destravar o índice.
    if not in_am_session(repo_root):
        preexisting_unmerged = get_unmerged_paths(repo_root)
        if preexisting_unmerged:
            print(
                f"[info] detectados {len(preexisting_unmerged)} conflito(s) sem sessao git am ativa. "
                "Tentando auto-resolver..."
            )
            if not resolve_conflicts_with_azure(repo_root, azure_root, ignored_specs, rename_map):
                print(
                    "[dica] use --rename-map-yml para informar arquivos renomeados quando necessario.",
                    file=sys.stderr,
                )
                print(
                    "[info] conflito nao resolvido automaticamente. Resolva manualmente e execute novamente.",
                    file=sys.stderr,
                )
                return 2
            print(
                "[ok] conflitos resolvidos e adicionados ao index. "
                "Nao existe sessao git am ativa para continuar automaticamente.",
                file=sys.stderr,
            )
            return 3

    if in_am_session(repo_root):
        print("[info] sessao git am em andamento. Retomando do ponto atual...")
        if ignored_specs:
            print(f"[info] ignorando {len(ignored_specs)} arquivo(s) em conflitos.")
        if rename_map:
            print(f"[info] mapa de renome com {len(rename_map)} entrada(s).")
        return auto_continue_loop(repo_root, azure_root, ignored_specs, rename_map)

    if args.derive_from_branch and not args.apply_branch:
        print(
            "[erro] --derive-from-branch exige --apply-branch para definir a branch de aplicacao.",
            file=sys.stderr,
        )
        return 1

    if args.apply_branch:
        checkout_or_create_apply_branch(repo_root, args.apply_branch, args.derive_from_branch)

    if patches_dir is None:
        print("[erro] informe --patches-dir ou defina PATCHES_DIR para iniciar a aplicacao.", file=sys.stderr)
        return 1

    if not patches_dir.is_dir():
        print(f"[erro] pasta de patches nao encontrada: {patches_dir}", file=sys.stderr)
        return 1

    patches = collect_patches(patches_dir)
    if not patches:
        print(f"[erro] nenhum .patch encontrado em: {patches_dir}", file=sys.stderr)
        return 1

    print(f"[info] iniciando git am --3way com {len(patches)} patches...")
    rc = start_am_session(repo_root, patches, ignored_specs)
    if rc == 0:
        print("[ok] todos os patches aplicados sem conflito.")
        return 0

    if not in_am_session(repo_root):
        print("[erro] git am falhou sem abrir sessao de conflito.", file=sys.stderr)
        return rc

    print("[info] conflito detectado. Entrando em auto-resolucao...")
    if ignored_specs:
        print(f"[info] ignorando {len(ignored_specs)} arquivo(s) em conflitos.")
    if rename_map:
        print(f"[info] mapa de renome com {len(rename_map)} entrada(s).")
    return auto_continue_loop(repo_root, azure_root, ignored_specs, rename_map)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as err:
        print(f"[erro] {err}", file=sys.stderr)
        raise SystemExit(1)
