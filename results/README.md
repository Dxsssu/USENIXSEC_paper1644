# Results Directory

This directory contains result artifacts from different parts of the project.

## `exploratory_result/`

This folder stores the experimental outputs for the **Exploratory Study** section.
It evaluates alert triage capability under different prompting strategies using three models:

- `Qwen3-14B`
- `Qwen3-30B-A3B`
- `Qwen3-32B`

## `one_day_result_example/`

This folder stores sample outputs from a one-day system run.
Due to privacy constraints, only a subset of the results is publicly included.

Included sample files:
- `module1_output.json`: module1 aggregation/filtering output sample.
- `final_alerts.json`: final alerts after staged triage.
- `final_alerts_enriched.json`: enriched final alerts with additional labels/statistics.
- `module3_log_investigation.md`: module3 investigation write-up with context-enriched prompt and verdict example.
