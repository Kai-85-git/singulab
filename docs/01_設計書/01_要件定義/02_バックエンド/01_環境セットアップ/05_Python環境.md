# 05_Python 環境

## venv 作成

```powershell
# プロジェクトルートで
python -m venv .venv
.venv\Scripts\Activate.ps1
```

## 必須パッケージのインストール

```powershell
pip install httpx pydantic structlog python-dotenv numpy pandas matplotlib pyyaml
```

## 各パッケージの用途

| パッケージ | 用途 |
| --- | --- |
| httpx | OpenAI 互換 API 呼び出し(sync/async 両対応) |
| pydantic | LLM 出力 JSON の検証 |
| structlog | 構造化ログ |
| python-dotenv | 環境変数管理 |
| numpy / pandas | 結果解析 |
| matplotlib | 可視化(議事録 §6 の 4 象限比較等) |
| pyyaml | config.yaml 読み込み |

## Python バージョン

- **Python 3.10+** を推奨(asyncio 関連の機能、型ヒント)
- 確認: `python --version`

## requirements.txt 化

依存を固定したい場合:

```powershell
pip freeze > requirements.txt
# 後で再現するときは
pip install -r requirements.txt
```

---

← [04_モデルpull](04_モデルpull.md) | [README](README.md) | → [06_初回ヘルスチェック](06_初回ヘルスチェック.md)
