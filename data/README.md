# Data Directory

This directory contains **sample data** used in this project.

## 1. Alert log samples

The following files are alert log samples:

- `alarm-tianyan.json`
- `cty-nginx.json`
- `huorong.json`
- `tianyan.json`
- `waf.json`
- `zhongzi.json`

Due to privacy constraints, each file currently includes only one example alert.
In the actual project pipeline, these alerts are fetched directly from Elasticsearch.
We plan to release fuller logs after proper desensitization/anonymization in a later update.

## 2. VirusTotal IP reputation samples

The `vt_reports/` directory contains the IP reputation part of our threat intelligence, retrieved from VirusTotal.
Full content can be obtained by configuring a valid VirusTotal API key in the project configuration.

## 3. CMDB asset mapping samples

The `tianyan_asset_mapping.json` file contains sample enterprise CMDB asset mapping data.
For privacy reasons, this file only includes a subset of records, and sensitive fields have been removed.
