from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from elasticsearch import Elasticsearch

from .config import ElasticConfig


@dataclass
class ElasticRawAlertFetcher:
    cfg: ElasticConfig
    client: Elasticsearch | None = None

    def __post_init__(self) -> None:
        if not self.cfg.enabled:
            self.client = None
            return
        self.client = Elasticsearch(
            f"{self.cfg.scheme}://{self.cfg.host}:{self.cfg.port}",
            request_timeout=self.cfg.request_timeout_s,
        )

    def fetch_by_reference_ids(self, reference_ids: list[str]) -> list[dict[str, Any]]:
        if self.client is None or not reference_ids:
            return []

        results: list[dict[str, Any]] = []
        for offset in range(0, len(reference_ids), self.cfg.batch_size):
            batch = reference_ids[offset : offset + self.cfg.batch_size]
            query = {
                "query": {
                    "bool": {
                        "should": [
                            {"terms": {"event.id": batch}},
                            {"terms": {"id": batch}},
                            {"terms": {"alert_id": batch}},
                            {"ids": {"values": batch}},
                        ],
                        "minimum_should_match": 1,
                    }
                },
                "size": len(batch),
            }
            try:
                resp = self.client.search(index=self.cfg.index, body=query)
            except Exception:
                continue
            hits = resp.get("hits", {}).get("hits", [])
            for hit in hits:
                src = hit.get("_source")
                if isinstance(src, dict):
                    results.append(src)
        return results
