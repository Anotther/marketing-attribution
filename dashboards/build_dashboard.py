"""Generator for the Grafana dashboard JSON (PRD RF5.1, RF5.2).

Produces ``dashboards/grafana_dashboard.json`` -- a portable, importable
dashboard that queries the PostgreSQL store produced by the pipeline. The Postgres
datasource is referenced via a ``DS_POSTGRES`` input variable so the dashboard is
portable across Grafana instances (on import the user picks the datasource).

Run:  python dashboards/build_dashboard.py
"""

from __future__ import annotations

import json
from pathlib import Path

POSTGRES = {"type": "postgres", "uid": "${DS_POSTGRES}"}

MODEL_REVENUE_SQL = """
SELECT
  channel_name,
  first_click_revenue  AS "First-Click",
  last_click_revenue   AS "Last-Click",
  linear_revenue       AS "Linear",
  markov_revenue       AS "Markov",
  shapley_revenue      AS "Shapley"
FROM resultados_atribuicao
ORDER BY channel_name
""".strip()

MODEL_CREDIT_SQL = """
SELECT
  channel_name,
  first_click_credit  AS "First-Click",
  last_click_credit   AS "Last-Click",
  linear_credit       AS "Linear",
  markov_credit       AS "Markov",
  shapley_credit      AS "Shapley"
FROM resultados_atribuicao
ORDER BY channel_name
""".strip()

FUNNEL_SQL = """
SELECT
  channel_name,
  total_sessions    AS "Sessions",
  total_conversions AS "Conversions"
FROM dim_canais
ORDER BY total_sessions DESC
""".strip()

TABLE_SQL = """
SELECT
  channel_name,
  ROUND(first_click_credit, 3)  AS first_click,
  ROUND(last_click_credit, 3)   AS last_click,
  ROUND(linear_credit, 3)       AS linear,
  ROUND(markov_credit, 3)       AS markov,
  ROUND(shapley_credit, 3)      AS shapley,
  ROUND(first_click_revenue, 2) AS first_click_rev,
  ROUND(markov_revenue, 2)      AS markov_rev,
  ROUND(shapley_revenue, 2)     AS shapley_rev
FROM resultados_atribuicao
ORDER BY shapley_credit DESC
""".strip()


def _target(sql: str, ref_id: str = "A") -> dict:
    return {
        "refId": ref_id,
        "datasource": POSTGRES,
        "editorMode": "code",
        "format": "table",
        "rawQuery": True,
        "rawSql": sql,
    }


def _stat(
    panel_id: int, title: str, sql: str, unit: str, grid: dict, color_mode: str = "value"
) -> dict:
    return {
        "id": panel_id,
        "type": "stat",
        "title": title,
        "gridPos": grid,
        "datasource": POSTGRES,
        "targets": [_target(sql)],
        "options": {
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "colorMode": color_mode,
            "graphMode": "area",
            "orientation": "auto",
            "textMode": "auto",
        },
        "fieldConfig": {"defaults": {"unit": unit}, "overrides": []},
    }


def _barchart(panel_id: int, title: str, sql: str, grid: dict, unit: str = "none") -> dict:
    return {
        "id": panel_id,
        "type": "barchart",
        "title": title,
        "gridPos": grid,
        "datasource": POSTGRES,
        "targets": [_target(sql)],
        "options": {
            "orientation": "auto",
            "xTickLabelRotation": 0,
            "xTickLabelSpacing": 0,
            "showValue": "auto",
            "stacking": "normal",
            "groupWidth": 0.7,
            "barWidth": 0.97,
            "barRadius": 0,
            "fullHighlight": False,
            "tooltip": {"mode": "single", "sort": "none"},
            "legend": {"displayMode": "list", "placement": "bottom", "showLegend": True},
        },
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "color": {"mode": "palette-classic"},
                "custom": {"lineWidth": 0, "fillOpacity": 80},
            },
            "overrides": [],
        },
    }


def build_dashboard() -> dict:
    panels = [
        {
            "id": 1,
            "type": "text",
            "title": "",
            "gridPos": {"x": 0, "y": 0, "w": 24, "h": 2},
            "options": {
                "mode": "markdown",
                "content": (
                    "# Omni-Channel Marketing Attribution\n"
                    "Multi-touch attribution across **First-Click · Last-Click · Linear · "
                    "Markov Chains · Shapley Value**. Source: PostgreSQL (`resultados_atribuicao`, "
                    "`dim_canais`, `fato_jornadas`)."
                ),
            },
        },
        _stat(
            2,
            "Total journeys",
            "SELECT COUNT(*) AS v FROM fato_jornadas",
            "short",
            {"x": 0, "y": 2, "w": 6, "h": 4},
        ),
        _stat(
            3,
            "Conversions",
            "SELECT COUNT(*) AS v FROM fato_jornadas WHERE converted",
            "short",
            {"x": 6, "y": 2, "w": 6, "h": 4},
        ),
        _stat(
            4,
            "Conversion rate",
            "SELECT AVG(CAST(converted AS INTEGER)) AS v FROM fato_jornadas",
            "percentunit",
            {"x": 12, "y": 2, "w": 6, "h": 4},
        ),
        _stat(
            5,
            "Total revenue",
            "SELECT COALESCE(SUM(transaction_revenue), 0) AS v FROM fato_jornadas",
            "currencyUSD",
            {"x": 18, "y": 2, "w": 6, "h": 4},
        ),
        _barchart(
            6,
            "Revenue by attribution model (per channel) — RF5.1",
            MODEL_REVENUE_SQL,
            {"x": 0, "y": 6, "w": 12, "h": 10},
            unit="currencyUSD",
        ),
        _barchart(
            7,
            "Conversion credit by model (per channel)",
            MODEL_CREDIT_SQL,
            {"x": 12, "y": 6, "w": 12, "h": 10},
            unit="short",
        ),
        _barchart(
            8,
            "Conversion funnel by channel (Sessions → Conversions) — RF5.2",
            FUNNEL_SQL,
            {"x": 0, "y": 16, "w": 24, "h": 10},
            unit="short",
        ),
        {
            "id": 9,
            "type": "table",
            "title": "Attribution results (detail)",
            "gridPos": {"x": 0, "y": 26, "w": 24, "h": 8},
            "datasource": POSTGRES,
            "targets": [_target(TABLE_SQL)],
            "options": {
                "showHeader": True,
                "sortBy": [{"displayName": "Shapley", "desc": True}],
                "cellHeight": "sm",
            },
            "fieldConfig": {"defaults": {"custom": {"align": "auto"}}, "overrides": []},
        },
    ]

    return {
        "id": None,
        "uid": None,
        "title": "Marketing Attribution Pipeline",
        "tags": ["marketing-attribution", "markov", "shapley", "postgresql"],
        "timezone": "browser",
        "schemaVersion": 39,
        "version": 0,
        "refresh": "",
        "time": {"from": "now-6h", "to": "now"},
        "fiscalYearStartMonth": 0,
        "liveNow": False,
        "weekStart": "",
        "editable": True,
        "graphTooltip": 0,
        "templating": {
            "list": [
                {
                    "name": "DS_POSTGRES",
                    "type": "datasource",
                    "pluginId": "postgres",
                    "pluginName": "PostgreSQL",
                    "label": "PostgreSQL datasource",
                    "hide": 0,
                    "query": "postgres",
                    "current": {"text": "PostgreSQL", "value": "PostgreSQL"},
                    "description": "Select the PostgreSQL datasource.",
                }
            ]
        },
        "annotations": {"list": []},
        "panels": panels,
        "links": [],
    }


def main() -> None:
    out = Path(__file__).parent / "grafana_dashboard.json"
    payload = json.dumps(build_dashboard(), indent=2, ensure_ascii=False) + "\n"
    out.write_text(payload, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
