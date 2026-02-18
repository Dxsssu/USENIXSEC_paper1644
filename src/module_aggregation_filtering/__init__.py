"""Lightweight aggregation and denoising module for SOCRATES."""

from .config import (
    AggregationConfig,
    AssetConfig,
    HistoryConfig,
    Module1Config,
    QueueConfig,
    ScoringConfig,
)

try:
    from .pipeline import LightweightAggregationPipeline, run_pipeline
except ModuleNotFoundError:
    LightweightAggregationPipeline = None  # type: ignore[assignment]
    run_pipeline = None  # type: ignore[assignment]

__all__ = [
    "AggregationConfig",
    "AssetConfig",
    "HistoryConfig",
    "Module1Config",
    "QueueConfig",
    "ScoringConfig",
    "LightweightAggregationPipeline",
    "run_pipeline",
]
