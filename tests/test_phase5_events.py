"""Phase 5(C-2-3 / C-3-3): AlienEvent / ZeroGravityEvent のユニットテスト。

- start_step 前は activate しない / 知覚情報も None
- start_step 以降は active になり、距離帯ごとに異なる prompt_text を返す(2026-05-01 段 3 改訂)
- 既存 FireEvent も `kind="fire"` を返すことを確認(後方互換)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.events.alien import AlienEvent
from src.events.fire import FireEvent
from src.events.zero_gravity import ZeroGravityEvent


def t1_alien_activates_at_start_step():
    print("[T1] AlienEvent: start_step での発火と距離依存の知覚(2026-05-01 段 3 改訂)")
    ev = AlienEvent(start_step=3, position=(0, 0), near_radius=8.0, visible_radius=18.0)
    # start_step 前
    assert ev.maybe_activate(2) is None, "should not activate before start_step"
    assert ev.perceived_info((0, 0)) is None, "should not be perceived before activation"
    # start_step ちょうど
    state = ev.maybe_activate(3)
    assert state is not None
    assert state["kind"] == "alien"
    assert state["active"] is True
    # 同 step を繰り返し呼んでも再発火しない
    assert ev.maybe_activate(4) is None
    # Near 帯(距離 0): 詳細視認
    near_info = ev.perceived_info((0, 0))
    assert near_info is not None
    assert near_info["kind"] == "alien"
    assert near_info["perception_band"] == "near"
    assert "目の前" in near_info["prompt_text"]
    # Mid 帯(距離 ~12): 遠望
    mid_info = ev.perceived_info((10, 7))
    assert mid_info is not None
    assert mid_info["perception_band"] == "mid"
    assert "遠くに" in mid_info["prompt_text"]
    # Far 帯(距離 ~141): 知覚不可
    far_info = ev.perceived_info((100, 100))
    assert far_info is None, "far agents should not perceive directly"
    print(f"   ✓ near={near_info['perception_band']} mid={mid_info['perception_band']} far=None")


def t2_zero_gravity_basic():
    print("[T2] ZeroGravityEvent: 基本挙動")
    ev = ZeroGravityEvent(start_step=1, prompt_text="無重力テスト")
    assert ev.maybe_activate(0) is None
    state = ev.maybe_activate(1)
    assert state["kind"] == "zero_gravity"
    info = ev.perceived_info((-10, 5))
    assert info is not None
    assert info["kind"] == "zero_gravity"
    assert info["prompt_text"] == "無重力テスト"
    print(f"   ✓ active 後の info: {info}")


def t3_fire_kind_field_added():
    print("[T3] FireEvent: kind='fire' が perceived_info に含まれる(後方互換)")
    ev = FireEvent(name="f1", start_step=0, intensity=0.8, radius=10, center=(0, 0))
    ev.maybe_activate(0)
    info = ev.perceived_info((1, 1))
    assert info is not None
    assert info["kind"] == "fire"
    assert info["name"] == "f1"
    assert "fire_position" in info
    print(f"   ✓ {info}")


def t4_event_has_no_effect_when_inactive():
    print("[T4] 非 active 時は perceived_info が必ず None")
    a = AlienEvent(start_step=10)
    z = ZeroGravityEvent(start_step=10)
    assert a.perceived_info((0, 0)) is None
    assert z.perceived_info((0, 0)) is None
    a.maybe_activate(5)
    z.maybe_activate(5)
    assert a.perceived_info((0, 0)) is None
    assert z.perceived_info((0, 0)) is None
    print("   ✓ start_step 未満では active にならない")


def t5_alien_position_and_movement():
    print("[T5] AlienEvent: 位置指定 + ランダムウォーク移動(2026-05-01 追補)")
    import random as _r
    rng = _r.Random(123)
    ev = AlienEvent(start_step=1, position=(0, 0), move_step_size=2, random_position_range=10)
    state = ev.maybe_activate(1)
    assert state["position"] == (0, 0)
    assert state["kind"] == "alien"

    # 5 step 動かして position が変わったことを確認
    positions = [ev.position]
    for _ in range(5):
        ev.maybe_move(rng=rng)
        positions.append(ev.position)
    assert any(p != (0, 0) for p in positions[1:]), f"never moved: {positions}"
    # 各座標は ±10 の範囲内に収まる
    for x, y in positions:
        assert -10 <= x <= 10 and -10 <= y <= 10, f"out of bounds: ({x}, {y})"
    print(f"   ✓ moved through: {positions}")

    # move_step_size=0 なら動かない
    still = AlienEvent(start_step=1, position=(5, 5), move_step_size=0)
    still.maybe_activate(1)
    still.maybe_move(rng=rng)
    assert still.position == (5, 5)
    print("   ✓ move_step_size=0 で固定")


def t6_alien_prompt_text_changes_after_move():
    print("[T6] AlienEvent: 移動するとプロンプト文も更新される")
    ev = AlienEvent(start_step=1, position=(10, 10), move_step_size=0)
    ev.maybe_activate(1)
    text_before = ev.prompt_text
    assert "(10, 10)" in text_before
    ev.position = (5, 7)  # 手動で移動
    text_after = ev.prompt_text
    assert "(5, 7)" in text_after
    assert text_before != text_after
    print(f"   ✓ before: {text_before}")
    print(f"   ✓ after : {text_after}")


if __name__ == "__main__":
    t1_alien_activates_at_start_step()
    t2_zero_gravity_basic()
    t3_fire_kind_field_added()
    t4_event_has_no_effect_when_inactive()
    t5_alien_position_and_movement()
    t6_alien_prompt_text_changes_after_move()
    print("\nALL TESTS PASSED ✓")
