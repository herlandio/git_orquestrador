# discard_generated_patches.py

## Convenção de caminho

Nos exemplos abaixo, use:

```bash
projeto_caminho="/caminho/do/seu/projeto"
```

Descarta arquivos `.patch` de uma pasta informada.

## Entrada obrigatória

- `--patches-dir` ou env `PATCHES_DIR`

## Uso rápido (sua estrutura)

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/discard_generated_patches.py" \
  --patches-dir "$projeto_caminho/_worktrees/azure-develop/patches" \
  --dry-run
```

## Exemplos

1. Remoção com confirmação:

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/discard_generated_patches.py" \
  --patches-dir "$projeto_caminho/_worktrees/azure-develop/patches"
```

2. Sem confirmação interativa:

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/discard_generated_patches.py" \
  --patches-dir "$projeto_caminho/_worktrees/azure-develop/patches" \
  --yes
```

3. Via variável de ambiente:

```bash
PATCHES_DIR="$projeto_caminho/_worktrees/azure-develop/patches" \
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/discard_generated_patches.py" --dry-run
```

## Opções

- `--patches-dir`: pasta dos patches
- `--dry-run`: só lista
- `--yes`: confirma sem prompt
