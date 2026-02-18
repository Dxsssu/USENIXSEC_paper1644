from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from module_alert_receiver.buffer import RedisAlertBuffer

from .aggregator import LightweightAggregator
from .asset_catalog import AssetCatalog
from .config import Module1Config
from .history_store import RedisHistoryStore
from .models import AggregatedAlert, AlertBucketSnapshot
from .normalizer import AlertNormalizer
from .scorer import LightweightRiskScorer


@dataclass
class LightweightAggregationPipeline:
    cfg: Module1Config
    normalizer: AlertNormalizer
    aggregator: LightweightAggregator
    scorer: LightweightRiskScorer
    asset_catalog: AssetCatalog
    history_store: RedisHistoryStore

    @classmethod
    def from_config(cls, cfg: Module1Config) -> "LightweightAggregationPipeline":
        return cls(
            cfg=cfg,
            normalizer=AlertNormalizer(),
            aggregator=LightweightAggregator(
                window_s=cfg.aggregation.window_s,
                max_ref_ids=cfg.aggregation.max_ref_ids,
            ),
            scorer=LightweightRiskScorer(cfg.scoring),
            asset_catalog=AssetCatalog.from_json_file(cfg.asset.table_path),
            history_store=RedisHistoryStore(
                key_prefix=cfg.history.key_prefix,
                history_days=cfg.aggregation.history_days,
            ),
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
            raw_alert = input_buffer.pop(redis_client, timeout_s=self.cfg.aggregation.pop_timeout_s)
            if raw_alert is not None:
                normalized = self.normalizer.normalize(raw_alert)
                self.aggregator.add(normalized)
            self._flush_expired(redis_client, output_buffer, suppressed_buffer)

    def _flush_expired(
        self,
        redis_client: Any,
        output_buffer: RedisAlertBuffer,
        suppressed_buffer: RedisAlertBuffer,
    ) -> None:
        now = datetime.now(UTC)
        snapshots = self.aggregator.flush_expired(now=now)
        for snapshot in snapshots:
            payload = self._build_payload(redis_client, snapshot)
            if self.scorer.is_high_priority(payload["score_breakdown"]):
                output_buffer.push(redis_client, payload["alert"])
            else:
                suppressed_buffer.push(redis_client, payload["alert"])

    def _build_payload(self, redis_client: Any, snapshot: AlertBucketSnapshot) -> dict[str, Any]:
        now = datetime.now(UTC)
        historical_daily_avg = self.history_store.get_14d_daily_avg(
            redis_client=redis_client,
            bucket_key=snapshot.bucket_key,
            now=now,
        )
        asset_profile = self.asset_catalog.resolve(snapshot.dip)
        score = self.scorer.score(snapshot, historical_daily_avg=historical_daily_avg, asset_profile=asset_profile)
        self.history_store.record(
            redis_client=redis_client,
            bucket_key=snapshot.bucket_key,
            count=snapshot.count,
            event_time=snapshot.window_end,
        )

        aggregated = AggregatedAlert(
            sip=snapshot.sip,
            dip=snapshot.dip,
            proto=snapshot.proto,
            rule_name=snapshot.rule_name,
            log_type=snapshot.log_type,
            reference_uuids=snapshot.raw_ref_ids,
            aggregated_count=snapshot.count,
            first_seen=int(snapshot.window_start.timestamp()),
            last_seen=int(snapshot.window_end.timestamp()),
            uri_template=snapshot.uri_template,
            risk_scores=score,
        )
        return {"alert": aggregated.to_dict(), "score_breakdown": score}


def run_pipeline(config: Module1Config) -> None:
    pipeline = LightweightAggregationPipeline.from_config(config)
    pipeline.run()
