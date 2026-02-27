# SOCRATES: An AI-Powered SOC Agent for Automated Network Alert Triage

This repository archives the paper “SOCRATES: An AI-Powered SOC Agent for Automated Network Alert Triage” (PDF: `docs/AI_Powered_SOC_Agents_for_Automated_Network_Alert_Triage.pdf`).

## Abstract

Modern Security Operations Centers (SOCs) are increasingly overwhelmed by massive volumes of network security alerts, most of which are false positives—leading to alert fatigue. While Large Language Models (LLMs) show promise in semantic understanding, applying them directly to real-world alert triage is hindered by (1) high false-positive rates due to missing enterprise-specific context and (2) prohibitive per-alert inference latency at SOC scale.

We propose SOCRATES, an AI-powered SOC agent for automated and scalable network alert triage. SOCRATES uses a staged, coarse-to-fine pipeline integrating three components: (1) a lightweight aggregation and filtering module to consolidate redundant alerts, (2) a business-logic self-learning module leveraging XGBoost to suppress recurring benign activities, and (3) a context-enhanced LLM investigation module that performs evidence-grounded reasoning by retrieving internal asset metadata and external threat intelligence. The paper reports a workload reduction ratio of 95.22% while retaining 99.63% of true attacks with an F1-score of 82.48%, and a one-year real-world deployment reducing manual investigation effort by over 80%.

## System Modules

SOCRATES follows a coarse-to-fine pipeline with one ingestion stage and three core triage stages:

1. Alert receiver: stream alerts from Elastic and push raw events to Redis.
2. Lightweight aggregation and filtering: normalize/aggregate alerts and score for denoising.
3. Business-logic self-learning: XGBoost-based suppression of recurring benign business traffic.
4. Context-enhanced LLM investigation: retrieve internal/external context and produce final triage verdicts.

## Project Architecture

```txt
USENIXSEC_paper1644/
├── README.md
├── main.py
├── pyproject.toml
├── uv.lock
├── config/
│   ├── system_config.json
│   └── assets_static.json
├── docs/
│   └── AI_Powered_SOC_Agents_for_Automated_Network_Alert_Triage.pdf
├── models/
│   └── README.md
├── prompts/
│   ├── module_context_enhanced_llm/
│   └── exploratory_study/
├── data/
│   ├── README.md
│   ├── alarm-tianyan.json
│   ├── cty-nginx.json
│   ├── huorong.json
│   ├── tianyan.json
│   ├── waf.json
│   ├── zhongzi.json
│   ├── asset_mapping.json
│   └── vt_reports/
├── results/
│   ├── README.md
│   ├── exploratory_result/
│   └── one_day_result_example/
└── src/
    ├── module_alert_receiver/
    ├── module_aggregation_filtering/
    ├── module_business_logic_self_learning/
    └── module_context_enhanced_llm/
```

## Run Project

1. Configure interfaces first (`config/system_config.json`):
   - Redis: `receiver.redis.url`, and each module queue `redis_url`.
   - Elasticsearch: `receiver.elastic.*`, `module2.elastic.*`, `module3.elastic.*`.
   - Internal/External APIs: `module3.cmdb.*`, `module3.external.*`.
   - Model paths: `module2.model.model_path`, `module3.llm.model_path`.
2. Create environment and install dependencies:
   - `uv venv`
   - `source .venv/bin/activate`
   - `uv sync`
3. (Optional) train module2 XGBoost model:
   - `uv run python main.py --config config/system_config.json train-module2`
4. Start full pipeline:
   - `uv run python main.py --config config/system_config.json run-all`
5. Run single modules if needed:
   - `uv run python main.py --config config/system_config.json run-receiver`
   - `uv run python main.py --config config/system_config.json run-module1`
   - `uv run python main.py --config config/system_config.json run-module2`
   - `uv run python main.py --config config/system_config.json run-module3`

Note: `run-*` commands perform startup connectivity checks. If Redis/Elasticsearch is unreachable or config is invalid, the process exits immediately with an error.

## Data and Results

- `data/` stores sample datasets used by this project:
  - Sample alert logs (`alarm-tianyan.json`, `cty-nginx.json`, `huorong.json`, `tianyan.json`, `waf.json`, `zhongzi.json`), where each file currently includes one example alert due to privacy constraints.
  - `vt_reports/`, which contains IP reputation samples from VirusTotal threat intelligence.
  - `asset_mapping.json`, which contains a privacy-preserving subset of enterprise CMDB asset mapping records.

- `results/` stores experiment and pipeline output artifacts:
  - `exploratory_result/` contains outputs for the Exploratory Study (different prompts across Qwen3-14B, Qwen3-30B-A3B, and Qwen3-32B).
  - `one_day_result_example/` contains a partial public sample of one-day system run outputs.
