# Omni-Channel Marketing Attribution Pipeline

Containerized multi-touch attribution pipeline that ingests Google Analytics journeys from BigQuery, applies **five attribution models** (First-Click, Last-Click, Linear, **Markov Chains**, **Shapley Value**) and persists results to **DuckDB + Parquet** for visualization in Grafana and Power BI.

> **Status:** Milestone 1 (Foundation) — config, logging, orchestration, Docker & CI in place. Ingestion, models and persistence arrive in M2–M5.

---

## Architecture

```
BigQuery (GA sample) → ingestion → preprocessing → [heuristics · markov · shapley] → persistence → DuckDB + Parquet
                                                                                                  ↓
                                                                              Grafana (DuckDB) · Power BI (Parquet)
```

See [`docs/PRD.md`](docs/PRD.md) for the full design, data model and maths appendix.

> **Status:** Milestones 1–4 complete + Grafana dashboard (M5). The pipeline ingests & cleans GA sessions, assembles journeys, computes all five attribution models, persists to DuckDB + Parquet, and ships a portable Grafana dashboard; only the Power BI report remains (M5).

## Quick start

```bash
# 1. Configure environment
cp .env.example .env              # edit GCP_PROJECT_ID etc.
mkdir -p credentials              # place gcp-service-account.json here

# 2. Run the pipeline in Docker (one-shot container)
docker compose up --build

# 3. Smoke test without GCP credentials
docker compose run --rm attribution --dry-run
```

## Local development

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt

# Quality gates (mirror CI)
ruff check . && ruff format --check . && mypy
pytest tests/ -v --cov=src
```

## Configuration

All settings come from environment variables (see [`.env.example`](.env.example)):

| Variable | Default | Description |
|----------|---------|-------------|
| `GCP_PROJECT_ID` | — *(required)* | GCP project holding the BigQuery dataset |
| `GOOGLE_APPLICATION_CREDENTIALS` | — *(required)* | Path to the service-account JSON |
| `BQ_DATASET` | `bigquery-public-data.google_analytics_sample` | Fully-qualified dataset |
| `BQ_START_DATE` / `BQ_END_DATE` | `2016-08-01` / `2017-08-01` | Extraction window (ISO-8601) |
| `DATA_DIR` | `/app/data` | Output volume for DuckDB/Parquet |
| `LOG_LEVEL` | `INFO` | `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL` |
| `BQ_MAX_RETRIES` | `3` | BigQuery retry attempts (exponential backoff) |

## Project layout

```
src/
├── main.py            # Entrypoint & orchestration (injectable ingester/persister)
├── config.py          # ENV-driven settings
├── logging_setup.py   # Structured logging + phase timing
├── ingestion.py       # BigQuery extraction + cleaning (RF1.1-RF1.4)
├── preprocessing.py   # Journey assembly + channel dimension (RF2.1-RF2.3, RF4.3)
├── persistence.py     # DuckDB store + Parquet export (RF4.1-RF4.6)
└── models/
    ├── base.py        # AttributionModel ABC + shared helpers
    ├── heuristics.py  # First / Last / Linear (RF3.1-RF3.3)
    ├── markov.py      # Markov Chains + Removal Effect (RF3.4)
    └── shapley.py     # Shapley Value (RF3.5)
tests/                 # pytest suite (config, logging, main, ingestion, preprocessing, models, persistence)
.github/workflows/ci.yml  # lint + typecheck + test + docker build
```

## Milestones

| # | Milestone | Status |
|---|-----------|--------|
| M1 | Foundation — repo, Docker, CI, config, logging | ✅ |
| M2 | Data In — BigQuery ingestion & cleaning | ✅ |
| M3 | Models — First/Last/Linear/Markov/Shapley | ✅ |
| M4 | Data Out — DuckDB + Parquet persistence | ✅ |
| M5 | Viz — Grafana dashboard | ✅ (Grafana) · ⏳ (Power BI) |
| M6 | Ship — README polish, CI green | ⏳ |

## Output artifacts

Running the pipeline writes to the `data/` volume:

| Artifact | Format | Tables / contents |
|----------|--------|-------------------|
| `attribution_data.duckdb` | DuckDB | `fato_jornadas`, `dim_canais`, `resultados_atribuicao` |
| `resultados_atribuicao.parquet` | Parquet | per-channel credit + revenue for all 5 models |
| `fato_jornadas.parquet` | Parquet | full journey paths |

Re-runs are idempotent (`CREATE OR REPLACE TABLE` + fresh inserts).

## Visualization — Grafana (RF5.1, RF5.2)

`dashboards/grafana_dashboard.json` is a portable dashboard querying the DuckDB
store via the [DuckDB datasource plugin](https://github.com/motherduck-oss/grafana-duckdb-datasource).
Regenerate it with `python dashboards/build_dashboard.py`.

**Panels:**
- 4 KPIs: total journeys, conversions, conversion rate, total revenue
- **Revenue by model per channel** (RF5.1) — bar chart, 5 models as series
- Conversion credit by model per channel — bar chart
- **Conversion funnel per channel** (RF5.2) — Sessions → Conversions from `dim_canais`
- Attribution results detail table

**Import (UI):** Dashboards → New → Import → upload `grafana_dashboard.json` →
pick the DuckDB datasource for the `DS_DUCKDB` variable.

**Import (API):** create a service-account token, then:

```bash
GRAFANA_TOKEN=<your-token>
jq -n --slurpfile d dashboards/grafana_dashboard.json '{
  dashboard: ($d[0] | .id=null | .uid=null),
  folderUid: null, overwrite: true,
  message: "import marketing attribution dashboard"
}' | curl -s -X POST http://localhost:3000/api/dashboards/db \
  -H "Authorization: Bearer $GRAFANA_TOKEN" \
  -H "Content-Type: application/json" -d @-
```

The DuckDB datasource must point at the pipeline's `data/attribution_data.duckdb`
(mount the file into the Grafana container if Grafana runs in Docker). A sample
DuckDB populated with synthetic journeys is written to `data/` on first run for
immediate testing.

## License

MIT
