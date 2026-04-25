# 05_VRAM 管理

## 0. VRAM バジェットの視覚化(RTX 3060 Laptop 6GB = 6144 MB)

### 例: Llama 3.2 3B (Q4_K_M) + 並列 8

```
┌──────────────────────────────────────────────────────────┐
│  6144 MB (=6GB)  RTX 3060 Laptop 全 VRAM                 │
├──────────────────────────────────────────────────────────┤
│  ████████████████████████ 余裕 (OOM 防止)        ~1944MB │
├──────────────────────────────────────────────────────────┤
│  ████████████ KV キャッシュ (並列 8、num_ctx=2048) ~1100MB │
├──────────────────────────────────────────────────────────┤
│  █████████████████████ モデル本体 (3B Q4_K_M)    ~2100MB │
├──────────────────────────────────────────────────────────┤
│  ███████ OS + Display + Ollama overhead          ~700MB │
└──────────────────────────────────────────────────────────┘
```

### モデル × 並列度の OOM 境界

| モデル \ 並列度 | 1 | 4 | 6 | 8 | 10 | 12 |
| --- | :-: | :-: | :-: | :-: | :-: | :-: |
| **3B** (Llama 3.2) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **4B** (Qwen3) | ✅ | ✅ | ✅ | ✅ | ⚠️ | ❌ |
| **8B** (Dolphin) | ⚠️ CPU オフロード必須 | ❌ | ❌ | ❌ | ❌ | ❌ |

凡例: ✅ 安定 / ⚠️ 際どい / ❌ OOM

## 1. 実測すべき指標

- **Peak VRAM usage**(モデル + KV + 余裕)
- **OOM の兆候**: Ollama ログに "cuda out of memory" が出るとフォールバック発動

## 2. 監視スクリプト

別ターミナルで常時 VRAM を観測:

```powershell
while ($true) {
  nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader
  Start-Sleep 5
}
```

または Python 側で定期サンプリング:

```python
import subprocess
import asyncio

async def vram_monitor(interval: float = 5.0, log_path: str = "logs/vram.jsonl"):
    while True:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True
        )
        used, total, util = [int(x.strip()) for x in r.stdout.split(",")]
        with open(log_path, "a") as f:
            f.write(f'{{"ts": {asyncio.get_event_loop().time()}, "vram_used_mb": {used}, "gpu_util": {util}}}\n')
        await asyncio.sleep(interval)
```

## 3. OOM 発生時のフォールバック順

1. `num_ctx` を 2048 → 1024 に半減
2. `num_predict` を 256 → 192 に絞る
3. バッチサイズを 8 → 4 に半減
4. モデルを 4B → 3B に切替
5. Ollama 再起動(`Restart-Service ollama` もしくは手動)

---

← [04_バッチ直列戦略](04_バッチ直列戦略.md) | [README](README.md) | → [06_サーマル対策](06_サーマル対策.md)
