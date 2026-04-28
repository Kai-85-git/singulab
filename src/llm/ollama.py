"""Ollama API クライアント。参考実装 ollama_client.py をそのまま移植。

> Phase 2 で `src/llm/base.py` の抽象化 + httpx async に置き換え予定。
"""
import logging
from typing import List

import requests

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 200
DEFAULT_REPEAT_PENALTY = 1.1
DEFAULT_REPEAT_LAST_N = 128
DEFAULT_MIN_P = 0.05
API_TIMEOUT = 60
CONNECTION_CHECK_TIMEOUT = 5


class OllamaClient:
    """Ollama API へのクライアント。"""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        repeat_penalty: float = DEFAULT_REPEAT_PENALTY,
        repeat_last_n: int = DEFAULT_REPEAT_LAST_N,
        min_p: float = DEFAULT_MIN_P,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.repeat_penalty = repeat_penalty
        self.repeat_last_n = repeat_last_n
        self.min_p = min_p
        self.api_url = f"{self.base_url}/api/generate"

    def generate(
        self,
        prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        if temperature is None:
            temperature = self.temperature
        if max_tokens is None:
            max_tokens = self.max_tokens

        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "repeat_penalty": self.repeat_penalty,
                    "repeat_last_n": self.repeat_last_n,
                    "min_p": self.min_p,
                },
            }
            response = requests.post(self.api_url, json=payload, timeout=API_TIMEOUT)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "").strip()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Ollama API: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error in Ollama client: {e}")
            return ""

    def check_connection(self) -> bool:
        try:
            response = requests.get(
                f"{self.base_url}/api/tags", timeout=CONNECTION_CHECK_TIMEOUT
            )
            return response.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        try:
            response = requests.get(
                f"{self.base_url}/api/tags", timeout=CONNECTION_CHECK_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []

    def check_model_exists(self) -> bool:
        return self.model in self.list_models()
