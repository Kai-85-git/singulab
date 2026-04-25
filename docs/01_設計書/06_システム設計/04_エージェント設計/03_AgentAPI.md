# 03_1 ステップ内の Agent API

参考実装を汎化した API。`event_infos` と `env_readings` が新規フィールド。

```python
agent.decide_message(
    place_status:  Optional[dict],           # 場所内のみ { agents_in_place, capacity, occupancy_rate }
    env_readings:  dict[str, float],         # 2 階の環境量(例: {"pheromone_food": 0.3})
    nearby_agents: list[Agent],
    event_infos:   list[dict],               # 知覚しているイベントの定量情報
    step:          int,
) -> MessageDecision
```

```python
agent.decide_action(
    place_status:    Optional[dict],
    env_readings:    dict[str, float],
    nearby_agents:   list[Agent],
    event_infos:     list[dict],
    message_to_send: str,
    step:            int,
) -> ActionDecision
```

---

← [02_エージェント状態](02_エージェント状態.md) | [README](README.md) | → [04_プロンプト構造](04_プロンプト構造.md)
