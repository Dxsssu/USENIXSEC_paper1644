# SOCRATES: An AI-Powered SOC Agent for Automated Network Alert Triage

This repository archives the paper “SOCRATES: An AI-Powered SOC Agent for Automated Network Alert Triage” (PDF: `AI_Powered_SOC_Agents_for_Automated_Network_Alert_Triage.pdf`).

## Abstract

Modern Security Operations Centers (SOCs) are increasingly overwhelmed by massive volumes of network security alerts, most of which are false positives—leading to alert fatigue. While Large Language Models (LLMs) show promise in semantic understanding, applying them directly to real-world alert triage is hindered by (1) high false-positive rates due to missing enterprise-specific context and (2) prohibitive per-alert inference latency at SOC scale.

We propose SOCRATES, an AI-powered SOC agent for automated and scalable network alert triage. SOCRATES uses a staged, coarse-to-fine pipeline integrating three components: (1) a lightweight aggregation and filtering module to consolidate redundant alerts, (2) a business-logic self-learning module leveraging XGBoost to suppress recurring benign activities, and (3) a context-enhanced LLM investigation module that performs evidence-grounded reasoning by retrieving internal asset metadata and external threat intelligence. The paper reports a workload reduction ratio of 95.22% while retaining 99.63% of true attacks with an F1-score of 82.48%, and a one-year real-world deployment reducing manual investigation effort by over 80%.

## System Modules

SOCRATES follows a coarse-to-fine pipeline with three sequential modules:

1. Aggregation and filtering: normalize heterogeneous alerts, aggregate redundant events, and apply lightweight scoring/thresholding to reduce volume before deeper analysis.
2. Business-logic self-learning: learn enterprise-specific benign patterns from historical alerts (via XGBoost) and suppress recurring business-induced false positives.
3. Context-enhanced LLM investigation: retrieve alert-centric context from internal sources (e.g., asset metadata and multi-source logs) and external threat intelligence, then produce evidence-grounded triage decisions and explanations.
