# Module3 日志研判结果示例

## 1) 告警输入

```json
{
  "sip": "10.130.35.30",
  "dip": "10.132.99.78",
  "proto": "ldap",
  "rule_name": "LDAP 账号暴力猜解",
  "log_type": "webids-ids_dolog",
  "uri_template": "/ldap/bind",
  "reference_uuids": [
    "56f8faa2ce03095425e35cdc39e44f4bd604eabc2a65d0969b76f4cfccf1afdf",
    "d1af54f484cc4f3920f27187dd698cb3bcf0cea14984186c9a486a27fc2e58f9",
    "2cedb303f9d0088c7aadf4e3b9726d874541529f7d2531bf9d6e30fea2588a17"
  ],
  "risk_scores": {
    "frequency_score": 0.4033,
    "rule_score": 0.6,
    "context_score": 0.3,
    "rarity_score": 0.0,
    "final_score": 49.03,
    "risk_level": "MEDIUM"
  },
  "module2_business_match": {
    "matched": false,
    "confidence": 0.08,
    "pattern_id": null,
    "reason": "no stable benign business pattern matched"
  }
}
```

## 2) 告警上下文富化（检索摘要）

- `search_tianyan_alarm_logs`: 同源IP在 `2026-01-19 13:20~13:48`（28 分钟）内对同一目标发起 41 次 LDAP 绑定失败，账号轮换明显。
- `get_cmdb_asset(dip)`: 目标 `10.132.99.78` 为 AD 域控，资产等级 `critical`，面向核心认证服务。
- `get_cmdb_asset(sip)`: 源 `10.130.35.30` 为普通办公终端，不在域管运维白名单。
- `search_huorong_logs`: 源主机在 `2026-01-19 13:23~13:47` 出现高频 `lsass` 访问告警，与认证失败窗口重叠。
- `search_nginx_logs`: 未见与该事件直接关联的 Web 访问证据。

## 3) 告警上下文富化后的完整提示词实例

```text
You are an enterprise SOC alert-triage copilot focused on evidence-driven decisions.

Operating principles:
- Use only information from the input alert and retrieved tool outputs.
- Never hallucinate missing facts, missing logs, or missing context.
- Prefer conservative judgment: if evidence is weak or conflicting, return INCONCLUSIVE.
- Keep outputs structured, auditable, and operationally actionable.

Decision policy:
- Distinguish between indicator-level evidence (IP/domain/hash reputation), behavior-level evidence
  (attack sequence, repeated exploit attempts), and context-level evidence (asset criticality, exposure, ownership).
- Do not over-weight a single weak signal (e.g., one noisy signature hit or one low-confidence reputation tag).
- Increase confidence only when multiple independent sources agree.
- If a source fails, explicitly reflect uncertainty instead of guessing.

Output discipline:
- Follow the requested JSON schema exactly.
- Do not output prose outside JSON.
- Keep confidence calibrated in [0, 1], where:
  - 0.0~0.3 = weak/insufficient evidence
  - 0.4~0.6 = mixed signals
  - 0.7~1.0 = strong multi-source consistency

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

ALERT:
{"sip": "10.130.35.30", "dip": "10.132.99.78", "proto": "ldap", "rule_name": "LDAP 账号暴力猜解", "log_type": "webids-ids_dolog", "uri_template": "/ldap/bind", "reference_uuids": ["56f8faa2ce03095425e35cdc39e44f4bd604eabc2a65d0969b76f4cfccf1afdf", "d1af54f484cc4f3920f27187dd698cb3bcf0cea14984186c9a486a27fc2e58f9", "2cedb303f9d0088c7aadf4e3b9726d874541529f7d2531bf9d6e30fea2588a17"], "risk_scores": {"frequency_score": 0.4033, "rule_score": 0.6, "context_score": 0.3, "rarity_score": 0.0, "final_score": 49.03, "risk_level": "MEDIUM"}, "module2_business_match": {"matched": false, "confidence": 0.08, "pattern_id": null, "reason": "no stable benign business pattern matched"}}

TOOL_SUMMARIES:
[
  {
    "tool": "search_tianyan_alarm_logs",
    "success": true,
    "query": {
      "query": {
        "bool": {
          "must": [
            {"match": {"sip": "10.130.35.30"}},
            {"match": {"dip": "10.132.99.78"}},
            {"match": {"rule_name": "LDAP 账号暴力猜解"}}
          ]
        }
      },
      "size": 30
    },
    "summary": "同源IP在2026-01-19 13:20~13:48窗口内对同一域控发起高频LDAP失败认证并轮换用户名，行为与口令爆破一致。",
    "error": null,
    "data": {
      "total": 41,
      "trimmed": true,
      "trimmed_from": 41,
      "signals": [
        {"type": "behavior", "value": "41 failed LDAP binds between 2026-01-19T13:20:00Z and 2026-01-19T13:48:00Z", "confidence": 0.91},
        {"type": "behavior", "value": "multiple account names rotated from single source", "confidence": 0.87}
      ]
    }
  },
  {
    "tool": "get_cmdb_asset",
    "success": true,
    "query": {"ip": "10.132.99.78"},
    "summary": "目标资产为核心AD域控，认证服务中断将产生较大业务影响。",
    "error": null,
    "data": {
      "status_code": 200,
      "result": {
        "ip": "10.132.99.78",
        "hostname": "ad-dc-01",
        "asset_role": "domain_controller",
        "criticality": "critical",
        "owner_team": "IAM",
        "internet_exposed": false
      },
      "signals": [
        {"type": "asset", "value": "domain_controller critical asset", "confidence": 0.95}
      ]
    }
  },
  {
    "tool": "get_cmdb_asset",
    "success": true,
    "query": {"ip": "10.130.35.30"},
    "summary": "源资产为普通办公终端，不属于认证系统运维或域管理白名单。",
    "error": null,
    "data": {
      "status_code": 200,
      "result": {
        "ip": "10.130.35.30",
        "hostname": "win-client-223",
        "asset_role": "office_endpoint",
        "criticality": "medium",
        "owner_team": "Finance",
        "admin_whitelist": false
      },
      "signals": [
        {"type": "asset", "value": "source host not in privileged admin whitelist", "confidence": 0.81}
      ]
    }
  },
  {
    "tool": "search_huorong_logs",
    "success": true,
    "query": {
      "query": {
        "bool": {
          "must": [
            {"match": {"host_ip": "10.130.35.30"}},
            {"match": {"event_name": "credential_access"}}
          ]
        }
      },
      "size": 20
    },
    "summary": "在2026-01-19 13:23~13:47时间窗内出现针对LSASS的可疑访问告警，和认证失败行为形成链路关联。",
    "error": null,
    "data": {
      "total": 3,
      "signals": [
        {"type": "behavior", "value": "suspicious lsass access on source host", "confidence": 0.74},
        {"type": "indicator", "value": "process tree shows powershell -> rundll32", "confidence": 0.69}
      ]
    }
  },
  {
    "tool": "search_nginx_logs",
    "success": true,
    "query": {
      "query": {
        "bool": {
          "must": [
            {"match": {"src_ip": "10.130.35.30"}},
            {"match": {"dst_ip": "10.132.99.78"}}
          ]
        }
      },
      "size": 20
    },
    "summary": "未检索到与该事件直接相关的Web侧证据。",
    "error": null,
    "data": {
      "total": 0,
      "signals": []
    }
  }
]
```

## 4) 研判结果（module3 输出）

```json
{
  "verdict": "MALICIOUS",
  "severity": "HIGH",
  "confidence": 0.88,
  "reasoning_summary": "源主机在2026-01-19 13:20~13:48对核心AD域控发起高频LDAP失败认证并伴随账号轮换，且源资产不具备域管运维权限，同时段存在凭证访问异常，综合判定为高可信恶意口令爆破/横向尝试。",
  "evidence": [
    {
      "source": "search_tianyan_alarm_logs",
      "detail": "41次LDAP失败认证集中发生在2026-01-19 13:20~13:48（28分钟）内，账号轮换明显。",
      "confidence": 0.91
    },
    {
      "source": "get_cmdb_asset",
      "detail": "目标10.132.99.78为critical级AD域控。",
      "confidence": 0.95
    },
    {
      "source": "get_cmdb_asset",
      "detail": "源10.130.35.30为办公终端且不在域管理白名单。",
      "confidence": 0.81
    },
    {
      "source": "search_huorong_logs",
      "detail": "源主机出现可疑LSASS访问，与认证攻击时窗重叠。",
      "confidence": 0.74
    }
  ],
  "tool_trace": [
    {
      "tool": "search_tianyan_alarm_logs",
      "success": true,
      "query": {
        "query": {
          "bool": {
            "must": [
              {"match": {"sip": "10.130.35.30"}},
              {"match": {"dip": "10.132.99.78"}},
              {"match": {"rule_name": "LDAP 账号暴力猜解"}}
            ]
          }
        },
        "size": 30
      },
      "summary": "同源IP在2026-01-19 13:20~13:48窗口内对同一域控发起高频LDAP失败认证并轮换用户名，行为与口令爆破一致。",
      "error": null,
      "data": {
        "total": 41,
        "trimmed": true,
        "trimmed_from": 41,
        "signals": [
          {"type": "behavior", "value": "41 failed LDAP binds between 2026-01-19T13:20:00Z and 2026-01-19T13:48:00Z", "confidence": 0.91},
          {"type": "behavior", "value": "multiple account names rotated from single source", "confidence": 0.87}
        ]
      }
    },
    {
      "tool": "get_cmdb_asset",
      "success": true,
      "query": {"ip": "10.132.99.78"},
      "summary": "目标资产为核心AD域控，认证服务中断将产生较大业务影响。",
      "error": null,
      "data": {
        "status_code": 200,
        "result": {
          "ip": "10.132.99.78",
          "hostname": "ad-dc-01",
          "asset_role": "domain_controller",
          "criticality": "critical",
          "owner_team": "IAM",
          "internet_exposed": false
        },
        "signals": [
          {"type": "asset", "value": "domain_controller critical asset", "confidence": 0.95}
        ]
      }
    },
    {
      "tool": "get_cmdb_asset",
      "success": true,
      "query": {"ip": "10.130.35.30"},
      "summary": "源资产为普通办公终端，不属于认证系统运维或域管理白名单。",
      "error": null,
      "data": {
        "status_code": 200,
        "result": {
          "ip": "10.130.35.30",
          "hostname": "win-client-223",
          "asset_role": "office_endpoint",
          "criticality": "medium",
          "owner_team": "Finance",
          "admin_whitelist": false
        },
        "signals": [
          {"type": "asset", "value": "source host not in privileged admin whitelist", "confidence": 0.81}
        ]
      }
    },
    {
      "tool": "search_huorong_logs",
      "success": true,
      "query": {
        "query": {
          "bool": {
            "must": [
              {"match": {"host_ip": "10.130.35.30"}},
              {"match": {"event_name": "credential_access"}}
            ]
          }
        },
        "size": 20
      },
      "summary": "在2026-01-19 13:23~13:47时间窗内出现针对LSASS的可疑访问告警，和认证失败行为形成链路关联。",
      "error": null,
      "data": {
        "total": 3,
        "signals": [
          {"type": "behavior", "value": "suspicious lsass access on source host", "confidence": 0.74},
          {"type": "indicator", "value": "process tree shows powershell -> rundll32", "confidence": 0.69}
        ]
      }
    },
    {
      "tool": "search_nginx_logs",
      "success": true,
      "query": {
        "query": {
          "bool": {
            "must": [
              {"match": {"src_ip": "10.130.35.30"}},
              {"match": {"dst_ip": "10.132.99.78"}}
            ]
          }
        },
        "size": 20
      },
      "summary": "未检索到与该事件直接相关的Web侧证据。",
      "error": null,
      "data": {
        "total": 0,
        "signals": []
      }
    }
  ],
  "recommended_action": "isolate",
  "timestamps": {
    "started_at": "2026-01-19T13:24:11.210000+00:00",
    "finished_at": "2026-01-19T13:24:12.098000+00:00",
    "duration_ms": 888
  }
}
```
