# generate_patches.py

## Convenção de caminho

Nos exemplos abaixo, use:

```bash
projeto_caminho="/caminho/do/seu/projeto"
```

Script para gerar arquivos `.patch` com `git format-patch`.

## O que ele faz

- valida se o diretório informado é um repositório Git
- cria a pasta de saída se não existir
- roda `git format-patch` com:
  - intervalo informado (`--interval`), ou
  - `--root` quando o intervalo vier vazio

## Uso rápido

```bash
cd "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/generate_patches.py" \
  --repo-root "$projeto_caminho/_worktrees/azure-develop" \
  --out-dir "$projeto_caminho/_worktrees/azure-develop/patches" \
  --interval "azure/develop..HEAD"
```

Sem intervalo (gera desde o root):

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/generate_patches.py" \
  --repo-root "$projeto_caminho/_worktrees/azure-develop" \
  --out-dir "$projeto_caminho/_worktrees/azure-develop/patches"
```

## Exemplos de uso (todas as possibilidades)

1. Intervalo explícito (caso mais comum):

```bash
cd "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/generate_patches.py" \
  --repo-root "$projeto_caminho/_worktrees/azure-develop" \
  --out-dir "$projeto_caminho/_worktrees/azure-develop/patches" \
  --interval "azure/develop..HEAD"
```

2. Sem `--interval`:

```bash
cd "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/generate_patches.py" \
  --repo-root "$projeto_caminho/_worktrees/azure-develop" \
  --out-dir "$projeto_caminho/_worktrees/azure-develop/patches"
```

3. Repositório atual e pasta padrão:

```bash
cd "$projeto_caminho/_worktrees/azure-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/generate_patches.py"
```

## Opções

- `--repo-root`: repositório alvo (default: diretório atual)
- `--out-dir`: pasta de saída dos patches (default: `<repo-root>/patches`)
- `--interval`: range de commits (ex.: `origin/main..HEAD`).
  Vazio usa `--root`.

## Código de saída

- `0`: sucesso
- `1`: erro de validação/execução
- `>1`: código retornado pelo próprio `git format-patch`
