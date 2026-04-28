# 03_Ollama 並列制御

## 1. サーバー側の設定

```powershell
$env:OLLAMA_NUM_PARALLEL = "8"   # 同時処理するリクエスト数
$env:OLLAMA_MAX_LOADED_MODELS = "1"  # モデル切替を抑制
```

詳細は [01_環境セットアップ/03_環境変数](../01_環境セットアップ/03_環境変数.md)。

## 2. クライアント側の制御

```python
import asyncio

# OLLAMA_NUM_PARALLEL と揃える
sem = asyncio.Semaphore(8)

async def call_one(agent_id, messages):
    async with sem:
        return await llm.chat(messages)

# 100 エージェント同時 → Semaphore が 8 に絞る
results = await asyncio.gather(*[call_one(i, msgs[i]) for i in range(100)])
```

---

← [02_モデル並列度時間](02_モデル並列度時間.md) | [README](README.md) | → [04_バッチ直列戦略](04_バッチ直列戦略.md)
