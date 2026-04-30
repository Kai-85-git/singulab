"""エコー(コピペ的発言)の具体例を抽出する。"""
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = (_HERE / ".." / ".." / "..").resolve()
ROOT = _PROJECT_ROOT / "output"
OUT = _HERE / "echo_examples.md"

sys.stdout.reconfigure(encoding="utf-8")


def char_ngrams(text: str, n: int = 4) -> set[str]:
    text = re.sub(r"\s+", "", text)
    return {text[i : i + n] for i in range(max(0, len(text) - n + 1))}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main() -> None:
    lines = ["# エコー(類似発言)の具体例\n"]

    for s in ["prod_local_startup", "prod_urban_startup", "prod_local_enterprise", "prod_urban_enterprise"]:
        msgs_path = ROOT / s / "messages.jsonl"
        if not msgs_path.exists():
            continue
        msgs = [json.loads(l) for l in msgs_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        unique = {}
        for m in msgs:
            k = (m["step"], m["from"])
            if k not in unique:
                unique[k] = m
        by_step: dict[int, list[dict]] = defaultdict(list)
        for m in unique.values():
            by_step[m["step"]].append(m)

        # 同 step 内で類似度 0.7 以上のペアを探す
        echoes = []
        for step, ms in by_step.items():
            ngrams = [char_ngrams(m["message"]) for m in ms]
            for i in range(len(ms)):
                for j in range(i + 1, len(ms)):
                    sim = jaccard(ngrams[i], ngrams[j])
                    if sim >= 0.7:
                        echoes.append((step, sim, ms[i], ms[j]))

        echoes.sort(key=lambda x: -x[1])
        lines.append(f"\n## {s} — {len(echoes)} 件の類似ペア(類似度 0.7+)\n")
        for step, sim, m1, m2 in echoes[:5]:
            lines.append(f"\n### step {step} — 類似度 {sim:.3f}\n")
            lines.append(f"- **Agent {m1['from']} → Agent {m1['to']}**:")
            lines.append(f"  > {m1['message'][:200]}")
            lines.append(f"- **Agent {m2['from']} → Agent {m2['to']}**:")
            lines.append(f"  > {m2['message'][:200]}")

        # 同じ agent の step k vs step k+1 が高類似なケース(膠着)
        by_agent: dict[int, list[tuple[int, str]]] = defaultdict(list)
        for m in unique.values():
            by_agent[m["from"]].append((m["step"], m["message"]))
        stagnations = []
        for aid, items in by_agent.items():
            items.sort()
            for i in range(len(items) - 1):
                s1 = char_ngrams(items[i][1])
                s2 = char_ngrams(items[i + 1][1])
                sim = jaccard(s1, s2)
                if sim >= 0.7:
                    stagnations.append((aid, items[i][0], items[i + 1][0], sim, items[i][1], items[i + 1][1]))
        stagnations.sort(key=lambda x: -x[3])
        lines.append(f"\n#### 同 agent の連続 step 膠着(0.7+):{len(stagnations)} 件\n")
        for aid, s1, s2, sim, t1, t2 in stagnations[:3]:
            lines.append(f"\n- **Agent {aid} step {s1} → step {s2}** 類似度 {sim:.3f}")
            lines.append(f"  - step {s1}: > {t1[:160]}")
            lines.append(f"  - step {s2}: > {t2[:160]}")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote: {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
