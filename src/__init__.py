"""Omni-channel marketing attribution pipeline.

Containerized pipeline that ingests Google Analytics journeys from BigQuery,
applies five attribution models (First-Click, Last-Click, Linear, Markov Chains
and Shapley Value) and persists results to DuckDB + Parquet.
"""

__version__ = "0.1.0"
