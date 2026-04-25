# 03_Modelfile

```
FROM huihui_ai/llama3.2-abliterated:3b

PARAMETER temperature 0.7
PARAMETER num_ctx 2048
PARAMETER num_predict 256
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
PARAMETER seed 42

SYSTEM """"""
```

## 登録

```powershell
ollama create singulab-llama32-3b -f .claude/models/llama32-3b-abliterated-singulab.Modelfile
```

---

← [02_用途](02_用途.md) | [README](README.md) | → [04_推奨パラメータ](04_推奨パラメータ.md)
