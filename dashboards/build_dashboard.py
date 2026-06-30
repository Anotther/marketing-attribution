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
  channel,
  first_click_revenue  AS "First-Click",
  last_click_revenue   AS "Last-Click",
  linear_revenue       AS "Linear",
  markov_revenue       AS "Markov",
  shapley_revenue      AS "Shapley"
FROM resultados_atribuicao
ORDER BY channel
""".strip()

MODEL_CREDIT_SQL = """
SELECT
  channel,
  first_click_credit  AS "First-Click",
  last_click_credit   AS "Last-Click",
  linear_credit       AS "Linear",
  markov_credit       AS "Markov",
  shapley_credit      AS "Shapley"
FROM resultados_atribuicao
ORDER BY channel
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
  channel,
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
    panel_id: int,
    title: str,
    sql: str,
    unit: str,
    grid: dict,
    description: str,
    color: str = "green",
) -> dict:
    return {
        "id": panel_id,
        "type": "stat",
        "title": title,
        "description": description,
        "transparent": True,
        "gridPos": grid,
        "datasource": POSTGRES,
        "targets": [_target(sql)],
        "options": {
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "colorMode": "value",
            "graphMode": "none",
            "justifyMode": "auto",
            "orientation": "auto",
            "textMode": "auto",
        },
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "color": {"mode": "fixed", "fixedColor": color},
            },
            "overrides": [],
        },
    }


def _barchart(
    panel_id: int,
    title: str,
    sql: str,
    grid: dict,
    description: str,
    unit: str = "none",
) -> dict:
    return {
        "id": panel_id,
        "type": "barchart",
        "title": title,
        "description": description,
        "transparent": True,
        "gridPos": grid,
        "datasource": POSTGRES,
        "targets": [_target(sql)],
        "options": {
            "orientation": "auto",
            "xTickLabelRotation": 0,
            "xTickLabelSpacing": 0,
            "showValue": "auto",
            "stacking": "normal",
            "groupWidth": 0.8,
            "barWidth": 0.9,
            "barRadius": 4,
            "fullHighlight": False,
            "tooltip": {"mode": "multi", "sort": "desc"},
            "legend": {
                "displayMode": "table",
                "placement": "bottom",
                "showLegend": True,
                "calcs": [],
            },
        },
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "color": {"mode": "palette-classic"},
                "custom": {"lineWidth": 0, "fillOpacity": 90},
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
            "transparent": True,
            "gridPos": {"x": 0, "y": 0, "w": 24, "h": 3},
            "options": {
                "mode": "markdown",
                "content": (
                    "# 🎯 Omni-Channel Marketing Attribution\n\n"
                    "Welcome to the **Marketing Attribution Dashboard**. This view provides "
                    "a comparative analysis of how different models—from traditional "
                    "heuristics to advanced game-theoretic approaches—distribute "
                    "conversion credit across your marketing channels.\n\n"
                    "**Models included**: First-Click, Last-Click, Linear, Markov Chains "
                    "(Probabilistic), and Shapley Value (Game Theory)."
                ),
            },
        },
        _stat(
            2,
            "Total Journeys",
            "SELECT COUNT(*) AS v FROM fato_jornadas",
            "short",
            {"x": 0, "y": 3, "w": 6, "h": 4},
            "Total number of marketing journeys (sessions grouped by user) tracked in the dataset.",
            "blue",
        ),
        _stat(
            3,
            "Total Conversions",
            "SELECT COUNT(*) AS v FROM fato_jornadas WHERE converted",
            "short",
            {"x": 6, "y": 3, "w": 6, "h": 4},
            "Number of journeys that culminated in a transaction.",
            "green",
        ),
        _stat(
            4,
            "Conversion Rate",
            "SELECT AVG(CAST(converted AS INTEGER)) AS v FROM fato_jornadas",
            "percentunit",
            {"x": 12, "y": 3, "w": 6, "h": 4},
            "Percentage of journeys that resulted in a successful conversion.",
            "orange",
        ),
        _stat(
            5,
            "Total Revenue",
            "SELECT COALESCE(SUM(transaction_revenue), 0) AS v FROM fato_jornadas",
            "currencyUSD",
            {"x": 18, "y": 3, "w": 6, "h": 4},
            "Total monetary value generated across all converted journeys.",
            "purple",
        ),
        _barchart(
            6,
            "Revenue by Attribution Model",
            MODEL_REVENUE_SQL,
            {"x": 0, "y": 7, "w": 12, "h": 10},
            (
                "Compares how much revenue is credited to each channel according to "
                "the different attribution models. (Requirement: RF5.1)"
            ),
            unit="currencyUSD",
        ),
        _barchart(
            7,
            "Conversion Credit by Model",
            MODEL_CREDIT_SQL,
            {"x": 12, "y": 7, "w": 12, "h": 10},
            "Displays the number of conversions attributed to each channel across all models.",
            unit="short",
        ),
        _barchart(
            8,
            "Conversion Funnel (Sessions to Conversions)",
            FUNNEL_SQL,
            {"x": 0, "y": 17, "w": 24, "h": 10},
            (
                "Visualizes the drop-off from total sessions to actual conversions "
                "for each marketing channel. (Requirement: RF5.2)"
            ),
            unit="short",
        ),
        {
            "id": 9,
            "type": "table",
            "title": "Attribution Results (Detail)",
            "description": (
                "Tabular breakdown of credit and revenue assigned to each channel by model. "
                "Ranked by Shapley Value."
            ),
            "transparent": True,
            "gridPos": {"x": 0, "y": 27, "w": 24, "h": 8},
            "datasource": POSTGRES,
            "targets": [_target(TABLE_SQL)],
            "options": {
                "showHeader": True,
                "sortBy": [{"displayName": "Shapley", "desc": True}],
                "cellHeight": "sm",
            },
            "fieldConfig": {
                "defaults": {"custom": {"align": "auto"}},
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "shapley"},
                        "properties": [{"id": "custom.displayMode", "value": "color-background"}],
                    }
                ],
            },
        },
    ]

    return {
        "id": None,
        "uid": None,
        "title": "Marketing Attribution Pipeline",
        "description": "Multi-touch attribution models including Markov Chains and Shapley Value",
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
        "graphTooltip": 1,
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
