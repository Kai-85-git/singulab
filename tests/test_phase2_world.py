"""Phase 2-1 機能の動作確認テスト(pytest 不要、直接実行可能)。

確認項目:
1. place 入れ子優先順位(B1-02)
2. capacity 強制 + place_entry_denied イベント(B1-03)
3. World.attempt_move による位置更新と clamp_to_field(B1-04)
4. 初期配置 random_in_place(B1-05)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.world.world import World
from src.world.place import get_place_at_position


PLACES = [
    {
        "name": "main_office",
        "type": "office",
        "center_x": 0,
        "center_y": 0,
        "half_size": 10,
        "capacity": 100,
    },
    {
        "name": "meeting_room",
        "type": "meeting",
        "center_x": 5,
        "center_y": 5,
        "half_size": 2,
        "capacity": 1,  # 1 人だけ入れる
    },
]


class FakeAgent:
    """move/agent への依存を最小化したスタブ。"""

    def __init__(self, agent_id: int, position):
        self.id = agent_id
        self.position = position
        self.current_place = None
        self.total_moves = 0

    def update_state(self, places):
        place = get_place_at_position(self.position, places)
        self.current_place = place["name"] if place else None


def t1_nesting_priority():
    print("[T1] place 入れ子優先順位")
    # (5, 5) は main_office と meeting_room の両方に含まれる
    # → 内側(half_size 最小) = meeting_room が返るべき
    p = get_place_at_position((5, 5), PLACES)
    assert p is not None and p["name"] == "meeting_room", f"got {p}"
    print(f"   ✓ (5,5) -> {p['name']}")

    # (-3, -3) は main_office にだけ含まれる
    p = get_place_at_position((-3, -3), PLACES)
    assert p is not None and p["name"] == "main_office", f"got {p}"
    print(f"   ✓ (-3,-3) -> {p['name']}")

    # (20, 20) はどちらにも含まれない
    p = get_place_at_position((20, 20), PLACES)
    assert p is None
    print(f"   ✓ (20,20) -> None")


def t2_capacity_enforcement():
    print("[T2] capacity 強制と place_entry_denied")
    world = World(PLACES, half_space_size=25)

    # Agent A は (2, 5) にいる(main_office 内、meeting_room 外: x=2 < 3)
    # Agent B は meeting_room 内 (5, 5) にいる
    a = FakeAgent(0, (2, 5))
    b = FakeAgent(1, (5, 5))
    a.update_state(PLACES)
    b.update_state(PLACES)
    assert a.current_place == "main_office", f"a got {a.current_place}"
    assert b.current_place == "meeting_room", f"b got {b.current_place}"

    # Agent A が右に動こうとする → (3, 5) は meeting_room 境界内 → capacity=1 で B 在席 → 拒否
    final_pos, events = world.attempt_move(a, "right", [a, b])
    assert final_pos == (2, 5), f"位置が変わってはいけない、got {final_pos}"
    assert any(e["type"] == "place_entry_denied" for e in events), f"events={events}"
    print(f"   ✓ A の入室拒否: events={[e['type'] for e in events]}")

    # B が左に出る → (4, 5) は依然 meeting_room 内(x=4∈[3,7])なので place_change 発火しない
    # 一旦左に2歩出して main_office に戻す
    final_pos, events = world.attempt_move(b, "left", [a, b])
    assert final_pos == (4, 5)  # まだ meeting_room
    assert not any(e["type"] == "place_change" for e in events), f"premature change: {events}"
    final_pos, events = world.attempt_move(b, "left", [a, b])
    assert final_pos == (3, 5)  # 境界(x=3)はまだ meeting_room
    final_pos, events = world.attempt_move(b, "left", [a, b])
    assert final_pos == (2, 5)  # x=2 → main_office
    types = [e["type"] for e in events]
    assert "place_change" in types, f"events={events}"
    print(f"   ✓ B 退室時に place_change 発火: events={types}")


def t3_clamp_to_field():
    print("[T3] フィールド境界 clamp")
    world = World(PLACES, half_space_size=10)
    a = FakeAgent(0, (10, 0))
    a.update_state(PLACES)
    # 右方向に動くと x=11 で境界外 → clamp で x=10 のまま
    final_pos, events = world.attempt_move(a, "right", [a])
    assert final_pos == (10, 0), f"got {final_pos}"
    types = [e["type"] for e in events]
    assert "clamp_to_field" in types, f"events={events}"
    print(f"   ✓ (10,0) → right で clamp 検出: events={types}")


def t4_random_in_place():
    print("[T4] random_in_place(配置範囲確認)")
    import random
    random.seed(123)
    world = World(PLACES, half_space_size=25)
    for _ in range(20):
        pos = world.random_position_in_place("meeting_room", random)
        assert 3 <= pos[0] <= 7 and 3 <= pos[1] <= 7, f"out of bounds: {pos}"
    print(f"   ✓ 20 回サンプリング、すべて meeting_room 矩形内")


if __name__ == "__main__":
    t1_nesting_priority()
    t2_capacity_enforcement()
    t3_clamp_to_field()
    t4_random_in_place()
    print("\nALL TESTS PASSED ✓")
