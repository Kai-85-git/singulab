"""Place 定義と所在判定。1 階(物)の中核。"""
from typing import List, Optional, Tuple, TypedDict


class PlaceConfig(TypedDict):
    """Place 設定。参考実装 utils.py の TypedDict をそのまま踏襲。"""
    name: str
    type: str
    center_x: int
    center_y: int
    half_size: int
    capacity: int


def is_position_in_place(
    position: Tuple[int, int],
    half_size: int,
    center_x: int = 0,
    center_y: int = 0,
) -> bool:
    """位置が place 内かどうか(矩形内包判定)。

    Args:
        position: (x, y) 座標
        half_size: 中心からの半幅(矩形は中心 ± half_size)
        center_x: place 中心 X(既定 0)
        center_y: place 中心 Y(既定 0)
    """
    x, y = position
    return (
        center_x - half_size <= x <= center_x + half_size
        and center_y - half_size <= y <= center_y + half_size
    )


def get_place_at_position(
    position: Tuple[int, int],
    places: List[PlaceConfig],
) -> Optional[PlaceConfig]:
    """位置を含む place を返す。

    重なる place が複数あった場合、**half_size が最小の place** を返す
    (= 矩形面積が最小 = 内側の place を優先)。
    設計書 [03_1階-物/03_場の構造定義 §4](../../docs/01_設計書/03_1階-物/03_場の構造定義.md) 参照。
    """
    candidates = [
        place
        for place in places
        if is_position_in_place(
            position,
            place["half_size"],
            place["center_x"],
            place["center_y"],
        )
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda p: p["half_size"])
