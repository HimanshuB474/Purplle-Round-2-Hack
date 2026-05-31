"""HOG person fallback for back-office (STAFF) camera when YOLO finds no tracks."""

from __future__ import annotations

import math

import cv2
import numpy as np

_hog: cv2.HOGDescriptor | None = None


def _get_hog() -> cv2.HOGDescriptor:
    global _hog
    if _hog is None:
        _hog = cv2.HOGDescriptor()
        _hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    return _hog


def detect_hog_boxes(frame: np.ndarray) -> list[tuple[float, float, float, float, float]]:
    """Return list of (x1, y1, x2, y2, confidence) in original frame coordinates."""
    h, w = frame.shape[:2]
    work = frame
    scale_back = 1.0
    if w > 1280:
        scale_back = w / 1280.0
        work = cv2.resize(frame, (1280, int(h / scale_back)))

    hog = _get_hog()
    rects, weights = hog.detectMultiScale(
        work,
        winStride=(8, 8),
        padding=(16, 16),
        scale=1.05,
    )
    boxes: list[tuple[float, float, float, float, float]] = []
    for i, (x, y, bw, bh) in enumerate(rects):
        wt = float(weights[i]) if len(weights) > i else 0.5
        conf = min(0.92, max(0.38, wt * 0.15))
        x1 = x * scale_back
        y1 = y * scale_back
        x2 = (x + bw) * scale_back
        y2 = (y + bh) * scale_back
        boxes.append((x1, y1, x2, y2, conf))
    return boxes


def match_hog_track(
    tracks: dict[int, object],
    cx: float,
    cy: float,
    *,
    max_dist: float = 140.0,
) -> int | None:
    best_id: int | None = None
    best_dist = max_dist
    for tid, state in tracks.items():
        lx = getattr(state, "last_cx", None)
        ly = getattr(state, "last_cy", None)
        if lx is None or ly is None:
            continue
        dist = math.hypot(lx - cx, ly - cy)
        if dist < best_dist:
            best_dist = dist
            best_id = tid
    return best_id
