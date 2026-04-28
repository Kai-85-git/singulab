# 07_大集団で性能不足なら: llama-server 切替

Ollama では足りない場合、llama-server `--cont-batching` へ切替(同一 GGUF を流用)。

```powershell
# Ollama が裏で持っている GGUF のパスを取得
$model_path = "$env:USERPROFILE\.ollama\models\blobs\sha256-..."

# llama.cpp の server バイナリで起動
.\llama-server.exe `
  -m $model_path `
  --parallel 12 `
  --cont-batching `
  --ctx-size 2048 `
  --n-gpu-layers 99 `
  --host 0.0.0.0 --port 8080
```

クライアント側は `LLM_BASE_URL=http://localhost:8080/v1` に切替えるだけ。

## 想定効果

- 同一ハードで **スループット +30-50%**(継続バッチングの恩恵)
- ただし llama.cpp のビルド/入手が必要(初期コストあり)

---

← [06_サーマル対策](06_サーマル対策.md) | [README](README.md) | → [08_性能測定プロトコル](08_性能測定プロトコル.md)
