"""3階(世界の法則)モジュール。

Phase 2-3 で WorldLaws / CommunicationPhysics / AgentMemory を実装。
B3-02(message_delay 強制配送)は Phase 3 以降で追加予定。
"""
from .base import MessageDelay, WorldLaws
from .communication import CommunicationPhysics
from .cognition import AgentMemory, MemoryEntry

__all__ = [
    "MessageDelay",
    "WorldLaws",
    "CommunicationPhysics",
    "AgentMemory",
    "MemoryEntry",
]
