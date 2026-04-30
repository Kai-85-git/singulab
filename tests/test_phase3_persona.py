"""Phase 3-1 / Phase 5(B-1-3): Persona + config_loader のユニットテスト。

2026-04-29 議事録の決定でペルソナを MBTI 新スキーマに刷新。
旧スキーマ(role / tenure_years / location_label など)は受け付けず、
明示的なエラーメッセージで移行を促すことを確認する。
"""
import random
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.persona import MBTI_TYPES, Persona, PersonaFactory
from src.config_loader import deep_merge, load_config
from src.simulation import Simulation


def t1_persona_to_prompt():
    print("[T1] Persona.to_prompt 日本語(議事録 §4.4 雛形)")
    p = Persona(age=32, gender="male", nationality="日本", mbti="INTJ")
    s = p.to_prompt()
    assert "30代の男性" in s, f"age decade missing: {s}"
    assert "国籍: 日本" in s
    assert "MBTI: INTJ" in s
    assert "日本語で回答してください" in s
    print(f"   ✓ {s.replace(chr(10), ' / ')}")


def t2_persona_factory_distribution():
    print("[T2] PersonaFactory: 分布 + 範囲")
    factory = PersonaFactory(
        age_range=(20, 40),
        gender_values=["male", "female"],
        nationality_pool=["日本", "米国", "中国"],
        mbti_values=["INTJ", "ENFP", "ISFJ"],
    )
    rng = random.Random(42)
    ages, genders, nats, mbtis = set(), set(), set(), set()
    for i in range(200):
        p = factory.generate(i, rng=rng)
        assert 20 <= p.age <= 40
        assert p.gender in ["male", "female"]
        assert p.nationality in ["日本", "米国", "中国"]
        assert p.mbti in ["INTJ", "ENFP", "ISFJ"]
        ages.add(p.age)
        genders.add(p.gender)
        nats.add(p.nationality)
        mbtis.add(p.mbti)
    assert genders == {"male", "female"}, f"got {genders}"
    assert nats == {"日本", "米国", "中国"}, f"got {nats}"
    assert mbtis == {"INTJ", "ENFP", "ISFJ"}, f"got {mbtis}"
    print(f"   ✓ 200 回生成 age={min(ages)}-{max(ages)} mbti{mbtis}")


def t3_factory_validation_and_legacy_rejection():
    print("[T3] PersonaFactory: 新スキーマのバリデーション + 旧スキーマ拒否")

    # 各バリデーション
    try:
        PersonaFactory(age_range=(40, 20), gender_values=["m"], nationality_pool=["x"])
    except ValueError as e:
        print(f"   ✓ inverted age_range rejected: {e}")
    try:
        PersonaFactory(age_range=(20, 40), gender_values=[], nationality_pool=["x"])
    except ValueError as e:
        print(f"   ✓ empty gender_values rejected: {e}")
    try:
        PersonaFactory(age_range=(20, 40), gender_values=["m"], nationality_pool=[])
    except ValueError as e:
        print(f"   ✓ empty nationality_pool rejected: {e}")
    try:
        PersonaFactory(
            age_range=(20, 40),
            gender_values=["m"],
            nationality_pool=["x"],
            mbti_values=["INVALID"],
        )
    except ValueError as e:
        print(f"   ✓ unknown mbti rejected: {e}")

    # 旧スキーマ → 移行メッセージ付き拒否
    legacy_cfg = {
        "location_label": "都心",
        "company_type_label": "大企業",
        "name_pool": ["A"],
        "role_distribution": {"x": 1.0},
        "tenure_range": [1, 3],
    }
    try:
        PersonaFactory.from_config(legacy_cfg)
        raise AssertionError("legacy schema should be rejected")
    except ValueError as e:
        msg = str(e)
        assert "Legacy persona schema" in msg
        assert "07_ペルソナ拡張" in msg
        print(f"   ✓ legacy schema rejected with migration hint")


def t4_deep_merge():
    print("[T4] deep_merge")
    base = {"a": 1, "b": {"x": 10, "y": 20}, "c": [1, 2, 3]}
    override = {"a": 99, "b": {"y": 200, "z": 300}, "c": [9]}
    merged = deep_merge(base, override)
    assert merged["a"] == 99
    assert merged["b"] == {"x": 10, "y": 200, "z": 300}
    assert merged["c"] == [9]
    assert base["b"] == {"x": 10, "y": 20}
    print(f"   ✓ merged: {merged}")


def t5_load_config_with_extends():
    print("[T5] load_config: extends 機構")
    with tempfile.TemporaryDirectory() as d:
        base_path = Path(d) / "base.yaml"
        scenario_path = Path(d) / "scenario.yaml"
        base_path.write_text(
            "simulation:\n  duration: 100\n  half_space_size: 25\n"
            "agents:\n  num_agents: 10\n  memory_limit: 20\n",
            encoding="utf-8",
        )
        scenario_path.write_text(
            "extends: base.yaml\n"
            "simulation:\n  duration: 5\n"
            "agents:\n  num_agents: 100\n",
            encoding="utf-8",
        )
        cfg = load_config(str(scenario_path))
        assert cfg["simulation"]["duration"] == 5
        assert cfg["simulation"]["half_space_size"] == 25
        assert cfg["agents"]["num_agents"] == 100
        assert cfg["agents"]["memory_limit"] == 20
        assert "extends" not in cfg
        print(f"   ✓ duration=5, num_agents=100, memory_limit=20(継承)")


def t6_factory_from_config_new_schema():
    print("[T6] PersonaFactory.from_config: 新スキーマ受け入れ")
    cfg = {
        "age": {"range": [25, 45]},
        "gender": {"values": ["male", "female"]},
        "nationality": {"pool": ["日本", "ブラジル", "ドイツ"]},
        "mbti": {"values": ["INTJ", "ENFP"]},
    }
    factory = PersonaFactory.from_config(cfg)
    rng = random.Random(0)
    p = factory.generate(0, rng=rng)
    assert 25 <= p.age <= 45
    assert p.nationality in ["日本", "ブラジル", "ドイツ"]
    assert p.mbti in ["INTJ", "ENFP"]
    # 部分指定でデフォルト充填
    minimal = PersonaFactory.from_config({})
    p2 = minimal.generate(1, rng=rng)
    assert 20 <= p2.age <= 60
    assert p2.mbti in MBTI_TYPES
    print(f"   ✓ p={p.to_metadata()}, defaults={p2.to_metadata()}")


def t7_load_config_conversation_profiles():
    print("[T7] load_config: conversation_profiles を保持")
    with tempfile.TemporaryDirectory() as d:
        base_path = Path(d) / "base.yaml"
        scenario_path = Path(d) / "scenario.yaml"
        base_path.write_text(
            "simulation:\n  duration: 5\n  half_space_size: 25\n"
            "agents:\n  num_agents: 2\n  memory_limit: 20\n",
            encoding="utf-8",
        )
        scenario_path.write_text(
            "extends: base.yaml\n"
            "agents:\n"
            "  conversation_profiles:\n"
            "    - role: 進行役\n"
            "      goal: 状況を共有する\n"
            "    - role: 確認役\n"
            "      goal: 事実を確認する\n",
            encoding="utf-8",
        )
        cfg = load_config(str(scenario_path))
        profiles = cfg["agents"]["conversation_profiles"]
        assert len(profiles) == 2
        assert profiles[0]["role"] == "進行役"
        assert profiles[1]["goal"] == "事実を確認する"
        print(f"   ✓ profiles={profiles}")


def t8_simulation_accepts_conversation_profiles():
    print("[T8] Simulation: conversation_profiles を Agent prompt に渡す")
    sim = Simulation(config_path="config/scenario_alien_5.yaml", output_dir=None)
    assert len(sim.conversation_profiles) == sim.num_agents == 5
    fragment = sim._conversation_profile_to_prompt(0)
    assert "現場での役割" in fragment
    assert "当日の進行役" in fragment
    assert "会話では" in fragment
    print("   ✓ scenario_alien_5 の会話プロファイルを読み込み")


if __name__ == "__main__":
    t1_persona_to_prompt()
    t2_persona_factory_distribution()
    t3_factory_validation_and_legacy_rejection()
    t4_deep_merge()
    t5_load_config_with_extends()
    t6_factory_from_config_new_schema()
    t7_load_config_conversation_profiles()
    t8_simulation_accepts_conversation_profiles()
    print("\nALL TESTS PASSED ✓")
