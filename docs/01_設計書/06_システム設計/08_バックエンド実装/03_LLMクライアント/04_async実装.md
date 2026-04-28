# 04_async 実装(本番向け)

100 エージェントを並列で動かすための async 版。

```python
# backend/llm_client_async.py
import asyncio
import httpx
import os
from typing import Optional

class AsyncLLMClient:
    def __init__(self, base_url: Optional[str] = None, model: str = "huihui_ai/qwen3-abliterated:4b",
                 max_concurrent: int = 8):
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
        self.model = model
        self.http = httpx.AsyncClient(timeout=60.0)
        self.sem = asyncio.Semaphore(max_concurrent)  # OLLAMA_NUM_PARALLEL と揃える

    async def chat(self, messages: list[dict], **params) -> dict:
        async with self.sem:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": params.get("temperature", 0.8),
                "max_tokens": params.get("num_predict", 256),
                "seed": params.get("seed"),
                "stream": False,
            }
            r = await self.http.post(f"{self.base_url}/chat/completions", json=payload)
            r.raise_for_status()
            return r.json()
```

`max_concurrent` は `OLLAMA_NUM_PARALLEL`([01_環境セットアップ/03_環境変数](../01_環境セットアップ/03_環境変数.md))と揃えること。

---

← [03_最小実装_sync](03_最小実装_sync.md) | [README](README.md) | → [05_エラーハンドリング](05_エラーハンドリング.md)
