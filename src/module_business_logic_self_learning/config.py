from __future__ import annotations

from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class QueueConfig:
    redis_url: str = "redis://localhost:6379/0"
    input_key: str = "socrates:alerts:aggregated"
    output_key: str = "socrates:alerts:investigation"
    suppressed_key: str = "socrates:alerts:business_suppressed"
    output_maxlen: int | None = None
    suppressed_maxlen: int | None = None
    pop_timeout_s: int = 1

    @classmethod
    def from_env(cls) -> "QueueConfig":
        output_maxlen_env = getenv("M2_OUTPUT_MAXLEN", "")
        suppressed_maxlen_env = getenv("M2_SUPPRESSED_MAXLEN", "")
        return cls(
            redis_url=getenv("M2_REDIS_URL", cls.redis_url),
            input_key=getenv("M2_INPUT_KEY", cls.input_key),
            output_key=getenv("M2_OUTPUT_KEY", cls.output_key),
            suppressed_key=getenv("M2_SUPPRESSED_KEY", cls.suppressed_key),
            output_maxlen=int(output_maxlen_env) if output_maxlen_env else None,
            suppressed_maxlen=int(suppressed_maxlen_env) if suppressed_maxlen_env else None,
            pop_timeout_s=int(getenv("M2_POP_TIMEOUT_S", str(cls.pop_timeout_s))),
        )


@dataclass(frozen=True)
class ElasticConfig:
    enabled: bool = True
    host: str = "10.132.99.60"
    port: int = 9200
    scheme: str = "http"
    index: str = "alerts-*"
    request_timeout_s: int = 5
    batch_size: int = 200

    @classmethod
    def from_env(cls) -> "ElasticConfig":
        enabled = getenv("M2_ES_ENABLED", "true").strip().lower() not in ("0", "false", "no")
        return cls(
            enabled=enabled,
            host=getenv("M2_ES_HOST", cls.host),
            port=int(getenv("M2_ES_PORT", str(cls.port))),
            scheme=getenv("M2_ES_SCHEME", cls.scheme),
            index=getenv("M2_ES_INDEX", cls.index),
            request_timeout_s=int(getenv("M2_ES_TIMEOUT_S", str(cls.request_timeout_s))),
            batch_size=int(getenv("M2_ES_BATCH_SIZE", str(cls.batch_size))),
        )


@dataclass(frozen=True)
class ModelConfig:
    model_path: str = "models/business_self_learning_xgboost.pkl"
    decision_threshold: float = 0.72
    min_instance_count: int = 2

    @classmethod
    def from_env(cls) -> "ModelConfig":
        return cls(
            model_path=getenv("M2_MODEL_PATH", cls.model_path),
            decision_threshold=float(getenv("M2_DECISION_THRESHOLD", str(cls.decision_threshold))),
            min_instance_count=int(getenv("M2_MIN_INSTANCE_COUNT", str(cls.min_instance_count))),
        )


@dataclass(frozen=True)
class FeatureConfig:
    structural_dim: int = 32
    semantic_dim: int = 48
    temporal_dim: int = 16
    business_hours_start: int = 8
    business_hours_end: int = 18

    @classmethod
    def from_env(cls) -> "FeatureConfig":
        return cls(
            structural_dim=int(getenv("M2_STRUCTURAL_DIM", str(cls.structural_dim))),
            semantic_dim=int(getenv("M2_SEMANTIC_DIM", str(cls.semantic_dim))),
            temporal_dim=int(getenv("M2_TEMPORAL_DIM", str(cls.temporal_dim))),
            business_hours_start=int(getenv("M2_BIZ_START", str(cls.business_hours_start))),
            business_hours_end=int(getenv("M2_BIZ_END", str(cls.business_hours_end))),
        )


@dataclass(frozen=True)
class TrainConfig:
    train_jsonl_path: str = "data/module2_train.jsonl"
    train_window_days: int = 14
    test_ratio: float = 0.2
    random_seed: int = 42
    n_estimators: int = 300
    max_depth: int = 6
    learning_rate: float = 0.05
    subsample: float = 0.85
    colsample_bytree: float = 0.85

    @classmethod
    def from_env(cls) -> "TrainConfig":
        return cls(
            train_jsonl_path=getenv("M2_TRAIN_JSONL_PATH", cls.train_jsonl_path),
            train_window_days=int(getenv("M2_TRAIN_WINDOW_DAYS", str(cls.train_window_days))),
            test_ratio=float(getenv("M2_TEST_RATIO", str(cls.test_ratio))),
            random_seed=int(getenv("M2_RANDOM_SEED", str(cls.random_seed))),
            n_estimators=int(getenv("M2_N_ESTIMATORS", str(cls.n_estimators))),
            max_depth=int(getenv("M2_MAX_DEPTH", str(cls.max_depth))),
            learning_rate=float(getenv("M2_LEARNING_RATE", str(cls.learning_rate))),
            subsample=float(getenv("M2_SUBSAMPLE", str(cls.subsample))),
            colsample_bytree=float(getenv("M2_COLSAMPLE_BYTREE", str(cls.colsample_bytree))),
        )


@dataclass(frozen=True)
class Module2Config:
    queue: QueueConfig
    elastic: ElasticConfig
    model: ModelConfig
    features: FeatureConfig
    train: TrainConfig

    @classmethod
    def from_env(cls) -> "Module2Config":
        return cls(
            queue=QueueConfig.from_env(),
            elastic=ElasticConfig.from_env(),
            model=ModelConfig.from_env(),
            features=FeatureConfig.from_env(),
            train=TrainConfig.from_env(),
        )
