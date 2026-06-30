# AGENTS.md

## Language
- Responda sempre em português brasileiro (pt-BR).

## Dev environment tips
- Use Python 3.11+ para desenvolvimento local.
- Crie um ambiente virtual antes de instalar dependências: `python -m venv .venv && source .venv/bin/activate`.
- Instale dependências com `pip install -r requirements-dev.txt -r requirements.txt`.
- Execute o pipeline no host com `.venv/bin/python -m src.main`.
- Configure `.env` a partir de `.env.example`, exporte as variáveis no shell e forneça credenciais GCP em `credentials/`.
- Use o PostgreSQL existente `postgres-dev` via `localhost:5433`; não crie container da aplicação para desenvolvimento local.
- Guarde artefatos gerados pelo pipeline em `data/`; não use `.context/` para outputs de execução.

## Testing instructions
- Execute `pytest` para rodar a suíte configurada no `pyproject.toml`.
- Use `pytest tests/<arquivo>.py -k <nome>` ao iterar em uma falha específica.
- Rode `ruff check .`, `ruff format --check .` e `mypy` para lint, formatação e tipagem.
- Antes de abrir PR, execute `ruff check . && ruff format --check . && mypy && pytest`.
- Adicione ou atualize testes junto de mudanças em `src/`, modelos de atribuição, persistência, ingestão ou CLI/scripts.

## PR instructions
- Siga Conventional Commits (por exemplo, `feat(models): add attribution metric`).
- Descreva impactos em dados, schema, BigQuery, PostgreSQL ou dashboards quando aplicável.
- Anexe saída de exemplo do CLI/pipeline ou paths dos Parquet gerados quando o comportamento mudar.
- Confirme que artefatos em `data/` foram regenerados apenas quando a mudança exigir e não inclua credenciais ou dados sensíveis.

## Repository map
- `src/` — código Python do pipeline de atribuição: configuração, ingestão BigQuery, pré-processamento, modelos, persistência e logging.
- `src/models/` — algoritmos de atribuição, incluindo heurísticas, Markov e Shapley.
- `tests/` — testes pytest para pipeline, modelos, configuração, ingestão e persistência.
- `data/` — artefatos Parquet gerados pelo pipeline para consumo analítico; edite manualmente apenas quando a tarefa envolver outputs versionados ou documentação do diretório.
- `dashboards/` — dashboard Grafana JSON e script Python para regeneração.
- `docs/` — documentação funcional/produto existente, incluindo `docs/PRD.md`.
- `.context/` — documentação e playbooks auxiliares para agentes; não trate como destino de artefatos do pipeline.
- `PROJECT_SETUP.md` — notas de setup do projeto; atualize quando fluxos de instalação ou execução mudarem.

## AI Context References
- Documentation index: `.context/docs/README.md`
- Agent playbooks: `.context/agents/README.md`
