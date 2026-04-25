# 03_JSONL スキーマ

## 1. `messages.jsonl`(参考実装踏襲)

```json
{
  "step": 10,
  "from": 3,
  "to": 7,
  "message": "Let's go to the left bar, it's quieter there.",
  "reasoning": "I want to suggest a less crowded place."
}
```

1 メッセージ × 1 受信者で 1 行。同じメッセージを複数人に送ると複数行になる。

## 2. `memory_reasoning.jsonl`(参考実装踏襲)

```json
{
  "step": 10,
  "id": 3,
  "memory": "Agent 7 is nearby, considering the left bar.",
  "reasoning": "I chose to move left to follow Agent 7's suggestion."
}
```

## 3. `events.jsonl`(新規)

```json
{"step": 35, "type": "fire", "name": "fire_1", "action": "activated", "position": [15, 10], "params": {"intensity": 0.8, "radius": 15}}
{"step": 35, "type": "fire", "name": "fire_1", "action": "perceived", "agent_id": 3, "distance": 7.2}
```

- `activated`: イベント発生時に 1 回
- `perceived`: そのステップで各エージェントが知覚したかどうか(距離判定のログ)

## 4. `metrics.jsonl`(新規)

各ステップ 1 行。創発指標を時系列で追う。

```json
{
  "step": 10,
  "occupancy_overall": 0.55,
  "occupancy_by_place": {"left_bar": 0.42, "right_bar": 0.70},
  "agents_outside": 9,
  "messages_sent": 12,
  "unique_senders": 7,
  "agents_in_fire_radius": 0,
  "message_length_mean": 18.4,
  "novel_terms": ["money", "rule"],
  "memory_stay_rate": 0.15
}
```

指標の定義は [05_創発指標](05_創発指標.md) 参照。

## 5. `actions.jsonl`(任意)

```json
{"step": 10, "id": 3, "action": "move", "direction": "left", "from": [2, 0], "to": [1, 0]}
{"step": 10, "id": 4, "action": "stay", "direction": null, "from": [-3, 5], "to": [-3, 5]}
```

---

← [02_出力ファイル一覧](02_出力ファイル一覧.md) | [README](README.md) | → [04_可視化出力](04_可視化出力.md)
