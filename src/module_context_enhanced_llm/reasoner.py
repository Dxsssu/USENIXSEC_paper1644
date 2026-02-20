from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .config import ReasonerConfig
from .llm_client import Qwen32BClient
from .models import InvestigationAlert, InvestigationVerdict, ToolCall, ToolResult, utc_now_iso
from .prompt_loader import PromptBundle
from .retrieval_orchestrator import RetrievalOrchestrator
from .tool_registry import build_tool_specs


@dataclass
class InvestigationReasoner:
    llm: Qwen32BClient
    prompts: PromptBundle
    orchestrator: RetrievalOrchestrator
    cfg: ReasonerConfig

    def investigate(self, alert: InvestigationAlert) -> InvestigationVerdict:
        started_at = utc_now_iso()
        started_ns = datetime.now().timestamp()

        plan_calls = self._plan_tool_calls(alert)
        if not plan_calls:
            plan_calls = self._fallback_tool_calls(alert)

        tool_results: list[ToolResult] = []
        for call in plan_calls[: self.cfg.max_tool_iterations]:
            result = self.orchestrator.execute(call)
            summarized = self._summarize_tool_result(alert, result)
            tool_results.append(summarized)

        verdict_data = self._final_reasoning(alert, tool_results)
        finished_at = utc_now_iso()
        duration_ms = int((datetime.now().timestamp() - started_ns) * 1000)

        verdict = self._normalize_verdict(verdict_data)
        return InvestigationVerdict(
            verdict=verdict["verdict"],
            severity=verdict["severity"],
            confidence=verdict["confidence"],
            reasoning_summary=verdict["reasoning_summary"],
            evidence=verdict["evidence"],
            tool_trace=[item.compact() for item in tool_results],
            recommended_action=verdict["recommended_action"],
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
        )

    def _plan_tool_calls(self, alert: InvestigationAlert) -> list[ToolCall]:
        fallback = {"tool_calls": []}
        tool_specs = [spec.__dict__ for spec in build_tool_specs()]
        prompt = (
            f"{self.prompts.system_prompt}\n\n"
            f"{self.prompts.planning_prompt}\n\n"
            f"ALERT:\n{json.dumps(alert.brief(), ensure_ascii=False)}\n\n"
            f"TOOLS:\n{json.dumps(tool_specs, ensure_ascii=False)}\n"
        )
        plan_json = self.llm.generate_json(prompt, fallback=fallback)
        calls = plan_json.get("tool_calls", [])
        if not isinstance(calls, list):
            return []
        parsed: list[ToolCall] = []
        allowed = {spec.name for spec in build_tool_specs()}
        for item in calls:
            if not isinstance(item, dict):
                continue
            tool_name = str(item.get("tool", "")).strip()
            if tool_name not in allowed:
                continue
            args = item.get("args", {})
            if not isinstance(args, dict):
                args = {}
            parsed.append(
                ToolCall(
                    tool=tool_name,
                    args=args,
                    rationale=str(item.get("rationale", "")),
                )
            )
        return parsed

    def _fallback_tool_calls(self, alert: InvestigationAlert) -> list[ToolCall]:
        brief = alert.brief()
        sip = str(brief.get("sip", "")).strip()
        dip = str(brief.get("dip", "")).strip()
        rule_name = str(brief.get("rule_name", "")).strip()
        calls: list[ToolCall] = []
        if dip:
            calls.append(ToolCall(tool="get_cmdb_asset", args={"ip": dip}, rationale="asset context"))
        if sip:
            calls.append(ToolCall(tool="virustotal_ip_reputation", args={"ip": sip}, rationale="source reputation"))
        query = {"bool": {"must": [{"match": {"rule_name": rule_name}}]}} if rule_name else {"match_all": {}}
        calls.append(ToolCall(tool="search_waf_logs", args={"query": query, "size": 30}, rationale="waf context"))
        if rule_name and "CVE-" in rule_name.upper():
            calls.append(ToolCall(tool="cve_search", args={"query": rule_name}, rationale="cve enrichment"))
        return calls

    def _summarize_tool_result(self, alert: InvestigationAlert, result: ToolResult) -> ToolResult:
        fallback = {"summary": result.summary, "signals": []}
        prompt = (
            f"{self.prompts.system_prompt}\n\n"
            f"{self.prompts.tool_summary_prompt}\n\n"
            f"ALERT:\n{json.dumps(alert.brief(), ensure_ascii=False)}\n\n"
            f"TOOL_RESULT:\n{json.dumps(result.compact(), ensure_ascii=False)}\n"
        )
        summary_json = self.llm.generate_json(prompt, fallback=fallback)
        summary = str(summary_json.get("summary", result.summary)).strip()
        result.summary = summary if summary else result.summary
        signals = summary_json.get("signals", [])
        if isinstance(signals, list):
            result.data["signals"] = signals[:20]
        return result

    def _final_reasoning(self, alert: InvestigationAlert, tool_results: list[ToolResult]) -> dict[str, Any]:
        fallback = {
            "verdict": "INCONCLUSIVE",
            "severity": "MEDIUM",
            "confidence": 0.4,
            "reasoning_summary": "Insufficient evidence for a definitive decision.",
            "evidence": [],
            "recommended_action": "manual_review",
        }
        payload = [item.compact() for item in tool_results]
        prompt = (
            f"{self.prompts.system_prompt}\n\n"
            f"{self.prompts.final_prompt}\n\n"
            f"ALERT:\n{json.dumps(alert.brief(), ensure_ascii=False)}\n\n"
            f"TOOL_SUMMARIES:\n{json.dumps(payload, ensure_ascii=False)}\n"
        )
        return self.llm.generate_json(prompt, fallback=fallback)

    def _normalize_verdict(self, data: dict[str, Any]) -> dict[str, Any]:
        verdict = str(data.get("verdict", "INCONCLUSIVE")).upper()
        if verdict not in {"MALICIOUS", "BENIGN", "SUSPICIOUS", "INCONCLUSIVE"}:
            verdict = "INCONCLUSIVE"
        severity = str(data.get("severity", "MEDIUM")).upper()
        if severity not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            severity = "MEDIUM"
        try:
            confidence = float(data.get("confidence", 0.4))
        except (TypeError, ValueError):
            confidence = 0.4
        confidence = max(0.0, min(confidence, 1.0))
        evidence = data.get("evidence", [])
        if not isinstance(evidence, list):
            evidence = []
        return {
            "verdict": verdict,
            "severity": severity,
            "confidence": confidence,
            "reasoning_summary": str(data.get("reasoning_summary", "")).strip()
            or "No reasoning summary provided.",
            "evidence": evidence[:20],
            "recommended_action": str(data.get("recommended_action", "manual_review")).strip()
            or "manual_review",
        }
