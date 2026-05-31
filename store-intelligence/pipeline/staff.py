"""Staff classification — see docs/context/06-detection-pipeline.md"""

from __future__ import annotations


def classify_staff(
    camera_role: str,
    exclude_from_metrics: bool,
    frame_bgr: object | None,
    bbox_xyxy: tuple[float, float, float, float],
) -> tuple[bool, float]:
    """Staff = back-office camera only; floor cameras are customers unless role is STAFF."""
    if exclude_from_metrics or camera_role == "STAFF":
        return True, 0.95
    return False, 0.75
