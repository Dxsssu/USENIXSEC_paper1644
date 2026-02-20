from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import numpy as np

from .models import parse_datetime


@dataclass
class TemporalFeatureExtractor:
    dim: int = 16
    business_start_hour: int = 8
    business_end_hour: int = 18
    _last_seen_ts_by_key: dict[str, float] = field(default_factory=dict)

    def transform(self, raw_alert: dict[str, Any], context: dict[str, Any], key: str) -> np.ndarray:
        timestamp = self._extract_timestamp(raw_alert, context)
        hour = float(timestamp.hour)
        dow = float(timestamp.weekday())
        is_weekend = 1.0 if timestamp.weekday() >= 5 else 0.0
        is_business_hours = (
            1.0
            if self.business_start_hour <= timestamp.hour < self.business_end_hour and not is_weekend
            else 0.0
        )
        month = float(timestamp.month)
        quarter = float(((timestamp.month - 1) // 3) + 1)
        is_holiday = self._is_holiday(timestamp)

        current_ts = float(timestamp.timestamp())
        prev_ts = self._last_seen_ts_by_key.get(key)
        delta_s = 0.0 if prev_ts is None else max(current_ts - prev_ts, 0.0)
        self._last_seen_ts_by_key[key] = current_ts

        vector = np.zeros(self.dim, dtype=np.float32)
        base = [
            hour / 23.0,
            dow / 6.0,
            is_weekend,
            is_business_hours,
            (month - 1.0) / 11.0,
            (quarter - 1.0) / 3.0,
            is_holiday,
            min(delta_s / 86400.0, 7.0) / 7.0,
            min(current_ts / 2_000_000_000.0, 1.0),
        ]
        vector[: len(base)] = np.array(base, dtype=np.float32)
        return vector

    def _extract_timestamp(self, raw_alert: dict[str, Any], context: dict[str, Any]) -> datetime:
        candidates = (
            self._lookup(raw_alert, "@timestamp"),
            self._lookup(raw_alert, "timestamp"),
            self._lookup(context, "last_seen"),
            self._lookup(context, "first_seen"),
            datetime.now(tz=UTC),
        )
        for value in candidates:
            dt = parse_datetime(value)
            if dt is not None:
                return dt
        return datetime.now(tz=UTC)

    def _lookup(self, payload: dict[str, Any], dotted_path: str) -> Any:
        if dotted_path in payload:
            return payload[dotted_path]
        current: Any = payload
        for part in dotted_path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    def _is_holiday(self, timestamp: datetime) -> float:
        # Lightweight approximation to keep dependency-free behavior.
        month_day = (timestamp.month, timestamp.day)
        us_fixed_holidays = {(1, 1), (7, 4), (12, 25)}
        return 1.0 if month_day in us_fixed_holidays else 0.0
