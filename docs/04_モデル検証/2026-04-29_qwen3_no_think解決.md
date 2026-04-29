# M-05: Qwen3 `/no_think` 解決(2026-04-29)

| 項目 | 値 |
| --- | --- |
| 実施者 | Claude(自動)|
| 実施日 | 2026-04-29 |
| 対象 | `huihui_ai/qwen3-abliterated:4b` |
| 結論 | ✅ **`think: false` パラメータが正解**(`/no_think` プロンプト挿入は効かない) |

## 1. 動機

[3 モデル JSON 出力品質検証(2026-04-28)](2026-04-28_3モデル_JSON出力品質.md) で、Qwen3 4B に `/no_think` を user 末尾に付けても thinking が 2562〜3234 字残ることが判明していた。これを解決して **大集団 100 体運用にも Qwen3 4B abliterated を使える状態** にするのが本検証の目的。

## 2. 検証方法

同一プロンプトで 5 アプローチを `/api/chat` に投げ、`message.thinking.length` と `eval_count` を比較。

```
prompt: "あなたはエージェント1(男性、32歳、東京の会社員)です。今日の気分を1〜2文の独白で答えてください。"
options: temperature=0.5, num_predict=512
```

| ID | アプローチ |
| --- | --- |
| A | ベースライン(thinking ON 既定) |
| B | `/no_think` を user 末尾に付加 |
| C | `/no_think` を user 先頭に付加 |
| D | `/no_think` を **system message** に置く |
| E | **`think: false` パラメータ**(Ollama 0.21+ の正式 API)|

## 3. 結果

| ID | thinking_len | eval_count | tok/s | 判定 |
| --- | --- | --- | --- | --- |
| A. baseline | 1744 | 447 | 25.4 | (基準) |
| B. /no_think 末尾 | 1229 | 333 | 25.2 | ❌ 短縮するが残存 |
| C. /no_think 先頭 | 1779 | 458 | 25.0 | ❌ 効果なし(逆に baseline 同等) |
| D. /no_think in system | 1075 | 285 | 26.0 | ❌ 短縮のみ、完全抑制せず |
| **E. `think: false` API param** | **0** | **26** | **28.6** | ✅ **完全抑制 + 17 倍効率化** |

> 全 5 アプローチで応答品質(content)は問題なし。差は thinking の有無と eval_count のみ。

## 4. なぜ `/no_think` プロンプトは効かなかったか

Qwen3 系の `/no_think` は **chat template での命令** であり、Ollama の API レイヤーで `enable_thinking: false` フラグに変換されてはじめて効く。
ユーザメッセージ本文に `/no_think` という文字列を入れても、テンプレートはそれを **通常テキストとして扱う** ため、thinking ブロックは生成され続ける。

Ollama 0.21+ の正式 API パラメータ `think` は、内部的に Jinja chat template の `enable_thinking` フラグに直接バインドされるため、確実に thinking を抑制できる。

## 5. `/api/generate` でも検証

念のため `/api/generate` 側でも `think: false` が機能することを確認:

```
elapsed_ms: 3043, eval_count: 17, response_len: 28
--- response ---
今日はちょっと眠いな。でも、明日はきっと新しい一日だよ。
```

→ ✅ 動作。**本プロジェクトは `/api/generate` ベースなので OllamaClient に `think` パラメータを足すだけで解決**。

## 6. 採用方針への影響

[Phase 3-2/3-3 試走時点](../03_ToDo/verifications/Phase3-3_試走_2026-04-29.md) では Qwen3 4B abliterated を thinking ON で使うと **100 体 × 100 step が約 8 時間** という見積もりだったが、`think: false` で:

| 規模 | thinking ON | think: false |
| --- | --- | --- |
| 1 呼出 平均 token | ~500(thinking 込) | ~25 |
| 100 体 × 100 step × 8 並列 | 約 8 時間 | **約 24 分** |

→ Qwen3 4B abliterated は **大集団 100 体本番にも投入可能** な現実的速度を獲得。

これで [Phase 0.5 採用方針](../03_ToDo/02_実装ロードマップ.md) は以下に更新できる:

| シナリオ | 第 1 候補 | thinking |
| --- | --- | --- |
| 全規模 | **Qwen3 4B abliterated** | **OFF**(think: false) |
| 速度重視時のみ | Llama 3.2 3B abliterate | (thinking モデルではない) |

## 7. 実装

[src/llm/ollama.py](../../src/llm/ollama.py) の `OllamaClient` コンストラクタに `think: Optional[bool] = None` を追加。
None なら API リクエストに含めず(モデル既定)、True/False なら明示送信。

[config/base.yaml](../../config/base.yaml) のデフォルト LLM:

```yaml
llm:
  model: "huihui_ai/qwen3-abliterated:4b"
  think: false  # M-05 検証(2026-04-29)で thinking 抑制が必須と判明
```

[src/simulation.py](../../src/simulation.py) で `llm_config.get("think")` を OllamaClient に渡す。
既存シナリオ(`scenario_bar_fire.yaml` 等で `llm:` を持たない)は base.yaml 経由で think:false を継承。

## 8. 関連ドキュメント

- 生ログ: [no_think_logs/results.jsonl](no_think_logs/results.jsonl)
- スクリプト: [no_think_logs/run_test.ps1](no_think_logs/run_test.ps1)
- 旧検証(問題発覚): [2026-04-28_3モデル_JSON出力品質 §3.1](2026-04-28_3モデル_JSON出力品質.md)
- フォルダ説明: [README](README.md)
