from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(UTC)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=UTC)
    if isinstance(value, str) and value:
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized).astimezone(UTC)
        except ValueError:
            return datetime.now(tz=UTC)
    return datetime.now(tz=UTC)


@dataclass
class AggregatedAlert:
    sip: str
    dip: str
    proto: str
    rule_name: str
    log_type: str
    reference_uuids: list[str]
    aggregated_count: int
    first_seen: int
    last_seen: int
    uri_template: str
    risk_scores: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AggregatedAlert":
        return cls(
            sip=str(payload.get("sip", "unknown_src")),
            dip=str(payload.get("dip", "unknown_dst")),
            proto=str(payload.get("proto", "unknown_proto")).lower(),
            rule_name=str(payload.get("rule_name", "unknown_rule")),
            log_type=str(payload.get("log_type", "unknown_log_type")),
            reference_uuids=[str(item) for item in payload.get("reference_uuids", [])],
            aggregated_count=int(payload.get("aggregated_count", 1)),
            first_seen=int(payload.get("first_seen", 0)),
            last_seen=int(payload.get("last_seen", 0)),
            uri_template=str(payload.get("uri_template", "-")),
            risk_scores=payload.get("risk_scores", {}) if isinstance(payload.get("risk_scores", {}), dict) else {},
            raw=payload,
        )

    @property
    def first_seen_dt(self) -> datetime:
        return parse_datetime(self.first_seen)

    @property
    def last_seen_dt(self) -> datetime:
        return parse_datetime(self.last_seen)


@dataclass
class MatchDecision:
    aggregate_score: float
    threshold: float
    min_instance_count: int
    instance_scores: list[float]
    is_business_false_positive: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "aggregate_score": round(self.aggregate_score, 4),
            "threshold": round(self.threshold, 4),
            "min_instance_count": self.min_instance_count,
            "instance_scores": [round(item, 4) for item in self.instance_scores],
            "is_business_false_positive": self.is_business_false_positive,
        }


@dataclass
class TrainRecord:
    label: int
    aggregated_alert: dict[str, Any]
    raw_alerts: list[dict[str, Any]]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TrainRecord":
        raw_alerts = payload.get("raw_alerts")
        if not isinstance(raw_alerts, list) or not raw_alerts:
            raw_alerts = [payload.get("raw_alert", payload.get("alert", payload))]
        parsed_alerts = [item for item in raw_alerts if isinstance(item, dict)]
        aggregated_alert = payload.get("aggregated_alert")
        if not isinstance(aggregated_alert, dict):
            aggregated_alert = payload.get("alert", {})
            if not isinstance(aggregated_alert, dict):
                aggregated_alert = {}
        label_value = int(payload.get("label", payload.get("is_business_false_positive", 0)))
        return cls(
            label=1 if label_value > 0 else 0,
            aggregated_alert=aggregated_alert,
            raw_alerts=parsed_alerts,
        )
