# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

Singulab ハッカソン(2026-05-07 提出)向けの、LLM エージェントによる多体社会シミュレーション。
兵頭氏の **3 階層フレームワーク**(1 階:物 / 2 階:環境 / 3 階:物理・重力)に沿って世界を構築し、
ルールでは書けない **創発** を観察する。LLM 推論は **Ollama** (ローカル) 経由。

## よく使うコマンド

```bash
# シミュレーション実行(基本形)
python -m src.main --config config/scenario_alien_5.yaml --output-dir output/run_xxx

# テスト
pytest                                # 全件
pytest tests/test_phase5_events.py    # 単一ファイル
pytest tests/test_phase3_persona.py::test_xxx  # 単一テスト

# 単一ランの解析(metrics.json を生成)
python -m tools.analyze_run output/<run_dir>

# 複数ランの横並び集計
python -m tools.aggregate_runs output/

# フレーム PNG → mp4(要 FFmpeg)
python -m tools.generate_video output/<run_dir>

# 議事録 ↔ 要件定義の整合チェック(本番ラン前に必ず)
python tools/check_design_freshness.py

# 本番ランの一括実行(PowerShell, .venv 前提)
pwsh scripts/run_prod_runs.ps1
```

実行前に Ollama が起動済みで、`config.llm.model` のモデルが pull 済みであること。
未接続なら `Simulation.run()` は冒頭でエラー終了する。

## アーキテクチャ

### 3 階層 + エージェント(設計の中核)

[src/](src/) は兵頭氏フレームワークの 3 階層に分かれる。各層を直接弄らず、
エントリポイントの [src/simulation.py](src/simulation.py) が層をまたぐ責務を持つ。

| 層 | モジュール | 役割 |
| --- | --- | --- |
| 1 階 (物) | [src/world/](src/world/) | `World` が place 解決 / capacity 強制 / 移動を集約。`agent.move()` 直叩きは禁止、必ず `World.attempt_move` 経由 |
| 2 階 (環境) | [src/world/environment.py](src/world/environment.py) | `Environment.economy` 等、見えないが影響する量。プロンプト断片を生成 |
| 3 階 (物理) | [src/physics/](src/physics/) | `WorldLaws`(通信半径・認知上限・遅延)+ `CommunicationPhysics`(到達判定) |
| エージェント | [src/agent/](src/agent/) | `Agent` が LLM 経由で `decide_message` / `decide_action` を返す。`Persona`(MBTI/年齢/国籍)はプロンプト断片化 |

### Simulation のステップ構造

[src/simulation.py](src/simulation.py) の `step_simulation()` は以下の固定順:

1. **Event 発火判定** — [src/events/](src/events/) (`fire` / `alien` / `zero_gravity`)。`base.collect_perceived_events` でエージェント視点に変換
2. **メッセージ決定** — `CommunicationPhysics.determine_recipients` で近傍特定 → `agent.decide_message`
3. **メッセージ送信** — `receive_message` が認知メモリイベント(`memory_evicted` / `re_encountered`)を返す
4. **行動決定** — `agent.decide_action`(直前のメッセージを文脈に含める)
5. **移動実行** — `World.attempt_move` が capacity 違反を `place_entry_denied` イベントで弾く
6. **統計・履歴・可視化** — `viz.Visualizer` がフレーム PNG を保存

### ログと出力(出力先 `output/<run_dir>/`)

- `messages.jsonl` / `memory_reasoning.jsonl` / `events.jsonl` — [src/runlog/jsonl.py](src/runlog/jsonl.py) の `JsonlLogger`
- `run_metadata.json` — シナリオ・seed・personas・LLM 設定。**ラン後解析の根拠**
- `frames/frame_*.png` + `simulation.mp4` — `visualization.save_frames=true` のとき
- `metrics.json` — `tools.analyze_run` 実行後に生成

### Config(YAML 継承)

[config/](config/) はすべて [config/base.yaml](config/base.yaml) を `extends:` で継承する形(`src/config_loader.py`)。
シナリオ側は **差分のみ** 書く。本番シナリオ命名: `scenario_<theme>_<num_agents>.yaml`(例: `scenario_alien_100.yaml`)。

イベントは新形式 `events:` セクション(`type: fire | alien | zero_gravity`)を使う。
旧 `fires:` セクションは後方互換のためにのみ残されている。

### LLM クライアント

[src/llm/ollama.py](src/llm/ollama.py) のみ。Qwen3 系の `think:` パラメータに対応(MBTI ペルソナの効果を測るため `think:false` がデフォルト運用)。

## プロジェクト固有の運用ルール

> 2026-04-30 ステージ F(プロセス改善)で導入。
> Phase 4 で議事録未読のまま本番ランを実行し、約 4 時間を無駄にした事故([問題点リスト §2-A](docs/03_ToDo/2026-04-30_問題点リスト.md))の再発防止。

### 1. 重要な切替はユーザ承認が必要(F-2)

以下の操作は **必ずユーザに 1 行確認**(「○○に切り替えていいですか?」)を入れてから実行する。独断不可:

- LLM モデルの切替(本番中、シナリオを跨いでの差し替えも含む)
- 集団サイズの大きな変更(5 → 50、10 → 100 等、3 倍を超える変更)
- シナリオの差し替え(`scenario_alien_5` → `scenario_zero_gravity_5` のような根本的な切替)
- 既存の `output/prod_*` を上書きする操作
- 1 時間以上かかる見込みの逐次ラン
- 粉川氏マシン側で実行すべきラン(34B × 100 体)を私側で代替実行しようとする
- `.gitignore` の変更や、コミット済みファイルの削除

> **理由**:Phase 4 で走行中に Qwen3 4B → Llama 3.2 3B → Qwen3 4B と独断で切り替え、品質低下と中国語混入を招いた([問題点リスト §2-B](docs/03_ToDo/2026-04-30_問題点リスト.md))。

### 2. タスク完了判定の二段化(F-3)

タスクを「完了」にできるのは以下の **両方** が満たされたとき:

| 段階 | 完了条件 |
| --- | --- |
| **段階 1**(私) | 成果物が生成された(ファイル存在 / テスト合格 / メトリクス出力)|
| **段階 2**(ユーザ) | ユーザがその成果物を **意図したものか確認**した |

- todo の `completed` ステータスは段階 1 達成で付けてよい。ただし段階 2 が未確認なら **報告時に「ユーザ確認待ち」と明示**する
- 重要な節目(本番ラン完走、提出物生成、コミット)では「これで意図と合っていますか?」を 1 行確認

### 3. 本番ラン前のチェックリスト適用(F-1)

[`.claude/skills/pre-run-checklist/`](.claude/skills/pre-run-checklist/) のスキルを、以下のいずれかに当てはまるラン前に必ず通す:

- `agents.num_agents >= 10`(大集団)
- `simulation.duration >= 30`(長 step)
- 1 ランあたり **15 分以上** の見積もり
- 4 シナリオ以上の連続実行
- 提出物 PDF の元になる本番ラン
- ユーザが「本番ラン」「prod_*」を指示している

軽量な検証ラン(5 体 × 5〜10 step、`output/echo_check_*` 等)は対象外。

### 4. 議事録 → 要件定義 → 実装の流れ(F-4)

実装に入る前に、必ず:

1. **議事録**([docs/02_ミーティング/](docs/02_ミーティング/))で最新の決定を確認
2. **要件定義**([docs/01_設計書/01_要件定義/](docs/01_設計書/01_要件定義/))に議事録の決定が反映されているか確認
3. 反映されていなければ、**まず要件定義を更新**(コードを動かす前に)
4. その上で実装に入る

> **理由**:議事録の決定が要件定義に反映されないまま実装すると、後追いで設計書を直すことになり、検証ログ・PDF・コードすべてに影響が及ぶ。

## 提出マイルストーン

- 提出締切: 2026-05-07
- 次回ミーティング(粉川氏): 2026-05-03〜05-05
- 進行状況: [問題解決 ToDo](docs/03_ToDo/2026-04-30_問題解決ToDo.md)

## 重要なドキュメント

| 種別 | 場所 |
| --- | --- |
| 議事録 | [docs/02_ミーティング/](docs/02_ミーティング/) |
| 要件定義 | [docs/01_設計書/01_要件定義/](docs/01_設計書/01_要件定義/) |
| 実装ロードマップ | [docs/03_ToDo/02_実装ロードマップ.md](docs/03_ToDo/02_実装ロードマップ.md) |
| モデル / プロンプト検証ログ | [docs/04_モデル検証/](docs/04_モデル検証/) |
| エコー検証パイプライン | [docs/04_モデル検証/conversation_check/](docs/04_モデル検証/conversation_check/) |
| 100 体ラン手順書 | [docs/05_運用手順/粉川氏向け_100体ラン手順.md](docs/05_運用手順/粉川氏向け_100体ラン手順.md) |
| 問題点と再発防止 | [docs/03_ToDo/2026-04-30_問題点リスト.md](docs/03_ToDo/2026-04-30_問題点リスト.md) |

## Git ルール(IRIS 共通)

- コミットメッセージは日本語
- force push 禁止
- `.env` はコミットしない
- 兵頭氏共有コードは `.gitignore` で除外(パブリック共有禁止)
