"""Attribution model package.

Five models conform to the :class:`~src.models.base.AttributionModel` interface:
- ``heuristics``: First-Click, Last-Click, Linear
- ``markov``: Markov Chains (Removal Effect)
- ``shapley``: Shapley Value (cooperative game theory)

:func:`run_all_models` evaluates every model on the same journeys and returns
the consolidated credit comparison frame (PRD RF3.6). :func:`attribute_full`
additionally carries per-model revenue, feeding the ``resultados_atribuicao``
table (PRD section 9.3).
"""

from __future__ import annotations

import logging

import pandas as pd

from src.models.base import (
    AttributionModel,
    AttributionModelError,
    AttributionResult,
    Journeys,
    validate_journeys,
)
from src.models.heuristics import (
    first_click_model,
    last_click_model,
    linear_model,
)
from src.models.markov import MarkovChainsModel
from src.models.shapley import ShapleyValueModel

logger = logging.getLogger("attribution.models")

#: Model name -> credit column in the consolidated output (PRD RF3.6).
MODEL_COLUMNS: dict[str, str] = {
    "first_click": "first_click",
    "last_click": "last_click",
    "linear": "linear",
    "markov": "markov",
    "shapley": "shapley",
}

#: Credit + revenue columns written to ``resultados_atribuicao`` (PRD section 9.3).
RESULTADO_COLUMNS: tuple[str, ...] = (
    "channel",
    "first_click_credit",
    "last_click_credit",
    "linear_credit",
    "markov_credit",
    "shapley_credit",
    "first_click_revenue",
    "last_click_revenue",
    "linear_revenue",
    "markov_revenue",
    "shapley_revenue",
)

__all__ = [
    "AttributionModel",
    "AttributionModelError",
    "AttributionResult",
    "Journeys",
    "MODEL_COLUMNS",
    "MarkovChainsModel",
    "RESULTADO_COLUMNS",
    "ShapleyValueModel",
    "attribute_full",
    "first_click_model",
    "last_click_model",
    "linear_model",
    "run_all_models",
]


def _model_registry() -> list[AttributionModel]:
    return [
        first_click_model(),
        last_click_model(),
        linear_model(),
        MarkovChainsModel(),
        ShapleyValueModel(),
    ]


def attribute_full(journeys: pd.DataFrame) -> pd.DataFrame:
    """Run every model and return per-channel credits **and** revenue.

    Columns: ``channel`` plus ``<model>_credit`` and ``<model>_revenue`` for each
    of the five models (see :data:`RESULTADO_COLUMNS`). Both the credits and the
    revenue of each model sum to the totals over converting journeys.
    """
    validate_journeys(journeys)
    channels = sorted({channel for path in journeys["channel_path"] for channel in path})
    data: dict[str, pd.Series] = {}

    for model in _model_registry():
        result = model.attribute(journeys).set_index("channel")
        credit_col = MODEL_COLUMNS[model.name]
        data[f"{credit_col}_credit"] = result["conversions"].reindex(channels).fillna(0.0)
        data[f"{credit_col}_revenue"] = result["revenue"].reindex(channels).fillna(0.0)
        logger.info(
            "models.attribute model=%s credited=%.4f revenue=%.4f",
            credit_col,
            float(data[f"{credit_col}_credit"].sum()),
            float(data[f"{credit_col}_revenue"].sum()),
        )

    table = pd.DataFrame(data, index=channels)
    table.index.name = "channel"
    return table.reset_index().reindex(columns=list(RESULTADO_COLUMNS))


def run_all_models(journeys: pd.DataFrame) -> pd.DataFrame:
    """Consolidated per-channel conversion credits for the 5 models (RF3.6).

    Returns a dataframe with one row per channel and columns ``channel``,
    ``first_click``, ``last_click``, ``linear``, ``markov`` and ``shapley`` --
    each the per-channel conversion credit (float64). Credits of every column
    sum to the total number of converting journeys.
    """
    full = attribute_full(journeys)
    credit_cols = ["channel", *MODEL_COLUMNS.values()]
    renamed = {f"{name}_credit": name for name in MODEL_COLUMNS}
    return full.rename(columns=renamed)[credit_cols]
