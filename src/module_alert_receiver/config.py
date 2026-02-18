from __future__ import annotations

from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class ElasticConfig:
    host: str = "10.132.99.60"
    port: int = 9200
    scheme: str = "http"
    index: str = "alerts-*"
    sort_field: str = "@timestamp"
    batch_size: int = 200
    poll_interval_s: float = 2.0
    start_time: str | None = None

    @classmethod
    def from_env(cls) -> "ElasticConfig":
        return cls(
            host=getenv("ES_HOST", cls.host),
            port=int(getenv("ES_PORT", str(cls.port))),
            scheme=getenv("ES_SCHEME", cls.scheme),
            index=getenv("ES_INDEX", cls.index),
            sort_field=getenv("ES_SORT_FIELD", cls.sort_field),
            batch_size=int(getenv("ES_BATCH_SIZE", str(cls.batch_size))),
            poll_interval_s=float(getenv("ES_POLL_INTERVAL_S", str(cls.poll_interval_s))),
            start_time=getenv("ES_START_TIME", cls.start_time or "") or None,
        )


@dataclass(frozen=True)
class RedisConfig:
    url: str = "redis://localhost:6379/0"
    queue_key: str = "socrates:alerts"
    maxlen: int | None = None

    @classmethod
    def from_env(cls) -> "RedisConfig":
        maxlen_env = getenv("REDIS_QUEUE_MAXLEN", "")
        maxlen = int(maxlen_env) if maxlen_env else None
        return cls(
            url=getenv("REDIS_URL", cls.url),
            queue_key=getenv("REDIS_QUEUE_KEY", cls.queue_key),
            maxlen=maxlen,
        )


@dataclass(frozen=True)
class ReceiverConfig:
    elastic: ElasticConfig
    redis: RedisConfig

    @classmethod
    def from_env(cls) -> "ReceiverConfig":
        return cls(elastic=ElasticConfig.from_env(), redis=RedisConfig.from_env())
