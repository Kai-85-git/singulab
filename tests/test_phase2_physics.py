"""Phase 2-3 機能の動作確認テスト。

確認項目:
1. WorldLaws のデフォルト + バリデーション(B3-04)
2. communication_radius の place 単位 override(B3-01)
3. CommunicationPhysics.determine_recipients(同一エリア + 距離)
4. AgentMemory の K 制限 + LRU(B3-03)
5. memory_re_encountered イベント
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.physics import (
    AgentMemory,
    CommunicationPhysics,
    MessageDelay,
    WorldLaws,
)


# ---------- T1 / T2: WorldLaws ----------


def t1_world_laws_defaults():
    print("[T1] WorldLaws デフォルト + from_config")
    laws = WorldLaws.from_config(None)
    assert laws.communication_radius == 5.0
    assert laws.communication_radius_overrides == {}
    assert laws.cognitive_limit == 30
    assert isinstance(laws.message_delay, MessageDelay)
    print(f"   ✓ defaults: r_comm=5.0, K=30, delay 0/1/3")

    laws = WorldLaws.from_config(
        {
            "communication_radius": 8.0,
            "communication_radius_overrides": {"meeting_room": 12.0},
            "cognitive_limit": 5,
            "message_delay": {"same_place_near": 0, "same_place_far": 2, "cross_place": 4},
        }
    )
    assert laws.comm_radius_for("meeting_room") == 12.0
    assert laws.comm_radius_for("main_office") == 8.0
    assert laws.comm_radius_for(None) == 8.0
    print(f"   ✓ override: meeting_room=12.0 / その他=8.0")


def t2_world_laws_validation():
    print("[T2] WorldLaws バリデーション")
    try:
        WorldLaws(communication_radius=-1.0)
    except ValueError as e:
        print(f"   ✓ negative r_comm rejected: {e}")
    try:
        WorldLaws(communication_radius=5.0, communication_radius_overrides={"x": 0})
    except ValueError as e:
        print(f"   ✓ zero override rejected: {e}")
    try:
        WorldLaws(communication_radius=5.0, cognitive_limit=0)
    except ValueError as e:
        print(f"   ✓ zero cognitive_limit rejected: {e}")
    try:
        MessageDelay(same_place_near=-1)
    except ValueError as e:
        print(f"   ✓ negative delay rejected: {e}")


# ---------- T3: CommunicationPhysics ----------


class FakeAgent:
    def __init__(self, agent_id, position, current_place=None):
        self.id = agent_id
        self.position = position
        self.current_place = current_place
        self.in_place = current_place is not None


def t3_communication_recipients():
    print("[T3] CommunicationPhysics.determine_recipients")
    laws = WorldLaws(
        communication_radius=5.0,
        communication_radius_overrides={"meeting_room": 10.0},
    )
    comm = CommunicationPhysics(laws)

    # 全員 outside、距離 4 → 全員届く
    a = FakeAgent(0, (0, 0))
    b = FakeAgent(1, (3, 0))
    c = FakeAgent(2, (6, 0))  # r=5 を超える
    rec = comm.determine_recipients(a, [a, b, c])
    ids = sorted(r.id for r in rec)
    assert ids == [1], f"got {ids}"
    print(f"   ✓ outside、距離 5 以下: 受信者={ids}")

    # 異なる place は届かない
    a = FakeAgent(0, (0, 0), current_place="main_office")
    b = FakeAgent(1, (3, 0))  # outside
    c = FakeAgent(2, (1, 0), current_place="main_office")  # 同 place
    rec = comm.determine_recipients(a, [a, b, c])
    ids = sorted(r.id for r in rec)
    assert ids == [2], f"got {ids}"
    print(f"   ✓ outside vs in-place 隔絶: 受信者={ids}")

    # meeting_room は overrides で半径 10 を使う
    a = FakeAgent(0, (0, 0), current_place="meeting_room")
    b = FakeAgent(1, (8, 0), current_place="meeting_room")  # 距離 8 だが r=10
    rec = comm.determine_recipients(a, [a, b])
    ids = sorted(r.id for r in rec)
    assert ids == [1], f"got {ids}"
    print(f"   ✓ meeting_room override: 距離 8 でも届く")


# ---------- T4 / T5: AgentMemory ----------


def t4_agent_memory_k_eviction():
    print("[T4] AgentMemory K 制限 + LRU 追い出し")
    mem = AgentMemory(k=2)
    e1 = mem.record_interaction(other_id=10, step=1)
    e2 = mem.record_interaction(other_id=20, step=2)
    assert any(ev["type"] == "memory_added" for ev in e1)
    assert any(ev["type"] == "memory_added" for ev in e2)
    assert sorted(mem.known_ids()) == [10, 20]
    print(f"   ✓ 2 件追加: known={mem.known_ids()}")

    # 30 を追加 → K=2 超過 → 10(最古)が evict される
    e3 = mem.record_interaction(other_id=30, step=3)
    types = [ev["type"] for ev in e3]
    assert "memory_evicted" in types
    assert "memory_added" in types
    assert 10 not in mem.known_ids()
    assert sorted(mem.known_ids()) == [20, 30]
    evicted = next(ev for ev in e3 if ev["type"] == "memory_evicted")
    assert evicted["other_id"] == 10
    print(f"   ✓ 30 追加で 10 が evict: events={types}")

    # 既知の 20 と再接触 → イベント無し(LRU 更新のみ)
    e4 = mem.record_interaction(other_id=20, step=4, msg={"content": "hi"})
    assert e4 == []
    # その後 40 追加で evict されるのは 30(20 の方が新しい)
    e5 = mem.record_interaction(other_id=40, step=5)
    evicted2 = next(ev for ev in e5 if ev["type"] == "memory_evicted")
    assert evicted2["other_id"] == 30, f"got {evicted2}"
    print(f"   ✓ LRU: 既知 20 を更新 → 次は 30 が追い出される")


def t5_memory_re_encountered():
    print("[T5] memory_re_encountered イベント")
    mem = AgentMemory(k=1)
    mem.record_interaction(other_id=10, step=1)
    mem.record_interaction(other_id=20, step=2)  # 10 が evict
    assert 10 not in mem.known_ids()

    # 10 と再接触
    e = mem.record_interaction(other_id=10, step=10)
    types = [ev["type"] for ev in e]
    assert "memory_re_encountered" in types, f"got {types}"
    re = next(ev for ev in e if ev["type"] == "memory_re_encountered")
    assert re["gap_steps"] == 10 - 1, f"got {re}"  # last_interaction_step だった step 1 から 10 までの差
    print(f"   ✓ 再接触検知: gap_steps={re['gap_steps']}")


if __name__ == "__main__":
    t1_world_laws_defaults()
    t2_world_laws_validation()
    t3_communication_recipients()
    t4_agent_memory_k_eviction()
    t5_memory_re_encountered()
    print("\nALL TESTS PASSED ✓")
