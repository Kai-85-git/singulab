# 06_出力の JSON 検証

エージェントの発話は **JSON 形式** で出力させて Python 側で厳密検証する。

## 1. スキーマ定義(pydantic)

```python
from pydantic import BaseModel, Field
from typing import Literal

class AgentTurn(BaseModel):
    utterance: str = Field(description="発話内容。沈黙なら空文字")
    action: Literal["stay", "move_to_office", "move_to_meeting", "listen"]
    target_id: int | None = Field(None, description="誰に話しているか(全員なら None)")
```

## 2. プロンプトで形式指定

詳細は [05_プロンプト実装](../05_プロンプト実装/) 参照。system prompt で:

```
出力は以下の JSON 形式のみで返答してください:
{"utterance": "...", "action": "stay|move_to_office|move_to_meeting|listen", "target_id": null}
```

## 3. パース + リペア

```python
import json
from pydantic import ValidationError

def parse_agent_turn(raw: str) -> AgentTurn | None:
    # ```json ... ``` を剥がす
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(raw)
        return AgentTurn.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        return None  # 失敗時は「沈黙」扱いに
```

---

← [05_エラーハンドリング](05_エラーハンドリング.md) | [README](README.md) | → [07_抽象化の勘所](07_抽象化の勘所.md)
