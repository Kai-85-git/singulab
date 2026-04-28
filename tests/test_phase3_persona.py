"""Phase 3-1: Persona + config_loader のユニットテスト。"""
import random
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.persona import Persona, PersonaFactory
from src.config_loader import deep_merge, load_config


def t1_persona_to_prompt():
    print("[T1] Persona.to_prompt 日本語")
    p = Persona(
        name="田中",
        role="エンジニア",
        tenure_years=5,
        gender="male",
        location_label="都心",
        company_type_label="大企業",
    )
    s = p.to_prompt()
    assert "田中" in s
    assert "都心" in s
    assert "大企業" in s
    assert "5年目" in s
    assert "エンジニア" in s
    assert "男性" in s
    print(f"   ✓ {s}")


def t2_persona_factory_distribution():
    print("[T2] PersonaFactory: 分布 + 範囲")
    factory = PersonaFactory(
        location_label="都心",
        company_type_label="スタートアップ",
        name_pool=["A", "B", "C"],
        role_distribution={"X": 0.5, "Y": 0.5},
        tenure_range=(1, 3),
    )
    rng = random.Random(42)
    roles = set()
    tenures = set()
    for i in range(100):
        p = factory.generate(i, "male", rng)
        assert p.name in ["A", "B", "C"]
        assert p.role in ["X", "Y"]
        assert 1 <= p.tenure_years <= 3
        roles.add(p.role)
        tenures.add(p.tenure_years)
    assert roles == {"X", "Y"}, f"got {roles}"
    assert tenures == {1, 2, 3}, f"got {tenures}"
    print(f"   ✓ 100 回生成して role/tenure 範囲を網羅")


def t3_factory_validation():
    print("[T3] PersonaFactory: バリデーション")
    try:
        PersonaFactory("a", "b", [], {"x": 1.0}, (1, 2))
    except ValueError as e:
        print(f"   ✓ empty name_pool rejected: {e}")
    try:
        PersonaFactory("a", "b", ["A"], {}, (1, 2))
    except ValueError as e:
        print(f"   ✓ empty role_distribution rejected: {e}")
    try:
        PersonaFactory("a", "b", ["A"], {"x": 1.0}, (5, 1))
    except ValueError as e:
        print(f"   ✓ inverted tenure_range rejected: {e}")


def t4_deep_merge():
    print("[T4] deep_merge")
    base = {"a": 1, "b": {"x": 10, "y": 20}, "c": [1, 2, 3]}
    override = {"a": 99, "b": {"y": 200, "z": 300}, "c": [9]}
    merged = deep_merge(base, override)
    assert merged["a"] == 99
    assert merged["b"] == {"x": 10, "y": 200, "z": 300}
    assert merged["c"] == [9]  # リストは置き換え
    # base は不変
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
            "simulation:\n  duration: 5\n"  # 上書き
            "agents:\n  num_agents: 100\n",  # 上書き
            encoding="utf-8",
        )
        cfg = load_config(str(scenario_path))
        assert cfg["simulation"]["duration"] == 5
        assert cfg["simulation"]["half_space_size"] == 25  # base から継承
        assert cfg["agents"]["num_agents"] == 100
        assert cfg["agents"]["memory_limit"] == 20  # base から継承
        assert "extends" not in cfg  # 抜き出し済み
        print(f"   ✓ duration=5, half_space=25(継承), num_agents=100, memory_limit=20(継承)")


def t6_real_scenario_files():
    print("[T6] 実 yaml(4 象限)が読み込める")
    scenarios = [
        "config/scenario_urban_enterprise.yaml",
        "config/scenario_urban_startup.yaml",
        "config/scenario_local_enterprise.yaml",
        "config/scenario_local_startup.yaml",
    ]
    for path in scenarios:
        cfg = load_config(path)
        assert "places" in cfg
        assert cfg["places"], f"{path}: places empty"
        assert "agents" in cfg
        persona_cfg = cfg["agents"].get("persona")
        assert persona_cfg is not None, f"{path}: no persona"
        loc = persona_cfg["location_label"]
        ct = persona_cfg["company_type_label"]
        econ = cfg["environment"]["economy"]
        print(f"   ✓ {Path(path).stem}: {loc}×{ct}, economy={econ}, agents={cfg['agents']['num_agents']}")


if __name__ == "__main__":
    t1_persona_to_prompt()
    t2_persona_factory_distribution()
    t3_factory_validation()
    t4_deep_merge()
    t5_load_config_with_extends()
    t6_real_scenario_files()
    print("\nALL TESTS PASSED ✓")
