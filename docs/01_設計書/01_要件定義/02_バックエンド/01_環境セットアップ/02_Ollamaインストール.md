# 02_Ollama のインストール

## インストール

```powershell
# winget 経由(推奨)
winget install Ollama.Ollama
```

または公式サイトから手動: https://ollama.com/download/windows

## 動作確認

```powershell
ollama --version
ollama run llama3.2:1b "hi"   # 軽量モデルで起動確認
```

`ollama --version` でバージョンが表示され、`llama3.2:1b` が応答すればインストール成功。

## 確認すべきバージョン

- **Ollama 0.6 以降**を推奨(Gemma 3 系含む新モデル対応のため)
- バージョンが古い場合: `winget upgrade Ollama.Ollama`

---

← [01_前提の確認](01_前提の確認.md) | [README](README.md) | → [03_環境変数](03_環境変数.md)
