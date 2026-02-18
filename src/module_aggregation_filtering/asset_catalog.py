from __future__ import annotations

import ipaddress
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AssetProfile:
    criticality: float = 0.4
    exposure: float = 0.3
    sensitive: bool = False


@dataclass
class AssetCatalog:
    entries: list[dict[str, Any]]

    @classmethod
    def from_json_file(cls, path: str) -> "AssetCatalog":
        file_path = Path(path)
        if not file_path.exists():
            return cls(entries=[])
        raw = json.loads(file_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            rows = raw.get("assets", [])
        elif isinstance(raw, list):
            rows = raw
        else:
            rows = []
        return cls(entries=[row for row in rows if isinstance(row, dict)])

    def resolve(self, ip_text: str) -> AssetProfile:
        ip_obj = self._to_ip(ip_text)
        if ip_obj is None:
            return AssetProfile()

        direct_match: dict[str, Any] | None = None
        cidr_match: dict[str, Any] | None = None
        for row in self.entries:
            row_ip = row.get("ip")
            if isinstance(row_ip, str) and row_ip == ip_text:
                direct_match = row
                break
            row_cidr = row.get("cidr")
            if isinstance(row_cidr, str) and cidr_match is None:
                try:
                    if ip_obj in ipaddress.ip_network(row_cidr, strict=False):
                        cidr_match = row
                except ValueError:
                    continue

        matched = direct_match or cidr_match
        if matched is None:
            return self._default_profile(ip_obj)
        return AssetProfile(
            criticality=self._clamp01(matched.get("criticality", 0.4)),
            exposure=self._clamp01(matched.get("exposure", 0.3)),
            sensitive=bool(matched.get("sensitive", False)),
        )

    def _default_profile(self, ip_obj: Any) -> AssetProfile:
        if ip_obj.is_private:
            return AssetProfile(criticality=0.45, exposure=0.2, sensitive=False)
        return AssetProfile(criticality=0.5, exposure=0.7, sensitive=False)

    def _to_ip(self, ip_text: str) -> Any:
        try:
            return ipaddress.ip_address(ip_text)
        except ValueError:
            return None

    def _clamp01(self, value: Any) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = 0.0
        return max(0.0, min(numeric, 1.0))
