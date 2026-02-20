from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
from elasticsearch import Elasticsearch

from .config import CMDBConfig, ElasticConfig
from .models import ToolResult


@dataclass
class InternalTools:
    es_cfg: ElasticConfig
    cmdb_cfg: CMDBConfig

    def __post_init__(self) -> None:
        self._es = Elasticsearch(
            f"{self.es_cfg.scheme}://{self.es_cfg.host}:{self.es_cfg.port}",
            request_timeout=self.es_cfg.timeout_s,
        )

    def search_waf_logs(self, query: dict[str, Any], size: int | None = None) -> ToolResult:
        return self._search_es("search_waf_logs", self.es_cfg.index_waf, query, size)

    def search_tianyan_alarm_logs(self, query: dict[str, Any], size: int | None = None) -> ToolResult:
        return self._search_es("search_tianyan_alarm_logs", self.es_cfg.index_tianyan_alarm, query, size)

    def search_zhongzi_logs(self, query: dict[str, Any], size: int | None = None) -> ToolResult:
        return self._search_es("search_zhongzi_logs", self.es_cfg.index_zhongzi, query, size)

    def search_nginx_logs(self, query: dict[str, Any], size: int | None = None) -> ToolResult:
        return self._search_es("search_nginx_logs", self.es_cfg.index_nginx, query, size)

    def search_huorong_logs(self, query: dict[str, Any], size: int | None = None) -> ToolResult:
        return self._search_es("search_huorong_logs", self.es_cfg.index_huorong, query, size)

    def get_cmdb_asset(self, ip: str) -> ToolResult:
        if not self.cmdb_cfg.base_url:
            return ToolResult(
                tool="get_cmdb_asset",
                success=False,
                summary="CMDB base URL is not configured.",
                error="cmdb_base_url_missing",
            )
        headers = {"Accept": "application/json"}
        if self.cmdb_cfg.api_key:
            headers["Authorization"] = f"Bearer {self.cmdb_cfg.api_key}"
        try:
            response = requests.get(
                self.cmdb_cfg.base_url,
                params={"ip": ip},
                headers=headers,
                timeout=self.cmdb_cfg.timeout_s,
            )
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                data = response.json()
            else:
                data = {"raw_text": response.text[:4000]}
            return ToolResult(
                tool="get_cmdb_asset",
                success=response.ok,
                query={"ip": ip},
                summary=f"CMDB query returned status={response.status_code}",
                data={"status_code": response.status_code, "result": data},
                error=None if response.ok else f"http_{response.status_code}",
            )
        except Exception as exc:
            return ToolResult(
                tool="get_cmdb_asset",
                success=False,
                query={"ip": ip},
                summary="CMDB query failed.",
                error=str(exc),
            )

    def _search_es(self, tool_name: str, index: str, query: dict[str, Any], size: int | None) -> ToolResult:
        final_size = int(size or self.es_cfg.default_size)
        final_size = max(1, min(final_size, 200))
        body = {"query": query, "size": final_size}
        try:
            resp = self._es.search(index=index, body=body)
            hits = resp.get("hits", {}).get("hits", [])
            rows = [item.get("_source", {}) for item in hits if isinstance(item.get("_source"), dict)]
            return ToolResult(
                tool=tool_name,
                success=True,
                query=body,
                summary=f"{tool_name} returned {len(rows)} rows from index={index}.",
                data={"total": len(rows), "rows": rows},
            )
        except Exception as exc:
            return ToolResult(
                tool=tool_name,
                success=False,
                query=body,
                summary=f"{tool_name} failed.",
                error=str(exc),
            )
