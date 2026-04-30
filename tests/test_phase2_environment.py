"""Phase 2-2 機能の動作確認テスト。

確認項目:
1. Environment.from_config(neutral デフォルト)
2. enum バリデーション(未知値で ValueError)
3. economy_text のデフォルト + 上書き
4. frozen インスタンスは変更不可
5. prompt_fragment が config の値を返す
6. Agent の prompt に景気文セクションが入る
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.agent import Agent
from src.world.environment import (
    DEFAULT_ECONOMY_TEXT,
    Environment,
    _VALID_LEVELS,
)


def t1_default_neutral():
    print("[T1] config なしでデフォルト neutral")
    env = Environment.from_config(None)
    assert env.economy == "neutral"
    assert env.prompt_fragment() == DEFAULT_ECONOMY_TEXT["neutral"]
    print(f"   ✓ {env.economy} -> '{env.prompt_fragment()}'")


def t2_invalid_value():
    print("[T2] 未知値で ValueError")
    try:
        Environment.from_config({"economy": "rainy"})
    except ValueError as e:
        print(f"   ✓ raised ValueError: {e}")
        return
    raise AssertionError("ValueError が出るべき")


def t3_default_text_for_each_level():
    print("[T3] 各 level でデフォルト文が返る")
    for level in _VALID_LEVELS:
        env = Environment.from_config({"economy": level})
        assert env.prompt_fragment() == DEFAULT_ECONOMY_TEXT[level]
        print(f"   ✓ {level}: {env.prompt_fragment()}")


def t4_text_override():
    print("[T4] economy_text の上書き")
    env = Environment.from_config(
        {
            "economy": "bad",
            "economy_text": {
                "bad": "現在、世界的なリセッションの最中にある。",
            },
        }
    )
    assert env.prompt_fragment() == "現在、世界的なリセッションの最中にある。"
    # 他レベルはデフォルトのまま
    other = Environment.from_config({"economy": "good", "economy_text": {"bad": "X"}})
    assert other.prompt_fragment() == DEFAULT_ECONOMY_TEXT["good"]
    print(f"   ✓ override -> '{env.prompt_fragment()}'")


def t5_frozen_instance():
    print("[T5] frozen instance は変更不可")
    env = Environment.from_config({"economy": "neutral"})
    try:
        env.economy = "bad"  # type: ignore
    except Exception as e:
        print(f"   ✓ {type(e).__name__}: {e}")
        return
    raise AssertionError("FrozenInstanceError が出るべき")


def t6_agent_prompt_contains_environment():
    print("[T6] Agent の prompt に景気文が含まれる")
    # Agent のコンストラクタは llm_client を要求するが、prompt 構築だけで使わないので適当な物でOK
    class FakeLLM:
        pass

    fake_llm = FakeLLM()
    places = [
        {"name": "office", "type": "office", "center_x": 0, "center_y": 0, "half_size": 5, "capacity": 10}
    ]

    env = Environment.from_config({"economy": "bad"})
    agent = Agent(
        agent_id=0,
        initial_position=(0, 0),
        llm_client=fake_llm,  # type: ignore
        communication_radius=5,
        half_space_size=25,
        places=places,
        num_agents=1,
        environment_fragment=env.prompt_fragment(),
        conversation_fragment="現場での役割: 記録係\n今の目的: 具体的な情報を確認する",
    )

    msg_prompt = agent.create_message_prompt(place_status=None, nearby_agents=[], step=1)
    act_prompt = agent.create_decision_prompt(place_status=None, nearby_agents=[], step=1)

    assert "=== ENVIRONMENT ===" in msg_prompt, "message prompt に ENVIRONMENT セクションがない"
    assert "=== ENVIRONMENT ===" in act_prompt, "action prompt に ENVIRONMENT セクションがない"
    assert "景気は悪く" in msg_prompt
    assert "景気は悪く" in act_prompt
    assert "Speak to a nearby agent" in msg_prompt
    assert "abstract phrase" in msg_prompt
    assert "=== CONVERSATION PROFILE ===" in msg_prompt
    assert "記録係" in msg_prompt
    print("   ✓ message / action 両 prompt に景気文を確認")

    # environment_fragment 未指定の場合はセクションが入らない
    agent_no_env = Agent(
        agent_id=1,
        initial_position=(0, 0),
        llm_client=fake_llm,  # type: ignore
        communication_radius=5,
        half_space_size=25,
        places=places,
        num_agents=1,
    )
    p = agent_no_env.create_decision_prompt(place_status=None, nearby_agents=[], step=1)
    assert "=== ENVIRONMENT ===" not in p
    print("   ✓ environment_fragment 未指定時はセクション挿入なし")


if __name__ == "__main__":
    t1_default_neutral()
    t2_invalid_value()
    t3_default_text_for_each_level()
    t4_text_override()
    t5_frozen_instance()
    t6_agent_prompt_contains_environment()
    print("\nALL TESTS PASSED ✓")
