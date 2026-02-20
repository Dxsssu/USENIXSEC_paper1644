from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any

import numpy as np


def _hash_to_bin(text: str, dim: int) -> int:
    digest = hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()
    return int(digest[:8], 16) % dim


@dataclass
class StructuralFeatureExtractor:
    dim: int = 32

    def transform(self, raw_alert: dict[str, Any], context: dict[str, Any]) -> np.ndarray:
        vector = np.zeros(self.dim, dtype=np.float32)
        for token in self._categorical_tokens(raw_alert, context):
            idx = _hash_to_bin(token, self.dim)
            vector[idx] += 1.0
        vector /= max(float(np.linalg.norm(vector)), 1.0)
        return vector

    def _categorical_tokens(self, raw_alert: dict[str, Any], context: dict[str, Any]) -> list[str]:
        sip = self._first(raw_alert, context, "source.ip", "src_ip", "sip")
        dip = self._first(raw_alert, context, "destination.ip", "dst_ip", "dip")
        proto = self._first(raw_alert, context, "network.transport", "proto", "protocol")
        rule_name = self._first(raw_alert, context, "rule.name", "rule_name")
        uri_template = self._first(raw_alert, context, "uri_template", "url.path", "http.request.uri", "uri")
        log_type = self._first(raw_alert, context, "log_type", "event.dataset", "event.module", "type")

        sport = self._to_int(self._first(raw_alert, context, "source.port", "sport", "src_port"))
        dport = self._to_int(self._first(raw_alert, context, "destination.port", "dport", "dst_port"))
        sport_bucket = self._port_bucket(sport)
        dport_bucket = self._port_bucket(dport)

        return [
            f"sip:{sip}",
            f"dip:{dip}",
            f"proto:{str(proto).lower()}",
            f"rule:{rule_name}",
            f"uri:{uri_template}",
            f"log_type:{log_type}",
            f"sport_bucket:{sport_bucket}",
            f"dport_bucket:{dport_bucket}",
            f"sip_dip:{sip}->{dip}",
            f"rule_proto:{rule_name}|{str(proto).lower()}",
        ]

    def _port_bucket(self, port: int) -> str:
        if port <= 0:
            return "unknown"
        if port < 1024:
            return "system"
        if port < 49152:
            return "registered"
        return "dynamic"

    def _first(self, raw_alert: dict[str, Any], context: dict[str, Any], *paths: str) -> str:
        for path in paths:
            value = self._lookup(raw_alert, path)
            if value is None:
                value = self._lookup(context, path)
            if value is not None and value != "":
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

    def _to_int(self, value: Any) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return -1
