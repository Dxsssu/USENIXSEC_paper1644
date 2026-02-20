from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    args_schema: dict[str, Any]


def build_tool_specs() -> list[ToolSpec]:
    query_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "object", "description": "Elasticsearch DSL query"},
            "size": {"type": "integer", "minimum": 1, "maximum": 200},
        },
        "required": ["query"],
    }
    return [
        ToolSpec("search_waf_logs", "Search WAF logs using Elasticsearch DSL.", query_schema),
        ToolSpec(
            "search_tianyan_alarm_logs",
            "Search Tianyan-Alarm logs using Elasticsearch DSL.",
            query_schema,
        ),
        ToolSpec("search_zhongzi_logs", "Search Zhongzi logs using Elasticsearch DSL.", query_schema),
        ToolSpec("search_nginx_logs", "Search Nginx logs using Elasticsearch DSL.", query_schema),
        ToolSpec("search_huorong_logs", "Search Huorong logs using Elasticsearch DSL.", query_schema),
        ToolSpec(
            "get_cmdb_asset",
            "Query CMDB asset info by IP.",
            {
                "type": "object",
                "properties": {
                    "ip": {"type": "string"},
                },
                "required": ["ip"],
            },
        ),
        ToolSpec(
            "virustotal_ip_reputation",
            "Query VirusTotal IP reputation.",
            {
                "type": "object",
                "properties": {
                    "ip": {"type": "string"},
                },
                "required": ["ip"],
            },
        ),
        ToolSpec(
            "cve_search",
            "Query CVE details by keyword or CVE ID.",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
        ),
    ]
