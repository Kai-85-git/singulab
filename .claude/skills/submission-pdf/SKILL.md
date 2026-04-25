---
name: submission-pdf
description: Singulab ハッカソンの最終提出用 PDF(日本語・技術ブログ調)を生成する。ユーザが「提出物を作って」「PDF を作って」「ハッカソン用にまとめて」「説明資料を作って」「成果物 PDF」「審査員向けの資料」「初稿/再生成して」などと言ったとき、または `docs/`(議事録・要件定義・設計書)や `runs/`(実行ログ jsonl)を成果物にまとめる必要があるときに必ずこのスキルを使う。章単位の差し替え再生成、Pandoc + LaTeX + Noto JP による組版、検証結果(tok/s, VRAM, 完走時間, 拒否率, 創発指標)と創発観察ログ抜粋の取り込みを行う。
---

# Singulab 提出 PDF 生成

Singulab ハッカソン(締切 **2026-05-07**、初稿目標 **2026-05-01**)の最終提出 PDF を、`docs/` と `runs/` の素材から生成するためのスキル。提出物は **PDF + 別途録画する MP4** で、PDF はその思想・経緯・検証結果を伝える担当。

> 重要なメタ情報は [`templates/metadata.yaml`](templates/metadata.yaml) を参照。トーン・読者・章立ては固定。**勝手にトーンを変えない。**

## このスキルの中核

- **言語**: 日本語のみ
- **トーン**: 技術ブログ調(論文調でもカジュアルでもない)
- **読者**: ハッカソン審査員
- **エンジン**: Pandoc + XeLaTeX、フォントは Noto Sans/Serif JP
- **再生成**: 章 = 1ファイル。差し替え可能を死守
- **核となる問い**: 「LLMモデル / 男女比 / 人種 / 年齢 を変えると、創発(嘘・派閥・通貨・反乱・合意形成・発言権)はどう変わるか」をブレずに通すこと

> 技術スタックの羅列にしない。常に「**パラメータ X を変えたら創発 Y が変化した**」の構造で書く。これがブレると平凡な提出物になる。

## いつ使うか

ユーザがおおよそ以下のいずれかを意図している場合、このスキルを使う:

- 提出 PDF を最初から生成してほしい(初稿)
- 検証結果が増えたので特定の章だけ再生成してほしい
- レビュー後の修正を反映して再ビルドしてほしい
- 表紙・目次・ヘッダ・フォントのスタイル調整

ユーザが**本番の**動画を欲しがる場合は、PDF が完成してから OBS 等で実シミュレーションを収録する想定(本スキルの範囲外)。一方、**サンプル / プレースホルダ動画**は [`scripts/sample_mp4.py`](scripts/sample_mp4.py) で生成可能(`SAMPLE` ウォーターマーク付きで本物と区別)。

## ワークフロー

### Phase 1 — 状態確認(必ず最初に行う)

1. `output/` ディレクトリの存在と既存 PDF の有無を確認
2. `runs/` の最新ディレクトリと jsonl ログ(`llm_io.jsonl`、`perf.jsonl`、`vram.jsonl`、`events.jsonl`、`emergence.jsonl`)の有無を確認
3. `docs/01_設計書/`、`docs/02_ミーティング/`、`docs/00_アイデア/` の主要ファイルを Glob で把握
4. ユーザに「何を作るか」を確認:
   - **初稿**: 全章をテンプレからドラフト化
   - **章再生成**: どの章を、どの素材で更新するか
   - **スタイル変更のみ**: テンプレ・metadata だけ更新して再ビルド

### Phase 2 — 素材収集

[`scripts/collect_assets.py`](scripts/collect_assets.py) を実行して、`build/assets.json` に集約する。集約対象:

- 議事録(`docs/02_ミーティング/`)から日付・参加者・決定事項
- 設計書 README の Mermaid 図(そのまま埋め込む)
- LLM 選定根拠(`docs/01_設計書/02_LLMモデル/2026-04-24_選定と推奨/`)
- 創発シナリオ集(`docs/00_アイデア/2026-04-23_創発シナリオ集.md`)
- 実行ログ(`runs/<最新>/*.jsonl`)から数値指標と会話抜粋

ログがまだ無い場合は **「TBD: 検証実行後に差し替え」**プレースホルダを残す(消さない)。

### Phase 3 — 章ドラフト生成

[`templates/`](templates/) の章テンプレを `build/chapters/` にコピーして、Phase 2 で集めた `assets.json` を参照しつつ各章を埋める。各章の書き方は [`references/chapter_guide.md`](references/chapter_guide.md) に従う。

**章一覧(順序固定)**:

| # | ファイル | 内容 |
| --- | --- | --- |
| 00 | [`00_表紙.md`](templates/00_表紙.md) | タイトル / 著者 / 日付 / GitHub |
| 01 | [`01_思想と背景.md`](templates/01_思想と背景.md) | なぜ作るか・参考実装からの差分・3階層モデル |
| 02 | [`02_システム構成.md`](templates/02_システム構成.md) | アーキ図 / モデル選定 / ハードウェア |
| 03 | [`03_検証結果.md`](templates/03_検証結果.md) | tok/s, VRAM, 完走時間, 拒否率(表+グラフ) |
| 04 | [`04_創発観察.md`](templates/04_創発観察.md) | 嘘・派閥・通貨・反乱の生ログ抜粋 |
| 05 | [`05_頑張った点.md`](templates/05_頑張った点.md) | パラメータ比較設計と失敗・没案 |
| 06 | [`06_未解決課題.md`](templates/06_未解決課題.md) | 当日までに解けなかった問題 |
| 07 | [`07_今後の展望.md`](templates/07_今後の展望.md) | 拡張案(細胞/虫/人/ウイルス) |

各章の冒頭に HTML コメント `<!-- chapter: NN, regen-key: <hash> -->` を入れて再生成時の対象識別に使う。

### Phase 4 — PDF ビルド

```powershell
.claude/skills/submission-pdf/scripts/build_pdf.ps1 -Output output/singulab_submission.pdf
```

引数なしなら全章ビルド。`-Chapters 03,04` で章を絞れる(章単位差し替えのため)。

ビルドが落ちる主因はフォント未インストール。失敗したら [`references/pandoc_setup.md`](references/pandoc_setup.md) に従って Noto JP と XeLaTeX を確認する。

### Phase 5 — レビューループ

1. 生成 PDF をユーザに提示(`output/singulab_submission.pdf`)
2. ユーザがコメント → 指摘された章だけ `build/chapters/NN_*.md` を編集 → Phase 4 を `-Chapters NN` で再実行
3. 全章 OK になったら `output/` の最終 PDF を確定。`build/` は残す(後日の差し替え用)

### Phase 6 — サンプル MP4(任意)

ユーザが**本物の動画ではなく**「サンプル」「デモ」「プレースホルダ」動画を求めた場合のみ:

```bash
python .claude/skills/submission-pdf/scripts/sample_mp4.py
# オプション: --seconds 20 --fps 30 --out output/sample.mp4
```

`output/sample_simulation.mp4` が生成される。**`SAMPLE` ウォーターマークを必ず保持**(本物の検証結果と取り違えられないため)。本番動画は `runs/` のログが揃った後 OBS で実シミュレーションを録画する。

## 失敗・没案を残す

技術選定の議論経緯(abliterated を選んだ理由、JP モデルを断念した経緯、System.Speech → VOICEVOX への切替など)は **05_頑張った点.md** か該当章の脚注に必ず残す。「失敗を消さない」がこのプロジェクトの編集方針。

> **Why:** 思考過程を見せること自体が提出物の価値。「答えだけ書いた綺麗な資料」を出すと審査員には何も伝わらない。
> 詳細: [`references/chapter_guide.md`](references/chapter_guide.md) の「失敗の書き方」節。

## 比較設計のフレーミング

検証結果(03)・創発観察(04)・頑張った点(05)は、**必ずこの形式で書く**:

```
パラメータ X を [A → B] に変えた → 創発 Y が [P → Q] に変化した
  - 観察された会話例: ...
  - 数値裏付け: ...
  - 解釈: ...
```

技術スタックの羅列(「Ollama を使いました」「Qwen3 を選びました」)で章を埋めない。それは 02_システム構成 の仕事。

## 出力先

```
output/
  singulab_submission.pdf       # 確定版
build/
  chapters/                     # 章単位の編集中ソース
    00_表紙.md
    01_思想と背景.md
    ...
  assets.json                   # collect_assets.py の出力
  metadata.yaml                 # 著者・日付など(templates からコピー)
```

`build/` は再生成のキャッシュであり、コミットして良い(レビュー履歴として有用)。

## 関連スキル

- [`pdf`](../pdf/SKILL.md) — PDF の読み取り・分割・結合・OCR。提出 PDF 生成では使わないが、参考実装 PDF を読むときに併用する場合あり
- [`push`](../push/SKILL.md) — 生成・修正をコミット & プッシュするとき
