from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

import numpy as np

WORD_RE = re.compile(r"[A-Za-z0-9_]{2,}")


def _hash_to_bin(text: str, dim: int) -> int:
    digest = hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()
    return int(digest[:8], 16) % dim


@dataclass
class SemanticFeatureExtractor:
    dim: int = 48

    def transform(self, raw_alert: dict[str, Any], context: dict[str, Any]) -> np.ndarray:
        text = self._build_semantic_text(raw_alert, context)
        tokens = WORD_RE.findall(text.lower())
        vector = np.zeros(self.dim, dtype=np.float32)
        if not tokens:
            return vector
        for token in tokens:
            idx = _hash_to_bin(token, self.dim)
            vector[idx] += 1.0
        vector /= max(float(np.linalg.norm(vector)), 1.0)
        return vector

    def _build_semantic_text(self, raw_alert: dict[str, Any], context: dict[str, Any]) -> str:
        fields = [
            self._first(raw_alert, context, "payload"),
            self._first(raw_alert, context, "message"),
            self._first(raw_alert, context, "http.request.body.content"),
            self._first(raw_alert, context, "http.request.body"),
            self._first(raw_alert, context, "uri_template"),
            self._first(raw_alert, context, "url.path"),
            self._first(raw_alert, context, "rule_name"),
            self._first(raw_alert, context, "log_type"),
        ]
        return " ".join(item for item in fields if item)

    def _first(self, raw_alert: dict[str, Any], context: dict[str, Any], path: str) -> str:
        value = self._lookup(raw_alert, path)
        if value is None:
            value = self._lookup(context, path)
        return str(value) if value is not None else ""

    def _lookup(self, payload: dict[str, Any], dotted_path: str) -> Any:
        if dotted_path in payload:
            return payload[dotted_path]
        current: Any = payload
        for part in dotted_path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current
