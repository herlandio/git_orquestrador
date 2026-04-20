# drop_empty_commits_auto.py

## Convenção de caminho

Nos exemplos abaixo, use:

```bash
projeto_caminho="/caminho/do/seu/projeto"
```

Script para remover commits vazios automaticamente no intervalo `BASE..HEAD`.

## O que ele faz

- valida se o diretório é um repositório Git
- valida que não existe sessão ativa de `rebase`/`am`
- valida que a working tree está limpa
- identifica commits vazios no range (`git diff-tree` sem arquivos alterados)
- remove os commits vazios um a um com `git rebase --onto <empty>^ <empty>`
- cria tag de backup automaticamente antes de reescrever histórico (padrão)
- remove a tag de backup automaticamente quando a operação termina com sucesso

## Pré-requisitos

- Python 3
- executar no worktree alvo (ex.: `gitlab-develop`)
- working tree limpa (`git status --porcelain` vazio)

## Uso rápido

```bash
cd "$projeto_caminho/_worktrees/gitlab-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/drop_empty_commits_auto.py --base ORIG_HEAD"
```

## Exemplos de uso (todas as possibilidades)

1. Execução padrão com base explícita:

```bash
cd "$projeto_caminho/_worktrees/gitlab-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/drop_empty_commits_auto.py --base ORIG_HEAD"
```

Remove commits vazios no intervalo `ORIG_HEAD..HEAD` e cria tag de backup.

2. Apenas análise (`--dry-run`):

```bash
cd "$projeto_caminho/_worktrees/gitlab-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/drop_empty_commits_auto.py --base ORIG_HEAD --dry-run"
```

Lista os commits vazios encontrados sem reescrever histórico.

3. Sem criar tag de backup:

```bash
cd "$projeto_caminho/_worktrees/gitlab-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/drop_empty_commits_auto.py --base ORIG_HEAD --no-backup-tag"
```

Reescreve histórico sem criar tag de segurança.

4. Prefixo personalizado da tag:

```bash
cd "$projeto_caminho/_worktrees/gitlab-develop"
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/drop_empty_commits_auto.py --base ORIG_HEAD --backup-tag-prefix backup-limpeza-vazios"
```

Cria backup usando o prefixo informado.

5. Repositório não atual (`--repo-root`):

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/drop_empty_commits_auto.py" \
  --repo-root $projeto_caminho/_worktrees/gitlab-develop \
  --base ORIG_HEAD
```

Permite executar a partir de outro diretório, apontando o repo alvo.

## Opções

- `--repo-root`: repositório alvo (default: diretório atual)
- `--base`: commit base do intervalo (default: `ORIG_HEAD`)
- `--dry-run`: lista todos os commits vazios encontrados no intervalo, sem alterar histórico
- `--no-backup-tag`: desativa criação automática de tag de backup
- `--backup-tag-prefix`: prefixo da tag de backup  
  default: `backup-before-drop-empty`

## Exemplos

Com base explícita:

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/drop_empty_commits_auto.py --base 3c7399d2"
```

Dry-run:

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/drop_empty_commits_auto.py --base ORIG_HEAD --dry-run"
```

Sem tag de backup automática:

```bash
python3 "$projeto_caminho/_worktrees/azure-develop/scripts/git_orquestrador/src/drop_empty_commits_auto.py --base ORIG_HEAD --no-backup-tag"
```

## Tag de backup

Por padrão o script cria uma tag temporária no `HEAD` atual antes de reescrever:

```text
backup-before-drop-empty-YYYYMMDD-HHMMSS
```

Comportamento:

- em sucesso: a tag é removida automaticamente
- em erro/interrupção: a tag permanece para recuperação manual

## Códigos de saída

- `0`: execução concluída com sucesso
- `1`: erro de execução/validação (ex.: base inválida, árvore suja)
- `2`: há sessão de `rebase`/`am` em andamento

## Limitações e observações

- o script reescreve histórico local (não use em branch já compartilhado sem alinhar com o time)
- se ocorrer conflito durante o rebase automático, o script para e você deve resolver manualmente:
  - `git rebase --continue`, ou
  - `git rebase --abort`
