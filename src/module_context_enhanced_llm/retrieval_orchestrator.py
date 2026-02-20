from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import ToolCall, ToolResult
from .tools_external import ExternalTools
from .tools_internal import InternalTools

INTERNAL_QUERY_TOOLS = {
    "search_waf_logs",
    "search_tianyan_alarm_logs",
    "search_zhongzi_logs",
    "search_nginx_logs",
    "search_huorong_logs",
}


@dataclass
class RetrievalOrchestrator:
    internal_tools: InternalTools
    external_tools: ExternalTools
    tool_result_max_items: int = 30

    def execute(self, call: ToolCall) -> ToolResult:
        name = call.tool
        args = call.args
        if name in INTERNAL_QUERY_TOOLS:
            query = args.get("query")
            size = args.get("size")
            if not isinstance(query, dict):
                query = {"match_all": {}}
            return self._trim_rows(getattr(self.internal_tools, name)(query=query, size=size))

        if name == "get_cmdb_asset":
            ip = str(args.get("ip", "")).strip()
            if not ip:
                return ToolResult(tool=name, success=False, summary="Missing ip argument.", error="missing_ip")
            return self.internal_tools.get_cmdb_asset(ip=ip)

        if name == "virustotal_ip_reputation":
            ip = str(args.get("ip", "")).strip()
            if not ip:
                return ToolResult(tool=name, success=False, summary="Missing ip argument.", error="missing_ip")
            return self.external_tools.virustotal_ip_reputation(ip=ip)

        if name == "cve_search":
            query = str(args.get("query", "")).strip()
            if not query:
                return ToolResult(tool=name, success=False, summary="Missing query argument.", error="missing_query")
            return self.external_tools.cve_search(query=query)

        return ToolResult(
            tool=name,
            success=False,
            summary=f"Unknown tool: {name}",
            error="unknown_tool",
        )

    def _trim_rows(self, result: ToolResult) -> ToolResult:
        rows = result.data.get("rows")
        if isinstance(rows, list) and len(rows) > self.tool_result_max_items:
            result.data["rows"] = rows[: self.tool_result_max_items]
            result.data["trimmed"] = True
            result.data["trimmed_from"] = len(rows)
        return result
