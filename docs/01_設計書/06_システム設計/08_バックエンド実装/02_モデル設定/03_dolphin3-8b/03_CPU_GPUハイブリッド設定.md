# 03_CPU+GPU ハイブリッド設定

8B は 6GB VRAM に GPU フルロードできない。**一部の層を CPU にオフロード** する。

## 1. Modelfile(GPU 層数を制御)

```
FROM huihui_ai/dolphin3-abliterated:8b-llama3.1-q4_K_M

PARAMETER temperature 0.7
PARAMETER num_ctx 2048
PARAMETER num_predict 192
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
PARAMETER seed 42
PARAMETER num_gpu 20         # 全 32 層中、GPU には 20 層だけ載せる(残り 12 層は CPU)

SYSTEM """"""
```

## 2. 登録

```powershell
ollama create singulab-dolphin3-8b -f .claude/models/dolphin3-8b-abliterated-singulab.Modelfile
```

## 3. `num_gpu` のチューニング

| `num_gpu` | VRAM 使用 | 速度 | 備考 |
| --- | --- | --- | --- |
| 16 | ~3.5GB | ~6 tok/s | CPU 比重大、遅い |
| **20** ✅ | ~4.5GB | ~10 tok/s | **既定** |
| 24 | ~5.5GB | ~13 tok/s | OOM リスクあり |
| 28 | ~6GB+ | OOM | 動かない |

→ Phase 2 検証時に実機で `num_gpu` を 16/20/24 と振って最適値を決める。

---

← [02_用途](02_用途.md) | [README](README.md) | → [04_推奨パラメータ](04_推奨パラメータ.md)
