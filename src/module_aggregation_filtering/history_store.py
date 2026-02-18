from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass
class RedisHistoryStore:
    key_prefix: str
    history_days: int = 14

    @property
    def _days_index_key(self) -> str:
        return f"{self.key_prefix}:days"

    def get_14d_daily_avg(self, redis_client: Any, bucket_key: str, now: datetime) -> float:
        start_day = datetime(now.year, now.month, now.day, tzinfo=UTC) - timedelta(days=self.history_days - 1)
        end_day = datetime(now.year, now.month, now.day, tzinfo=UTC)
        day_keys = redis_client.zrangebyscore(
            self._days_index_key,
            min=start_day.timestamp(),
            max=end_day.timestamp(),
        )
        if not day_keys:
            return 0.0

        pipe = redis_client.pipeline()
        for day_key in day_keys:
            pipe.hget(self._daily_hash_key(day_key), bucket_key)
        values = pipe.execute()
        total = sum(int(value or 0) for value in values)
        return total / max(len(day_keys), 1)

    def record(self, redis_client: Any, bucket_key: str, count: int, event_time: datetime) -> None:
        day_key = event_time.date().isoformat()
        day_epoch = datetime(event_time.year, event_time.month, event_time.day, tzinfo=UTC).timestamp()
        hash_key = self._daily_hash_key(day_key)

        pipe = redis_client.pipeline()
        pipe.hincrby(hash_key, bucket_key, count)
        pipe.zadd(self._days_index_key, {day_key: day_epoch})
        pipe.expire(hash_key, int((self.history_days + 2) * 86400))
        pipe.execute()

        self._prune_old_days(redis_client, event_time)

    def _prune_old_days(self, redis_client: Any, now: datetime) -> None:
        cutoff = datetime(now.year, now.month, now.day, tzinfo=UTC) - timedelta(days=self.history_days)
        stale_days = redis_client.zrangebyscore(self._days_index_key, min="-inf", max=cutoff.timestamp())
        if not stale_days:
            return
        pipe = redis_client.pipeline()
        for day_key in stale_days:
            pipe.delete(self._daily_hash_key(day_key))
        pipe.zremrangebyscore(self._days_index_key, min="-inf", max=cutoff.timestamp())
        pipe.execute()

    def _daily_hash_key(self, day_key: str) -> str:
        return f"{self.key_prefix}:{day_key}"
