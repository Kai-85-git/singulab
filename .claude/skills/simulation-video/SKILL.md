---
name: simulation-video
description: Singulab シミュレーションのラン結果(`output/<run_dir>/`)から、左にフィールド画像・右にメッセージと思考のサイドパネルを並べた動画(`simulation_with_text.mp4`)を生成する。エージェントごとに色分け・年齢/性別/MBTI を表示し、固定スロット配置でかくつかない。**動画を作って欲しい・mp4 を作りたい・simulation の様子を確認したい・思考やメッセージが見える動画にしたい・粉川氏や提出物に共有する動画が欲しい・ラン結果を可視化したい・seg・prod 系のラン dir を可視化したいと言われたら必ずこのスキルを使う**(普通の `simulation.mp4` だけ欲しいときは `tools/generate_video.py` を直接呼ぶ)。
---

# simulation-video

Singulab のラン結果ディレクトリ(`messages.jsonl` / `memory_reasoning.jsonl` / `frames/*.png` / `run_metadata.json` を含むもの)から、**フィールド画像 + 右側にメッセージ・思考の固定スロットパネル + ペルソナラベル(年齢/性別/MBTI)** を並べた `simulation_with_text.mp4` を生成する。

参考実装(`docs/10_共有資料/.../simulation.mp4`)はフィールド単体のみ表示だが、本スキルは右側パネルを追加して「会話の流れ」と「内面(memory / reasoning)」を 1 本で同時に追えるようにしたもの。2026-05-01 のセッションで作成。

## いつ使うか

- 「動画を作って」「動画を見やすくして」「mp4 にして」と頼まれたとき
- 「シミュレーションの様子を確認したい」「ラン結果を可視化したい」と言われたとき
- 提出物(粉川氏共有・ハッカソンプレゼン用)で**会話と思考が同時に見える動画**が必要なとき
- ラン名の例:`prod_v3_alien_5` / `seg3_check_alien_5` / `prod_v2_*` / 任意の `output/**/run_dir`

「シンプルにフィールドだけの動画でいい」(従来の `simulation.mp4`)を望んでいる場合はこのスキルではなく `tools/generate_video.py` を使う。

## 前提

- Ollama 等のラン実行は不要(既に完走したラン dir を入力にする)
- ラン dir に以下が揃っていること:
  - `frames/frame_*.png`(フィールド画像)
  - `messages.jsonl`
  - `memory_reasoning.jsonl`
  - `run_metadata.json`(personas を読むため)
- ffmpeg がパスにあること(なければ PNG 段階で停止する)

## 使い方

`tools/generate_video_with_text.py` を呼ぶだけ。プロジェクトルート(`departments/r_and_d/singulab/`)で実行する。

```bash
python -m tools.generate_video_with_text <run_dir> [--fps 2] [--recent 5] [-y]
```

出力:
- `<run_dir>/frames_with_text/frame_*.png`(中間、再生成可)
- `<run_dir>/simulation_with_text.mp4`(本命)

## 既定値と微調整の指針

| オプション | 既定値 | 上げる/下げる判断 |
| --- | --- | --- |
| `--fps` | `2` | `1` にすると 1 フレーム読みやすい(static に近づく)。`3〜4` でテンポよく流す |
| `--recent` | `6`(コードのデフォルト)、本番で 100 体クラスは `5` 推奨 | スロット数=表示するメッセージ数。エージェント数や duration が長いランは少なめに(各スロットを大きく) |
| `-y` | OFF | 既存 mp4 を上書きしたいとき必須 |

5 体ラン × 30 step は既定値で十分。100 体ランは `--recent 4` 程度に抑えると 1 件あたりの面積が広くなる。

## 動画レイアウトの要点(設計の why)

1. **左:フィールド画像、右:テキストパネル**(20×11 inch、1727×987 px 程度)
2. **エージェントごとの色分け**(Agent 0=青 / 1=橙 / 2=緑 / 3=赤 / 4=紫 …)。送信者と受信者で色が変わるため、誰が話しているか一目で分かる
3. **ペルソナラベル**:`Agent 2 (55歳 / 男 / ISFP)` 形式。年齢×MBTI×性別で個性が読み取りやすい
4. **固定スロット配置**:メッセージは N スロット(既定 6)、思考は num_agents スロット。**長さに応じて配置がジャンプしない**(=「かくつき」防止)。短いメッセージは空行で埋め、長いメッセージは末尾「…」で省略
5. **メッセージ本文は常に 2 行**(`_wrap_fixed_lines()`)。これがレイアウト安定の本質
6. **思考は Agent 0〜N を id 順で固定**。その step に発話していなくてもスロットは確保される(空欄)
7. **背景色**でセクション区別:メッセージ=薄青、思考=薄紫、ヘッダ=濃紺
8. **日本語フォント候補**: Yu Gothic → Meiryo → MS Gothic → Hiragino Sans → Noto Sans CJK JP → sans-serif

## トラブルシューティング

| 症状 | 原因 / 対応 |
| --- | --- |
| `ERROR: no frames directory` | ラン中に `visualization.save_frames: true` が無効だった可能性。base.yaml で確認 |
| `ERROR: ffmpeg not found` | `winget install ffmpeg` または `--ffmpeg <path>` で明示 |
| 動画がかくつく | 既に固定スロットだが、`--recent` を増やしすぎると 1 件あたりの面積が縮む。減らす |
| 文字化け(コンソール上) | Windows cp932 表示だけの問題。出力 PNG / mp4 自体は UTF-8 で正しく描画される |
| 既存 `simulation_with_text.mp4` で `output already exists` | `-y` を付けて上書き |
| メッセージが切れて読みにくい | `--recent` を減らす(スロット数を減らすと 1 件あたり 2 行 → そのままだが面積拡大) or `_wrap_fixed_lines` の `max_lines` を 3 に増やすコード改修 |
| ペルソナラベルが表示されない | `run_metadata.json` の `personas` フィールド欠落。M-13 以降のランなら必ず存在 |

## 関連

- 元ツール:[tools/generate_video_with_text.py](../../../tools/generate_video_with_text.py)
- 従来形式(フィールドのみ):[tools/generate_video.py](../../../tools/generate_video.py)
- 検証ログでの動画利用例:[M-12](../../../docs/04_モデル検証/2026-05-01_M-12_イベント途中発火と視覚化.md) / [M-13](../../../docs/04_モデル検証/2026-05-01_M-13_インプット側多様化_段2_3.md)
- 出力先カテゴリ規約:[output/README.md](../../../output/README.md)
