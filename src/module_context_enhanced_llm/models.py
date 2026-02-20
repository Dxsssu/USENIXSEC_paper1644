from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


@dataclass
class InvestigationAlert:
    payload: dict[str, Any]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "InvestigationAlert":
        return cls(payload=payload)

    def brief(self) -> dict[str, Any]:
        fields = [
            "sip",
            "dip",
            "proto",
            "rule_name",
            "log_type",
            "uri_template",
            "reference_uuids",
            "risk_scores",
            "module2_business_match",
        ]
        return {key: self.payload.get(key) for key in fields if key in self.payload}


@dataclass
class ToolCall:
    tool: str
    args: dict[str, Any]
    rationale: str = ""


@dataclass
class ToolResult:
    tool: str
    success: bool
    query: dict[str, Any] | None = None
    summary: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def compact(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "success": self.success,
            "query": self.query,
            "summary": self.summary,
            "error": self.error,
            "data": self.data,
        }


@dataclass
class InvestigationVerdict:
    verdict: str
    severity: str
    confidence: float
    reasoning_summary: str
    evidence: list[dict[str, Any]]
    tool_trace: list[dict[str, Any]]
    recommended_action: str
    started_at: str
    finished_at: str
    duration_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "severity": self.severity,
            "confidence": round(self.confidence, 4),
            "reasoning_summary": self.reasoning_summary,
            "evidence": self.evidence,
            "tool_trace": self.tool_trace,
            "recommended_action": self.recommended_action,
            "timestamps": {
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "duration_ms": self.duration_ms,
            },
        }
