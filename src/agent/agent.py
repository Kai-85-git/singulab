"""Agent: LLM 駆動エージェント。

参考実装 [docs/10_共有資料/2d-multi-places-simulation-on-fire-public/agent.py] を Phase 1 で
ほぼ verbatim に移植。Phase 2 以降で persona / memory / prompt / 通信判定を分離する。
"""
import json
import logging
import math
from typing import Dict, List, Optional, Tuple, TypedDict

from src.llm.ollama import OllamaClient
from src.physics.cognition import AgentMemory
from src.world.place import PlaceConfig, get_place_at_position

logger = logging.getLogger(__name__)

FALLBACK_REASONING_LENGTH = 100
MAX_MESSAGE_WORDS = 200

# X 増加 = 右、Y 増加 = 上
DIRECTION_MAP = {
    "up": (0, 1),
    "down": (0, -1),
    "left": (-1, 0),
    "right": (1, 0),
}


class MessageDecision(TypedDict):
    message: str
    reasoning: str


class ActionDecision(TypedDict):
    action: str
    direction: Optional[str]
    memory: str
    reasoning: str


class Agent:
    """LLM 駆動の 2D エージェント。"""

    def __init__(
        self,
        agent_id: int,
        initial_position: Tuple[int, int],
        llm_client: OllamaClient,
        communication_radius: float,
        half_space_size: int,
        places: List[PlaceConfig],
        num_agents: int,
        gender: str = "male",
        memory_limit: int = 20,
        memory_size: int = 5,
        message_history_limit: int = 10,
        message_context_size: int = 3,
        environment_fragment: str = "",
        cognitive_limit: Optional[int] = None,
        persona_fragment: str = "",
    ):
        self.id = agent_id
        self.position = initial_position
        self.llm_client = llm_client
        self.communication_radius = communication_radius
        self.half_space_size = half_space_size
        self.places = places
        self.num_agents = num_agents
        self.gender = gender

        self.memory_limit = memory_limit
        self.memory_size = memory_size
        self.message_history_limit = message_history_limit
        self.message_context_size = message_context_size

        # 2 階(環境)の景気文。空文字なら未挿入。Phase 2-2 で導入。
        self.environment_fragment = environment_fragment

        # ペルソナ文(日本語)。Phase 3-1 で導入。
        self.persona_fragment = persona_fragment

        # 3 階(世界の法則)の認知限界。Phase 2-3 で導入。
        # cognitive_limit=None なら無効化(Phase 1 互換動作)
        self.cognitive_memory: Optional[AgentMemory] = (
            AgentMemory(cognitive_limit) if cognitive_limit is not None else None
        )

        self.in_place = False
        self.current_place: Optional[str] = None
        self.memory: List[str] = []
        self.received_messages: List[Dict] = []

        self.steps_in_place = 0
        self.steps_outside_place = 0
        self.total_moves = 0

    def is_in_place(self, position: Tuple[int, int]) -> bool:
        return get_place_at_position(position, self.places) is not None

    def distance_to(self, other_position: Tuple[int, int]) -> float:
        dx = self.position[0] - other_position[0]
        dy = self.position[1] - other_position[1]
        return math.sqrt(dx * dx + dy * dy)

    def get_nearby_agents(self, all_agents: List["Agent"]) -> List["Agent"]:
        """通信可能な近傍エージェントを返す(同一エリア + 半径内)。"""
        nearby = []
        for agent in all_agents:
            if agent.id != self.id:
                dist = self.distance_to(agent.position)
                same_area = (not self.in_place and not agent.in_place) or (
                    self.in_place
                    and agent.in_place
                    and self.current_place == agent.current_place
                )
                if dist <= self.communication_radius and same_area:
                    nearby.append(agent)
        return nearby

    def _build_nearby_agents_context(
        self, nearby_agents: List["Agent"], include_position: bool = True
    ) -> str:
        if not nearby_agents:
            return "No nearby agents."
        lines = []
        for agent in nearby_agents:
            if agent.in_place:
                place_info = next(
                    (p for p in self.places if p["name"] == agent.current_place), None
                )
                if place_info is None:
                    raise ValueError(
                        f"Agent {agent.id} is in place '{agent.current_place}' but this place is not found."
                    )
                place_type = place_info["type"]
                status = f"in {agent.current_place} ({place_type})"
            else:
                status = "outside the places"
            if include_position:
                lines.append(
                    f"Agent {agent.id} ({agent.gender}) is at "
                    f"({agent.position[0]}, {agent.position[1]}) and is {status}"
                )
            else:
                lines.append(f"Agent {agent.id} ({agent.gender}) is {status}")
        return "\n".join(lines)

    def _build_memory_context(self) -> str:
        if not self.memory:
            return "No previous experiences."
        recent = self.memory[-self.memory_size:]
        return "\n".join([f"- {m}" for m in recent])

    def _build_messages_context(self) -> str:
        if not self.received_messages:
            return "No messages received."
        recent = self.received_messages[-self.message_context_size:]
        return "\n".join(
            [f"from Agent {msg['from']}: {msg['content']}" for msg in recent]
        )

    def _build_environment_section(self) -> str:
        """2 階(環境)の景気文を system prompt 末尾に挿入するセクションを返す。

        命令ではなく状態記述として与える(設計書 04_2階-環境/03_景気の表現方式 参照)。
        """
        if not self.environment_fragment:
            return ""
        return f"\n=== ENVIRONMENT ===\n{self.environment_fragment}\n"

    def _build_persona_section(self) -> str:
        """ペルソナ文(日本語)を YOUR CURRENT STATE 直前に挿入するセクション。"""
        if not self.persona_fragment:
            return ""
        return f"\n=== PERSONA ===\n{self.persona_fragment}\n"

    def _build_fire_section(self, fire_info: Optional[List[Dict]]) -> str:
        if not fire_info:
            return ""
        lines = ["\n=== FIRE EVENT ==="]
        for fi in fire_info:
            lines.append(
                f"Fire \"{fi['name']}\":\n"
                f"  Position: ({fi['fire_position'][0]}, {fi['fire_position'][1]})\n"
                f"  Intensity: {fi['intensity']} (scale: 0.0 to 1.0)\n"
                f"  Radius: {fi['radius']}\n"
                f"  Your distance: {fi['agent_distance']}"
            )
        return "\n".join(lines) + "\n"

    def _limit_message_words(self, message: str) -> str:
        if not message:
            return message
        words = message.split()
        if len(words) > MAX_MESSAGE_WORDS:
            logger.warning(
                f"Agent {self.id}: Message exceeds {MAX_MESSAGE_WORDS} words "
                f"({len(words)} words). Sent as-is."
            )
        return message

    def create_message_prompt(
        self,
        place_status: Optional[Dict],
        nearby_agents: List["Agent"],
        step: int,
        fire_info: Optional[List[Dict]] = None,
    ) -> str:
        nearby_text = self._build_nearby_agents_context(nearby_agents, include_position=False)
        memory_text = self._build_memory_context()
        messages_text = self._build_messages_context()

        current_place_info = None
        if self.in_place and self.current_place:
            current_place_info = next(
                (p for p in self.places if p["name"] == self.current_place), None
            )
            if current_place_info is None:
                raise ValueError(
                    f"Agent {self.id} is in place '{self.current_place}' but not found."
                )

        if self.in_place and place_status and current_place_info:
            place_section_text = (
                f"\nYou are currently in the {current_place_info['type']} "
                f"({current_place_info['name']})."
                f"\n  Number of agents here: {place_status.get('agents_in_place', 0)}"
                f"\n  Capacity: {place_status.get('capacity', 0)}"
                f"\n  Occupancy rate: {place_status.get('occupancy_rate', 0.0):.2f}"
            )
        else:
            place_section_text = ""

        unique_types = list({p["type"] for p in self.places})
        world_description = f"a 2D world with multiple places ({', '.join(unique_types)})"
        fire_section = self._build_fire_section(fire_info)
        environment_section = self._build_environment_section()
        persona_section = self._build_persona_section()

        prompt = f"""You are Agent {self.id} ({self.gender}) in {world_description}.
{persona_section}
=== YOUR CURRENT STATE ===
Gender: {self.gender}
In place: {"Yes" if self.in_place else "No"}
{"Current place: " + self.current_place if self.in_place else ""}
{place_section_text}
{environment_section}{fire_section}
=== NEARBY AGENTS (you can communicate with these agents) ===
{nearby_text}

=== PREVIOUS MEMORY ===
{memory_text}

=== MESSAGES FROM OTHERS ===
{messages_text}

=== YOUR TASK ===
Decide what message you want to send to nearby agents. You can share your observations, experiences, or thoughts about the places and situation.

=== RESPOND IN JSON ===
{{
    "message": "message to nearby agents (max 200 words, optional if you don't want to send a message)",
    "reasoning": "brief explanation of why you want to send this message"
}}

Step: {step}
"""
        return prompt

    def create_decision_prompt(
        self,
        place_status: Optional[Dict],
        nearby_agents: List["Agent"],
        step: int,
        message_to_send: str = "",
        fire_info: Optional[List[Dict]] = None,
    ) -> str:
        nearby_text = self._build_nearby_agents_context(nearby_agents)
        memory_text = self._build_memory_context()
        messages_text = self._build_messages_context()

        current_place_info = None
        if self.in_place and self.current_place:
            current_place_info = next(
                (p for p in self.places if p["name"] == self.current_place), None
            )
            if current_place_info is None:
                raise ValueError(
                    f"Agent {self.id} is in place '{self.current_place}' but not found."
                )

        if self.in_place and place_status and current_place_info:
            place_section_text = (
                f"\nYou are currently in the {current_place_info['type']} "
                f"({current_place_info['name']})."
                f"\n  Number of agents here: {place_status.get('agents_in_place', 0)}"
                f"\n  Capacity: {place_status.get('capacity', 0)}"
                f"\n  Occupancy rate: {place_status.get('occupancy_rate', 0.0):.2f}"
            )
        else:
            place_section_text = ""

        place_locations = []
        for place in self.places:
            place_locations.append(
                f"{place['name']} ({place['type']}): center at ({place['center_x']}, {place['center_y']}), "
                f"covers X from {place['center_x'] - place['half_size']} to {place['center_x'] + place['half_size']}, "
                f"Y from {place['center_y'] - place['half_size']} to {place['center_y'] + place['half_size']}"
            )
        place_locations_text = "\n".join(place_locations)

        unique_types = list({p["type"] for p in self.places})
        world_description = f"a 2D world with multiple places ({', '.join(unique_types)})"

        message_section = ""
        if message_to_send:
            message_section = f"\n=== MESSAGE YOU DECIDED TO SEND ===\n{message_to_send}\n"
        fire_section = self._build_fire_section(fire_info)
        environment_section = self._build_environment_section()
        persona_section = self._build_persona_section()

        prompt = f"""You are Agent {self.id} ({self.gender}) in {world_description}.
{persona_section}
=== YOUR CURRENT STATE ===
Gender: {self.gender}
Position: ({self.position[0]}, {self.position[1]})
In place: {"Yes" if self.in_place else "No"}
{"Current place: " + self.current_place if self.in_place else ""}
{place_section_text}
{environment_section}{fire_section}
=== PLACE LOCATIONS ===
{place_locations_text}

=== NEARBY AGENTS ===
{nearby_text}

=== PREVIOUS MEMORY ===
{memory_text}

=== MESSAGES FROM OTHERS ===
{messages_text}
{message_section}=== AVAILABLE ACTIONS ===
- "stay": remain at current position
- "move" with direction: "up" (Y+1), "down" (Y-1), "left" (X-1), "right" (X+1)

Field boundaries: X and Y from -{self.half_space_size} to +{self.half_space_size}

=== RESPOND IN JSON ===
{{
    "action": "move" or "stay",
    "direction": "up", "down", "left", or "right" (only if action is "move"),
    "memory": "what you want to remember for the next step (your thoughts, observations, intentions)",
    "reasoning": "brief explanation of your decision"
}}

Step: {step}
"""
        return prompt

    @staticmethod
    def _extract_json_from_text(text: str) -> Optional[str]:
        """波カッコ対応で最初の JSON オブジェクトを抜き出す。"""
        start = text.find("{")
        if start == -1:
            return None
        depth = 0
        in_string = False
        escape_next = False
        for i, ch in enumerate(text[start:], start=start):
            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_string:
                escape_next = True
                continue
            if ch == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start: i + 1]
        return None

    @staticmethod
    def _extract_direction_from_text(text: str) -> Optional[str]:
        t = text.lower()
        for d in ("up", "down", "left", "right"):
            if d in t:
                return d
        return None

    def parse_message_response(self, response: str) -> MessageDecision:
        json_str = self._extract_json_from_text(response)
        if json_str:
            try:
                parsed = json.loads(json_str)
                message = self._limit_message_words(parsed.get("message", ""))
                return {"message": message, "reasoning": parsed.get("reasoning", "")}
            except json.JSONDecodeError as e:
                logger.debug(f"JSON parse failed: {response[:80]}... ({e})")
        return {
            "message": "",
            "reasoning": response[:FALLBACK_REASONING_LENGTH],
        }

    def parse_action_response(self, response: str) -> ActionDecision:
        json_str = self._extract_json_from_text(response)
        if json_str:
            try:
                parsed = json.loads(json_str)
                return {
                    "action": parsed.get("action", "stay"),
                    "direction": parsed.get("direction"),
                    "memory": parsed.get("memory", ""),
                    "reasoning": parsed.get("reasoning", ""),
                }
            except json.JSONDecodeError as e:
                logger.debug(f"JSON parse failed: {response[:80]}... ({e})")

        action = "stay"
        direction = None
        if "move" in response.lower():
            action = "move"
            direction = self._extract_direction_from_text(response)
        return {
            "action": action,
            "direction": direction,
            "memory": "",
            "reasoning": response[:FALLBACK_REASONING_LENGTH],
        }

    def decide_message(
        self,
        place_status: Optional[Dict],
        nearby_agents: List["Agent"],
        step: int,
        fire_info: Optional[List[Dict]] = None,
    ) -> MessageDecision:
        prompt = self.create_message_prompt(place_status, nearby_agents, step, fire_info=fire_info)
        try:
            response = self.llm_client.generate(prompt)
            return self.parse_message_response(response)
        except Exception as e:
            logger.error(f"Error in agent {self.id} message decision: {e}")
            return {"message": "", "reasoning": "Error occurred"}

    def decide_action(
        self,
        place_status: Optional[Dict],
        nearby_agents: List["Agent"],
        step: int,
        message_to_send: str = "",
        fire_info: Optional[List[Dict]] = None,
    ) -> ActionDecision:
        prompt = self.create_decision_prompt(
            place_status, nearby_agents, step, message_to_send, fire_info=fire_info
        )
        try:
            response = self.llm_client.generate(prompt)
            decision = self.parse_action_response(response)
            memory_content = decision.get("memory", "")
            entry = (
                f"Step {step}: {memory_content}"
                if memory_content
                else f"Step {step}: {decision.get('reasoning', 'No memory')}"
            )
            self.memory.append(entry)
            if len(self.memory) > self.memory_limit:
                self.memory.pop(0)
            return decision
        except Exception as e:
            logger.error(f"Error in agent {self.id} action decision: {e}")
            return {"action": "stay", "direction": None, "memory": "", "reasoning": "Error occurred"}

    def move(self, direction: str) -> Tuple[int, int]:
        x, y = self.position
        dx, dy = DIRECTION_MAP.get(direction, (0, 0))
        h = self.half_space_size
        new_x = max(-h, min(h, x + dx))
        new_y = max(-h, min(h, y + dy))
        self.position = (new_x, new_y)
        self.total_moves += 1
        return self.position

    def receive_message(
        self, from_agent_id: int, content: str, step: Optional[int] = None
    ) -> List[Dict]:
        """発話を受信。発生した認知メモリイベントを返す(無効なら空リスト)。"""
        msg = {
            "from": from_agent_id,
            "content": content,
            "step": step if step is not None else len(self.received_messages),
        }
        self.received_messages.append(msg)
        if len(self.received_messages) > self.message_history_limit:
            self.received_messages.pop(0)
        logger.info(f'Agent {self.id} received message from Agent {from_agent_id}: "{content}"')

        events: List[Dict] = []
        if self.cognitive_memory is not None and step is not None:
            cog_events = self.cognitive_memory.record_interaction(
                other_id=from_agent_id, step=step, msg=msg
            )
            for ev in cog_events:
                events.append({**ev, "agent_id": self.id})
        return events

    def update_state(self, places: Optional[List[PlaceConfig]] = None):
        if places is None:
            places = self.places
        place_at_position = get_place_at_position(self.position, places)
        self.in_place = place_at_position is not None
        self.current_place = place_at_position["name"] if place_at_position else None
        if self.in_place:
            self.steps_in_place += 1
        else:
            self.steps_outside_place += 1
