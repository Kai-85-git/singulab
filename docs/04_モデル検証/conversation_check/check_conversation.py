"""エージェント同士が本当に会話しているか、ただエコーしているだけかを検証する。

3 つの観点:
1. エコー度: 同 step 内で複数 agent の発言が似ているか(文字 N-gram の重複率)
2. 受信反映度: agent が直前の受信メッセージの内容を反映しているか(キーワードオーバーラップ)
3. 文脈進化度: step が進むほど発話内容が変化しているか / 固定化しているか
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# このスクリプトは docs/04_モデル検証/conversation_check/ 配下にある。
# プロジェクトルートは __file__ から 3 階層上 (docs/04_モデル検証/conversation_check/X.py → ../../..)。
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = (_HERE / ".." / ".." / "..").resolve()
ROOT = _PROJECT_ROOT / "output"
DEFAULT_SCENARIOS = [
    "prod_local_startup",
    "prod_urban_startup",
    "prod_local_enterprise",
    "prod_urban_enterprise",
]
DEFAULT_OUT = _HERE / "conversation_check.md"
# argv で対象シナリオを上書きできる:
#   python check_conversation.py echo_check_v1
#   python check_conversation.py echo_check_v1 prod_local_startup --out=v1.md
SCENARIOS = []
OUT = DEFAULT_OUT
for arg in sys.argv[1:]:
    if arg.startswith("--out="):
        OUT = _HERE / arg[len("--out=") :]
    else:
        SCENARIOS.append(arg)
if not SCENARIOS:
    SCENARIOS = DEFAULT_SCENARIOS

sys.stdout.reconfigure(encoding="utf-8")


def char_ngrams(text: str, n: int = 4) -> set[str]:
    """日本語向けの文字 N-gram セット(空白除去後)。"""
    text = re.sub(r"\s+", "", text)
    return {text[i : i + n] for i in range(max(0, len(text) - n + 1))}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def keywords(text: str) -> set[str]:
    """形態素解析なしで「キーワードっぽい連続漢字 + 英単語」を抽出。"""
    kanji_seq = re.findall(r"[一-龥々]{2,}", text)
    katakana_seq = re.findall(r"[ァ-ヴー]{2,}", text)
    ascii_word = re.findall(r"[A-Za-z_]{3,}", text)
    return set(kanji_seq + katakana_seq + ascii_word)


def analyze(scenario: str) -> dict:
    msgs_path = ROOT / scenario / "messages.jsonl"
    if not msgs_path.exists():
        return {}
    msgs = [json.loads(l) for l in msgs_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    # messages.jsonl は (step, from, message) が同じだと to 違いで重複しているので、unique 化
    unique = {}
    for m in msgs:
        k = (m["step"], m["from"])
        if k not in unique:
            unique[k] = m

    # step ごとに発言を集める
    by_step: dict[int, list[dict]] = defaultdict(list)
    for m in unique.values():
        by_step[m["step"]].append(m)

    # 1. エコー度: 同 step 内のペアで Jaccard 類似度を計算
    echo_scores = []
    for step, ms in by_step.items():
        if len(ms) < 2:
            continue
        ngrams = [char_ngrams(m["message"]) for m in ms]
        for i in range(len(ms)):
            for j in range(i + 1, len(ms)):
                echo_scores.append(jaccard(ngrams[i], ngrams[j]))

    # 2. 受信反映度: agent ごとに「step k の発言と step k 時点で受信していた直近メッセージのキーワードオーバーラップ」
    received: dict[int, list[str]] = defaultdict(list)  # agent_id -> [received message texts]
    reflection_scores = []
    for step in sorted(by_step.keys()):
        # まず step k の発言を集める前に、step k-1 までの受信を反映
        for m in by_step[step]:
            sender = m["from"]
            text = m["message"]
            recipients = [mm["to"] for mm in msgs if mm["step"] == step and mm["from"] == sender]
            for r in recipients:
                received[r].append(text)
        # 次に step k+1 で各 agent の発言が、それまでに受信した直近 3 メッセージとどれくらい重なるか
    # (上のループは受信を蓄積しただけ。次のループで反映度を測る)
    received2: dict[int, list[str]] = defaultdict(list)
    for step in sorted(by_step.keys()):
        for m in by_step[step]:
            agent_id = m["from"]
            recent_received = received2[agent_id][-3:]
            if recent_received and m["message"]:
                msg_kw = keywords(m["message"])
                recv_kw = set().union(*[keywords(r) for r in recent_received])
                reflection_scores.append(jaccard(msg_kw, recv_kw))
            # 今 step で受信したものを次 step 用に追加
            for mm in msgs:
                if mm["step"] == step and mm["to"] == agent_id:
                    received2[agent_id].append(mm["message"])

    # 3. 文脈進化度: agent ごとに「step k の発言と step k+1 の発言の類似度」
    progression = defaultdict(list)
    by_agent: dict[int, list[tuple[int, str]]] = defaultdict(list)
    for m in unique.values():
        by_agent[m["from"]].append((m["step"], m["message"]))
    for agent_id, items in by_agent.items():
        items.sort()
        for i in range(len(items) - 1):
            s1 = char_ngrams(items[i][1])
            s2 = char_ngrams(items[i + 1][1])
            progression[agent_id].append(jaccard(s1, s2))

    avg_self_similarity = (
        sum(s for ps in progression.values() for s in ps)
        / max(1, sum(len(ps) for ps in progression.values()))
    )

    return {
        "scenario": scenario,
        "n_unique_msgs": len(unique),
        "n_steps": len(by_step),
        "echo_mean": (sum(echo_scores) / len(echo_scores)) if echo_scores else 0.0,
        "echo_max": max(echo_scores) if echo_scores else 0.0,
        "echo_n_pairs": len(echo_scores),
        "reflection_mean": (sum(reflection_scores) / len(reflection_scores)) if reflection_scores else 0.0,
        "reflection_n": len(reflection_scores),
        "self_similarity": avg_self_similarity,
        "by_agent_self_sim": {aid: (sum(ps) / len(ps)) if ps else 0.0 for aid, ps in progression.items()},
    }


def main() -> None:
    rows = [analyze(s) for s in SCENARIOS]
    rows = [r for r in rows if r]

    lines = [
        "# エージェント間の会話の実態チェック\n",
        "## 指標の意味\n",
        "- **echo_mean / echo_max**: 同 step 内の異なる agent の発言ペアの Jaccard 類似度(4-gram)。",
        "  **0.3 を超えるとエコー(似た発言)が起きていると疑える**。1.0 はコピペ\n",
        "- **reflection_mean**: agent の発言が、それまでに受信したメッセージのキーワードと",
        "  どれくらい重なるか。**0.1〜0.3 程度なら受信を踏まえた応答、0 に近いと無視**\n",
        "- **self_similarity**: 同じ agent の連続する step の発言類似度。",
        "  **0.5 を超えると同じことを言い続けている状態(膠着)**\n",
        "\n## 結果\n",
        "| シナリオ | echo_mean | echo_max | reflection_mean | self_similarity | unique_msgs |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in rows:
        lines.append(
            f"| {r['scenario']} | {r['echo_mean']:.3f} | {r['echo_max']:.3f} | "
            f"{r['reflection_mean']:.3f} | {r['self_similarity']:.3f} | {r['n_unique_msgs']} |"
        )

    lines.append("\n## エージェント別の自己類似度(同じことを言い続けているか)\n")
    for r in rows:
        lines.append(f"\n### {r['scenario']}\n")
        for aid, sim in sorted(r["by_agent_self_sim"].items()):
            tag = " ⚠️ 膠着" if sim > 0.5 else (" 🟡 やや反復" if sim > 0.3 else "")
            lines.append(f"- Agent {aid}: self-similarity = {sim:.3f}{tag}")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote: {OUT}")
    for r in rows:
        print(f"\n=== {r['scenario']} ===")
        for k, v in r.items():
            if k != "by_agent_self_sim":
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
