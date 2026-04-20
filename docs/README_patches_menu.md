# menu_principal.py

## Convenção de caminho

Nos exemplos abaixo, use:

```bash
projeto_caminho="/caminho/do/seu/projeto"
```


## Observação sobre nomes de worktree/branch

- `azure-develop` e `gitlab-develop` usados nas docs são apenas exemplos.
- Você pode usar outros nomes/apelidos ao criar worktrees e branches locais.
- Sempre substitua esses nomes pelos que você definiu no seu fluxo.

Menu interativo para orquestrar o fluxo de patches e worktrees.

## Execução

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/menu_principal.py"
```

## Opções atuais do menu

1. `Gerenciar worktrees`
- chama `worktrees.py`
- subcomandos: `init`, `add`, `list`, `remove`, `remove-ref`
- pode receber via prompt/env: `REMOTE_AZURE`, `REMOTE_GITLAB`, `DEFAULT_BRANCH`, `WORKTREES_ROOT`

2. `Gerar patches`
- chama `generate_patches.py`
- configura `--repo-root`, `--out-dir`, `--interval`

3. `Reescrever HUs/TASKs`
- chama `remap_patch_subjects.py`
- exige `MAP` e `PATCHES_DIR` (prompt/env)
- opcional: `PATTERNS_MAP` para regex externas de identificação
- suporta `--dry-run`

4. `Aplicar patches`
- chama `apply_patches_auto_resolve.py`
- exige `--repo-root`, `--azure-root`, `--patches-dir` (prompt)
- opcionais: `--ignore-yml`, `--rename-map-yml`, `--apply-branch`, `--derive-from-branch`

5. `[!] Descartar patches gerados`
- chama `discard_generated_patches.py`
- exige `--patches-dir` (prompt/env)

6. `[!] Remover commits vazios`
- chama `drop_empty_commits_auto.py`
- configura `--repo-root`, `--base`, `--dry-run`, backup tag

7. `[!] Descartar commits a partir de um ponto`
- chama `discard_commits_from_point.py`
- configura `--repo-root`, `--to`, backup tag

0. `Sair`

## Exemplos práticos por opção

1. opção `1`: criar worktrees padrão (`init`)
2. opção `2`: gerar patches do range `azure/develop..HEAD`
3. opção `3`: rodar remap em `dry-run`
4. opção `4`: aplicar no repo GitLab com `ignore.yml`
5. opção `5`: limpar `.patch` com `--dry-run`
6. opção `6`: identificar commits vazios com base `ORIG_HEAD`
7. opção `7`: reset local para `HEAD~3`

## Observações

- opções `[!]` são operações críticas
- sempre valide `git status` antes de opções críticas
- resoluções de conflito podem exigir intervenção manual
