from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from module_alert_receiver.buffer import RedisAlertBuffer

from .config import Module2Config
from .matcher import BusinessAlertMatcher
from .models import AggregatedAlert
from .raw_fetcher import ElasticRawAlertFetcher


@dataclass
class BusinessSelfLearningPipeline:
    cfg: Module2Config
    matcher: BusinessAlertMatcher
    fetcher: ElasticRawAlertFetcher

    @classmethod
    def from_config(cls, cfg: Module2Config) -> "BusinessSelfLearningPipeline":
        return cls(
            cfg=cfg,
            matcher=BusinessAlertMatcher.from_artifact(cfg.model),
            fetcher=ElasticRawAlertFetcher(cfg.elastic),
        )

    def run(self) -> None:
        input_buffer = RedisAlertBuffer(
            url=self.cfg.queue.redis_url,
            queue_key=self.cfg.queue.input_key,
        )
        output_buffer = RedisAlertBuffer(
            url=self.cfg.queue.redis_url,
            queue_key=self.cfg.queue.output_key,
            maxlen=self.cfg.queue.output_maxlen,
        )
        suppressed_buffer = RedisAlertBuffer(
            url=self.cfg.queue.redis_url,
            queue_key=self.cfg.queue.suppressed_key,
            maxlen=self.cfg.queue.suppressed_maxlen,
        )
        redis_client = input_buffer.connect()

        while True:
            payload = input_buffer.pop(redis_client, timeout_s=self.cfg.queue.pop_timeout_s)
            if payload is None:
                continue
            if not isinstance(payload, dict):
                continue

            aggregated = AggregatedAlert.from_dict(payload)
            raw_alerts = self.fetcher.fetch_by_reference_ids(aggregated.reference_uuids)
            if not raw_alerts:
                raw_alerts = [self._build_fallback_raw_alert(aggregated)]

            decision = self.matcher.evaluate(aggregated, raw_alerts)
            output_payload = self._attach_decision(aggregated.raw, decision.to_dict(), len(raw_alerts))

            if decision.is_business_false_positive:
                suppressed_buffer.push(redis_client, output_payload)
            else:
                output_buffer.push(redis_client, output_payload)

    def _attach_decision(
        self,
        original_alert: dict[str, Any],
        decision: dict[str, Any],
        fetched_instance_count: int,
    ) -> dict[str, Any]:
        payload = dict(original_alert)
        payload["module2_business_match"] = decision
        payload["module2_business_match"]["fetched_instance_count"] = fetched_instance_count
        payload["module"] = "module_business_logic_self_learning"
        payload["version"] = 1
        return payload

    def _build_fallback_raw_alert(self, aggregated: AggregatedAlert) -> dict[str, Any]:
        return {
            "@timestamp": aggregated.last_seen,
            "source": {"ip": aggregated.sip},
            "destination": {"ip": aggregated.dip},
            "proto": aggregated.proto,
            "rule_name": aggregated.rule_name,
            "log_type": aggregated.log_type,
            "uri_template": aggregated.uri_template,
            "reference_uuids": aggregated.reference_uuids,
        }


def run_pipeline(cfg: Module2Config) -> None:
    pipeline = BusinessSelfLearningPipeline.from_config(cfg)
    pipeline.run()
