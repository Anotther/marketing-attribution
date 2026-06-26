# GraphQL para GitHub Projects v2

Use estes blocos com `gh api graphql`. Prefira variaveis `-f` para strings e `-F` para numeros/booleanos.

## Autenticacao

```bash
gh auth status
gh auth refresh -s project
```

Para somente leitura, `read:project` e suficiente. Para criar ou atualizar itens/campos, use `project`.

## Descobrir projeto

Organizacao:

```bash
gh api graphql \
  -f organization='ORG' \
  -F number=1 \
  -f query='
query($organization: String!, $number: Int!) {
  organization(login: $organization) {
    projectV2(number: $number) {
      id
      title
      url
      shortDescription
    }
  }
}'
```

Usuario:

```bash
gh api graphql \
  -f user='USER' \
  -F number=1 \
  -f query='
query($user: String!, $number: Int!) {
  user(login: $user) {
    projectV2(number: $number) {
      id
      title
      url
      shortDescription
    }
  }
}'
```

Listar projetos de uma organizacao:

```bash
gh api graphql \
  -f organization='ORG' \
  -f query='
query($organization: String!) {
  organization(login: $organization) {
    projectsV2(first: 50) {
      nodes { id number title url closed }
    }
  }
}'
```

## Listar campos

```bash
gh api graphql \
  -f projectId='PROJECT_ID' \
  -f query='
query($projectId: ID!) {
  node(id: $projectId) {
    ... on ProjectV2 {
      fields(first: 50) {
        nodes {
          ... on ProjectV2FieldCommon {
            __typename
            id
            name
            dataType
          }
          ... on ProjectV2SingleSelectField {
            __typename
            id
            name
            dataType
            options { id name }
          }
          ... on ProjectV2IterationField {
            __typename
            id
            name
            dataType
            configuration {
              iterations { id title startDate duration }
              completedIterations { id title startDate duration }
            }
          }
        }
      }
    }
  }
}'
```

## Listar itens

```bash
gh api graphql \
  -f projectId='PROJECT_ID' \
  -F first=50 \
  -f query='
query($projectId: ID!, $first: Int!) {
  node(id: $projectId) {
    ... on ProjectV2 {
      items(first: $first) {
        nodes {
          id
          type
          isArchived
          content {
            ... on Issue { id number title url state assignees(first: 10) { nodes { login } } labels(first: 10) { nodes { name } } }
            ... on PullRequest { id number title url state assignees(first: 10) { nodes { login } } labels(first: 10) { nodes { name } } }
            ... on DraftIssue { id title body }
          }
          fieldValues(first: 30) {
            nodes {
              ... on ProjectV2ItemFieldTextValue { text field { ... on ProjectV2FieldCommon { name } } }
              ... on ProjectV2ItemFieldNumberValue { number field { ... on ProjectV2FieldCommon { name } } }
              ... on ProjectV2ItemFieldDateValue { date field { ... on ProjectV2FieldCommon { name } } }
              ... on ProjectV2ItemFieldSingleSelectValue { name field { ... on ProjectV2FieldCommon { name } } }
              ... on ProjectV2ItemFieldIterationValue { title startDate duration field { ... on ProjectV2FieldCommon { name } } }
            }
          }
        }
      }
    }
  }
}'
```

## Obter node ID de issue ou PR

Issue:

```bash
gh api graphql \
  -f owner='OWNER' \
  -f repo='REPO' \
  -F number=123 \
  -f query='
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    issue(number: $number) { id title url }
  }
}'
```

Pull request:

```bash
gh api graphql \
  -f owner='OWNER' \
  -f repo='REPO' \
  -F number=123 \
  -f query='
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) { id title url }
  }
}'
```

## Adicionar item existente

```bash
gh api graphql \
  -f projectId='PROJECT_ID' \
  -f contentId='CONTENT_ID' \
  -f query='
mutation($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
    item { id }
  }
}'
```

## Criar draft issue no projeto

```bash
gh api graphql \
  -f projectId='PROJECT_ID' \
  -f title='TITLE' \
  -f body='BODY' \
  -f query='
mutation($projectId: ID!, $title: String!, $body: String) {
  addProjectV2DraftIssue(input: {projectId: $projectId, title: $title, body: $body}) {
    projectItem { id }
  }
}'
```

## Atualizar campos customizados

Texto:

```bash
gh api graphql \
  -f projectId='PROJECT_ID' \
  -f itemId='ITEM_ID' \
  -f fieldId='FIELD_ID' \
  -f text='VALUE' \
  -f query='
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $text: String!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $projectId
    itemId: $itemId
    fieldId: $fieldId
    value: { text: $text }
  }) { projectV2Item { id } }
}'
```

Numero:

```bash
gh api graphql \
  -f projectId='PROJECT_ID' \
  -f itemId='ITEM_ID' \
  -f fieldId='FIELD_ID' \
  -F number=3 \
  -f query='
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $number: Float!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $projectId
    itemId: $itemId
    fieldId: $fieldId
    value: { number: $number }
  }) { projectV2Item { id } }
}'
```

Data:

```bash
gh api graphql \
  -f projectId='PROJECT_ID' \
  -f itemId='ITEM_ID' \
  -f fieldId='FIELD_ID' \
  -f date='2026-05-02' \
  -f query='
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $date: Date!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $projectId
    itemId: $itemId
    fieldId: $fieldId
    value: { date: $date }
  }) { projectV2Item { id } }
}'
```

Single-select:

```bash
gh api graphql \
  -f projectId='PROJECT_ID' \
  -f itemId='ITEM_ID' \
  -f fieldId='FIELD_ID' \
  -f optionId='OPTION_ID' \
  -f query='
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $projectId
    itemId: $itemId
    fieldId: $fieldId
    value: { singleSelectOptionId: $optionId }
  }) { projectV2Item { id } }
}'
```

Iteration:

```bash
gh api graphql \
  -f projectId='PROJECT_ID' \
  -f itemId='ITEM_ID' \
  -f fieldId='FIELD_ID' \
  -f iterationId='ITERATION_ID' \
  -f query='
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $iterationId: String!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $projectId
    itemId: $itemId
    fieldId: $fieldId
    value: { iterationId: $iterationId }
  }) { projectV2Item { id } }
}'
```

## Remover item do projeto

Confirme antes de usar.

```bash
gh api graphql \
  -f projectId='PROJECT_ID' \
  -f itemId='ITEM_ID' \
  -f query='
mutation($projectId: ID!, $itemId: ID!) {
  deleteProjectV2Item(input: {projectId: $projectId, itemId: $itemId}) {
    deletedItemId
  }
}'
```
