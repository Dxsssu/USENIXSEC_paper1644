from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .config import LLMConfig

JSON_BLOCK_RE = re.compile(r"\{.*\}", re.S)


@dataclass
class Qwen32BClient:
    cfg: LLMConfig

    def __post_init__(self) -> None:
        self._tokenizer = None
        self._model = None

    def generate_text(self, prompt: str) -> str:
        self._ensure_loaded()
        messages = [{"role": "user", "content": prompt}]
        tokenizer = self._tokenizer
        model = self._model
        assert tokenizer is not None and model is not None

        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = tokenizer([text], return_tensors="pt").to(model.device)
        output_ids = model.generate(
            **inputs,
            max_new_tokens=self.cfg.max_new_tokens,
            temperature=self.cfg.temperature,
            top_p=self.cfg.top_p,
            do_sample=True if self.cfg.temperature > 0 else False,
        )
        generated = output_ids[0][inputs.input_ids.shape[1] :]
        return tokenizer.decode(generated, skip_special_tokens=True).strip()

    def generate_json(self, prompt: str, fallback: dict[str, Any]) -> dict[str, Any]:
        text = self.generate_text(prompt)
        parsed = self._parse_json(text)
        if parsed is None:
            return fallback
        return parsed

    def _parse_json(self, text: str) -> dict[str, Any] | None:
        text = text.strip()
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
        match = JSON_BLOCK_RE.search(text)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            return None
        return None

    def _ensure_loaded(self) -> None:
        if self._tokenizer is not None and self._model is not None:
            return
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise ImportError(
                "Missing dependencies for Qwen model runtime. Install transformers and torch."
            ) from exc

        tokenizer = AutoTokenizer.from_pretrained(self.cfg.model_path, trust_remote_code=True)
        if self.cfg.device == "auto":
            device_map = "auto"
        else:
            device_map = {"": self.cfg.device}
        model = AutoModelForCausalLM.from_pretrained(
            self.cfg.model_path,
            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            device_map=device_map,
            trust_remote_code=True,
        )
        model.eval()
        self._tokenizer = tokenizer
        self._model = model
