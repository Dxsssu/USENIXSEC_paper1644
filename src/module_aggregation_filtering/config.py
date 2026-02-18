from __future__ import annotations

from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class QueueConfig:
    redis_url: str = "redis://localhost:6379/0"
    input_key: str = "socrates:alerts"
    output_key: str = "socrates:alerts:aggregated"
    suppressed_key: str = "socrates:alerts:suppressed"
    output_maxlen: int | None = None
    suppressed_maxlen: int | None = None

    @classmethod
    def from_env(cls) -> "QueueConfig":
        output_maxlen_env = getenv("AGGR_OUTPUT_MAXLEN", "")
        suppressed_maxlen_env = getenv("AGGR_SUPPRESSED_MAXLEN", "")
        return cls(
            redis_url=getenv("AGGR_REDIS_URL", cls.redis_url),
            input_key=getenv("AGGR_INPUT_KEY", cls.input_key),
            output_key=getenv("AGGR_OUTPUT_KEY", cls.output_key),
            suppressed_key=getenv("AGGR_SUPPRESSED_KEY", cls.suppressed_key),
            output_maxlen=int(output_maxlen_env) if output_maxlen_env else None,
            suppressed_maxlen=int(suppressed_maxlen_env) if suppressed_maxlen_env else None,
        )


@dataclass(frozen=True)
class AggregationConfig:
    window_s: int = 300
    flush_interval_s: float = 1.0
    pop_timeout_s: int = 1
    max_ref_ids: int = 200
    history_days: int = 14

    @classmethod
    def from_env(cls) -> "AggregationConfig":
        return cls(
            window_s=int(getenv("AGGR_WINDOW_S", str(cls.window_s))),
            flush_interval_s=float(getenv("AGGR_FLUSH_INTERVAL_S", str(cls.flush_interval_s))),
            pop_timeout_s=int(getenv("AGGR_POP_TIMEOUT_S", str(cls.pop_timeout_s))),
            max_ref_ids=int(getenv("AGGR_MAX_REF_IDS", str(cls.max_ref_ids))),
            history_days=int(getenv("AGGR_HISTORY_DAYS", str(cls.history_days))),
        )


@dataclass(frozen=True)
class ScoringConfig:
    threshold: float = 50.0
    w_freq: float = 0.35
    w_rule: float = 0.25
    w_ctx: float = 0.20
    w_rare: float = 0.20

    @classmethod
    def from_env(cls) -> "ScoringConfig":
        return cls(
            threshold=float(getenv("AGGR_SCORE_THRESHOLD", str(cls.threshold))),
            w_freq=float(getenv("AGGR_W_FREQ", str(cls.w_freq))),
            w_rule=float(getenv("AGGR_W_RULE", str(cls.w_rule))),
            w_ctx=float(getenv("AGGR_W_CTX", str(cls.w_ctx))),
            w_rare=float(getenv("AGGR_W_RARE", str(cls.w_rare))),
        )


@dataclass(frozen=True)
class AssetConfig:
    table_path: str = "config/assets_static.json"

    @classmethod
    def from_env(cls) -> "AssetConfig":
        return cls(table_path=getenv("AGGR_ASSET_TABLE_PATH", cls.table_path))


@dataclass(frozen=True)
class HistoryConfig:
    key_prefix: str = "socrates:aggr:hist"

    @classmethod
    def from_env(cls) -> "HistoryConfig":
        return cls(key_prefix=getenv("AGGR_HISTORY_PREFIX", cls.key_prefix))


@dataclass(frozen=True)
class Module1Config:
    queue: QueueConfig
    aggregation: AggregationConfig
    scoring: ScoringConfig
    asset: AssetConfig
    history: HistoryConfig

    @classmethod
    def from_env(cls) -> "Module1Config":
        return cls(
            queue=QueueConfig.from_env(),
            aggregation=AggregationConfig.from_env(),
            scoring=ScoringConfig.from_env(),
            asset=AssetConfig.from_env(),
            history=HistoryConfig.from_env(),
        )
