"""フィールド境界と座標系。Phase 1 では境界 clamp ヘルパのみ。"""
from typing import Tuple


class Field:
    """中心 (0, 0) を持つ正方フィールド。境界は ±half_space_size。"""

    def __init__(self, half_space_size: int):
        self.half_space_size = half_space_size

    @property
    def bounds(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """((xmin, xmax), (ymin, ymax))"""
        h = self.half_space_size
        return ((-h, h), (-h, h))

    def clamp(self, position: Tuple[int, int]) -> Tuple[int, int]:
        """フィールド境界に丸める。"""
        x, y = position
        h = self.half_space_size
        return (max(-h, min(h, x)), max(-h, min(h, y)))

    def in_bounds(self, position: Tuple[int, int]) -> bool:
        x, y = position
        h = self.half_space_size
        return -h <= x <= h and -h <= y <= h
