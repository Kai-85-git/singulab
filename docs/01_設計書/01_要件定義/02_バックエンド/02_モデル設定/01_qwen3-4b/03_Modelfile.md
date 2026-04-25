# 03_Modelfile

`.claude/models/qwen3-4b-abliterated-singulab.Modelfile`:

```
FROM huihui_ai/qwen3-abliterated:4b

# 推論パラメータ
PARAMETER temperature 0.8
PARAMETER num_ctx 2048
PARAMETER num_predict 256
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
PARAMETER seed 42

# Qwen3 の thinking モードを抑制(本実験では「考えすぎ」を避ける)
PARAMETER stop "<think>"

# SYSTEM は実行時に Python から動的に組み立てるため空にする
SYSTEM """"""
```

## 登録

```powershell
ollama create singulab-qwen3-4b -f .claude/models/qwen3-4b-abliterated-singulab.Modelfile
```

---

← [02_用途](02_用途.md) | [README](README.md) | → [04_推奨パラメータ](04_推奨パラメータ.md)
