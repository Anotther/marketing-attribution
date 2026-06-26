---
name: gh-projects-tasks
description: Consultar, listar, adicionar e atualizar tarefas em quadros do GitHub Projects/Projects v2 usando GitHub app/tools, GitHub CLI ou GraphQL. Use quando o usuario pedir para ver ou mudar tarefas, cards, itens, status, prioridade, iteracao, datas, responsaveis, labels ou campos de um project/Projeto/Projectz do GitHub, especialmente em quadros de organizacao ou usuario.
---

# GitHub Projects Tasks

## Overview

Use esta skill para operar tarefas em GitHub Projects v2 com baixo risco: descobrir o projeto correto, consultar itens/campos, aplicar atualizacoes e reportar exatamente o que mudou.

Projects v2 usa a API GraphQL para a maioria das operacoes de itens e campos. Para consultas e mutacoes GraphQL prontas, leia `references/graphql.md` quando precisar montar comandos `gh api graphql`.

## Workflow

1. Identifique o alvo:
   - Extraia owner, escopo e numero pela URL quando fornecida: `/orgs/ORG/projects/NUMBER` ou `/users/USER/projects/NUMBER`.
   - Quando faltar a URL, descubra o owner/repo com `git remote -v`, `gh repo view --json owner,name`, ou pergunte se houver mais de um projeto plausivel.
   - Nao confunda repository Projects legados com Projects v2.

2. Verifique acesso:
   - Use ferramentas do GitHub quando ja estiverem disponiveis para leitura de repo/issue/PR.
   - Para Projects v2, prefira `gh api graphql`.
   - Rode `gh auth status` antes de operar. Para leitura, o token precisa de `read:project`; para alteracoes, precisa de `project`.
   - Se o token nao tiver escopo suficiente, informe o comando recomendado: `gh auth refresh -s project` ou `gh auth login --scopes project`.

3. Resolva IDs antes de alterar:
   - Obtenha `projectId` pelo owner e numero.
   - Liste campos do projeto e mapeie nomes para `fieldId`.
   - Para campos single-select, mapeie o valor desejado para `optionId`.
   - Para iteracao, mapeie a janela desejada para `iterationId`.
   - Localize o `itemId` do card no projeto; o ID da issue/PR (`contentId`) nao substitui o `itemId` em updates de campo.

4. Execute com cuidado:
   - Para consultas, retorne uma tabela curta com titulo, URL/conteudo, status e campos relevantes.
   - Para alteracoes pedidas explicitamente, aplique a mutacao e depois consulte novamente o item para confirmar.
   - Se o pedido for ambiguo ou puder afetar muitos itens, apresente o plano e aguarde confirmacao.
   - Nao invente valores de campos. Se o valor solicitado nao existir em single-select/iteration, liste opcoes validas e pare.

## Operacoes Comuns

### Listar tarefas

Use filtros do proprio projeto quando o usuario pedir por status, responsavel, prioridade, sprint ou texto. Se a API do Project nao expuser exatamente o filtro, liste itens suficientes e filtre localmente pelo JSON retornado.

### Adicionar tarefa

Quando a tarefa ja existir como issue/PR, adicione-a com `addProjectV2ItemById` usando o node ID da issue/PR. Quando o usuario pedir uma tarefa avulsa no quadro, crie draft issue com `addProjectV2DraftIssue`. Depois ajuste campos em chamadas separadas.

### Atualizar campos

Use `updateProjectV2ItemFieldValue` para campos customizados de texto, numero, data, single-select e iteration. Para `Assignees`, `Labels`, `Milestone` e `Repository`, atualize a issue/PR subjacente com mutacoes ou comandos apropriados, pois esses campos pertencem ao conteudo, nao ao item do projeto.

### Remover ou arquivar

Confirme antes de remover, arquivar, fechar issues ou executar mudancas em lote. Para exclusao do item do projeto, use `deleteProjectV2Item`; isso remove o card do projeto, nao necessariamente fecha a issue/PR.

## Reporting

Ao finalizar:

- Diga o projeto operado e o owner.
- Para consultas, inclua os itens encontrados e os campos usados.
- Para atualizacoes, inclua antes/depois dos campos alterados e o link da issue/PR ou item quando disponivel.
- Informe claramente quando nao foi possivel executar por falta de autenticacao, escopo `project`, permissao no projeto ou ambiguidade do alvo.

## Reference

- `references/graphql.md`: comandos GraphQL reutilizaveis para descobrir projetos, campos, itens, adicionar cards e atualizar valores.
- GitHub Docs: Projects integra issues/PRs e sincroniza dados nos dois sentidos; a API GraphQL e o GitHub CLI sao os caminhos documentados para automacao de Projects v2.
