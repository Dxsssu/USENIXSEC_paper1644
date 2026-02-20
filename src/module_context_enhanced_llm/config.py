from __future__ import annotations

from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class QueueConfig:
    redis_url: str = "redis://localhost:6379/0"
    input_key: str = "socrates:alerts:investigation"
    output_key: str = "socrates:alerts:final"
    manual_review_key: str = "socrates:alerts:manual_review"
    output_maxlen: int | None = None
    manual_review_maxlen: int | None = None
    pop_timeout_s: int = 1

    @classmethod
    def from_env(cls) -> "QueueConfig":
        output_maxlen_env = getenv("M3_OUTPUT_MAXLEN", "")
        manual_maxlen_env = getenv("M3_MANUAL_MAXLEN", "")
        return cls(
            redis_url=getenv("M3_REDIS_URL", cls.redis_url),
            input_key=getenv("M3_INPUT_KEY", cls.input_key),
            output_key=getenv("M3_OUTPUT_KEY", cls.output_key),
            manual_review_key=getenv("M3_MANUAL_REVIEW_KEY", cls.manual_review_key),
            output_maxlen=int(output_maxlen_env) if output_maxlen_env else None,
            manual_review_maxlen=int(manual_maxlen_env) if manual_maxlen_env else None,
            pop_timeout_s=int(getenv("M3_POP_TIMEOUT_S", str(cls.pop_timeout_s))),
        )


@dataclass(frozen=True)
class LLMConfig:
    model_path: str = "models/Qwen3-32B"
    prompts_dir: str = "prompts/module_context_enhanced_llm"
    device: str = "auto"
    max_new_tokens: int = 1200
    temperature: float = 0.1
    top_p: float = 0.9

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            model_path=getenv("M3_MODEL_PATH", cls.model_path),
            prompts_dir=getenv("M3_PROMPTS_DIR", cls.prompts_dir),
            device=getenv("M3_DEVICE", cls.device),
            max_new_tokens=int(getenv("M3_MAX_NEW_TOKENS", str(cls.max_new_tokens))),
            temperature=float(getenv("M3_TEMPERATURE", str(cls.temperature))),
            top_p=float(getenv("M3_TOP_P", str(cls.top_p))),
        )


@dataclass(frozen=True)
class ElasticConfig:
    host: str = "10.132.99.60"
    port: int = 9200
    scheme: str = "http"
    timeout_s: int = 10
    default_size: int = 50
    index_waf: str = "waf-*"
    index_tianyan_alarm: str = "tianyan-alarm-*"
    index_zhongzi: str = "zhongzi-*"
    index_nginx: str = "nginx-*"
    index_huorong: str = "huorong-*"

    @classmethod
    def from_env(cls) -> "ElasticConfig":
        return cls(
            host=getenv("M3_ES_HOST", cls.host),
            port=int(getenv("M3_ES_PORT", str(cls.port))),
            scheme=getenv("M3_ES_SCHEME", cls.scheme),
            timeout_s=int(getenv("M3_ES_TIMEOUT_S", str(cls.timeout_s))),
            default_size=int(getenv("M3_ES_DEFAULT_SIZE", str(cls.default_size))),
            index_waf=getenv("M3_ES_INDEX_WAF", cls.index_waf),
            index_tianyan_alarm=getenv("M3_ES_INDEX_TIANYAN_ALARM", cls.index_tianyan_alarm),
            index_zhongzi=getenv("M3_ES_INDEX_ZHONGZI", cls.index_zhongzi),
            index_nginx=getenv("M3_ES_INDEX_NGINX", cls.index_nginx),
            index_huorong=getenv("M3_ES_INDEX_HUORONG", cls.index_huorong),
        )


@dataclass(frozen=True)
class CMDBConfig:
    base_url: str = ""
    api_key: str = ""
    timeout_s: int = 8

    @classmethod
    def from_env(cls) -> "CMDBConfig":
        return cls(
            base_url=getenv("M3_CMDB_BASE_URL", cls.base_url),
            api_key=getenv("M3_CMDB_API_KEY", cls.api_key),
            timeout_s=int(getenv("M3_CMDB_TIMEOUT_S", str(cls.timeout_s))),
        )


@dataclass(frozen=True)
class ExternalConfig:
    vt_base_url: str = "https://www.virustotal.com/api/v3"
    vt_api_key: str = ""
    cve_base_url: str = "https://api.cvesearch.com"
    cve_api_key: str = ""
    timeout_s: int = 10

    @classmethod
    def from_env(cls) -> "ExternalConfig":
        return cls(
            vt_base_url=getenv("M3_VT_BASE_URL", cls.vt_base_url),
            vt_api_key=getenv("M3_VT_API_KEY", cls.vt_api_key),
            cve_base_url=getenv("M3_CVE_BASE_URL", cls.cve_base_url),
            cve_api_key=getenv("M3_CVE_API_KEY", cls.cve_api_key),
            timeout_s=int(getenv("M3_EXTERNAL_TIMEOUT_S", str(cls.timeout_s))),
        )


@dataclass(frozen=True)
class ReasonerConfig:
    max_tool_iterations: int = 8
    tool_result_max_items: int = 30
    manual_review_confidence_threshold: float = 0.55

    @classmethod
    def from_env(cls) -> "ReasonerConfig":
        return cls(
            max_tool_iterations=int(getenv("M3_MAX_TOOL_ITERATIONS", str(cls.max_tool_iterations))),
            tool_result_max_items=int(getenv("M3_TOOL_RESULT_MAX_ITEMS", str(cls.tool_result_max_items))),
            manual_review_confidence_threshold=float(
                getenv(
                    "M3_MANUAL_REVIEW_CONF_THRESHOLD",
                    str(cls.manual_review_confidence_threshold),
                )
            ),
        )


@dataclass(frozen=True)
class Module3Config:
    queue: QueueConfig
    llm: LLMConfig
    elastic: ElasticConfig
    cmdb: CMDBConfig
    external: ExternalConfig
    reasoner: ReasonerConfig

    @classmethod
    def from_env(cls) -> "Module3Config":
        return cls(
            queue=QueueConfig.from_env(),
            llm=LLMConfig.from_env(),
            elastic=ElasticConfig.from_env(),
            cmdb=CMDBConfig.from_env(),
            external=ExternalConfig.from_env(),
            reasoner=ReasonerConfig.from_env(),
        )
