from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class PromptBundle:
    system_prompt: str
    planning_prompt: str
    tool_summary_prompt: str
    final_prompt: str


class PromptLoader:
    def __init__(self, prompts_dir: str) -> None:
        self.prompts_dir = Path(prompts_dir)

    def load(self) -> PromptBundle:
        return PromptBundle(
            system_prompt=self._read_or_default("system_prompt.md", self._default_system()),
            planning_prompt=self._read_or_default("planning_prompt.md", self._default_planning()),
            tool_summary_prompt=self._read_or_default("tool_summary_prompt.md", self._default_tool_summary()),
            final_prompt=self._read_or_default("final_prompt.md", self._default_final()),
        )

    def _read_or_default(self, filename: str, default: str) -> str:
        path = self.prompts_dir / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        return default

    def _default_system(self) -> str:
        return (
            "You are a SOC investigation assistant. Use only provided tools and evidence. "
            "Avoid speculation. Always output valid JSON when asked."
        )

    def _default_planning(self) -> str:
        return (
            "Given ALERT and available TOOLS, produce a JSON object: "
            '{"tool_calls":[{"tool":"tool_name","args":{},"rationale":"..."}]}'
        )

    def _default_tool_summary(self) -> str:
        return (
            "Summarize tool output into concise evidence JSON: "
            '{"summary":"...","signals":[{"type":"...","value":"...","confidence":0.0}]}'
        )

    def _default_final(self) -> str:
        return (
            "Produce final verdict JSON: "
            '{"verdict":"MALICIOUS|BENIGN|SUSPICIOUS|INCONCLUSIVE","severity":"LOW|MEDIUM|HIGH|CRITICAL",'
            '"confidence":0.0,"reasoning_summary":"...","evidence":[...],"recommended_action":"..."}'
        )
