"""日本語強制指示が Qwen3 4B abliterated に効くかの確認スクリプト。

修正前 prompt(persona section に日本語強制なし)と
修正後 prompt(LANGUAGE REQUIREMENT セクション追加)を同じ条件で比較。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from urllib import request

OLLAMA = "http://localhost:11434/api/generate"
MODEL = "huihui_ai/qwen3-abliterated:4b"


PROMPT_BEFORE = """You are Agent 0 (male) in a 2D world with multiple places (office, meeting_room).

=== PERSONA ===
あなたは田中(男性)、地方にあるスタートアップで働く3年目のエンジニアです。

=== YOUR CURRENT STATE ===
Gender: male
In place: Yes
Current place: main_office

=== ENVIRONMENT ===
景気は悪い。資金繰りが厳しい。

=== NEARBY AGENTS (you can communicate with these agents) ===
Agent 1 (female) is in main_office (office)
Agent 2 (male) is in main_office (office)

=== PREVIOUS MEMORY ===
No previous experiences.

=== MESSAGES FROM OTHERS ===
No messages received.

=== YOUR TASK ===
Decide what message you want to send to nearby agents.

=== RESPOND IN JSON ===
{
    "message": "message to nearby agents (max 200 words)",
    "reasoning": "brief explanation"
}

Step: 0
"""


PROMPT_AFTER = """You are Agent 0 (male) in a 2D world with multiple places (office, meeting_room).

=== PERSONA ===
あなたは田中(男性)、地方にあるスタートアップで働く3年目のエンジニアです。

=== LANGUAGE REQUIREMENT (CRITICAL) ===
All JSON string values (message, reasoning, memory) MUST be written in Japanese (日本語).
Do NOT use Chinese, English, or romaji. 日本語以外は不可。

=== YOUR CURRENT STATE ===
Gender: male
In place: Yes
Current place: main_office

=== ENVIRONMENT ===
景気は悪い。資金繰りが厳しい。

=== NEARBY AGENTS (you can communicate with these agents) ===
Agent 1 (female) is in main_office (office)
Agent 2 (male) is in main_office (office)

=== PREVIOUS MEMORY ===
No previous experiences.

=== MESSAGES FROM OTHERS ===
No messages received.

=== YOUR TASK ===
Decide what message you want to send to nearby agents.

=== RESPOND IN JSON ===
{
    "message": "message to nearby agents (max 200 words)",
    "reasoning": "brief explanation"
}

Step: 0
"""


def call(prompt: str) -> dict:
    body = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.5,
            "num_predict": 512,
            "repeat_penalty": 1.1,
            "min_p": 0.05,
        },
    }
    data = json.dumps(body).encode("utf-8")
    req = request.Request(OLLAMA, data=data, headers={"Content-Type": "application/json"})
    t0 = time.time()
    with request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    elapsed = time.time() - t0
    return {
        "response": result.get("response", ""),
        "eval_count": result.get("eval_count"),
        "elapsed_sec": round(elapsed, 2),
    }


def detect_chinese(text: str) -> bool:
    """日本語特有のひらがな・カタカナがゼロで漢字だけなら中国語の可能性。"""
    has_hiragana = any("぀" <= ch <= "ゟ" for ch in text)
    has_katakana = any("゠" <= ch <= "ヿ" for ch in text)
    has_cjk = any("一" <= ch <= "鿿" for ch in text)
    if not has_cjk:
        return False
    return not (has_hiragana or has_katakana)


def main() -> None:
    out_path = Path(__file__).parent / "results.jsonl"
    print(f"Writing to: {out_path}", flush=True)

    summary = []
    for label, prompt in [("BEFORE", PROMPT_BEFORE), ("AFTER", PROMPT_AFTER)]:
        for trial in range(1, 4):
            print(f"--- {label} trial {trial} ---", flush=True)
            res = call(prompt)
            chinese = detect_chinese(res["response"])
            record = {
                "label": label,
                "trial": trial,
                "elapsed_sec": res["elapsed_sec"],
                "eval_count": res["eval_count"],
                "is_chinese_only": chinese,
                "response": res["response"],
            }
            with out_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(
                f"  elapsed={res['elapsed_sec']}s eval={res['eval_count']} chinese_only={chinese}",
                flush=True,
            )
            summary.append((label, trial, chinese, res["elapsed_sec"], res["eval_count"]))

    print("\n=== Summary ===", flush=True)
    for label, trial, chinese, sec, ec in summary:
        print(f"  {label} t{trial}: chinese={chinese} {sec}s eval={ec}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
