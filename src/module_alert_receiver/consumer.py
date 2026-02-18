from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .buffer import RedisAlertBuffer
from .config import RedisConfig


@dataclass
class AlertConsumer:
    buffer: RedisAlertBuffer

    def consume(
        self,
        handler: Callable[[dict[str, Any]], None],
        timeout_s: int = 1,
    ) -> None:
        client = self.buffer.connect()
        while True:
            alert = self.buffer.pop(client, timeout_s=timeout_s)
            if alert is None:
                continue
            handler(alert)


def print_handler(alert: dict[str, Any]) -> None:
    alert_id = alert.get("id") or alert.get("alert_id") or "unknown"
    print(f"alert={alert_id} keys={list(alert.keys())[:5]}")


def run_consumer(config: RedisConfig | None = None) -> None:
    redis_cfg = config or RedisConfig.from_env()
    buffer = RedisAlertBuffer(
        url=redis_cfg.url,
        queue_key=redis_cfg.queue_key,
        maxlen=redis_cfg.maxlen,
    )
    consumer = AlertConsumer(buffer=buffer)
    consumer.consume(print_handler)


if __name__ == "__main__":
    run_consumer()
