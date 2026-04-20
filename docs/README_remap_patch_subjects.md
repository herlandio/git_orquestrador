# remap_patch_subjects.py

## Convenção de caminho

Nos exemplos abaixo, use:

```bash
projeto_caminho="/caminho/do/seu/projeto"
```

Reescreve `Subject` dos `.patch` trocando ID Azure (HU/TASK) por ID GitLab.

## Entrada obrigatória

- `--map` ou env `MAP`
- `--patches-dir` ou env `PATCHES_DIR`
- padrões de identificação podem vir de `--patterns-map`/`PATTERNS_MAP` (opcional)

## Argumentos

- `--dry-run`: simula sem alterar arquivo
- `--map`: YAML de mapeamento
- `--patches-dir`: pasta com `.patch`
- `--patterns-map`: YAML com regex dos padrões de HU/TASK que podem aparecer

## Uso rápido (sua estrutura)

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/remap_patch_subjects.py" \
  --map "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/map/azure-to-gitlab-ids.yml" \
  --patterns-map "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/map/hu-patterns.yml" \
  --patches-dir "$projeto_caminho/_worktrees/azure-develop/patches" \
  --dry-run
```

## Exemplos

1. Aplicar de fato:

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/remap_patch_subjects.py" \
  --map "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/map/azure-to-gitlab-ids.yml" \
  --patterns-map "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/map/hu-patterns.yml" \
  --patches-dir "$projeto_caminho/_worktrees/azure-develop/patches"
```

2. Via variáveis de ambiente:

```bash
MAP="$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/map/azure-to-gitlab-ids.yml" \
PATTERNS_MAP="$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/map/hu-patterns.yml" \
PATCHES_DIR="$projeto_caminho/_worktrees/azure-develop/patches" \
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/remap_patch_subjects.py" --dry-run
```

## Arquivo externo de padrões

Arquivo sugerido:

```bash
$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/map/hu-patterns.yml
```

Formato:

```yaml
min_id_digits: 4
id_patterns:
  - '[Hh][Uu][\\s_\\-#]*([0-9][0-9\\s]{0,20})'
  - '(?:TASK|TASKS?)[\\s_\\-#]*([0-9][0-9\\s]{0,20})'
  - '#[ \\t]*([0-9][0-9 \\t]{0,20})'
```

Regra importante: cada regex deve ter o ID no **primeiro grupo de captura**.

## Comportamento sem mapeamento

Quando não encontra par no YAML, o script pergunta no terminal:
- `s`/`skip`/Enter: pula patch atual
- `a`/`abort`: aborta e restaura backups da sessão
