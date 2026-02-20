from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .config import FeatureConfig
from .feature_semantic import SemanticFeatureExtractor
from .feature_structural import StructuralFeatureExtractor
from .feature_temporal import TemporalFeatureExtractor


@dataclass
class FeaturePipeline:
    structural: StructuralFeatureExtractor
    semantic: SemanticFeatureExtractor
    temporal: TemporalFeatureExtractor

    @classmethod
    def from_config(cls, cfg: FeatureConfig) -> "FeaturePipeline":
        return cls(
            structural=StructuralFeatureExtractor(dim=cfg.structural_dim),
            semantic=SemanticFeatureExtractor(dim=cfg.semantic_dim),
            temporal=TemporalFeatureExtractor(
                dim=cfg.temporal_dim,
                business_start_hour=cfg.business_hours_start,
                business_end_hour=cfg.business_hours_end,
            ),
        )

    def transform_one(self, raw_alert: dict[str, Any], context: dict[str, Any]) -> np.ndarray:
        key = self._temporal_key(raw_alert, context)
        v_struct = self.structural.transform(raw_alert, context)
        v_sem = self.semantic.transform(raw_alert, context)
        v_tmp = self.temporal.transform(raw_alert, context, key=key)
        return np.concatenate([v_struct, v_sem, v_tmp], axis=0).astype(np.float32)

    @property
    def feature_dim(self) -> int:
        return self.structural.dim + self.semantic.dim + self.temporal.dim

    def export_state(self) -> dict[str, Any]:
        return {
            "structural_dim": self.structural.dim,
            "semantic_dim": self.semantic.dim,
            "temporal_dim": self.temporal.dim,
            "business_start_hour": self.temporal.business_start_hour,
            "business_end_hour": self.temporal.business_end_hour,
        }

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "FeaturePipeline":
        cfg = FeatureConfig(
            structural_dim=int(state["structural_dim"]),
            semantic_dim=int(state["semantic_dim"]),
            temporal_dim=int(state["temporal_dim"]),
            business_hours_start=int(state["business_start_hour"]),
            business_hours_end=int(state["business_end_hour"]),
        )
        return cls.from_config(cfg)

    def _temporal_key(self, raw_alert: dict[str, Any], context: dict[str, Any]) -> str:
        sip = self._first(raw_alert, context, "source.ip", "sip", "src_ip")
        dip = self._first(raw_alert, context, "destination.ip", "dip", "dst_ip")
        rule = self._first(raw_alert, context, "rule.name", "rule_name")
        return f"{sip}|{dip}|{rule}"

    def _first(self, raw_alert: dict[str, Any], context: dict[str, Any], *paths: str) -> str:
        for path in paths:
            value = self._lookup(raw_alert, path)
            if value is None:
                value = self._lookup(context, path)
            if value is not None:
                return str(value)
        return "-"

    def _lookup(self, payload: dict[str, Any], dotted_path: str) -> Any:
        if dotted_path in payload:
            return payload[dotted_path]
        current: Any = payload
        for part in dotted_path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current
