"""Simulation Orchestrator(Phase 2 リファクタ版)。

Phase 1 で参考実装等価まで移植したのち、Phase 2-1 で以下を追加:
- World クラス(src/world/world.py)に place 解決・capacity 強制・移動を集中
- agent.move() の直叩きを廃止、World.attempt_move 経由に
- events.jsonl 出力(place_change / place_entry_denied / clamp_to_field)
- 初期配置モード `random_outside`(既存)/ `random_in_place`(新規)
- run_metadata.json 出力(scenario / seed / agents / places の要約)
"""
from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

from src.agent.agent import Agent
from src.agent.persona import Persona, PersonaFactory
from src.config_loader import load_config
from src.events.alien import AlienEvent
from src.events.base import Event, collect_perceived_events
from src.events.fire import FireEvent
from src.events.zero_gravity import ZeroGravityEvent
from src.llm.ollama import OllamaClient
from src.physics.base import WorldLaws
from src.physics.communication import CommunicationPhysics
from src.runlog.jsonl import JsonlLogger
from src.viz.visualizer import Visualizer
from src.world.environment import Environment
from src.world.place import PlaceConfig
from src.world.world import World

logger = logging.getLogger(__name__)

MAX_POSITION_ATTEMPTS = 1000
LOG_INTERVAL = 10


class Simulation:
    """Phase 2-1 までの責務を持つシミュレーション本体。"""

    def __init__(self, config_path: str = "config.yaml", output_dir: Optional[str] = None):
        # Phase 3-1: extends 階層読み込み対応
        self.config = load_config(config_path)

        self.config_path = config_path
        self.output_dir = output_dir
        self.runlog = JsonlLogger(output_dir)

        # Visualizer は output_dir + visualization.save_frames=true のとき生成
        viz_cfg = self.config.get("visualization") or {}
        self.viz: Optional[Visualizer] = None
        self._viz_save_frames = bool(viz_cfg.get("save_frames", False))
        self._viz_frame_interval = int(viz_cfg.get("frame_interval", 1))

        seed = self.config.get("random_seed")
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
            logger.info(f"random_seed = {seed} に固定")
        self._seed = seed

        sim_config = self.config["simulation"]
        self.duration: int = sim_config["duration"]
        self.half_space_size: int = sim_config["half_space_size"]
        self.half_place_size: int = sim_config.get("half_place_size", 5)

        agent_config = self.config["agents"]
        self.num_agents: int = agent_config["num_agents"]
        self.communication_radius: float = agent_config["communication_radius"]
        self.memory_limit: int = agent_config.get("memory_limit", 20)
        self.memory_size: int = agent_config.get("memory_size", 5)
        self.message_history_limit: int = agent_config.get("message_history_limit", 10)
        self.message_context_size: int = agent_config.get("message_context_size", 3)
        self.initial_placement: str = agent_config.get("initial_placement", "random_outside")
        self.home_place: Optional[str] = agent_config.get("home_place")

        # Phase 3-1: ペルソナ設定(あれば)
        persona_cfg = agent_config.get("persona")
        self.persona_factory: Optional[PersonaFactory] = (
            PersonaFactory.from_config(persona_cfg) if persona_cfg else None
        )
        self._personas: List[Optional[Persona]] = []

        if "places" not in self.config:
            raise ValueError("'places' is required in config")
        self.places: List[PlaceConfig] = self.config["places"]
        if not isinstance(self.places, list) or not self.places:
            raise ValueError("'places' must be a non-empty list")
        required_fields = ["name", "type", "center_x", "center_y", "half_size", "capacity"]
        for i, place in enumerate(self.places):
            for f in required_fields:
                if f not in place:
                    raise ValueError(f"Place at index {i} missing field: '{f}'")

        # Phase 2: World に place / field / 移動責務を集約
        self.world = World(self.places, self.half_space_size)
        logger.info(
            f"World initialized: {len(self.places)} place(s) "
            f"{[p['name'] for p in self.places]} (types: {[p['type'] for p in self.places]})"
        )

        # Visualizer は output_dir があり、かつ save_frames=true のときだけ有効化
        if output_dir and self._viz_save_frames:
            self.viz = Visualizer(
                output_dir=output_dir,
                half_space_size=self.half_space_size,
                places=self.places,
                frame_interval=self._viz_frame_interval,
            )
            logger.info(
                f"Visualizer enabled: frames every {self._viz_frame_interval} step(s) "
                f"-> {self.viz.frames_dir}"
            )

        # Phase 2-2: 2 階(環境)
        self.environment = Environment.from_config(self.config.get("environment"))
        logger.info(
            f"Environment: economy={self.environment.economy} "
            f'-> "{self.environment.prompt_fragment()}"'
        )

        # Phase 2-3: 3 階(世界の法則)
        self.world_laws = WorldLaws.from_config(self.config.get("world_laws"))
        # 設計書では CommunicationPhysics を 3 階モジュールに集約するが、
        # Phase 2-3 では到達距離判定のみ使い、Phase 1 互換の同一エリア判定もここから引く
        self.communication = CommunicationPhysics(self.world_laws)
        # config に world_laws が無くても WorldLaws はデフォルトを返すが、
        # その場合は Phase 1 互換動作のため agents.communication_radius を上書き優先する
        if self.config.get("world_laws") is None:
            # 旧 agents.communication_radius を WorldLaws に流し込む
            self.world_laws = WorldLaws(
                communication_radius=self.communication_radius,
                communication_radius_overrides={},
                cognitive_limit=self.world_laws.cognitive_limit,
                message_delay=self.world_laws.message_delay,
            )
            self.communication = CommunicationPhysics(self.world_laws)
        logger.info(
            f"WorldLaws: comm_radius={self.world_laws.communication_radius}, "
            f"overrides={dict(self.world_laws.communication_radius_overrides)}, "
            f"cognitive_limit={self.world_laws.cognitive_limit}"
        )

        # Events
        # 旧:`fires:` セクションのみ対応していた。
        # 2026-04-30 改訂(問題解決ToDo §C):`events:` セクションで type 判別 alien / zero_gravity 等
        # を受け付けるように拡張。`fires:` は後方互換として残す。
        self.events: List[Event] = []
        for i, fc in enumerate(self.config.get("fires", []) or []):
            ev = FireEvent(
                name=fc.get("name", f"fire_{i}"),
                start_step=fc["start_step"],
                intensity=fc["intensity"],
                radius=fc["radius"],
                center=((fc["center_x"], fc["center_y"]) if "center_x" in fc else None),
                random_position_range=self.half_space_size,
            )
            self.events.append(ev)
            pos_info = (
                f"({fc['center_x']}, {fc['center_y']})" if "center_x" in fc else "random"
            )
            logger.info(
                f"FireEvent '{ev.name}' configured: step={fc['start_step']}, "
                f"intensity={fc['intensity']}, radius={fc['radius']}, position={pos_info}"
            )

        # 新形式(type 判別)
        for i, ec in enumerate(self.config.get("events", []) or []):
            etype = ec.get("type")
            if etype == "fire":
                ev = FireEvent(
                    name=ec.get("name", f"fire_{i}"),
                    start_step=ec["start_step"],
                    intensity=ec["intensity"],
                    radius=ec["radius"],
                    center=(ec["center_x"], ec["center_y"]) if "center_x" in ec else None,
                    random_position_range=self.half_space_size,
                )
            elif etype == "alien":
                ev = AlienEvent(
                    name=ec.get("name", f"alien_{i}"),
                    start_step=ec.get("start_step", 1),
                    prompt_text=ec.get(
                        "prompt_text",
                        "現在、地球外生命体との接触が確認されています。",
                    ),
                )
            elif etype == "zero_gravity":
                ev = ZeroGravityEvent(
                    name=ec.get("name", f"zero_gravity_{i}"),
                    start_step=ec.get("start_step", 1),
                    prompt_text=ec.get(
                        "prompt_text",
                        "現在、無重力状態が発生しています。物理法則が崩壊しています。",
                    ),
                )
            else:
                raise ValueError(f"unknown event type: {etype!r} (event index {i})")
            self.events.append(ev)
            logger.info(f"{type(ev).__name__} '{ev.name}' configured: start_step={ev.start_step}")

        llm_config = self.config["llm"]
        self.llm_client = OllamaClient(
            base_url=llm_config["base_url"],
            model=llm_config["model"],
            temperature=llm_config.get("temperature", 0.7),
            max_tokens=llm_config.get("max_tokens", 200),
            repeat_penalty=llm_config.get("repeat_penalty", 1.1),
            repeat_last_n=llm_config.get("repeat_last_n", 128),
            min_p=llm_config.get("min_p", 0.05),
            think=llm_config.get("think"),  # None / True / False
        )
        if llm_config.get("think") is not None:
            logger.info(f"LLM think mode: {llm_config['think']} (Qwen3 系の thinking 抑制用)")

        self.agents: List[Agent] = []
        self.step = 0
        self.history: List[Dict] = []

        self.stats: Dict = {
            "place_occupancy": [],
            "agents_in_place": [],
            "agents_outside_place": [],
            "communication_events": [],
            "places": {p["name"]: {"occupancy": [], "agents_in_place": []} for p in self.places},
            "agents_in_fire_radius": [],
            "place_entry_denied_count": 0,  # Phase 2-1 で導入
            "memory_evicted_count": 0,  # Phase 2-3
            "memory_re_encountered_count": 0,  # Phase 2-3
        }

    # ---------- 初期化 ----------

    def _generate_initial_positions(self) -> List[Tuple[int, int]]:
        """初期配置モードに応じた位置リストを返す。"""
        mode = self.initial_placement
        if mode == "random_outside":
            return self._init_random_outside()
        if mode == "random_in_place":
            if not self.home_place:
                raise ValueError(
                    "agents.home_place is required when initial_placement='random_in_place'"
                )
            return self._init_random_in_place(self.home_place)
        raise ValueError(f"Unknown initial_placement: {mode}")

    def _init_random_outside(self) -> List[Tuple[int, int]]:
        positions: List[Tuple[int, int]] = []
        used: Set[Tuple[int, int]] = set()
        attempts = 0
        while len(positions) < self.num_agents and attempts < MAX_POSITION_ATTEMPTS:
            pos = self.world.random_position_outside_places(random)
            if pos is None or pos in used:
                attempts += 1
                continue
            positions.append(pos)
            used.add(pos)
            attempts += 1
        if len(positions) < self.num_agents:
            logger.warning(
                f"Only generated {len(positions)} unique outside positions. Filling rest randomly."
            )
            h = self.half_space_size
            while len(positions) < self.num_agents:
                pos = (random.randint(-h, h), random.randint(-h, h))
                if pos not in used:
                    positions.append(pos)
                    used.add(pos)
        return positions

    def _init_random_in_place(self, place_name: str) -> List[Tuple[int, int]]:
        place = self.world.get_place(place_name)
        if place is None:
            raise ValueError(f"home_place '{place_name}' not found in places")
        if place["capacity"] < self.num_agents:
            raise ValueError(
                f"home_place '{place_name}' capacity {place['capacity']} < num_agents {self.num_agents}"
            )
        positions: List[Tuple[int, int]] = []
        used: Set[Tuple[int, int]] = set()
        attempts = 0
        while len(positions) < self.num_agents and attempts < MAX_POSITION_ATTEMPTS:
            pos = self.world.random_position_in_place(place_name, random)
            if pos in used:
                attempts += 1
                continue
            positions.append(pos)
            used.add(pos)
            attempts += 1
        return positions

    def initialize_agents(self) -> None:
        logger.info(
            f"Initializing {self.num_agents} agents (placement={self.initial_placement})..."
        )
        positions = self._generate_initial_positions()
        for i in range(self.num_agents):
            gender = random.choice(["male", "female"])
            persona: Optional[Persona] = None
            persona_fragment = ""
            if self.persona_factory is not None:
                persona = self.persona_factory.generate(i, gender, rng=random)
                persona_fragment = persona.to_prompt()
            self._personas.append(persona)

            agent = Agent(
                agent_id=i,
                initial_position=positions[i],
                llm_client=self.llm_client,
                communication_radius=self.communication_radius,
                half_space_size=self.half_space_size,
                places=self.places,
                num_agents=self.num_agents,
                gender=gender,
                memory_limit=self.memory_limit,
                memory_size=self.memory_size,
                message_history_limit=self.message_history_limit,
                message_context_size=self.message_context_size,
                environment_fragment=self.environment.prompt_fragment(),
                cognitive_limit=self.world_laws.cognitive_limit,
                persona_fragment=persona_fragment,
            )
            agent.update_state()
            self.agents.append(agent)

        if self.persona_factory is not None:
            # 新スキーマ(2026-04-29 議事録改訂):age / gender / nationality / mbti
            logger.info(
                f"Personas generated: {self.num_agents} agents "
                f"(age={self.persona_factory.age_range}, "
                f"nationalities={self.persona_factory.nationality_pool}, "
                f"mbti={len(self.persona_factory.mbti_values)} types)"
            )
        logger.info("Agents initialized")

    def write_run_metadata(self) -> None:
        """run_metadata.json を出力。"""
        metadata = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "config_path": self.config_path,
            "random_seed": self._seed,
            "duration": self.duration,
            "num_agents": self.num_agents,
            "initial_placement": self.initial_placement,
            "home_place": self.home_place,
            "places": [
                {
                    "name": p["name"],
                    "type": p["type"],
                    "center": [p["center_x"], p["center_y"]],
                    "half_size": p["half_size"],
                    "capacity": p["capacity"],
                }
                for p in self.places
            ],
            "environment": self.environment.to_metadata(),
            "world_laws": self.world_laws.to_metadata(),
            "personas": [
                (p.to_metadata() if p is not None else None)
                for p in self._personas
            ] if self.persona_factory is not None else None,
            "llm": {
                "model": self.llm_client.model,
                "base_url": self.llm_client.base_url,
                "temperature": self.llm_client.temperature,
            },
        }
        self.runlog.log_run_metadata(metadata)

    # ---------- ヘルパ ----------

    def get_agents_in_place(self, place_name: Optional[str] = None) -> List[Agent]:
        if place_name:
            return [a for a in self.agents if a.current_place == place_name]
        return [a for a in self.agents if a.in_place]

    def get_place_status(self, place_name: Optional[str] = None) -> Dict:
        if place_name:
            place_config = self.world.get_place(place_name)
            if not place_config:
                raise ValueError(f"Place '{place_name}' not found")
            n = len(self.get_agents_in_place(place_name))
            return {
                "place_name": place_name,
                "agents_in_place": n,
                "capacity": place_config["capacity"],
                "occupancy_rate": n / place_config["capacity"],
            }
        agents_in = len(self.get_agents_in_place())
        place_statuses = {}
        for p in self.places:
            n = len(self.get_agents_in_place(p["name"]))
            place_statuses[p["name"]] = {
                "place_name": p["name"],
                "agents_in_place": n,
                "capacity": p["capacity"],
                "occupancy_rate": n / p["capacity"],
            }
        return {
            "agents_in_place": agents_in,
            "occupancy_rate": agents_in / self.num_agents,
            "places": place_statuses,
        }

    # ---------- メインループ ----------

    def step_simulation(self) -> None:
        self.step += 1

        for ev in self.events:
            new_state = ev.maybe_activate(self.step)
            if new_state is not None:
                # 旧 fire 専用ログを kind 別に分岐(2026-04-30 §C 改訂)
                kind = new_state.get("kind", "unknown")
                if kind == "fire":
                    logger.info(
                        f"EVENT '{new_state['name']}' (fire) activated at step {self.step}: "
                        f"position={new_state.get('position')}, "
                        f"intensity={new_state.get('intensity')}, "
                        f"radius={new_state.get('radius')}"
                    )
                else:
                    logger.info(
                        f"EVENT '{new_state['name']}' ({kind}) activated at step {self.step}: "
                        f"prompt_text={new_state.get('prompt_text', '(no prompt_text)')!r}"
                    )

        for agent in self.agents:
            agent.update_state(self.places)

        # Phase 1: collect message decisions
        # Phase 2-3 で agent.get_nearby_agents → CommunicationPhysics.determine_recipients に置換
        message_decisions = []
        for agent in self.agents:
            nearby = self.communication.determine_recipients(agent, self.agents)
            place_status = (
                self.get_place_status(agent.current_place)
                if (agent.in_place and agent.current_place)
                else None
            )
            fire_info = collect_perceived_events(self.events, agent.position)
            decision = agent.decide_message(place_status, nearby, self.step, fire_info=fire_info)
            message_decisions.append((agent, decision, nearby))

        # Phase 2: send messages
        # 認知メモリイベント(memory_added/evicted/re_encountered)もここで集める
        cognition_events: List[Dict] = []
        for agent, decision, nearby in message_decisions:
            content = decision.get("message", "")
            if content and nearby:
                logger.info(
                    f'Step {self.step}: Agent {agent.id} -> {len(nearby)} nearby: "{content}"'
                )
                for other in nearby:
                    cog_evs = other.receive_message(agent.id, content, step=self.step)
                    cognition_events.extend(cog_evs)
                    self.runlog.log_message(
                        step=self.step,
                        from_id=agent.id,
                        to_id=other.id,
                        message=content,
                        reasoning=decision.get("reasoning", ""),
                    )

        # Phase 3: collect action decisions
        action_decisions = []
        memory_records = []
        for agent, _msg_decision, nearby in message_decisions:
            place_status = (
                self.get_place_status(agent.current_place)
                if (agent.in_place and agent.current_place)
                else None
            )
            msg_content = _msg_decision.get("message", "")
            fire_info = collect_perceived_events(self.events, agent.position)
            action = agent.decide_action(
                place_status, nearby, self.step, msg_content, fire_info=fire_info
            )
            action_decisions.append((agent, action))
            memory_records.append(
                {
                    "step": self.step,
                    "id": agent.id,
                    "memory": action.get("memory", ""),
                    "reasoning": action.get("reasoning", ""),
                }
            )
        self.runlog.log_memory_reasoning_batch(memory_records)

        # Phase 4: execute movement via World (capacity enforcement + events)
        step_events: List[Dict] = list(cognition_events)  # Phase 2-3 認知メモリ系
        for agent, action in action_decisions:
            if action["action"] == "move" and action["direction"]:
                _, events = self.world.attempt_move(agent, action["direction"], self.agents)
                for ev in events:
                    if ev["type"] == "place_entry_denied":
                        self.stats["place_entry_denied_count"] += 1
                step_events.extend(events)
        # cognition イベントの集計
        for ev in cognition_events:
            if ev["type"] == "memory_evicted":
                self.stats["memory_evicted_count"] += 1
            elif ev["type"] == "memory_re_encountered":
                self.stats["memory_re_encountered_count"] += 1
        if step_events:
            self.runlog.log_event_batch(self.step, step_events)

        # Update state after movement
        for agent in self.agents:
            agent.update_state(self.places)

        # Stats
        agents_in = len(self.get_agents_in_place())
        overall = self.get_place_status()
        self.stats["place_occupancy"].append(overall["occupancy_rate"])
        self.stats["agents_in_place"].append(agents_in)
        self.stats["agents_outside_place"].append(self.num_agents - agents_in)
        for p in self.places:
            ps = self.get_place_status(p["name"])
            self.stats["places"][p["name"]]["occupancy"].append(ps["occupancy_rate"])
            self.stats["places"][p["name"]]["agents_in_place"].append(ps["agents_in_place"])

        active_fires = [ev for ev in self.events if isinstance(ev, FireEvent) and ev.active]
        if active_fires:
            in_radius: Set[int] = set()
            for fire in active_fires:
                if fire.center is None:
                    continue
                for agent in self.agents:
                    if agent.distance_to(fire.center) <= fire.radius:
                        in_radius.add(agent.id)
            self.stats["agents_in_fire_radius"].append(len(in_radius))
        else:
            self.stats["agents_in_fire_radius"].append(0)

        self.history.append(
            {
                "step": self.step,
                "place_status": overall,
                "agent_positions": [a.position for a in self.agents],
                "agents_in_place": [a.id for a in self.get_agents_in_place()],
                "fire_states": [
                    ev.state() for ev in self.events
                    if isinstance(ev, FireEvent) and ev.active
                ],
            }
        )

        if self.step % LOG_INTERVAL == 0:
            place_info = ", ".join(
                f"{p['name']}: {self.get_place_status(p['name'])['agents_in_place']}"
                for p in self.places
            )
            logger.info(
                f"Step {self.step}/{self.duration}: {agents_in} in places ({place_info}), "
                f"{overall['occupancy_rate']:.1%} occupancy"
            )

        # 1 ステップ分のフレーム保存(visualizer 有効時のみ)
        if self.viz is not None:
            fire_states = [
                ev.state() for ev in self.events
                if isinstance(ev, FireEvent) and ev.active
            ]
            self.viz.save_frame(
                step=self.step,
                agents=self.agents,
                place_status=overall,
                fire_states=fire_states,
                comm_radius=self.world_laws.communication_radius,
            )

    def run(self) -> None:
        logger.info("Starting simulation...")
        if not self.llm_client.check_connection():
            logger.error("Cannot connect to Ollama. Please make sure Ollama is running.")
            return
        self.initialize_agents()
        self.write_run_metadata()
        try:
            while self.step < self.duration:
                self.step_simulation()
        except KeyboardInterrupt:
            logger.info("Simulation interrupted by user")
        except Exception as e:
            logger.error(f"Error during simulation: {e}", exc_info=True)
        logger.info("Simulation completed")

    def get_statistics(self) -> Dict:
        if not self.stats["place_occupancy"]:
            return {}
        po = np.array(self.stats["place_occupancy"])
        ap = np.array(self.stats["agents_in_place"])
        return {
            "mean_occupancy": float(np.mean(po)),
            "std_occupancy": float(np.std(po)),
            "mean_agents_in_place": float(np.mean(ap)),
            "max_agents_in_place": int(np.max(ap)),
            "min_agents_in_place": int(np.min(ap)),
            "total_steps": self.step,
            "place_entry_denied_count": self.stats["place_entry_denied_count"],
            "memory_evicted_count": self.stats["memory_evicted_count"],
            "memory_re_encountered_count": self.stats["memory_re_encountered_count"],
        }
