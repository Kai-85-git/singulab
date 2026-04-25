# 04_採用モデルの pull

## pull コマンド

```powershell
# メイン(小集団・大集団兼用)
ollama pull huihui_ai/qwen3-abliterated:4b

# 100 人大集団の本命(最大並列)
ollama pull huihui_ai/llama3.2-abliterated:3b

# 品質検証用(stretch、CPU オフロード併用)
ollama pull huihui_ai/dolphin3-abliterated:8b-llama3.1-q4_K_M
```

## 容量目安(ダウンロード時)

| モデル | ダウンロード | ディスク占有 |
| --- | --- | --- |
| Qwen3 4B Q4_K_M | ~2.7GB | ~2.7GB |
| Llama 3.2 3B Q4_K_M | ~2.1GB | ~2.1GB |
| Dolphin 3.0 8B Q4_K_M | ~4.9GB | ~4.9GB |

**合計 ~10GB**。Ollama の既定保存先は `C:\Users\<user>\.ollama\models\`。

## 確認

```powershell
ollama list
```

3 モデルが表示されれば OK。SHA ダイジェストは [02_モデル設定](../02_モデル設定/) の run metadata に記録する。

## 保存先の変更(SSD 容量が厳しい場合)

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_MODELS", "D:\ollama\models", "User")
```

設定後 Ollama を再起動。既存モデルは自動移動されないため、手動コピーまたは再 pull が必要。

---

← [03_環境変数](03_環境変数.md) | [README](README.md) | → [05_Python環境](05_Python環境.md)
