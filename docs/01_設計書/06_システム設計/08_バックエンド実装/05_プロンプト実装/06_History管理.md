# 06_History の管理

## 1. 会話履歴の持ち方

```python
@dataclass
class Agent:
    id: int
    persona: Persona
    pos: tuple[float, float]
    memory: deque[Message]  # 最大 K 件(cognitive_limit)
```

## 2. LLM 呼び出しごとに system prompt を組み直す

- 多ターン会話 API の history は使わない
- **毎回 stateless に system + user を組み立てる**
- → 記憶の選択的忘却(認知限界)を Python 側で完全制御可能

## 3. 最小メモリ実装

```python
from collections import deque

class AgentMemory:
    def __init__(self, capacity: int):
        self.msgs = deque(maxlen=capacity)

    def add(self, msg):
        self.msgs.append(msg)

    def recent(self, n: int | None = None) -> list:
        if n is None:
            return list(self.msgs)
        return list(self.msgs)[-n:]
```

---

← [05_3階層モデル責任分解](05_3階層モデル責任分解.md) | [README](README.md) | → [07_実装疑似コード](07_実装疑似コード.md)
