from __future__ import annotations

import hashlib
import ipaddress
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .models import NormalizedAlert

UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
)
SHA_RE = re.compile(r"\b[a-fA-F0-9]{40,64}\b")
HEX_TOKEN_RE = re.compile(r"\b[0-9a-fA-F]{12,39}\b")
BASE64_TOKEN_RE = re.compile(r"\b[A-Za-z0-9+_-]{16,}={0,2}\b")
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
TIMESTAMP_RE = re.compile(r"\b\d{10,13}\b")
LONG_NUM_RE = re.compile(r"\b\d{4,}\b")
QUERY_KEY_VALUE_RE = re.compile(r"([?&])([^=&]+)=([^&]*)")

PRIVATE_SEVERITY_MAP = {
    "critical": 1.0,
    "high": 0.8,
    "medium": 0.5,
    "low": 0.2,
    "info": 0.05,
}


@dataclass
class AlertNormalizer:
    def normalize(self, alert: dict[str, Any]) -> NormalizedAlert:
        timestamp = self._parse_timestamp(self._first_value(alert, "@timestamp", "timestamp", "time"))
        sip = self._string_or_default(self._first_value(alert, "source.ip", "src_ip", "sip"), "unknown_src")
        dip = self._string_or_default(
            self._first_value(alert, "destination.ip", "dst_ip", "dip"),
            "unknown_dst",
        )
        proto = self._string_or_default(
            self._first_value(alert, "network.transport", "proto", "protocol"),
            "unknown_proto",
        ).lower()
        rule_name = self._string_or_default(
            self._first_value(alert, "rule.name", "rule_name", "signature", "alert.rule"),
            "unknown_rule",
        )
        log_type = self._string_or_default(
            self._first_value(alert, "log_type", "event.dataset", "type", "event.module"),
            "unknown_log_type",
        )
        uri = self._string_or_default(self._first_value(alert, "url.path", "http.request.uri", "uri"), "-")
        uri_template = self._normalize_uri(uri)

        severity_score = self._normalize_score(self._first_value(alert, "severity", "rule.severity", "priority"))
        confidence_score = self._normalize_score(self._first_value(alert, "confidence", "risk_score", "risk.score"))
        src_external = self._is_external_ip(sip)
        dst_sensitive = self._is_sensitive_asset(alert)

        return NormalizedAlert(
            raw_id=self._derive_raw_id(alert, timestamp),
            timestamp=timestamp,
            sip=sip,
            dip=dip,
            proto=proto,
            rule_name=rule_name,
            log_type=log_type,
            uri_template=uri_template,
            severity_score=severity_score,
            confidence_score=confidence_score,
            src_external=src_external,
            dst_sensitive=dst_sensitive,
            raw=alert,
        )

    def _derive_raw_id(self, alert: dict[str, Any], timestamp: datetime) -> str:
        direct_id = self._first_value(alert, "event.id", "id", "alert_id", "_id")
        if direct_id:
            return str(direct_id)
        raw_blob = f"{timestamp.isoformat()}|{alert}".encode("utf-8", errors="ignore")
        return hashlib.sha256(raw_blob).hexdigest()

    def _parse_timestamp(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value.astimezone(UTC)
        if isinstance(value, str) and value:
            normalized = value.replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(normalized).astimezone(UTC)
            except ValueError:
                pass
        return datetime.now(UTC)

    def _normalize_uri(self, uri: str) -> str:
        cleaned = uri.strip() or "-"
        cleaned = QUERY_KEY_VALUE_RE.sub(self._replace_query_value, cleaned)
        cleaned = UUID_RE.sub("<UUID>", cleaned)
        cleaned = SHA_RE.sub("<HASH>", cleaned)
        cleaned = HEX_TOKEN_RE.sub("<TOKEN>", cleaned)
        cleaned = BASE64_TOKEN_RE.sub("<B64TOKEN>", cleaned)
        cleaned = EMAIL_RE.sub("<EMAIL>", cleaned)
        cleaned = IP_RE.sub("<IP>", cleaned)
        cleaned = TIMESTAMP_RE.sub("<TIMESTAMP>", cleaned)
        cleaned = LONG_NUM_RE.sub("<NUM>", cleaned)
        cleaned = re.sub(r"/{2,}", "/", cleaned)
        cleaned = re.sub(r"(?<=/)[A-Za-z0-9_-]{20,}(?=/|$)", "<TOKEN>", cleaned)
        return cleaned[:2048]

    def _replace_query_value(self, match: re.Match[str]) -> str:
        prefix, raw_key, raw_value = match.groups()
        key = raw_key.lower()
        value = raw_value.strip()
        if not value:
            return f"{prefix}{raw_key}="
        if any(token in key for token in ("token", "session", "auth", "passwd", "password", "secret", "sign")):
            return f"{prefix}{raw_key}=<SECRET>"
        if any(token in key for token in ("time", "timestamp", "_dc", "ts", "nonce")):
            return f"{prefix}{raw_key}=<TIMESTAMP>"
        if len(value) >= 24:
            return f"{prefix}{raw_key}=<TOKEN>"
        return f"{prefix}{raw_key}={value}"

    def _normalize_score(self, raw_score: Any) -> float:
        if raw_score is None:
            return 0.3
        if isinstance(raw_score, str):
            candidate = raw_score.strip().lower()
            if candidate in PRIVATE_SEVERITY_MAP:
                return PRIVATE_SEVERITY_MAP[candidate]
            try:
                raw_score = float(candidate)
            except ValueError:
                return 0.3
        if isinstance(raw_score, (int, float)):
            value = float(raw_score)
            if value > 1.0:
                value = min(value / 100.0, 1.0)
            return max(0.0, min(value, 1.0))
        return 0.3

    def _is_external_ip(self, ip_text: str) -> bool:
        try:
            ip_obj = ipaddress.ip_address(ip_text)
            return not (ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local)
        except ValueError:
            return False

    def _is_sensitive_asset(self, alert: dict[str, Any]) -> bool:
        candidates = (
            self._first_value(alert, "asset.criticality", "destination.asset_tier", "asset.tier"),
            self._first_value(alert, "destination.tags", "asset.tags"),
        )
        for value in candidates:
            text = str(value).lower()
            if any(token in text for token in ("critical", "prod", "payment", "core")):
                return True
        return False

    def _first_value(self, payload: dict[str, Any], *paths: str) -> Any:
        for path in paths:
            value = self._lookup_path(payload, path)
            if value is not None and value != "":
                return value
        return None

    def _lookup_path(self, payload: dict[str, Any], dotted_path: str) -> Any:
        if dotted_path in payload:
            return payload[dotted_path]
        current: Any = payload
        for part in dotted_path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    def _string_or_default(self, value: Any, default: str) -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text if text else default
