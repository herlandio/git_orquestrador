# apply_patches_auto_resolve.py

Aplica `.patch` com `git am --3way`, com auto-resolução de conflitos por cópia do worktree de origem.

## Convenção de caminho

Nos exemplos abaixo, use:

```bash
projeto_caminho="/caminho/do/seu/projeto"
```

## Observação sobre nomes de worktree/branch

- `azure-develop` e `gitlab-develop` usados nas docs são apenas exemplos.
- Você pode usar outros nomes/apelidos ao criar worktrees e branches locais.
- Sempre substitua esses nomes pelos que você definiu no seu fluxo.

## Pontos importantes

- `--azure-root` é obrigatório (ou `AZURE_ROOT`)
- `--patches-dir` é obrigatório para iniciar aplicação (ou `PATCHES_DIR`)
- `--repo-root` é destino (default: diretório atual)
- suporta `--ignore-yml`, `--rename-map-yml`, `--apply-branch`, `--derive-from-branch`

## Observação importante sobre `--repo-root`

- `--repo-root` deve apontar para o worktree/repo do **GitLab** (destino da aplicação).
- Se você executar o comando dentro do worktree **Azure** e não informar `--repo-root`, o script usará o diretório atual e tentará aplicar no Azure.
- Para evitar erro de contexto, sempre informe explicitamente:

```bash
--repo-root "$projeto_caminho/_worktrees/gitlab-develop"
```

## Uso rápido

```bash
cd "$projeto_caminho/_worktrees/gitlab-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/apply_patches_auto_resolve.py" \
  --repo-root "$projeto_caminho/_worktrees/gitlab-develop" \
  --azure-root "$projeto_caminho/_worktrees/azure-develop" \
  --patches-dir "$projeto_caminho/_worktrees/azure-develop/patches" \
  --ignore-yml "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/map/ignore.yml"
```

## Opções

- `--repo-root`: repositório destino
- `--azure-root`: worktree de origem para copiar arquivos em conflito (obrigatório via argumento/env)
- `--patches-dir`: pasta de `.patch` para iniciar aplicação (obrigatório via argumento/env)
- `--ignore-file`: arquivo a ignorar em conflito (pode repetir)
- `--ignore-yml`: YAML com ignorados
- `--rename-map-yml`: YAML com renomes
- `--apply-branch`: branch de aplicação (checkout/criação)
- `--derive-from-branch`: base para criar `--apply-branch`

## Exemplos de uso (todas as possibilidades)

1. Aplicação básica (sem mapas):

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/apply_patches_auto_resolve.py" \
  --repo-root "$projeto_caminho/_worktrees/gitlab-develop" \
  --azure-root "$projeto_caminho/_worktrees/azure-develop" \
  --patches-dir "$projeto_caminho/_worktrees/azure-develop/patches"
```

2. Com lista de ignorados via YAML:

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/apply_patches_auto_resolve.py" \
  --repo-root "$projeto_caminho/_worktrees/gitlab-develop" \
  --azure-root "$projeto_caminho/_worktrees/azure-develop" \
  --patches-dir "$projeto_caminho/_worktrees/azure-develop/patches" \
  --ignore-yml "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/map/ignore.yml"
```

3. Com mapa de renome:

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/apply_patches_auto_resolve.py" \
  --repo-root "$projeto_caminho/_worktrees/gitlab-develop" \
  --azure-root "$projeto_caminho/_worktrees/azure-develop" \
  --patches-dir "$projeto_caminho/_worktrees/azure-develop/patches" \
  --ignore-yml "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/map/ignore.yml" \
  --rename-map-yml "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/map/rename-map.yml"
```

4. Com `--ignore-file` repetido:

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/apply_patches_auto_resolve.py" \
  --repo-root "$projeto_caminho/_worktrees/gitlab-develop" \
  --azure-root "$projeto_caminho/_worktrees/azure-develop" \
  --patches-dir "$projeto_caminho/_worktrees/azure-develop/patches" \
  --ignore-file backend/routes/api.php \
  --ignore-file map.yml
```

5. Criando branch de aplicação a partir de base:

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/apply_patches_auto_resolve.py" \
  --repo-root "$projeto_caminho/_worktrees/gitlab-develop" \
  --azure-root "$projeto_caminho/_worktrees/azure-develop" \
  --patches-dir "$projeto_caminho/_worktrees/azure-develop/patches" \
  --derive-from-branch develop \
  --apply-branch patch/azure-sync-2026-04-20
```

6. Usando branch de aplicação já existente:

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/apply_patches_auto_resolve.py" \
  --repo-root "$projeto_caminho/_worktrees/gitlab-develop" \
  --azure-root "$projeto_caminho/_worktrees/azure-develop" \
  --patches-dir "$projeto_caminho/_worktrees/azure-develop/patches" \
  --apply-branch patch/azure-sync-2026-04-20
```

7. Retomada de sessão `git am` já em andamento:

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/apply_patches_auto_resolve.py" \
  --repo-root "$projeto_caminho/_worktrees/gitlab-develop" \
  --azure-root "$projeto_caminho/_worktrees/azure-develop" \
  --patches-dir "$projeto_caminho/_worktrees/azure-develop/patches"
```

8. Usando variáveis de ambiente (`AZURE_ROOT` e `PATCHES_DIR`):

```bash
AZURE_ROOT="$projeto_caminho/_worktrees/azure-develop" \
PATCHES_DIR="$projeto_caminho/_worktrees/azure-develop/patches" \
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/apply_patches_auto_resolve.py" \
  --repo-root "$projeto_caminho/_worktrees/gitlab-develop"
```

## Códigos de saída

- `0`: aplicação concluída
- `1`: erro de execução/validação
- `2`: conflito não resolvido automaticamente
- `3`: resolveu conflitos pré-existentes sem sessão `git am` ativa
