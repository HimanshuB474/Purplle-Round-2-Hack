"""Per-track session state for zone / entry logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


def new_visitor_id(seq: int) -> str:
    return f"VIS_{seq:04d}"


@dataclass
class TrackState:
    track_id: int
    visitor_id: str
    is_staff: bool
    staff_confidence: float = 0.7
    prev_cy: float | None = None
    last_cx: float | None = None
    last_cy: float | None = None
    inside_store: bool = False
    has_exited: bool = False
    current_zones: set[str] = field(default_factory=set)
    zone_entered_at: dict[str, float] = field(default_factory=dict)
    last_dwell_emit: dict[str, float] = field(default_factory=dict)
    session_seq: int = 0
    billing_active: bool = False
    billing_joined: bool = False
    billing_join_at: float | None = None
    sku_by_zone: dict[str, str | None] = field(default_factory=dict)
    zone_miss: dict[str, int] = field(default_factory=dict)
    frames_missing: int = 0
    exited_this_clip: bool = False
    entry_emitted: bool = False

    def bump_session(self) -> int:
        self.session_seq += 1
        return self.session_seq
