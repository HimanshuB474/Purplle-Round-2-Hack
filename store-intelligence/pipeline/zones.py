"""Zone polygon / line-crossing — see docs/context/06-detection-pipeline.md"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


def point_in_polygon(x: float, y: float, polygon: Sequence[Sequence[float]]) -> bool:
    """Ray-casting point-in-polygon test."""
    inside = False
    n = len(polygon)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi):
            inside = not inside
        j = i
    return inside


def entry_line_y(entry_line: Sequence[Sequence[float]]) -> float:
    """Horizontal entry line — average y of endpoints."""
    return (entry_line[0][1] + entry_line[1][1]) / 2.0


def crossed_entry_inbound(prev_y: float | None, cur_y: float, y_line: float, margin: float = 0) -> bool:
    if prev_y is None:
        return False
    line = y_line + margin
    return prev_y < line <= cur_y


def crossed_entry_outbound(prev_y: float | None, cur_y: float, y_line: float, margin: float = 0) -> bool:
    if prev_y is None:
        return False
    line = y_line - margin
    return prev_y >= line > cur_y


@dataclass(frozen=True)
class ZoneDef:
    zone_id: str
    polygon: list[list[float]]
    sku_zone: str | None = None


def zones_at_point(x: float, y: float, zones: list[ZoneDef]) -> list[ZoneDef]:
    return [z for z in zones if point_in_polygon(x, y, z.polygon)]


def parse_zone_defs(camera: dict) -> list[ZoneDef]:
    return [
        ZoneDef(
            zone_id=z["zone_id"],
            polygon=z["polygon"],
            sku_zone=z.get("sku_zone"),
        )
        for z in camera.get("zones", [])
    ]
