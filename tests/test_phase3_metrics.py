"""Phase 3-2: 観察指標(MetricsCalculator)のユニットテスト。"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.runlog.metrics import (
    MetricsCalculator,
    gini_coefficient,
    _utterance_counts,
    _pair_stability,
)


def t1_gini_extremes():
    print("[T1] gini_coefficient: 端ケース")
    assert gini_coefficient([]) == 0.0
    assert gini_coefficient([0, 0, 0, 0]) == 0.0
    assert gini_coefficient([10, 10, 10, 10]) == 0.0  # 完全均等
    g = gini_coefficient([0, 0, 0, 100])  # 1 人が独占
    assert 0.7 < g < 1.0, f"expected high gini, got {g}"
    g_mid = gini_coefficient([1, 2, 3, 4])
    assert 0 < g_mid < g
    print(f"   ✓ uniform=0, dominant={g:.3f}, mid={g_mid:.3f}")


def t2_utterance_counts_dedup():
    print("[T2] _utterance_counts: 同 step・同 from・同 message を重複排除")
    msgs = [
        {"step": 1, "from": 0, "to": 1, "message": "hi"},
        {"step": 1, "from": 0, "to": 2, "message": "hi"},  # 同 step 同 from 同 msg は 1 発話
        {"step": 1, "from": 0, "to": 3, "message": "hi"},
        {"step": 2, "from": 0, "to": 1, "message": "again"},  # 別 step なのでカウント
        {"step": 2, "from": 1, "to": 0, "message": "ok"},
    ]
    counts = _utterance_counts(msgs)
    assert counts == {0: 2, 1: 1}, f"got {counts}"
    print(f"   ✓ counts={counts}")


def t3_pair_stability_stable():
    print("[T3] _pair_stability: 常に同じ相手と話すと 1.0")
    msgs = []
    # 4 windows × 2 messages each, agent 0 always talks to 1
    for step in [1, 2, 3, 4, 5, 6, 7, 8]:
        msgs.append({"step": step, "from": 0, "to": 1, "message": "hi"})
        msgs.append({"step": step, "from": 1, "to": 0, "message": "hi"})
    stability, n = _pair_stability(msgs, duration_steps=8, n_windows=4)
    assert stability == 1.0, f"got {stability}"
    print(f"   ✓ 完全安定: stability={stability}, windows={n}")


def t4_pair_stability_unstable():
    print("[T4] _pair_stability: 相手が毎窓変わると 0.0")
    # 4 windows: agent 0 のトップ相手が 1 → 2 → 3 → 4 と変化
    msgs = [
        {"step": 1, "from": 0, "to": 1, "message": "x"},
        {"step": 3, "from": 0, "to": 2, "message": "x"},
        {"step": 5, "from": 0, "to": 3, "message": "x"},
        {"step": 7, "from": 0, "to": 4, "message": "x"},
    ]
    stability, n = _pair_stability(msgs, duration_steps=8, n_windows=4)
    assert stability == 0.0, f"got {stability}"
    print(f"   ✓ 完全不安定: stability={stability}, windows={n}")


def t5_calculator_minimal():
    print("[T5] MetricsCalculator: 最小ファイル一式で計算")
    with tempfile.TemporaryDirectory() as d:
        run = Path(d) / "run_test"
        run.mkdir()
        # run_metadata.json
        (run / "run_metadata.json").write_text(
            json.dumps(
                {
                    "duration": 4,
                    "num_agents": 3,
                    "personas": [
                        {"location_label": "都心", "company_type_label": "大企業"},
                        {"location_label": "都心", "company_type_label": "大企業"},
                        None,
                    ],
                    "environment": {"economy": "neutral"},
                }
            ),
            encoding="utf-8",
        )
        # messages.jsonl: 0 が圧倒的に発話、1 は 1 回、2 は沈黙
        (run / "messages.jsonl").write_text(
            "\n".join(
                json.dumps(m, ensure_ascii=False)
                for m in [
                    {"step": 1, "from": 0, "to": 1, "message": "a"},
                    {"step": 2, "from": 0, "to": 1, "message": "b"},
                    {"step": 3, "from": 0, "to": 1, "message": "c"},
                    {"step": 4, "from": 0, "to": 1, "message": "d"},
                    {"step": 4, "from": 1, "to": 0, "message": "e"},
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        # events.jsonl
        (run / "events.jsonl").write_text(
            "\n".join(
                json.dumps(e, ensure_ascii=False)
                for e in [
                    {"step": 2, "type": "place_change", "agent_id": 0, "from": "office", "to": None},
                    {"step": 3, "type": "memory_evicted", "agent_id": 1, "other_id": 9, "current_step": 3, "last_interaction_step": 1},
                    {"step": 4, "type": "memory_re_encountered", "agent_id": 1, "other_id": 9, "gap_steps": 3},
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        m = MetricsCalculator(str(run)).compute()
        assert m.num_agents == 3
        assert m.duration_steps == 4
        assert m.total_messages == 5
        assert m.unique_speakers == 2
        assert abs(m.silent_agent_rate - 1 / 3) < 1e-9
        # gini > 0.3 (skewed: 0=4, 1=1, 2=0)
        assert m.gini_utterance > 0.3, f"got {m.gini_utterance}"
        assert m.top_speaker_share == 4 / 5
        # pair stability: agent 0 always talks to 1 → 1.0
        assert m.event_counts.get("place_change") == 1
        assert m.event_counts.get("memory_evicted") == 1
        assert m.event_counts.get("memory_re_encountered") == 1
        assert m.re_encountered_avg_gap == 3.0
        assert m.scenario_label == "都心×大企業×neutral"
        print(
            f"   ✓ silent_rate={m.silent_agent_rate:.2f}, gini={m.gini_utterance:.3f}, "
            f"top_share={m.top_speaker_share:.2f}, label={m.scenario_label!r}"
        )


def t6_calculator_empty_run():
    print("[T6] MetricsCalculator: 空 run でもクラッシュしない")
    with tempfile.TemporaryDirectory() as d:
        m = MetricsCalculator(d).compute()
        assert m.total_messages == 0
        assert m.gini_utterance == 0.0
        assert m.event_counts == {}
        print(f"   ✓ empty: gini={m.gini_utterance}, msgs={m.total_messages}")


if __name__ == "__main__":
    t1_gini_extremes()
    t2_utterance_counts_dedup()
    t3_pair_stability_stable()
    t4_pair_stability_unstable()
    t5_calculator_minimal()
    t6_calculator_empty_run()
    print("\nALL TESTS PASSED ✓")
