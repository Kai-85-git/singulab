# 05_ディレクトリ構成(`config/`)

```
config/
├── base.yaml                      # 共通デフォルト(llm / logging / visualization)
├── scenario_bar_fire.yaml         # 参考実装と等価
├── scenario_cells.yaml            # 細胞シナリオ
├── scenario_virus_human.yaml      # ウイルス × 人間
└── scenario_moon_independence.yaml # 月面独立運動
```

CLI 側で `--config config/scenario_bar_fire.yaml` のように指定する。`base.yaml` はインクルード的に扱う(内部でマージ)。

---

← [04_バリデーション方針](04_バリデーション方針.md) | [README](README.md) | → [06_マイグレーション](06_マイグレーション.md)
