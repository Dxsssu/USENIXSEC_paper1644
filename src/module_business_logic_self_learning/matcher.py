from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .config import ModelConfig
from .feature_pipeline import FeaturePipeline
from .models import AggregatedAlert, MatchDecision


@dataclass
class BusinessAlertMatcher:
    model: Any
    feature_pipeline: FeaturePipeline
    threshold: float
    min_instance_count: int

    @classmethod
    def from_artifact(cls, model_cfg: ModelConfig) -> "BusinessAlertMatcher":
        path = Path(model_cfg.model_path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {model_cfg.model_path}")
        with path.open("rb") as f:
            artifact = pickle.load(f)
        feature_state = artifact.get("feature_state")
        if not isinstance(feature_state, dict):
            raise ValueError("Invalid model artifact: missing feature_state")
        threshold = float(artifact.get("threshold", model_cfg.decision_threshold))
        model = artifact.get("model")
        if model is None:
            raise ValueError("Invalid model artifact: missing model")
        return cls(
            model=model,
            feature_pipeline=FeaturePipeline.from_state(feature_state),
            threshold=threshold,
            min_instance_count=model_cfg.min_instance_count,
        )

    def evaluate(self, aggregated_alert: AggregatedAlert, raw_alerts: list[dict[str, Any]]) -> MatchDecision:
        context = aggregated_alert.raw
        features = [
            self.feature_pipeline.transform_one(raw_alert=item, context=context)
            for item in raw_alerts
        ]
        if not features:
            return MatchDecision(
                aggregate_score=0.0,
                threshold=self.threshold,
                min_instance_count=self.min_instance_count,
                instance_scores=[],
                is_business_false_positive=False,
            )

        x = np.vstack(features).astype(np.float32)
        prob = self.model.predict_proba(x)[:, 1]
        instance_scores = [float(item) for item in prob.tolist()]
        aggregate_score = self._aggregate_score(instance_scores)

        is_bfp = (
            len(instance_scores) >= self.min_instance_count
            and aggregate_score >= self.threshold
        )
        return MatchDecision(
            aggregate_score=aggregate_score,
            threshold=self.threshold,
            min_instance_count=self.min_instance_count,
            instance_scores=instance_scores,
            is_business_false_positive=is_bfp,
        )

    def _aggregate_score(self, instance_scores: list[float]) -> float:
        arr = np.array(instance_scores, dtype=np.float32)
        p95 = float(np.percentile(arr, 95))
        mean = float(np.mean(arr))
        hit_ratio = float(np.mean(arr >= self.threshold))
        return (0.5 * p95) + (0.3 * mean) + (0.2 * hit_ratio)
