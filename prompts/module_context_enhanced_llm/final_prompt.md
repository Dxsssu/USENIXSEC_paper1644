Perform final triage based on ALERT and TOOL_SUMMARIES, then output JSON:
{
  "verdict": "MALICIOUS|BENIGN|SUSPICIOUS|INCONCLUSIVE",
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "confidence": 0.0,
  "reasoning_summary": "concise analyst-facing conclusion",
  "evidence": [
    {"source": "tool_name", "detail": "...", "confidence": 0.0}
  ],
  "recommended_action": "block|isolate|monitor|manual_review"
}

Reasoning policy:
- Ground every conclusion in tool evidence; do not infer unsupported facts.
- Evaluate consistency across source types:
  - attack behavior (logs)
  - asset/business context (CMDB/internal data)
  - reputation/vulnerability context (external intel)
- Resolve conflicts explicitly:
  - if high-confidence signals conflict, downgrade confidence and prefer SUSPICIOUS/INCONCLUSIVE.
  - if evidence is sparse, default to INCONCLUSIVE.

Severity guidance:
- CRITICAL: clear active compromise or high-impact exploit against critical asset
- HIGH: strong malicious evidence with meaningful risk
- MEDIUM: suspicious pattern with partial support
- LOW: low-risk or likely benign residual signal

Evidence quality:
- Include 2~6 strongest evidence items.
- Each evidence item should be specific, not generic.
- Confidence must be in [0, 1].

Output JSON only.
