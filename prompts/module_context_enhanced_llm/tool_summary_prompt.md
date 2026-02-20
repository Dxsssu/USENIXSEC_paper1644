You will receive TOOL_RESULT. Extract security-relevant findings and return JSON:
{
  "summary": "one-sentence assessment",
  "signals": [
    {"type": "indicator|behavior|asset|reputation|vulnerability", "value": "...", "confidence": 0.0}
  ]
}

Extraction rules:
- Keep only high-value signals that materially affect triage decisions.
- Normalize noisy raw fields into concise analyst-readable facts.
- Prefer explicit observables (IPs, URIs, user-agents, CVEs, host roles, attack patterns).
- Deduplicate repeated evidence.

Confidence guidance:
- 0.0~0.3: weak / ambiguous / partial match
- 0.4~0.6: plausible but not independently confirmed
- 0.7~1.0: strong and specific signal with clear linkage

Failure handling:
- If tool output is empty, failed, or irrelevant, state it clearly in `summary`.
- In such cases, keep `signals` empty unless a minimal reliable fact still exists.

Output JSON only.
