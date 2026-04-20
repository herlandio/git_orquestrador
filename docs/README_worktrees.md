# worktrees.py

## Convenção de caminho

Nos exemplos abaixo, use:

```bash
projeto_caminho="/caminho/do/seu/projeto"
```


## Observação sobre nomes de worktree/branch

- `azure-develop` e `gitlab-develop` usados nas docs são apenas exemplos.
- Você pode usar outros nomes/apelidos ao criar worktrees e branches locais.
- Sempre substitua esses nomes pelos que você definiu no seu fluxo.

Script Python para criar e gerenciar `git worktree` em um repositório com dois remotes (por padrão `azure` e `gitlab`).

## O que ele faz

- cria worktrees padrão para `develop` dos dois remotes (`init`)
- cria worktree para branch/ref remota específica (`add`)
- lista worktrees registrados (`list`)
- remove worktree por caminho (`remove`)
- remove worktree + branch local espelho por remote/ref (`remove-ref`)
- permite customizar via variáveis de ambiente (`REMOTE_AZURE`, `REMOTE_GITLAB`, `DEFAULT_BRANCH`, `WORKTREES_ROOT`)

## Local do script

```bash
$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/worktrees.py
```

## Pré-requisitos

- Git instalado
- executar dentro de um repositório Git
- remotes configurados (`git remote -v`)

## Exemplos de uso (todas as possibilidades)

1. Ajuda:

```bash
cd "$projeto_caminho/_worktrees/azure-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/worktrees.py" --help
```

Mostra comandos e variáveis disponíveis.

2. `init` (cria worktrees padrão de `develop`):

```bash
cd "$projeto_caminho/_worktrees/azure-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/worktrees.py" init
```

Cria:
- `_worktrees/azure-develop` (track `azure/develop`)
- `_worktrees/gitlab-develop` (track `gitlab/develop`)

3. `add` para Azure:

```bash
cd "$projeto_caminho/_worktrees/azure-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/worktrees.py" add azure feature/30958
```

Cria branch local espelho `azure-feature-30958` e worktree correspondente.

4. `add` para GitLab:

```bash
cd "$projeto_caminho/_worktrees/azure-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/worktrees.py" add gitlab release/1.11.0
```

Cria branch local espelho `gitlab-release-1.11.0` e worktree correspondente.

5. `list`:

```bash
cd "$projeto_caminho/_worktrees/azure-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/worktrees.py" list
```

Lista worktrees registrados no clone local.

6. `remove` somente worktree (por caminho):

```bash
cd "$projeto_caminho/_worktrees/azure-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/worktrees.py" remove _worktrees/azure-feature-30958
```

Remove pasta/worktree; não remove branch local automaticamente.

7. `remove` com remoção de branch local espelho:

```bash
cd "$projeto_caminho/_worktrees/azure-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/worktrees.py" remove _worktrees/azure-feature-30958 --branch azure-feature-30958
```

Remove worktree e tenta remover a branch local informada.

8. `remove-ref` Azure:

```bash
cd "$projeto_caminho/_worktrees/azure-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/worktrees.py" remove-ref azure feature/30958
```

Resolve automaticamente nome da branch/pasta espelho e remove ambos.

9. `remove-ref` GitLab:

```bash
cd "$projeto_caminho/_worktrees/azure-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/worktrees.py" remove-ref gitlab develop
```

Remove o espelho de `gitlab/develop` no ambiente local.

10. `init` com `DEFAULT_BRANCH` customizada:

```bash
cd "$projeto_caminho/_worktrees/azure-develop"
DEFAULT_BRANCH=main python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/worktrees.py" init
```

Cria worktrees padrão usando `main` em vez de `develop`.

11. `init` com root customizado dos worktrees:

```bash
cd "$projeto_caminho/_worktrees/azure-develop"
WORKTREES_ROOT=/tmp/meus-worktrees python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/worktrees.py" init
```

Cria pastas de worktree no caminho informado.

12. remotes customizados:

```bash
cd "$projeto_caminho/_worktrees/azure-develop"
REMOTE_AZURE=origin REMOTE_GITLAB=upstream python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/worktrees.py" init
```

Usa nomes de remotes diferentes do padrão.

13. combinação completa de variáveis:

```bash
cd "$projeto_caminho/_worktrees/azure-develop"
REMOTE_AZURE=origin \
REMOTE_GITLAB=upstream \
DEFAULT_BRANCH=main \
WORKTREES_ROOT=/tmp/wt \
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/worktrees.py" init
```

Executa `init` com todas as configurações personalizadas no mesmo comando.

## Regras importantes

- o script não faz `git push` e não remove branch remota
- tudo que ele altera é local (worktree e branch local espelho)
- para `remove`, não execute de dentro do worktree que será removido

## Troubleshooting

Se algum worktree ficar órfão:

```bash
git worktree list
git worktree prune --expire now
```

Depois repita `remove` ou `remove-ref`.
