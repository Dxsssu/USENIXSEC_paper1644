from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from .aggregator import LightweightAggregator
from .asset_catalog import AssetProfile
from .config import ScoringConfig
from .models import AlertBucketSnapshot, ScoreBreakdown


@dataclass
class LightweightRiskScorer:
    cfg: ScoringConfig

    def score(
        self,
        snapshot: AlertBucketSnapshot,
        historical_daily_avg: float,
        asset_profile: AssetProfile,
    ) -> ScoreBreakdown:
        s_freq = self._frequency_score(snapshot.count, snapshot.window_start, snapshot.window_end)
        s_rule = self._rule_score(
            snapshot.avg_severity_score,
            snapshot.avg_confidence_score,
            snapshot.rule_name,
            snapshot.log_type,
        )
        s_ctx = self._context_score(
            snapshot.src_external_ratio,
            snapshot.dst_sensitive_ratio,
            asset_profile,
        )
        s_rare = self._rarity_score(historical_daily_avg)

        weighted_sum = (
            self.cfg.w_freq * s_freq
            + self.cfg.w_rule * s_rule
            + self.cfg.w_ctx * s_ctx
            + self.cfg.w_rare * s_rare
        )
        final_score = self._squash(weighted_sum)
        risk_level = self._risk_level(final_score)
        return ScoreBreakdown(
            frequency_score=round(s_freq, 4),
            rule_score=round(s_rule, 4),
            context_score=round(s_ctx, 4),
            rarity_score=round(s_rare, 4),
            final_score=round(final_score, 2),
            risk_level=risk_level,
        )

    def is_high_priority(self, score: ScoreBreakdown) -> bool:
        return score.final_score >= self.cfg.threshold

    def _frequency_score(self, count: int, first_seen: datetime, last_seen: datetime) -> float:
        base = LightweightAggregator.normalize_frequency(count)
        duration_s = max((last_seen - first_seen).total_seconds(), 1.0)
        burst = max(0.0, min((count / duration_s) / 2.0, 1.0))
        return max(0.0, min((0.6 * base) + (0.4 * burst), 1.0))

    def _rule_score(self, severity: float, confidence: float, rule_name: str, log_type: str) -> float:
        keyword_weight = self._rule_keyword_weight(rule_name, log_type)
        return max(0.0, min((0.45 * severity) + (0.35 * confidence) + (0.20 * keyword_weight), 1.0))

    def _context_score(
        self,
        src_external_ratio: float,
        dst_sensitive_ratio: float,
        asset_profile: AssetProfile,
    ) -> float:
        sensitive_flag = 1.0 if asset_profile.sensitive else 0.0
        combined_sensitive = max(dst_sensitive_ratio, sensitive_flag)
        return max(
            0.0,
            min(
                (0.40 * src_external_ratio)
                + (0.30 * asset_profile.criticality)
                + (0.20 * asset_profile.exposure)
                + (0.10 * combined_sensitive),
                1.0,
            ),
        )

    def _rarity_score(self, historical_daily_avg: float) -> float:
        return max(0.0, min(1.0 / (1.0 + math.log1p(historical_daily_avg + 1.0)), 1.0))

    def _squash(self, value: float) -> float:
        normalized = 1.0 / (1.0 + math.exp(-7.0 * (value - 0.5)))
        return normalized * 100.0

    def _risk_level(self, final_score: float) -> str:
        if final_score >= 85.0:
            return "CRITICAL"
        if final_score >= 70.0:
            return "HIGH"
        if final_score >= 45.0:
            return "MEDIUM"
        return "LOW"

    def _rule_keyword_weight(self, rule_name: str, log_type: str) -> float:
        text = f"{rule_name} {log_type}".lower()
        strong = ("rce", "remote code", "deserialization", "sql", "sqli", "command injection")
        medium = ("xss", "ssrf", "path traversal", "upload", "shell", "webattack")
        if any(token in text for token in strong):
            return 0.95
        if any(token in text for token in medium):
            return 0.75
        return 0.45
