from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import redis


@dataclass
class RedisAlertBuffer:
    url: str
    queue_key: str
    maxlen: int | None = None

    def connect(self) -> redis.Redis:
        return redis.Redis.from_url(self.url, decode_responses=True)

    def push(self, client: redis.Redis, alert: dict[str, Any]) -> None:
        payload = json.dumps(alert, ensure_ascii=True)
        if self.maxlen is None:
            client.rpush(self.queue_key, payload)
            return

        pipe = client.pipeline()
        pipe.rpush(self.queue_key, payload)
        pipe.ltrim(self.queue_key, -self.maxlen, -1)
        pipe.execute()

    def pop(self, client: redis.Redis, timeout_s: int = 1) -> dict[str, Any] | None:
        item = client.blpop(self.queue_key, timeout=timeout_s)
        if not item:
            return None
        _key, payload = item
        return json.loads(payload)
