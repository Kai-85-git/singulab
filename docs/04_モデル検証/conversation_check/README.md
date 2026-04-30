# 会話の実態チェック(2026-04-30 / Phase 4-A 本番ランの分析)

ユーザの観察(「1 人 1 人のエージェントが同じようなことを言っているように見える」)を実データで検証したフォルダ。
**結論:エージェントは "会話" していない。エコー(同じ発言の伝染)と膠着(同じことを繰り返す)が支配的**。

## 数値サマリ

| シナリオ | echo_mean | echo_max | reflection_mean | self_similarity |
| --- | ---: | ---: | ---: | ---: |
| prod_local_startup | 0.336 | **1.000** | 0.705 | 0.422 |
| prod_urban_startup | 0.310 | **1.000** | 0.675 | 0.560 |
| prod_local_enterprise | 0.278 | **1.000** | 0.733 | 0.579 |
| prod_urban_enterprise | 0.247 | **1.000** | 0.748 | **0.702** |

| 指標 | 意味 | 健全レンジ | 観測値の判定 |
| --- | --- | --- | --- |
| `echo_max` | 同 step 内で別 agent 同士の発言類似度の最大値 | < 0.3 | 全 4 シナリオで **1.000 = 一字一句コピペ** ❌ |
| `echo_mean` | 同 step 内ペアの平均類似度 | < 0.2 | 平均 0.29 ❌ |
| `reflection_mean` | 受信メッセージとのキーワード重複率 | 0.1〜0.3 | 0.7 = 受信文をそのまま使用 ❌ |
| `self_similarity` | 同 agent の連続 step の類似度 | < 0.3 | 最大 0.70 = 膠着 ❌ |

## ファイル一覧

| ファイル | 内容 |
| --- | --- |
| [`check_conversation.py`](check_conversation.py) | 上記 4 指標を `output/prod_*/messages.jsonl` から計算するスクリプト |
| [`conversation_check.md`](conversation_check.md) | 上記スクリプトの実行結果 |
| [`find_echo_examples.py`](find_echo_examples.py) | 完全コピペ・膠着の具体ペアを抽出 |
| [`echo_examples.md`](echo_examples.md) | 実際にどの step / agent でコピペが起きていたかの抜粋(全 4 シナリオ分) |

## 使い方

```powershell
# Phase 5 で改善対策を入れたあとに再ランしたら、もう一度回す:
.\.venv\Scripts\python.exe docs/04_モデル検証/conversation_check/check_conversation.py
.\.venv\Scripts\python.exe docs/04_モデル検証/conversation_check/find_echo_examples.py

# echo_max が 1.0 から下がっていれば、対策が効いている
```

## 関連ドキュメント

- 詳細議論:[2026-04-30 問題点リスト §7](../../03_ToDo/2026-04-30_問題点リスト.md#7-llm-同士が実際には会話していない問題2026-04-30-追加)
- Phase 4-A 検証ログ:[Phase4-A 本番ラン](../../03_ToDo/verifications/Phase4-A_本番ラン_2026-04-30.md)
- Phase 5 で実施する対策:同上 §7-E(7 項目)

## 検出された主な原因仮説

1. **`=== MESSAGES FROM OTHERS ===` セクションが強すぎる** — 受信した発言を LLM が「お手本」として直接コピー
2. **状態記述が固定的すぎる** — 毎 step 同じ PERSONA + ENVIRONMENT 注入で「同じ入力 → 同じ出力」化
3. **`max_tokens=512` の長文要求** — 短い感情表現で済むところを長文化させ、定型句で字数稼ぎ
4. **指示が多すぎる** — 議事録 §3.4 の兵頭氏アドバイス(「指示を書きすぎない」)に反する状態
