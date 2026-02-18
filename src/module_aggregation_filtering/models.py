from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class NormalizedAlert:
    raw_id: str
    timestamp: datetime
    sip: str
    dip: str
    proto: str
    rule_name: str
    log_type: str
    uri_template: str
    severity_score: float
    confidence_score: float
    src_external: bool
    dst_sensitive: bool
    raw: dict[str, Any]

    @property
    def bucket_key(self) -> str:
        parts = (self.sip, self.dip, self.proto, self.rule_name, self.log_type, self.uri_template)
        return "|".join(parts)


@dataclass
class AlertBucketSnapshot:
    bucket_key: str
    sip: str
    dip: str
    proto: str
    rule_name: str
    log_type: str
    uri_template: str
    window_start: datetime
    window_end: datetime
    count: int
    representative_alert: dict[str, Any]
    raw_ref_ids: list[str]
    avg_severity_score: float
    avg_confidence_score: float
    src_external_ratio: float
    dst_sensitive_ratio: float


@dataclass
class ScoreBreakdown:
    frequency_score: float
    rule_score: float
    context_score: float
    rarity_score: float
    final_score: float
    risk_level: str


@dataclass
class AggregatedAlert:
    sip: str
    dip: str
    proto: str
    rule_name: str
    log_type: str
    reference_uuids: list[str] = field(default_factory=list)
    aggregated_count: int = 0
    first_seen: int = 0
    last_seen: int = 0
    uri_template: str = "-"
    risk_scores: ScoreBreakdown | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.risk_scores is None:
            payload["risk_scores"] = None
        return payload
