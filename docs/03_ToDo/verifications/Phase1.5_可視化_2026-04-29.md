# Phase 1.5 (A-viz): 可視化(matplotlib + FFmpeg)検証ログ

| 項目 | 値 |
| --- | --- |
| 実施日 | 2026-04-29 |
| 範囲 | A-viz(Phase 1 残タスク)+ tools/generate_video.py + base.yaml に visualization セクション |
| 結果 | ✅ **PNG フレーム → mp4 のパイプラインが完走**(5 フレーム / 26.9 KB) |

## 1. 完了タスク

| 項目 | 内容 | 場所 |
| --- | --- | --- |
| FFmpeg 確認 | 8.0 essentials を `C:\ffmpeg\bin\ffmpeg.exe` で確認 | (システム既存) |
| Visualizer 移植 | 参考実装 visualization.py を Windows 互換に移植(Agg バックエンド固定)| [src/viz/visualizer.py](../../../src/viz/visualizer.py) |
| Simulation 統合 | `visualization.save_frames=true` で各ステップに `frames/frame_XXXX.png` 保存 | [src/simulation.py](../../../src/simulation.py) |
| 動画生成 CLI | `python -m tools.generate_video <run_dir>` で mp4 化 | [tools/generate_video.py](../../../tools/generate_video.py) |
| config 拡張 | base.yaml に `visualization: {save_frames, frame_interval}` セクション | [config/base.yaml](../../../config/base.yaml) |

## 2. 既存コードからの差分(参考実装 vs 本実装)

| 観点 | 参考実装 | 本実装 |
| --- | --- | --- |
| OS 検出 | `os.uname()` 使用(Windows で例外)| **削除**。Agg 固定で全 OS 動作 |
| バックエンド | 状況に応じて GUI / non-GUI を切替 | フレーム保存目的のため **Agg 固定**(GUI 不要)|
| フレーム保存先 | `output/frame_XXXX.png` | `<run_dir>/frames/frame_XXXX.png`(サブディレクトリ化)|
| frame_interval | なし | **追加**:N ステップに 1 枚にできる |
| place 色マップ | bar/cafe/library | **office/meeting/bar/cafe/library/restaurant/park** に拡張 |
| 動画生成 | Python 内 ffmpeg 呼出 | **`tools/generate_video.py` に分離**(ラン後に好きな fps で再生成可)|

## 3. スモークテスト

### 3.1 シナリオ([config/scenario_phase15_viz_demo.yaml](../../../config/scenario_phase15_viz_demo.yaml))

```yaml
extends: "scenario_local_startup.yaml"  # 地方×スタートアップ×bad
simulation:
  duration: 5
visualization:
  save_frames: true
  frame_interval: 1
```

### 3.2 実行

```powershell
.venv\Scripts\python.exe -m src.main \
    --config config/scenario_phase15_viz_demo.yaml \
    --output-dir output/phase15_viz_demo

python -m tools.generate_video output/phase15_viz_demo --fps 2 -y
```

### 3.3 出力

```
output/phase15_viz_demo/
├── events.jsonl          (938 B)
├── memory_reasoning.jsonl (10 KB)
├── messages.jsonl        (35 KB)
├── run_metadata.json     (2 KB)
├── simulation.log        (36 KB)
├── frames/               ← Phase 1.5 で追加
│   ├── frame_0001.png    (43 KB)
│   ├── frame_0002.png    (43 KB)
│   ├── frame_0003.png    (42 KB)
│   ├── frame_0004.png    (43 KB)
│   └── frame_0005.png    (43 KB)
└── simulation.mp4        (27 KB) ← Phase 1.5 で追加
```

### 3.4 フレーム品質(step 3 の例)

サンプルで確認:
- main_office(青)+ meeting_room(緑)の入れ子配置
- 5 体のエージェント(青星 = male & in_place、ID ラベル付き)
- 通信半径内のペアを灰色の線で接続
- タイトル: `Step 3 | in places: 5 (100%) | main_office: 5/20 | meeting_room: 0/5`
- 凡例: gender × in_place の 4 種

## 4. 設計書との整合

| 設計書要求 | 実装 | 備考 |
| --- | --- | --- |
| [02_モジュール構成 §1 ディレクトリ](../../01_設計書/06_システム設計/02_モジュール構成/01_ディレクトリ構成.md) `src/viz/visualizer.py` | ✅ | |
| 同上 `tools/generate_video.py` | ✅ | |
| [01_アーキテクチャ概要/02_コンポーネント責務](../../01_設計書/06_システム設計/01_アーキテクチャ概要/02_コンポーネント責務.md) Visualizer 責務 | ✅ フレーム保存・通信半径・火事円・タイトル | 統計プロットは保留 |

## 5. 規模見積もり

スモーク実測値から本番ランの想定:

| シナリオ | フレーム数 | フレームサイズ | mp4 サイズ |
| --- | --- | --- | --- |
| 5 体 × 5 step(本検証)| 5 | 約 43 KB/枚 | 27 KB |
| 10 体 × 30 step | 30 | 約 50 KB/枚 | ~200 KB |
| 100 体 × 100 step | 100 | 約 100 KB/枚 | ~2 MB |

→ 本番想定の 100 体 × 100 step でも **mp4 は 2 MB 程度に収まる** 見込み。提出物に同梱可能。

## 6. 注記

### 6.1 frame_interval の活用

100 step ランで毎ステップ保存すると 100 PNG = 10 MB。**`frame_interval: 5`** にすれば 20 PNG / ~2 MB に削減可能。提出物用にはこれで十分。

### 6.2 動画 fps の選び方

`tools.generate_video --fps N` で再生速度を変えられる:

- 短ラン(5 step): **fps=1〜2**(各ステップを目視できる)
- 中ラン(20〜30 step): **fps=3〜5**
- 長ラン(100 step): **fps=10**(視覚的なスムーズさ優先)

### 6.3 Phase 1 互換性

`visualization.save_frames` のデフォルトは false なので、既存シナリオは何もせず動く(可視化なし)。動画化したいシナリオで明示的に `true` に上書き。

## 7. 次に進むタスク

- 🔴 **本番ラン**(別フェーズ): 採用モデル切替 + 30+ step + 複数 seed + 動画化
- 🟡 M-05 Qwen3 `/no_think` 解決(本番ラン前段)
- 🔴 Phase 4 提出物作成(動画 4 本含む形でアセットを用意可能になった)

## 8. 関連ドキュメント

- 出力: [output/phase15_viz_demo/](../../../output/phase15_viz_demo/)(frames + mp4)
- src: [src/viz/visualizer.py](../../../src/viz/visualizer.py)
- tools: [tools/generate_video.py](../../../tools/generate_video.py)
- 設計書: [02_モジュール構成](../../01_設計書/06_システム設計/02_モジュール構成/) / [04_可視化出力](../../01_設計書/06_システム設計/06_ロギング・出力/04_可視化出力.md)
