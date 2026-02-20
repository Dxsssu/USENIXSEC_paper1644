from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import signal
import sys
import time
from pathlib import Path
from typing import Any, Callable

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from module_aggregation_filtering.config import (
    AggregationConfig as M1AggregationConfig,
    AssetConfig as M1AssetConfig,
    HistoryConfig as M1HistoryConfig,
    Module1Config,
    QueueConfig as M1QueueConfig,
    ScoringConfig as M1ScoringConfig,
)
from module_aggregation_filtering.pipeline import run_pipeline as run_module1
from module_alert_receiver.config import (
    ElasticConfig as ReceiverElasticConfig,
    ReceiverConfig,
    RedisConfig as ReceiverRedisConfig,
)
from module_alert_receiver.receiver import run_receiver
from module_business_logic_self_learning.config import (
    ElasticConfig as M2ElasticConfig,
    FeatureConfig as M2FeatureConfig,
    ModelConfig as M2ModelConfig,
    Module2Config,
    QueueConfig as M2QueueConfig,
    TrainConfig as M2TrainConfig,
)
from module_business_logic_self_learning.pipeline import run_pipeline as run_module2
from module_context_enhanced_llm.config import (
    CMDBConfig as M3CMDBConfig,
    ElasticConfig as M3ElasticConfig,
    ExternalConfig as M3ExternalConfig,
    LLMConfig as M3LLMConfig,
    Module3Config,
    QueueConfig as M3QueueConfig,
    ReasonerConfig as M3ReasonerConfig,
)
from module_context_enhanced_llm.pipeline import run_pipeline as run_module3


class ConnectivityError(RuntimeError):
    pass


def load_system_config(config_path: str) -> dict[str, Any]:
    path = Path(config_path)
    if not path.is_absolute():
        path = ROOT_DIR / path
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError("Top-level system config must be a JSON object.")
    return payload


def _get_obj(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"Config section '{key}' must be an object.")
    return value


def build_receiver_config(system_cfg: dict[str, Any]) -> ReceiverConfig:
    receiver_cfg = _get_obj(system_cfg, "receiver")
    elastic = ReceiverElasticConfig(**_get_obj(receiver_cfg, "elastic"))
    redis = ReceiverRedisConfig(**_get_obj(receiver_cfg, "redis"))
    return ReceiverConfig(elastic=elastic, redis=redis)


def build_module1_config(system_cfg: dict[str, Any]) -> Module1Config:
    m1_cfg = _get_obj(system_cfg, "module1")
    return Module1Config(
        queue=M1QueueConfig(**_get_obj(m1_cfg, "queue")),
        aggregation=M1AggregationConfig(**_get_obj(m1_cfg, "aggregation")),
        scoring=M1ScoringConfig(**_get_obj(m1_cfg, "scoring")),
        asset=M1AssetConfig(**_get_obj(m1_cfg, "asset")),
        history=M1HistoryConfig(**_get_obj(m1_cfg, "history")),
    )


def build_module2_config(system_cfg: dict[str, Any]) -> Module2Config:
    m2_cfg = _get_obj(system_cfg, "module2")
    return Module2Config(
        queue=M2QueueConfig(**_get_obj(m2_cfg, "queue")),
        elastic=M2ElasticConfig(**_get_obj(m2_cfg, "elastic")),
        model=M2ModelConfig(**_get_obj(m2_cfg, "model")),
        features=M2FeatureConfig(**_get_obj(m2_cfg, "features")),
        train=M2TrainConfig(**_get_obj(m2_cfg, "train")),
    )


def build_module3_config(system_cfg: dict[str, Any]) -> Module3Config:
    m3_cfg = _get_obj(system_cfg, "module3")
    return Module3Config(
        queue=M3QueueConfig(**_get_obj(m3_cfg, "queue")),
        llm=M3LLMConfig(**_get_obj(m3_cfg, "llm")),
        elastic=M3ElasticConfig(**_get_obj(m3_cfg, "elastic")),
        cmdb=M3CMDBConfig(**_get_obj(m3_cfg, "cmdb")),
        external=M3ExternalConfig(**_get_obj(m3_cfg, "external")),
        reasoner=M3ReasonerConfig(**_get_obj(m3_cfg, "reasoner")),
    )


def _start_process(target: Callable[..., None], name: str, args: tuple[Any, ...]) -> mp.Process:
    process = mp.Process(target=target, args=args, name=name)
    process.start()
    return process


def _ping_redis(url: str, timeout_s: float = 3.0) -> None:
    try:
        import redis
    except ImportError as exc:
        raise ConnectivityError("Missing dependency: redis") from exc
    try:
        client = redis.Redis.from_url(
            url,
            socket_connect_timeout=timeout_s,
            socket_timeout=timeout_s,
        )
        if not bool(client.ping()):
            raise ConnectivityError(f"Redis ping failed: {url}")
    except Exception as exc:
        raise ConnectivityError(f"Redis unreachable: {url}") from exc


def _ping_elastic(host: str, port: int, scheme: str, timeout_s: float = 5.0) -> None:
    try:
        from elasticsearch import Elasticsearch
    except ImportError as exc:
        raise ConnectivityError("Missing dependency: elasticsearch") from exc
    endpoint = f"{scheme}://{host}:{port}"
    try:
        client = Elasticsearch(endpoint, request_timeout=timeout_s)
        ok = bool(client.ping())
        client.close()
        if not ok:
            raise ConnectivityError(f"Elasticsearch ping failed: {endpoint}")
    except Exception as exc:
        raise ConnectivityError(f"Elasticsearch unreachable: {endpoint}") from exc


def validate_runtime_connectivity(command: str, system_cfg: dict[str, Any]) -> None:
    if command in {"run-all", "run-receiver"}:
        receiver_cfg = build_receiver_config(system_cfg)
        _ping_elastic(
            receiver_cfg.elastic.host,
            receiver_cfg.elastic.port,
            receiver_cfg.elastic.scheme,
            timeout_s=max(3.0, receiver_cfg.elastic.poll_interval_s),
        )
        _ping_redis(receiver_cfg.redis.url)

    if command in {"run-all", "run-module1"}:
        m1_cfg = build_module1_config(system_cfg)
        _ping_redis(m1_cfg.queue.redis_url)

    if command in {"run-all", "run-module2"}:
        m2_cfg = build_module2_config(system_cfg)
        _ping_redis(m2_cfg.queue.redis_url)
        if m2_cfg.elastic.enabled:
            _ping_elastic(
                m2_cfg.elastic.host,
                m2_cfg.elastic.port,
                m2_cfg.elastic.scheme,
                timeout_s=float(m2_cfg.elastic.request_timeout_s),
            )

    if command in {"run-all", "run-module3"}:
        m3_cfg = build_module3_config(system_cfg)
        _ping_redis(m3_cfg.queue.redis_url)
        _ping_elastic(
            m3_cfg.elastic.host,
            m3_cfg.elastic.port,
            m3_cfg.elastic.scheme,
            timeout_s=float(m3_cfg.elastic.timeout_s),
        )


def run_all(system_cfg: dict[str, Any]) -> None:
    receiver_cfg = build_receiver_config(system_cfg)
    module1_cfg = build_module1_config(system_cfg)
    module2_cfg = build_module2_config(system_cfg)
    module3_cfg = build_module3_config(system_cfg)

    processes = [
        _start_process(run_receiver, "receiver", (receiver_cfg,)),
        _start_process(run_module1, "module1", (module1_cfg,)),
        _start_process(run_module2, "module2", (module2_cfg,)),
        _start_process(run_module3, "module3", (module3_cfg,)),
    ]

    def _stop_all(*_: Any) -> None:
        for proc in processes:
            if proc.is_alive():
                proc.terminate()
        for proc in processes:
            proc.join(timeout=5)
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _stop_all)
    signal.signal(signal.SIGTERM, _stop_all)

    try:
        while True:
            dead = [proc.name for proc in processes if not proc.is_alive()]
            if dead:
                print(f"Detected exited subprocesses: {dead}. Stopping all.")
                _stop_all()
            time.sleep(2)
    except KeyboardInterrupt:
        _stop_all()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SOCRATES unified pipeline entrypoint")
    parser.add_argument(
        "--config",
        default="config/system_config.json",
        help="Path to unified JSON config file.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run-all", help="Run receiver + module1 + module2 + module3.")
    subparsers.add_parser("run-receiver", help="Run alert receiver only.")
    subparsers.add_parser("run-module1", help="Run module1 only.")
    subparsers.add_parser("run-module2", help="Run module2 only.")
    subparsers.add_parser("run-module3", help="Run module3 only.")
    subparsers.add_parser("train-module2", help="Train module2 XGBoost model.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    system_cfg = load_system_config(args.config)
    if args.command.startswith("run-"):
        try:
            validate_runtime_connectivity(args.command, system_cfg)
        except ConnectivityError as exc:
            raise SystemExit(f"[config-connectivity-check] {exc}") from exc

    if args.command == "run-all":
        run_all(system_cfg)
        return
    if args.command == "run-receiver":
        run_receiver(build_receiver_config(system_cfg))
        return
    if args.command == "run-module1":
        run_module1(build_module1_config(system_cfg))
        return
    if args.command == "run-module2":
        run_module2(build_module2_config(system_cfg))
        return
    if args.command == "run-module3":
        run_module3(build_module3_config(system_cfg))
        return
    if args.command == "train-module2":
        from module_business_logic_self_learning.trainer import train_from_jsonl

        summary = train_from_jsonl(build_module2_config(system_cfg))
        print(
            "trained",
            f"model={summary.model_path}",
            f"train_rows={summary.train_rows}",
            f"valid_rows={summary.valid_rows}",
            f"positive_ratio={summary.positive_ratio:.4f}",
            f"threshold={summary.threshold:.4f}",
        )
        return

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
