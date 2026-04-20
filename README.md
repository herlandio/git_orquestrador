# Guia Prático de Uso (Sequência Completa)

## Convenção de caminho

Nos exemplos abaixo, use:

```bash
projeto_caminho="/caminho/do/seu/projeto"
```

## Observação sobre nomes de worktree/branch

- `azure-develop` e `gitlab-develop` usados nas docs são apenas exemplos.
- Você pode usar outros nomes/apelidos ao criar worktrees e branches locais.
- Sempre substitua esses nomes pelos que você definiu no seu fluxo.

Este guia mostra o uso real dos scripts de `git_orquestrador` em ordem operacional.

Ordem recomendada:
1. criar/garantir worktrees
2. gerar patches
3. remapear Subject (HU/TASK)
4. aplicar patches com auto-resolução
5. limpar commits vazios (quando necessário)
6. descartar commits a partir de ponto (quando necessário)
7. limpar patches gerados (final do ciclo)

## Estrutura esperada

- Menu principal: `scripts/git_orquestrador/menu_principal.py`
- Scripts: `scripts/git_orquestrador/src`
- Mapas/YAML: `scripts/git_orquestrador/map`
- Documentações: `scripts/git_orquestrador/docs`

## Pré-requisitos mínimos

1. estar dentro de um clone Git válido
2. remotes configurados (normalmente `azure` e `gitlab`)
3. Python 3 disponível

## Dependências necessárias

Obrigatórias:
- `git` (com suporte a `git worktree`)
- `python3` (sem dependências externas de `pip`; apenas biblioteca padrão)
- acesso ao clone local com permissão de leitura/escrita

Dependências de configuração do projeto:
- remotes configurados no repositório (`azure` e `gitlab`, ou nomes equivalentes)
- arquivos de mapa em `scripts/git_orquestrador/map`:
  - `azure-to-gitlab-ids.yml`
  - `ignore.yml`
  - `rename-map.yml` (quando houver rename)

Recomendadas:
- shell Unix-like (`zsh`/`bash`) para executar os exemplos exatamente como estão
- branch local limpa antes das etapas críticas

Verificação rápida:

```bash
cd "$projeto_caminho/_worktrees/azure-develop"
git remote -v
python3 --version
git --version
git worktree list
```

---

## Passo 1 (primeiro): criar/gerenciar worktrees

### Pelo menu

```bash
cd "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/menu_principal.py"
```

No menu, escolha `1) Gerenciar worktrees`.

Subcomandos mais usados:
- `init`: cria worktrees padrão de `develop`
- `add`: cria worktree para branch remota específica
- `list`: lista worktrees
- `remove`: remove worktree por caminho
- `remove-ref`: remove por remote/ref (worktree + branch local espelho)

### Exemplo direto sem menu

```bash
cd "$projeto_caminho/_worktrees/azure-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/worktrees.py" init
```

---

## Passo 2: gerar patches (origem Azure)

Objetivo: gerar `.patch` do intervalo desejado.

### Pelo menu
- opção `2) Gerar patches`
- `repo-root`: worktree Azure de origem
- `out-dir`: pasta de patches (ex.: `/.../_worktrees/azure-develop/patches`)
- `interval`: ex. `azure/develop..HEAD`

### Exemplo direto

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/generate_patches.py" \
  --repo-root "$projeto_caminho/_worktrees/azure-develop" \
  --out-dir "$projeto_caminho/_worktrees/azure-develop/patches" \
  --interval "azure/develop..HEAD"
```

---

## Passo 3: remapear Subject dos patches (HU/TASK)

Objetivo: trocar IDs Azure por IDs GitLab no `Subject` dos `.patch`.

Arquivos usados:
- `map/azure-to-gitlab-ids.yml`
- `map/hu-patterns.yml` (opcional: regex externas de identificação)

### Pelo menu
- opção `3) Reescrever HUs/TASKs no Subject`
- `MAP`: apontar para `.../scripts/git_orquestrador/map/azure-to-gitlab-ids.yml`
- `PATTERNS_MAP`: opcional, para padrões customizados de HU/TASK
- `PATCHES_DIR`: pasta com `.patch`
- começar com `dry-run = sim`

### Exemplo direto

```bash
MAP="$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/map/azure-to-gitlab-ids.yml" \
PATTERNS_MAP="$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/map/hu-patterns.yml" \
PATCHES_DIR="$projeto_caminho/_worktrees/azure-develop/patches" \
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/remap_patch_subjects.py" --dry-run
```

Depois execute sem `--dry-run` para aplicar de fato.

---

## Passo 4: aplicar patches no destino GitLab

Objetivo: aplicar os patches com `git am` e auto-resolução de conflitos.

Arquivos usados:
- `map/ignore.yml`
- `map/rename-map.yml` (quando houver rename)

### Pelo menu
- opção `4) Aplicar patches com auto-resolução`
- `repo-root`: worktree GitLab de destino
- `azure-root`: worktree Azure
- `patches-dir`: pasta dos `.patch`
- `ignore-yml` e `rename-map-yml`: opcionais
- `apply-branch` e `derive-from-branch`: opcionais

### Exemplo direto (com branch de aplicação)

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/apply_patches_auto_resolve.py" \
  --repo-root "$projeto_caminho/_worktrees/gitlab-develop" \
  --azure-root "$projeto_caminho/_worktrees/azure-develop" \
  --patches-dir "$projeto_caminho/_worktrees/azure-develop/patches" \
  --ignore-yml "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/map/ignore.yml" \
  --rename-map-yml "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/map/rename-map.yml" \
  --derive-from-branch develop \
  --apply-branch patch/azure-sync-2026-04-20
```

---

## Passo 5 (opcional): remover commits vazios

Use quando o histórico local tiver commits sem alteração real após aplicação/rebase.

### Pelo menu
- opção `6) Remover commits vazios`
- base recomendada: `ORIG_HEAD`
- rodar `dry-run` primeiro

### Exemplo direto

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/drop_empty_commits_auto.py" \
  --repo-root "$projeto_caminho/_worktrees/gitlab-develop" \
  --base ORIG_HEAD \
  --dry-run
```

---

## Passo 6 (opcional/crítico): descartar commits a partir de um ponto

Use para rollback local rápido (reset destrutivo).

### Pelo menu
- opção `7) Descartar commits a partir de um ponto`
- informar `--to` (hash/ref)

### Exemplo direto

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/discard_commits_from_point.py" \
  --repo-root "$projeto_caminho/_worktrees/gitlab-develop" \
  --to f068ac4b \
  --yes
```

---

## Passo 7 (final): descartar patches gerados

Limpeza da pasta de `.patch` ao final do ciclo.

### Pelo menu
- opção `5) Descartar patches gerados`
- `dry-run` para prévia

### Exemplo direto

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/discard_generated_patches.py" \
  --patches-dir "$projeto_caminho/_worktrees/azure-develop/patches" \
  --dry-run
```

---

## Fluxo curto (resumo de produção)

1. `1` (worktrees `init`/`add`)
2. `2` (gerar patches)
3. `3` (`dry-run` e depois aplicar remap)
4. `4` (aplicar patches no GitLab)
5. `6` (opcional: limpar vazios)
6. `5` (limpar `.patch` no final)

## Observações de segurança

- faça `git status` antes de cada etapa crítica
- em etapas destrutivas (`5`, `6` e `7`), confirme backup/tag quando disponível
- nenhuma etapa substitui revisão humana do resultado final antes de push

---

## Executar testes com Docker

Build da imagem:

```bash
docker build -t git-orquestrador-tests .
```

Executar testes pela imagem:

```bash
docker run --rm git-orquestrador-tests
```

Executar testes com Docker Compose:

```bash
docker compose up --build tests
```
