Given ALERT and TOOLS, produce a retrieval plan in JSON:
{
  "tool_calls": [
    {"tool": "tool_name", "args": {...}, "rationale": "..."}
  ]
}

Planning requirements:
- Prioritize internal Elastic searches first (WAF/Tianyan-Alarm/Zhongzi/Nginx/Huorong) before external calls.
- Build Elastic DSL queries using alert fields whenever available:
  - sip / dip
  - rule_name
  - log_type
  - uri_template
- Prefer precise `bool.must` + narrow filters over broad `match_all`.
- Keep each query lightweight (small size and focused time scope if possible).
- Add `rationale` that states why this tool call reduces uncertainty.

When to call external tools:
- Use VirusTotal only for externally meaningful IP reputation checks.
- Use CVE search only when a likely CVE token, vulnerability signature, or exploit context exists.
- Avoid redundant external calls with no expected value.

Quality constraints:
- Return 3~8 tool calls unless evidence is already sufficient.
- Avoid duplicate calls with near-identical arguments.
- Output JSON only; no markdown, no extra commentary.
