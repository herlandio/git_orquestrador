# discard_commits_from_point.py

## Convenção de caminho

Nos exemplos abaixo, use:

```bash
projeto_caminho="/caminho/do/seu/projeto"
```

Script para descartar commits a partir de um ponto com `git reset --hard`.

## Importante: branch correta

- O reset atua na branch/referência atual do repositório informado em `--repo-root`.
- Antes de executar, confirme que você está na branch correta (a branch onde quer remover os commits).
- Exemplo de checagem:

```bash
git -C "$projeto_caminho/_worktrees/gitlab-develop" branch --show-current
```

## O que ele faz

- valida repositório Git
- resolve o alvo informado em `--to`
- cria tag de backup temporária automaticamente (padrão)
- remove a tag automaticamente quando a operação termina com sucesso
- pede confirmação explícita (`RESET`) antes de executar
- roda `git reset --hard <alvo>`

Observação:
- se houver erro/interrupção, a tag permanece para recuperação manual.

## Uso

```bash
cd "$projeto_caminho/_worktrees/gitlab-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/discard_commits_from_point.py --to f068ac4b"
```

Sem prompt interativo:

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/discard_commits_from_point.py --to f068ac4b --yes"
```

Sem criar tag de backup:

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/discard_commits_from_point.py --to f068ac4b --no-backup-tag"
```

Com validação de branch esperada (cancela se estiver na branch errada):

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/discard_commits_from_point.py --to f068ac4b --expected-branch develop"
```

## Exemplos de uso (todas as possibilidades)

1. Modo padrão (com prompt + tag de backup):

```bash
cd "$projeto_caminho/_worktrees/gitlab-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/discard_commits_from_point.py --to f068ac4b"
```

Solicita confirmação digitando `RESET` e cria tag de backup antes do reset.

2. Sem prompt interativo:

```bash
cd "$projeto_caminho/_worktrees/gitlab-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/discard_commits_from_point.py --to f068ac4b --yes"
```

Mantém tag de backup, mas executa sem pedir confirmação.

3. Sem tag automática:

```bash
cd "$projeto_caminho/_worktrees/gitlab-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/discard_commits_from_point.py --to f068ac4b --no-backup-tag"
```

Executa reset sem criar ponto de retorno automático.

4. Prefixo personalizado para backup:

```bash
cd "$projeto_caminho/_worktrees/gitlab-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/discard_commits_from_point.py --to f068ac4b --backup-tag-prefix backup-manual"
```

Cria tag de backup com prefixo customizado.

## Opções

- `--repo-root`: repositório alvo (default: diretório atual)
- `--to`: commit/ref de destino do reset (obrigatório)
- `--yes`: executa sem prompt de confirmação
- `--no-backup-tag`: desativa tag de backup automática
- `--backup-tag-prefix`: prefixo da tag de backup (default: `backup-before-discard`)
- `--expected-branch`: cancela a operação se a branch atual for diferente da informada
