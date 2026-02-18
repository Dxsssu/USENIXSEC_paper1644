from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime

from .models import AlertBucketSnapshot, NormalizedAlert


@dataclass
class _BucketState:
    bucket_key: str
    sip: str
    dip: str
    proto: str
    rule_name: str
    log_type: str
    uri_template: str
    window_start: datetime
    window_end: datetime
    count: int = 0
    sum_severity: float = 0.0
    sum_confidence: float = 0.0
    src_external_count: int = 0
    dst_sensitive_count: int = 0
    representative_alert: dict = field(default_factory=dict)
    raw_ref_ids: list[str] = field(default_factory=list)

    def add(self, alert: NormalizedAlert, max_ref_ids: int) -> None:
        self.count += 1
        self.sum_severity += alert.severity_score
        self.sum_confidence += alert.confidence_score
        if alert.src_external:
            self.src_external_count += 1
        if alert.dst_sensitive:
            self.dst_sensitive_count += 1
        if alert.timestamp < self.window_start:
            self.window_start = alert.timestamp
        if alert.timestamp > self.window_end:
            self.window_end = alert.timestamp
            self.representative_alert = alert.raw
        if len(self.raw_ref_ids) < max_ref_ids:
            self.raw_ref_ids.append(alert.raw_id)


@dataclass
class LightweightAggregator:
    window_s: int = 300
    max_ref_ids: int = 200

    def __post_init__(self) -> None:
        self._buckets: dict[str, _BucketState] = {}

    def add(self, alert: NormalizedAlert) -> None:
        state = self._buckets.get(alert.bucket_key)
        if state is None:
            state = _BucketState(
                bucket_key=alert.bucket_key,
                sip=alert.sip,
                dip=alert.dip,
                proto=alert.proto,
                rule_name=alert.rule_name,
                log_type=alert.log_type,
                uri_template=alert.uri_template,
                window_start=alert.timestamp,
                window_end=alert.timestamp,
                representative_alert=alert.raw,
            )
            self._buckets[alert.bucket_key] = state
        state.add(alert, self.max_ref_ids)

    def flush_expired(self, now: datetime | None = None) -> list[AlertBucketSnapshot]:
        now_ts = now or datetime.now(UTC)
        expired_keys: list[str] = []
        for bucket_key, state in self._buckets.items():
            idle_seconds = (now_ts - state.window_end).total_seconds()
            if idle_seconds >= self.window_s:
                expired_keys.append(bucket_key)

        return [self._to_snapshot(self._buckets.pop(key)) for key in expired_keys]

    def force_flush(self) -> list[AlertBucketSnapshot]:
        snapshots = [self._to_snapshot(state) for state in self._buckets.values()]
        self._buckets.clear()
        return snapshots

    def _to_snapshot(self, state: _BucketState) -> AlertBucketSnapshot:
        return AlertBucketSnapshot(
            bucket_key=state.bucket_key,
            sip=state.sip,
            dip=state.dip,
            proto=state.proto,
            rule_name=state.rule_name,
            log_type=state.log_type,
            uri_template=state.uri_template,
            window_start=state.window_start,
            window_end=state.window_end,
            count=state.count,
            representative_alert=state.representative_alert,
            raw_ref_ids=state.raw_ref_ids,
            avg_severity_score=state.sum_severity / max(state.count, 1),
            avg_confidence_score=state.sum_confidence / max(state.count, 1),
            src_external_ratio=state.src_external_count / max(state.count, 1),
            dst_sensitive_ratio=state.dst_sensitive_count / max(state.count, 1),
        )

    @staticmethod
    def normalize_frequency(count: int) -> float:
        # log-scale keeps large bursts bounded without flattening small differences.
        return max(0.0, min(math.log1p(count) / math.log(51), 1.0))
