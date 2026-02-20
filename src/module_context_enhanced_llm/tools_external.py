from __future__ import annotations

from dataclasses import dataclass

import requests

from .config import ExternalConfig
from .models import ToolResult


@dataclass
class ExternalTools:
    cfg: ExternalConfig

    def virustotal_ip_reputation(self, ip: str) -> ToolResult:
        url = f"{self.cfg.vt_base_url}/ip_addresses/{ip}"
        headers = {"accept": "application/json"}
        if self.cfg.vt_api_key:
            headers["x-apikey"] = self.cfg.vt_api_key
        try:
            response = requests.get(url, headers=headers, timeout=self.cfg.timeout_s)
            data = self._parse_response(response)
            return ToolResult(
                tool="virustotal_ip_reputation",
                success=response.ok,
                query={"ip": ip},
                summary=f"VirusTotal returned status={response.status_code}",
                data={"status_code": response.status_code, "result": data},
                error=None if response.ok else f"http_{response.status_code}",
            )
        except Exception as exc:
            return ToolResult(
                tool="virustotal_ip_reputation",
                success=False,
                query={"ip": ip},
                summary="VirusTotal query failed.",
                error=str(exc),
            )

    def cve_search(self, query: str) -> ToolResult:
        url = f"{self.cfg.cve_base_url}/search"
        headers = {}
        if self.cfg.cve_api_key:
            headers["X-Api-Key"] = self.cfg.cve_api_key
        try:
            response = requests.get(
                url,
                params={"q": query},
                headers=headers,
                timeout=self.cfg.timeout_s,
            )
            data = self._parse_response(response)
            return ToolResult(
                tool="cve_search",
                success=response.ok,
                query={"q": query},
                summary=f"CVE search returned status={response.status_code}",
                data={"status_code": response.status_code, "result": data},
                error=None if response.ok else f"http_{response.status_code}",
            )
        except Exception as exc:
            return ToolResult(
                tool="cve_search",
                success=False,
                query={"q": query},
                summary="CVE query failed.",
                error=str(exc),
            )

    def _parse_response(self, response: requests.Response) -> dict:
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            data = response.json()
            return data if isinstance(data, dict) else {"data": data}
        return {"raw_text": response.text[:4000]}
