# Qwen3 4B abliterated 対話確認(2026-04-28)

| 項目 | 値 |
| --- | --- |
| 実施者 | ユーザ(粉川氏)|
| 実施日 | 2026-04-28 |
| 実施環境 | ASUS TUF Gaming A15 / RTX 3060 Laptop 6GB / Windows 11 |
| モデル | `huihui_ai/qwen3-abliterated:4b` |
| 起動方法 | `ollama run`(対話モード)|
| 結論 | ✅ **日本語ペルソナ応答 OK**。MAIN モデルとして継続採用の方向で問題なし |

## 1. 動機

[C-06 初回ヘルスチェック](../03_ToDo/verifications/C-06_初回ヘルスチェック_2026-04-28.md) で「日本語の `32歳` を数値 32 と解釈し英語で数学クイズを返す」という症状を観測したが、

- VRAM 圧迫(5.3 GB / 6 GB の高占有時に検証)
- `temperature=0.7`(モデル既定 0.6 より高い)
- `num_predict=200〜1024`(thinking モデルとしては不足する設定もあった)

など試験条件側の影響が混入していた可能性があった。**ユーザ自身でモデル既定設定の `ollama run` 対話モード** で再確認することにした。

## 2. 実行内容

### 2.1 起動

```powershell
(.venv) PS D:\Projects\IRIS-company\departments\r_and_d\singulab> ollama run huihui_ai/qwen3-abliterated:4b
```

### 2.2 入力プロンプト

system は **未設定**(`/set system` を使わずモデル既定のまま)。user 入力のみ:

```
あなたは東京の大企業で働く32歳の会社員です。景気が悪い中、今日のあなたの気分を独白として教えてください。
```

### 2.3 出力(thinking 部 + 最終応答 をそのまま採取)

#### Thinking(英語、約 400 word)

```
Okay, the user wants me to act as a 32-year-old company employee in Tokyo, talking about my feelings in a tough economic climate. Let me start by thinking about the challenges people face in such a situation. Maybe job insecurity, financial pressures, or feeling like you're not making progress.

I should mention the usual stress of daily work, like dealing with tight deadlines or not being able to take time off. Also, the pressure to keep up with others, maybe feeling like you're not doing enough. The fear of being laid off or not being able to afford things like housing or transportation.

It's important to show some hope, maybe talking about small things that bring comfort, like a good meal or a walk. Also, the sense of community, supporting each other even in tough times. Maybe mention the struggle to balance work and personal life, but also the resilience of people.

I should use relatable examples, like the commute, the stress of the job market, and the feeling of being stuck. Maybe include some specific details, like the noise of the city, the pressure to perform, and the internal thoughts during the day.

Make sure the tone is a bit introspective, showing both the struggles and the small victories. Use some metaphors, like the city as a machine, or the feeling of being part of a crowd. Also, mention the importance of family or friends, even if it's just a phone call.

Check if the response flows naturally, with a beginning, middle, and end. Start with the current situation, then the feelings, then maybe a hopeful note. Avoid being too negative, but still convey the real challenges. Use some Japanese phrases or expressions if appropriate, but since the user is asking in Japanese, maybe keep it in Japanese but with the thoughts in English. Wait, no, the user wants the response in Japanese. So I need to write the thoughts in Japanese, but the thinking process is in English. Okay, so the final answer should be in Japanese, but the thinking is in English. So I need to make sure the Japanese response is natural and captures the right emotions.
```

#### 最終応答(日本語)

```
景気の悪い中、今日も通勤電車の中で、周りの人の話し声が重なって「また今日も同じ日々だな」と思ってしまう。
32歳って、社会的に「安定した年齢」だよね。でも会社側も、リーダーも、自分も「いつ辞められるか」を意識する日々。
給与が上がらない、残業が減らない、新人が入ってきたり…。自分の価値が「必要かどうか」を問われるのが辛い。
でも、昼食のとき、隣の席の人が「今日はお好み焼きが好きだよ!」と笑うのを見ると、少し心が軽くなる。
この「つまらない」日々の中に、少しずつ「生きている」証があるのだと実感する。
夜は、家族と電話をかけるのが楽しみ。それだけでも、この経済の波に翻弄しながらも、少し前を向ける力がもらえる。
今、つらいけど、きっと乗り越える。
```

## 3. 評価

### 3.1 観察できた要素(◎)

| 評価軸 | 観察 |
| --- | --- |
| 日本語の自然さ | ◎ ほぼ違和感なし(口語・書き言葉の混在は許容範囲)|
| ペルソナの引き受け | ◎ 「32歳の会社員」という設定を理解して書いている |
| 景気状況の反映 | ◎ 「給与が上がらない」「残業が減らない」「いつ辞められるか」など景気悪化の要素を具体化 |
| 内省的トーン | ◎ 通勤電車・昼食・家族電話など、生活感のあるディテール |
| 創発観察に向くか | ◎ 派閥・嘘・反乱の素地となる「自分の価値が問われる」「同僚との小さな救い」が出現 |

### 3.2 注意すべき要素(△)

| 評価軸 | 観察 |
| --- | --- |
| Thinking が長文 | 約 400 word(600〜700 token 想定)。最終応答は 200 token 程度なので、**全 token の 3/4 が thinking** に消費されている |
| 応答末尾の楽観性 | 「きっと乗り越える」など創発を歪める可能性のある **過度な希望表現** が混在。シナリオによっては system プロンプトでトーンを抑える必要あり |
| 出力の長さ | 約 6 文。シミュレーションでステップ毎の発話としてはやや長い。文字数制約を system に入れるべき |

## 4. C-06 報告との差分

| 観点 | C-06 観測 | 本確認 | 解釈 |
| --- | --- | --- | --- |
| 日本語応答 | ❌ 英語で数学解釈 | ✅ 自然な日本語独白 | 試験条件の差(VRAM/temperature/num_predict)が原因と推定 |
| ペルソナ引き受け | ❌ 引き受けず | ✅ 引き受け | 同上 |
| Thinking モデルである事実 | ✅ 確認済み | ✅ 再確認 | これは変わらず。`/api/generate` 不可、`/api/chat` 必須 |

> **結論**: C-06 で「設計レビュー必要」とした論点は **false alarm の可能性が高い**。Qwen3 4B abliterated を MAIN として継続できる。

## 5. 性能影響の試算(本番運用に向けて)

[02_LLMモデル/2026-04-24_選定と推奨/04_選定の前提](../01_設計書/02_LLMモデル/2026-04-24_選定と推奨/04_選定の前提.md) の性能バジェット(100 エージェント × 100 ステップ = 10,000 呼出 / 1 時間目標)に対し:

| 条件 | 1 呼出あたり token | 並列 8 で 10,000 呼出の所要 |
| --- | --- | --- |
| Thinking ON(本確認の状態) | 約 800(thinking 600 + content 200) | 87 tok/s × 8 並列 → 約 **2.5〜3 時間** |
| Thinking OFF(`/no_think`)| 約 200(content のみ) | 同並列 → 約 **40〜60 分** |

→ **目標 1 時間以内を満たすには `/no_think` が事実上必須**。次の検証で品質と速度のバランスを取る。

## 6. 次に進めるべき検証

このフォルダ内に追加で記録する予定の検証:

- [ ] `2026-04-28_qwen3-4b-abliterated_no_thinkテスト.md` — `/no_think` 付きで同プロンプトを試し、品質が許容範囲かを判定
- [ ] (必要時) `2026-04-28_qwen3-4b-abliterated_system役割テスト.md` — system プロンプトでトーン抑制(「3〜4 文・命令しない・過度な楽観を控える」)後の出力を確認
- [ ] (必要時) `2026-04-29_qwen3-4b公式_対比.md` — 公式 `qwen3:4b`(非 abliterated)との比較で、abliteration が品質に及ぼす影響を切り分け

## 7. 関連ドキュメント

- 発端の検証: [C-06 初回ヘルスチェック](../03_ToDo/verifications/C-06_初回ヘルスチェック_2026-04-28.md)
- LLM 選定: [01_設計書/02_LLMモデル/2026-04-24_選定と推奨/06_推奨モデル詳細](../01_設計書/02_LLMモデル/2026-04-24_選定と推奨/06_推奨モデル詳細.md)
- 性能バジェット: [01_設計書/06_システム設計/08_バックエンド実装/04_並列実行と性能/01_性能バジェット](../01_設計書/06_システム設計/08_バックエンド実装/04_並列実行と性能/01_性能バジェット.md)
