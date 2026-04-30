# Singulab プロジェクト詳細ルール

> Singulab ハッカソン(2026-05-07 提出)向け LLM 多体社会シミュレーションの開発・運用ルール集。
> [CLAUDE.md](../../CLAUDE.md) の運用ルールを補強し、コード変更時に守るべき設計上の不変条件を明文化する。

---

## 1. アーキテクチャ不変条件(コード変更時に必ず守る)

### 1.1 3 階層を跨ぐ責務分離

兵頭氏フレームワークの **1 階(物)/ 2 階(環境)/ 3 階(物理)** は混ぜない。

| 層 | 責務 | NG パターン |
| --- | --- | --- |
| 1 階 [src/world/](../../src/world/) | place 解決・capacity・移動 | `Agent` 内で place 配列を直接走査して capacity を判定する |
| 2 階 [src/world/environment.py](../../src/world/environment.py) | 経済状況などの不可視量、プロンプト断片化 | `Agent` で `os.getenv("ECONOMY")` を読む |
| 3 階 [src/physics/](../../src/physics/) | 通信半径・認知上限・遅延の判定 | `Agent.get_nearby_agents()` を新規追加して半径計算する |

**新しい近傍判定が必要になったら必ず `CommunicationPhysics.determine_recipients` を拡張**。エージェント側に距離計算を増やさない。

### 1.2 移動は World 経由のみ

- `agent.position = ...` の直接代入は禁止(`World.attempt_move` のみ)
- `agent.move(direction)` も使わない(Phase 2 で廃止済み)
- 新しい移動規則(瞬間移動、テレポート等)は `World` に新メソッドを足し、capacity チェックを必ず通す

### 1.3 イベント追加は `events/` 以下に閉じる

新規イベント(地震・停電など)を追加するときの手順:

1. [src/events/base.py](../../src/events/base.py) の `Event` 基底を継承
2. `maybe_activate(step)` と `state()` を実装
3. [src/simulation.py](../../src/simulation.py) の `events:` ループに `elif etype == "..."` を追加
4. プロンプト見え方は `collect_perceived_events` に入る形にする(`Agent` を直接書き換えない)

旧 `fires:` セクションは後方互換目的でのみ残す。新規シナリオでは必ず `events:` 形式で書く。

### 1.4 Config は `extends: base.yaml` で差分のみ

- [config/base.yaml](../../config/base.yaml) の値を全シナリオに複製しない
- ペルソナスキーマは `age / gender / nationality / mbti`(2026-04-29 改訂版)のみ。旧スキーマ(`name / role / tenure_years / ...`)を復活させない
- シナリオ命名規則: `scenario_<theme>_<num_agents>.yaml`

### 1.5 ログは `JsonlLogger` 経由で必ず構造化

- `print()` でデータを残さない(stdout は人間用ログのみ)
- `messages.jsonl` / `memory_reasoning.jsonl` / `events.jsonl` のスキーマを変える場合は **必ず `tools/analyze_run.py` の読み手と同時に変更**(片側だけ変えると過去ランの解析が壊れる)
- `run_metadata.json` はラン後解析の根拠なので、新フィールドの追加は OK だが、既存フィールドの **改名・削除は禁止**(過去ランとの互換が切れる)

---

## 2. 本番ラン運用ルール(プロセス改善 F-1〜F-4)

### 2.1 重要な切替はユーザ承認が必要(F-2)

以下は **必ず 1 行確認**(「○○に切り替えていいですか?」)を入れる。独断不可:

- LLM モデルの切替(本番中・シナリオ間も含む)
- 集団サイズ 3 倍超の変更(5 → 50、10 → 100 等)
- シナリオの根本差し替え(`scenario_alien_5` → `scenario_zero_gravity_5` 等)
- `output/prod_*` の上書き
- 1 時間以上かかる逐次ラン
- 粉川氏マシンで実行すべきラン(34B × 100 体)を私側で代替実行
- `.gitignore` 変更、コミット済みファイル削除

> 事故事例: Phase 4 で走行中に Qwen3 4B → Llama 3.2 3B → Qwen3 4B と独断切替し、品質低下と中国語混入を招いた。

### 2.2 タスク完了は二段階(F-3)

| 段階 | 完了条件 |
| --- | --- |
| 段階 1(私) | 成果物が生成された(ファイル存在 / テスト合格 / メトリクス出力)|
| 段階 2(ユーザ)| ユーザが意図したものか確認した |

- todo の `completed` ステータスは段階 1 達成で付けてよい
- 段階 2 が未確認なら **報告時に「ユーザ確認待ち」と明示**
- 節目(本番ラン完走 / 提出物生成 / コミット)では「これで意図と合っていますか?」を 1 行確認

### 2.3 本番ラン前チェックリスト(F-1)

[`.claude/skills/pre-run-checklist/`](../skills/pre-run-checklist/) を必ず通す条件:

- `agents.num_agents >= 10`
- `simulation.duration >= 30`
- 1 ランあたり 15 分以上の見積もり
- 4 シナリオ以上の連続実行
- 提出物 PDF の元になる本番ラン
- ユーザが「本番ラン」「prod_*」を指示している

軽量検証(5 体 × 5〜10 step、`output/echo_check_*`)は対象外。

### 2.4 議事録 → 要件定義 → 実装の順守(F-4)

実装着手前に必ず:

1. 議事録([docs/02_ミーティング/](../../docs/02_ミーティング/))で最新の決定を確認
2. 要件定義([docs/01_設計書/01_要件定義/](../../docs/01_設計書/01_要件定義/))に反映済みか確認
3. 反映されていなければ **要件定義を先に更新**(コードを動かす前に)
4. その後で実装

簡易整合チェック: `python tools/check_design_freshness.py`

---

## 3. テスト・コード変更のルール

### 3.1 Phase 命名は変えない

`tests/test_phase2_*.py` `tests/test_phase3_*.py` `tests/test_phase5_*.py` の Phase 番号は **実装ロードマップ**([docs/03_ToDo/02_実装ロードマップ.md](../../docs/03_ToDo/02_実装ロードマップ.md))の章番号と一致している。リネーム禁止。

### 3.2 ランダム性のあるテストは `random_seed` を固定

`base.yaml` の `random_seed: 42` がデフォルト。テストで再現性が要るときは Simulation 構築前に `random.seed()` / `np.random.seed()` を呼ぶ。

### 3.3 Ollama 依存テストは書かない

LLM 呼び出しを伴うテストは CI で落ちる。`OllamaClient` を直接呼ぶテストは `pytest.mark.skip` か、モック化で。

### 3.4 出力ディレクトリの安全策

- 既存の `output/prod_*` を上書きするスクリプトは書かない(2.1 ルール違反)
- 一時検証は `output/echo_check_*` または `output/run_<timestamp>` に出す
- `output/` 配下のフレーム PNG・mp4 は容量が大きいので、不要なものは PR 前に削除

---

## 4. ドキュメント・コミットのルール

### 4.1 議事録の決定を即コードに落とさない

議事録 → 要件定義 → 実装の順序を必ず通す(2.4)。要件定義の更新を伴う PR は、まず docs だけのコミットを切ってから実装コミットを足すと履歴が追いやすい。

### 4.2 コミットメッセージは日本語

IRIS 共通ルール。フェーズ・ステージの番号(例:「ステージ F(プロセス改善)完了」)を含めると進捗が追いやすい。

### 4.3 兵頭氏共有コードは公開しない

[docs/10_共有資料/](../../docs/10_共有資料/) は `.gitignore` 済み。ここから snippet を別ファイルにコピーして公開可能領域に出さない。

### 4.4 Force push 禁止 / `.env` 禁止

IRIS 共通。

---

## 5. クイックリファレンス

### 5.1 主要パス

| 用途 | パス |
| --- | --- |
| エントリポイント | [src/main.py](../../src/main.py) |
| シミュレーション本体 | [src/simulation.py](../../src/simulation.py) |
| LLM クライアント | [src/llm/ollama.py](../../src/llm/ollama.py) |
| 本番ラン PowerShell | [scripts/run_prod_runs.ps1](../../scripts/run_prod_runs.ps1) |
| 解析ツール | [tools/analyze_run.py](../../tools/analyze_run.py) / [tools/aggregate_runs.py](../../tools/aggregate_runs.py) |
| 動画生成 | [tools/generate_video.py](../../tools/generate_video.py) |
| 設計鮮度チェック | [tools/check_design_freshness.py](../../tools/check_design_freshness.py) |

### 5.2 提出マイルストーン

- 提出締切: 2026-05-07
- 次回 MTG(粉川氏): 2026-05-03〜05-05
- 進行状況: [docs/03_ToDo/2026-04-30_問題解決ToDo.md](../../docs/03_ToDo/2026-04-30_問題解決ToDo.md)
