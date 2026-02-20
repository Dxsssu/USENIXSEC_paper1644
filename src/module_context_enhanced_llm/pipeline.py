from __future__ import annotations

from dataclasses import dataclass

from module_alert_receiver.buffer import RedisAlertBuffer

from .config import Module3Config
from .llm_client import Qwen32BClient
from .models import InvestigationAlert
from .prompt_loader import PromptLoader
from .reasoner import InvestigationReasoner
from .retrieval_orchestrator import RetrievalOrchestrator
from .tools_external import ExternalTools
from .tools_internal import InternalTools


@dataclass
class ContextEnhancedLLMPipeline:
    cfg: Module3Config
    reasoner: InvestigationReasoner

    @classmethod
    def from_config(cls, cfg: Module3Config) -> "ContextEnhancedLLMPipeline":
        llm = Qwen32BClient(cfg.llm)
        prompts = PromptLoader(cfg.llm.prompts_dir).load()
        orchestrator = RetrievalOrchestrator(
            internal_tools=InternalTools(cfg.elastic, cfg.cmdb),
            external_tools=ExternalTools(cfg.external),
            tool_result_max_items=cfg.reasoner.tool_result_max_items,
        )
        reasoner = InvestigationReasoner(
            llm=llm,
            prompts=prompts,
            orchestrator=orchestrator,
            cfg=cfg.reasoner,
        )
        return cls(cfg=cfg, reasoner=reasoner)

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
        manual_buffer = RedisAlertBuffer(
            url=self.cfg.queue.redis_url,
            queue_key=self.cfg.queue.manual_review_key,
            maxlen=self.cfg.queue.manual_review_maxlen,
        )
        redis_client = input_buffer.connect()

        while True:
            payload = input_buffer.pop(redis_client, timeout_s=self.cfg.queue.pop_timeout_s)
            if payload is None or not isinstance(payload, dict):
                continue

            alert = InvestigationAlert.from_dict(payload)
            verdict = self.reasoner.investigate(alert)
            output_payload = dict(payload)
            output_payload["module3_investigation"] = verdict.to_dict()
            output_payload["module"] = "module_context_enhanced_llm"
            output_payload["version"] = 1

            should_manual = (
                verdict.verdict == "INCONCLUSIVE"
                or verdict.confidence < self.cfg.reasoner.manual_review_confidence_threshold
            )
            if should_manual:
                manual_buffer.push(redis_client, output_payload)
            else:
                output_buffer.push(redis_client, output_payload)


def run_pipeline(cfg: Module3Config) -> None:
    pipeline = ContextEnhancedLLMPipeline.from_config(cfg)
    pipeline.run()
