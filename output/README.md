# output/ ディレクトリ構成

> 2026-05-01 整理。それまで `output/` 直下に 30 件超のラン結果が散らばっていたため、目的別にカテゴリ分けした。
> **新しいランは引き続き `output/` 直下に出力される**(`scripts/*.ps1` および `python -m src.main --output-dir output/...` の慣行)。完走後、用途に応じて該当カテゴリへ手動で移すこと。

## カテゴリ一覧

| ディレクトリ | 用途 | 含まれるラン |
| --- | --- | --- |
| [01_phase_dev/](01_phase_dev/) | 開発時のフェーズ別動作検証 | `phase1_smoke` / `phase2_smoke` / `phase2_bad_econ` / `phase2_cognition` / `phase15_viz_demo` / `phase3_local_startup` / `phase3-3_local_enterprise` / `phase3-3_local_startup` / `phase3-3_urban_enterprise` / `phase3-3_urban_startup` |
| [02_echo_check/](02_echo_check/) | エコー対策検証(M-08 関連) | `echo_check_v1` / `echo_check_v2_mbti` |
| [03_prod_4quadrant_legacy/](03_prod_4quadrant_legacy/) | 旧 4 象限本番(廃止された比較軸) | `prod_local_enterprise` / `prod_local_startup` / `prod_urban_enterprise` / `prod_urban_startup` 各々 + `*_stdout.log` / `prod_runs_summary.log` / `prod_summary.csv` |
| [04_prod_v2_event/](04_prod_v2_event/) | 新比較軸(集団サイズ × 創発イベント)本番ラン | `prod_v2_alien_5` / `prod_v2_zero_gravity_5` |
| [05_seg_check/](05_seg_check/) | 段 2(personal_context)+ 段 3(イベント観察距離依存)機能検証 | `seg2_check_alien_5` + `*.stdout.log` / `seg3_check_alien_5` + `*.stdout.log` |
| [06_misc/](06_misc/) | その他成果物 | `sample_simulation.mp4`(動画化サンプル)/ `singulab_submission.pdf`(過去版提出 PDF) |

## カテゴリ判断のルール

新しいランを完走したら、以下で振り分け:

- **本番ラン**(議事録の決定事項に基づく、提出物 PDF の元になる)→ 比較軸の世代に合わせて 03 / 04
- **機能検証ラン**(新機能の動作確認、対策の効き検証)→ 02 / 05 / 必要なら新カテゴリ
- **開発時のスモーク・デモ**(5 体程度 × 短 step)→ 01
- **動画・PDF などの一回限り成果物** → 06

## ラン名から探したい場合

| ラン名 | 場所 |
| --- | --- |
| `phase*` で始まるもの | [01_phase_dev/](01_phase_dev/) |
| `echo_check_*` | [02_echo_check/](02_echo_check/) |
| `prod_local_*` / `prod_urban_*`(4 象限) | [03_prod_4quadrant_legacy/](03_prod_4quadrant_legacy/) |
| `prod_v2_*`(新比較軸) | [04_prod_v2_event/](04_prod_v2_event/) |
| `seg2_*` / `seg3_*` | [05_seg_check/](05_seg_check/) |
| `*.mp4` / `*.pdf` 一回限り | [06_misc/](06_misc/) |

## 既存ドキュメントからの参照

整理前のドキュメント(M-XX 検証ログ・要件定義書・問題解決 ToDo 等)は旧パス(例: `output/prod_v2_alien_5/`)で参照している箇所がある。リンクが切れている場合は `04_prod_v2_event/prod_v2_alien_5/` と読み替えること。今後リンク修正は必要時に都度対応する。

## .gitignore との関係

`output/` 配下は基本的に `.gitignore` 対象(容量が大きいため)。例外で git 管理したいラン(粉川氏側からの 100 体結果など)は明示的に `git add -f` するか、`.gitignore` の例外行で個別解除する。
