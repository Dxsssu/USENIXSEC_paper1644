from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Iterable

from elasticsearch import Elasticsearch

from .buffer import RedisAlertBuffer
from .config import ElasticConfig, ReceiverConfig


@dataclass
class ElasticAlertReceiver:
    client: Elasticsearch
    index: str
    sort_field: str = "@timestamp"
    batch_size: int = 200
    poll_interval_s: float = 2.0
    start_time: str | None = None

    def _build_query(self) -> dict[str, Any]:
        if not self.start_time:
            return {"match_all": {}}
        return {"range": {self.sort_field: {"gte": self.start_time}}}

    def stream(self) -> Iterable[dict[str, Any]]:
        query = self._build_query()
        search_after: list[Any] | None = None
        sort = [{self.sort_field: "asc"}, {"_shard_doc": "asc"}]

        while True:
            body: dict[str, Any] = {"query": query, "sort": sort, "size": self.batch_size}
            if search_after:
                body["search_after"] = search_after

            resp = self.client.search(index=self.index, body=body)
            hits = resp.get("hits", {}).get("hits", [])
            if not hits:
                time.sleep(self.poll_interval_s)
                continue

            for hit in hits:
                search_after = hit.get("sort")
                yield hit.get("_source", {})


def run_receiver(config: ReceiverConfig) -> None:
    es_cfg: ElasticConfig = config.elastic
    es = Elasticsearch(f"{es_cfg.scheme}://{es_cfg.host}:{es_cfg.port}")
    receiver = ElasticAlertReceiver(
        client=es,
        index=es_cfg.index,
        sort_field=es_cfg.sort_field,
        batch_size=es_cfg.batch_size,
        poll_interval_s=es_cfg.poll_interval_s,
        start_time=es_cfg.start_time,
    )

    buffer = RedisAlertBuffer(
        url=config.redis.url,
        queue_key=config.redis.queue_key,
        maxlen=config.redis.maxlen,
    )
    redis_client = buffer.connect()

    for alert in receiver.stream():
        buffer.push(redis_client, alert)
