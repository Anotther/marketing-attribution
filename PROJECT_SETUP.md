# 🚀 Project Setup — Marketing Attribution Pipeline

> Guia de setup inicial para desenvolvimento do projeto usando GitHub Projects.

---

## 📋 Informações do Repositório

| Atributo | Valor |
|----------|-------|
| **Repositório** | [Anotther/marketing-attribution](https://github.com/Anotther/marketing-attribution) |
| **GitHub Project** | [Marketing Attribution Pipeline](https://github.com/users/Anotther/projects/22) |
| **Branch principal** | `main` |
| **Licença** | MIT |
| **Linguagem** | Python 3.11 |
| **Runtime local** | Python 3.11+ com `.venv` |

### Topics do Repositório

```
marketing-attribution · markov-chains · shapley-value · bigquery · postgresql
data-engineering · python · grafana · power-bi · parquet
multi-touch-attribution · homelab · data-pipeline · analytics
```

---

## 📊 GitHub Project Board

**URL**: https://github.com/users/Anotther/projects/22

### Colunas (Status)

| Status | Cor | Descrição |
|--------|-----|-----------|
| **Backlog** | 🔘 Cinza | Items não priorizados |
| **Todo** | 🔵 Azul | Prontos para trabalho |
| **In Progress** | 🟡 Amarelo | Em desenvolvimento |
| **Review** | 🟠 Laranja | Aguardando revisão |
| **Done** | 🟢 Verde | Concluído |

### Milestones (Issues)

| # | Milestone | Issue | Fase |
|---|-----------|-------|------|
| 1 | **Foundation** — Repo + CI | [#1](https://github.com/Anotther/marketing-attribution/issues/1) | Setup |
| 2 | **Data In** — BigQuery Ingestion & Cleaning | [#2](https://github.com/Anotther/marketing-attribution/issues/2) | Ingestão |
| 3 | **Models** — 5 Attribution Models | [#3](https://github.com/Anotther/marketing-attribution/issues/3) | Processamento |
| 4 | **Data Out** — PostgreSQL + Parquet | [#4](https://github.com/Anotther/marketing-attribution/issues/4) | Persistência |
| 5 | **Viz** — Grafana + Power BI | [#5](https://github.com/Anotther/marketing-attribution/issues/5) | Visualização |
| 6 | **Ship** — README + Docs + Review | [#6](https://github.com/Anotther/marketing-attribution/issues/6) | Polish |

---

## 🔧 Workflow de Desenvolvimento

### Branch Strategy

```
main ← develop ← feature/M{N}-{description}
```

**Convenção de branches:**
- `feature/M1-project-setup` — Feature ligada ao Milestone 1
- `feature/M3-markov-model` — Feature ligada ao Milestone 3
- `fix/M2-bigquery-auth` — Fix ligado ao Milestone 2

### Commit Convention

Usar [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(ingestion): add BigQuery extraction with date range params
fix(markov): normalize removal effect probabilities
docs(readme): add architecture diagram
test(shapley): add coalition subset tests
chore(ci): update python version
```

### PR Workflow

1. Criar branch a partir de `develop`
2. Implementar + testes
3. Push e abrir PR com referência ao issue (`Closes #N`)
4. CI deve passar (lint + type-check + test)
5. Merge para `develop`
6. Release: merge `develop` → `main`

---

## 🛠️ Setup Local

### Pré-requisitos

- Python 3.11+ (para desenvolvimento local)
- Container PostgreSQL existente (`postgres-dev`) exposto em `localhost:5433`
- Git
- `gh` CLI (opcional, para gerenciar issues)
- Service Account GCP (para acessar BigQuery)

### Inicialização

```bash
# Clone o repositório
git clone https://github.com/Anotther/marketing-attribution.git
cd marketing-attribution

# Copiar variáveis de ambiente
cp .env.example .env
# Editar .env com suas configurações

# Colocar credenciais GCP
mkdir -p credentials/
# Copiar gcp-service-account.json para credentials/

# Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Exportar variáveis e executar o pipeline no host
set -a
source .env
set +a
.venv/bin/python -m src.main

# Executar testes
.venv/bin/python -m pytest tests/ -v --cov=src
```

### Variáveis de Ambiente

```env
# .env.example
GCP_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=credentials/gcp-service-account.json
BQ_START_DATE=2016-08-01
BQ_END_DATE=2017-08-01
DATA_DIR=data
LOG_LEVEL=INFO
DATABASE_URL=postgresql://user:pass@localhost:5433/marketing_db
```

---

## 🔌 BigQuery MCP — Ferramenta de Desenvolvimento

O ambiente de desenvolvimento possui o **BigQuery MCP Server** configurado, que pode ser usado para exploração interativa dos dados durante o desenvolvimento.

### Ferramentas Disponíveis

| Ferramenta | Uso |
|-----------|-----|
| `execute_sql` | Testar queries de extração diretamente |
| `get_table_info` | Explorar schema das tabelas do GA |
| `list_dataset_ids` | Listar datasets disponíveis |
| `ask_data_insights` | Análise exploratória via NLP |
| `analyze_contribution` | Análise de contribuição (complementar) |

### Status

> ⚠️ **Ação necessária**: O BigQuery MCP está instalado mas requer ativação das ferramentas no servidor MCP. O project ID padrão configurado é `1002549606374` — verificar se corresponde ao projeto GCP correto.

### Exemplo de Uso (quando ativado)

```sql
-- Explorar o schema do GA Sample Dataset
SELECT column_name, data_type 
FROM `bigquery-public-data.google_analytics_sample.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'ga_sessions_20170801';

-- Preview dos dados
SELECT fullVisitorId, channelGrouping, visitNumber, totals.transactions
FROM `bigquery-public-data.google_analytics_sample.ga_sessions_20170801`
LIMIT 10;
```

---

## 📁 Estrutura de Diretórios

```
marketing-attribution/
├── .github/workflows/ci.yml    # CI pipeline
├── docs/PRD.md                 # Product Requirements Document
├── requirements.txt            # Deps produção
├── requirements-dev.txt        # Deps desenvolvimento
├── .env.example                # Template de config
├── .gitignore                  # Exclusões
├── credentials/                # 🔒 Não commitado
├── data/                       # 📁 Outputs Parquet
├── src/                        # Código fonte
│   ├── main.py                 # Entrypoint
│   ├── config.py               # Configurações
│   ├── ingestion.py            # BigQuery extração
│   ├── preprocessing.py        # Montagem de jornadas
│   ├── models/                 # Modelos de atribuição
│   │   ├── base.py             # Interface ABC
│   │   ├── heuristics.py       # First, Last, Linear
│   │   ├── markov.py           # Markov Chains
│   │   └── shapley.py          # Shapley Value
│   └── persistence.py          # PostgreSQL + Parquet
├── tests/                      # Testes unitários
└── dashboards/                 # Grafana JSON + Power BI
```

---

## 📌 Links Úteis

- **Repositório**: https://github.com/Anotther/marketing-attribution
- **Project Board**: https://github.com/users/Anotther/projects/22
- **PRD**: [`docs/PRD.md`](docs/PRD.md)
- **GA Sample Dataset**: [bigquery-public-data.google_analytics_sample](https://console.cloud.google.com/bigquery?p=bigquery-public-data&d=google_analytics_sample)
- **PostgreSQL Docs**: https://www.postgresql.org/docs/
- **NetworkX Docs**: https://networkx.org/documentation/stable/
