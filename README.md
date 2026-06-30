# 📊 Pipeline de Atribuição de Marketing Omni-Channel

Um pipeline de engenharia de dados em Python que extrai o histórico de sessões de marketing via BigQuery (Google Analytics) e aplica algoritmos avançados de atribuição para determinar a contribuição real de cada canal nas conversões do negócio. 

Enquanto ferramentas comuns usam atribuição simplificada baseada em Last-Click, este projeto implementa modelos probabilísticos e baseados na teoria dos jogos (**Markov Chains** e **Shapley Value**) para distribuir o crédito de forma justa ao longo de toda a jornada de interações do usuário. 

O resultado processado é enviado para um banco de dados **PostgreSQL** e salvo localmente em formato **Parquet**, permitindo a criação de dashboards rápidos e portáveis no Grafana e no Power BI.

---

## 🏛️ Arquitetura

<!-- [INSERIR IMAGEM AQUI: Diagrama da Arquitetura do Sistema ilustrando desde a extração no BigQuery até a visualização no Grafana e Power BI] -->

O pipeline opera nos seguintes estágios:
1. **Ingestão**: Extrai dados transacionais do GA Sample Dataset localizados no BigQuery.
2. **Pré-processamento**: Limpa as informações e agrega as sessões sequencialmente para montar a jornada de touchpoints de cada usuário individual.
3. **Modelagem**: Aplica 5 abordagens matemáticas para cálculo de atribuição:
   - First-Click e Last-Click (Heurísticos)
   - Linear
   - Markov Chains (Efeito de Remoção e Cadeias de Markov)
   - Shapley Value (Teoria dos Jogos Cooperativos)
4. **Persistência**: Grava as jornadas, as dimensões dos canais e os resultados agregados de todos os modelos.

---

## 🚀 Como Executar (Quick Start)

A execução local usa o Python do host com `.venv` e grava no PostgreSQL existente `postgres-dev`, exposto no host em `localhost:5433`.

### 1. Configuração do Ambiente
Crie o arquivo de variáveis de ambiente a partir do exemplo fornecido e adicione suas credenciais do Google Cloud Platform (GCP) com acesso de leitura ao BigQuery:

```bash
# 1. Prepare as variáveis de ambiente
cp .env.example .env

# 2. Crie o diretório para a chave e insira sua service account
mkdir -p credentials
# Coloque o seu arquivo JSON (ex: gcp-service-account.json) dentro da pasta credentials/
```

*(Lembre-se de ajustar o valor de `GCP_PROJECT_ID` no seu `.env` gerado).*

### 2. Ambiente Python

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt -r requirements.txt
```

### 3. Rodando o Pipeline
Exporte as variáveis do `.env` e execute o módulo principal:

```bash
set -a
source .env
set +a
.venv/bin/python -m src.main
```

> O `DATABASE_URL` padrão do `.env.example` aponta para `postgresql://user:pass@localhost:5433/marketing_db`, compatível com o container existente `postgres-dev`.

---

## 🛠️ Desenvolvimento Local

Caso queira estender o pipeline ou rodar as rotinas de verificação localmente:

```bash
# Configurar o ambiente virtual (Python 3.11+)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt -r requirements.txt

# Verificação de qualidade de código (Lint e Tipagem - integrados com o CI)
ruff check . && ruff format --check . && mypy

# Testes automatizados unitários
pytest tests/ -v --cov=src
```

---

## 📁 Resultados e Artefatos (Outputs)

O pipeline foi construído com a premissa de idempotência, então cada nova rodada recriará as tabelas e arquivos adequadamente. Após a conclusão sem erros, seus dados estarão disponíveis em:

**1. Volume Compartilhado (Parquet)**
Arquivos persistidos nativamente no diretório `data/`:
- `resultados_atribuicao.parquet`
- `fato_jornadas.parquet`

**2. PostgreSQL Analítico**
O banco irá conter o esquema modelado pronto para leitura de dashboards:
- `fato_jornadas`
- `dim_canais`
- `resultados_atribuicao`

---

## 📈 Visualização: Grafana

A aplicação acompanha um painel analítico no Grafana validando todas as pontas da solução.

**Painéis disponíveis:**
- Comparação interativa de Receita Atribuída por Modelo.
- Métricas e KPIs Macro (Total de Jornadas, Volume de Conversões, Taxa de Conversão).
- Funil de Conversão segmentado pelos canais de aquisição.

**Como importar:**
1. Com uma instância do Grafana executando na mesma rede do seu PostgreSQL, navegue para `Dashboards -> New -> Import`.
2. Realize o upload do arquivo contido neste repositório: `dashboards/grafana_dashboard.json`.
3. No momento da importação, conecte a variável `DS_POSTGRES` apontando para o seu DataSource PostgreSQL interno.
4. *(Opcional)*: Se for realizar mudanças estruturais, você pode regenerar o arquivo json através da execução de `python dashboards/build_dashboard.py`.

---

## 🗂️ Estrutura do Projeto
```text
├── src/
│   ├── main.py            # Orquestração do Pipeline
│   ├── config.py          # Gerenciamento de Configuração via .env
│   ├── ingestion.py       # Extração através da API do GCP BigQuery
│   ├── preprocessing.py   # Transformação e montagem de jornadas
│   ├── persistence.py     # Carga no Postgres e exportação em Parquet
│   └── models/            # Módulos com Algoritmos de Atribuição
├── tests/                 # Suíte de Testes Unitários
└── dashboards/            # Artefatos JSON do Grafana e scripts
```

## 📄 Licença
Este projeto é distribuído sob a licença MIT. Veja o arquivo `LICENSE` para todos os detalhes.
