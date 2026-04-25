# 05_JSON I/O 契約

## 1. Message 出力

```json
{
    "message": "message to nearby agents (max 200 words, optional)",
    "reasoning": "brief explanation of why you want to send this message"
}
```

- `message` は空文字許容(送信しない選択肢)
- JSON パース失敗時は参考実装と同じく**テキストパース**へフォールバック(メッセージは空、`reasoning` に生出力の先頭 100 字)

## 2. Action 出力

```json
{
    "action": "move" or "stay",
    "direction": "up" | "down" | "left" | "right",
    "memory": "what to remember for next step",
    "reasoning": "brief explanation"
}
```

- `action == "stay"` なら `direction` は無視
- JSON パース失敗時はテキストパース(`move` を含むかで判定、方向キーワードを抽出)

---

← [04_プロンプト構造](04_プロンプト構造.md) | [README](README.md) | → [06_Memory設計](06_Memory設計.md)
