# 03_最小実装(sync)

```python
# backend/llm_client.py
import os
import httpx
from pydantic import BaseModel
from typing import Optional

class ChatMessage(BaseModel):
    role: str  # "system" | "user" | "assistant"
    content: str

class LLMResponse(BaseModel):
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int

class LLMClient:
    def __init__(self, base_url: Optional[str] = None, model: str = "huihui_ai/qwen3-abliterated:4b"):
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
        self.model = model
        self.http = httpx.Client(timeout=60.0)

    def chat(self, messages: list[ChatMessage], **params) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [m.model_dump() for m in messages],
            "temperature": params.get("temperature", 0.8),
            "max_tokens": params.get("num_predict", 256),
            "seed": params.get("seed"),
            "stream": False,
        }
        import time
        t0 = time.perf_counter()
        r = self.http.post(f"{self.base_url}/chat/completions", json=payload)
        r.raise_for_status()
        j = r.json()
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return LLMResponse(
            content=j["choices"][0]["message"]["content"],
            prompt_tokens=j["usage"]["prompt_tokens"],
            completion_tokens=j["usage"]["completion_tokens"],
            total_tokens=j["usage"]["total_tokens"],
            latency_ms=latency_ms,
        )
```

---

← [02_エンドポイント](02_エンドポイント.md) | [README](README.md) | → [04_async実装](04_async実装.md)
