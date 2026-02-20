"""Business logic self-learning module for SOCRATES."""

from typing import TYPE_CHECKING, Any

from .config import (
    ElasticConfig,
    FeatureConfig,
    ModelConfig,
    Module2Config,
    QueueConfig,
    TrainConfig,
)
from .pipeline import BusinessSelfLearningPipeline, run_pipeline

if TYPE_CHECKING:
    from .trainer import TrainSummary


def train_from_jsonl(*args: Any, **kwargs: Any) -> Any:
    from .trainer import train_from_jsonl as _train_from_jsonl

    return _train_from_jsonl(*args, **kwargs)


def __getattr__(name: str) -> Any:
    if name == "TrainSummary":
        from .trainer import TrainSummary as _TrainSummary

        return _TrainSummary
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "ElasticConfig",
    "FeatureConfig",
    "ModelConfig",
    "Module2Config",
    "QueueConfig",
    "TrainConfig",
    "BusinessSelfLearningPipeline",
    "TrainSummary",
    "run_pipeline",
    "train_from_jsonl",
]
