"""Detection + tracking on CCTV clips — YOLOv8 + ByteTrack."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2

from pipeline.config import (
    DETECT_CONF,
    DETECT_CONF_STAFF_CAM,
    DWELL_EMIT_SEC,
    DWELL_EMIT_SEC_SHORT_CLIP,
    ENTRY_LINE_MARGIN_PX,
    EVENT_STORE_ID,
    MAX_FRAMES,
    PERSON_CLASS_ID,
    SAMPLE_INTERVAL_SEC,
    SHORT_CLIP_MAX_SEC,
    TRACK_GONE_FRAMES,
    ZONE_EXIT_MISS_FRAMES,
    YOLO_MODEL,
)
from pipeline.emit import EventEmitter, frame_to_timestamp, write_jsonl
from pipeline.pos_filter import filter_false_billing_abandons
from pipeline.reid import (
    CrossCameraRegistry,
    appearance_histogram,
    merge_visitor_ids_post,
    parse_event_ts,
)
from pipeline.staff import classify_staff
from pipeline.staff_detect import detect_hog_boxes, match_hog_track
from pipeline.tracker import TrackState, new_visitor_id
from pipeline.zones import (
    ZoneDef,
    crossed_entry_inbound,
    crossed_entry_outbound,
    entry_line_y,
    parse_zone_defs,
    point_in_polygon,
    zones_at_point,
)


def _emit_entry_or_reentry(
    emitter: EventEmitter,
    state: TrackState,
    timestamp: str,
    det_conf: float,
    *,
    is_reentry: bool,
) -> None:
    seq = state.bump_session()
    emitter.emit(
        visitor_id=state.visitor_id,
        event_type="REENTRY" if is_reentry else "ENTRY",
        timestamp=timestamp,
        zone_id=None,
        dwell_ms=0,
        is_staff=state.is_staff,
        confidence=det_conf,
        session_seq=seq,
    )


def _emit_exit(
    emitter: EventEmitter,
    state: TrackState,
    timestamp: str,
    det_conf: float,
    *,
    role: str,
) -> None:
    if not state.inside_store and role != "ENTRY":
        return
    seq = state.bump_session()
    emitter.emit(
        visitor_id=state.visitor_id,
        event_type="EXIT",
        timestamp=timestamp,
        zone_id=None,
        dwell_ms=0,
        is_staff=state.is_staff,
        confidence=det_conf,
        session_seq=seq,
    )
    state.inside_store = False
    state.has_exited = True
    state.exited_this_clip = True
    state.current_zones.clear()
    state.billing_joined = False
    state.billing_active = False


def _process_staff_hog_frame(
    emitter: EventEmitter,
    tracks: dict[int, TrackState],
    *,
    frame,
    zones: list[ZoneDef],
    timestamp: str,
    video_sec: float,
    det_conf_floor: float,
    dwell_emit_sec: float,
    visitor_seq: list[int],
) -> None:
    """HOG fallback path for STAFF camera — all detections tagged is_staff=true."""
    hog_boxes = detect_hog_boxes(frame)
    active_ids: set[int] = set()
    next_tid = max(tracks.keys(), default=0) + 1

    for x1, y1, x2, y2, hog_conf in hog_boxes:
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        tid = match_hog_track(tracks, cx, cy)
        if tid is None:
            tid = next_tid
            next_tid += 1
            visitor_seq[0] += 1
            tracks[tid] = TrackState(
                track_id=tid,
                visitor_id=new_visitor_id(visitor_seq[0]),
                is_staff=True,
                staff_confidence=hog_conf,
                inside_store=True,
                entry_emitted=True,
            )

        state = tracks[tid]
        active_ids.add(tid)
        state.frames_missing = 0
        state.last_cx = cx
        state.last_cy = cy
        det_conf = max(det_conf_floor, hog_conf)

        hit_zones = zones_at_point(cx, cy, zones)
        _handle_zones(
            emitter,
            state,
            tracks,
            role="STAFF",
            zones=zones,
            hit_zones=hit_zones,
            timestamp=timestamp,
            video_sec=video_sec,
            det_conf=det_conf,
            dwell_emit_sec=dwell_emit_sec,
        )

    _update_missing_tracks(
        emitter,
        tracks,
        active_ids,
        role="STAFF",
        timestamp=timestamp,
        default_conf=det_conf_floor,
    )


def _load_model():
    from ultralytics import YOLO

    return YOLO(YOLO_MODEL)


def _billing_queue_depth(tracks: dict[int, TrackState], zones: list[ZoneDef]) -> int:
    billing_ids = {z.zone_id for z in zones if z.zone_id == "BILLING"}
    count = sum(
        1
        for s in tracks.values()
        if not s.is_staff and s.current_zones & billing_ids
    )
    return max(count, 1)


def _dwell_threshold(clip_duration_sec: float) -> float:
    if clip_duration_sec <= SHORT_CLIP_MAX_SEC:
        return min(DWELL_EMIT_SEC, DWELL_EMIT_SEC_SHORT_CLIP)
    return DWELL_EMIT_SEC


def _handle_entry_camera(
    emitter: EventEmitter,
    state: TrackState,
    *,
    role: str,
    zones: list[ZoneDef],
    y_line: float | None,
    cx: float,
    cy: float,
    timestamp: str,
    det_conf: float,
) -> None:
    if role != "ENTRY":
        return
    entry_zone = next((z for z in zones if z.zone_id == "ENTRY"), None)
    margin = ENTRY_LINE_MARGIN_PX

    if y_line is not None:
        if crossed_entry_inbound(state.prev_cy, cy, y_line, margin):
            _emit_entry_or_reentry(
                emitter, state, timestamp, det_conf, is_reentry=state.has_exited
            )
            state.has_exited = False
            state.inside_store = True
            state.entry_emitted = True
            state.frames_missing = 0
        elif crossed_entry_outbound(state.prev_cy, cy, y_line, margin):
            _emit_exit(emitter, state, timestamp, det_conf, role=role)

    if entry_zone and point_in_polygon(cx, cy, entry_zone.polygon):
        if not state.inside_store:
            _emit_entry_or_reentry(emitter, state, timestamp, det_conf, is_reentry=False)
            state.inside_store = True
            state.entry_emitted = True
            state.has_exited = False
        elif state.has_exited:
            _emit_entry_or_reentry(emitter, state, timestamp, det_conf, is_reentry=True)
            state.has_exited = False
            state.inside_store = True
            state.entry_emitted = True


def _handle_zones(
    emitter: EventEmitter,
    state: TrackState,
    tracks: dict[int, TrackState],
    *,
    role: str,
    zones: list[ZoneDef],
    hit_zones: list[ZoneDef],
    timestamp: str,
    video_sec: float,
    det_conf: float,
    dwell_emit_sec: float,
) -> None:
    hit_ids = {z.zone_id for z in hit_zones}

    for z in hit_zones:
        state.sku_by_zone[z.zone_id] = z.sku_zone
        state.zone_miss[z.zone_id] = 0

    for zid in list(state.current_zones):
        if zid in hit_ids:
            continue
        state.zone_miss[zid] = state.zone_miss.get(zid, 0) + 1
        if state.zone_miss[zid] < ZONE_EXIT_MISS_FRAMES:
            continue
        seq = state.bump_session()
        if zid == "BILLING" and state.billing_joined and not state.is_staff:
            emitter.emit(
                visitor_id=state.visitor_id,
                event_type="BILLING_QUEUE_ABANDON",
                timestamp=timestamp,
                zone_id="BILLING",
                dwell_ms=0,
                is_staff=state.is_staff,
                confidence=det_conf,
                session_seq=seq,
            )
            state.billing_joined = False
        emitter.emit(
            visitor_id=state.visitor_id,
            event_type="ZONE_EXIT",
            timestamp=timestamp,
            zone_id=zid,
            dwell_ms=0,
            is_staff=state.is_staff,
            confidence=det_conf,
            sku_zone=state.sku_by_zone.get(zid),
            session_seq=seq,
        )
        state.zone_entered_at.pop(zid, None)
        state.last_dwell_emit.pop(zid, None)
        state.zone_miss.pop(zid, None)
        state.current_zones.discard(zid)

    for z in hit_zones:
        zid = z.zone_id
        if zid == "ENTRY" and role == "ENTRY":
            state.current_zones.add(zid)
            continue
        if zid not in state.current_zones:
            seq = state.bump_session()
            emitter.emit(
                visitor_id=state.visitor_id,
                event_type="ZONE_ENTER",
                timestamp=timestamp,
                zone_id=zid,
                dwell_ms=0,
                is_staff=state.is_staff,
                confidence=det_conf,
                sku_zone=z.sku_zone,
                session_seq=seq,
            )
            state.zone_entered_at[zid] = video_sec
            state.last_dwell_emit[zid] = video_sec

            if zid == "BILLING" and role == "BILLING" and not state.is_staff:
                depth = _billing_queue_depth(tracks, zones)
                emitter.emit(
                    visitor_id=state.visitor_id,
                    event_type="BILLING_QUEUE_JOIN",
                    timestamp=timestamp,
                    zone_id="BILLING",
                    dwell_ms=0,
                    is_staff=state.is_staff,
                    confidence=det_conf,
                    queue_depth=depth,
                    sku_zone=z.sku_zone or "QUEUE",
                    session_seq=state.bump_session(),
                )
                state.billing_joined = True

        state.current_zones.add(zid)
        entered = state.zone_entered_at.get(zid, video_sec)
        last_dwell = state.last_dwell_emit.get(zid, entered)
        if video_sec - last_dwell >= dwell_emit_sec:
            dwell_ms = int((video_sec - entered) * 1000)
            emitter.emit(
                visitor_id=state.visitor_id,
                event_type="ZONE_DWELL",
                timestamp=timestamp,
                zone_id=zid,
                dwell_ms=max(dwell_ms, int(dwell_emit_sec * 1000)),
                is_staff=state.is_staff,
                confidence=det_conf * 0.95,
                sku_zone=state.sku_by_zone.get(zid),
                session_seq=state.bump_session(),
            )
            state.last_dwell_emit[zid] = video_sec


def _update_missing_tracks(
    emitter: EventEmitter,
    tracks: dict[int, TrackState],
    active_ids: set[int],
    *,
    role: str,
    timestamp: str,
    default_conf: float = 0.7,
) -> None:
    for tid, state in tracks.items():
        if tid in active_ids:
            state.frames_missing = 0
            continue
        if not state.inside_store:
            state.frames_missing += 1
            continue
        state.frames_missing += 1
        if state.frames_missing >= TRACK_GONE_FRAMES:
            _emit_exit(emitter, state, timestamp, default_conf, role=role)


def _finalize_clip(
    emitter: EventEmitter,
    tracks: dict[int, TrackState],
    *,
    role: str,
    timestamp: str,
) -> None:
    """EXIT for visitors still inside at end of clip (stepped out of FOV)."""
    for state in tracks.values():
        if state.inside_store and not state.is_staff:
            _emit_exit(emitter, state, timestamp, 0.75, role=role)


def process_camera(
    camera: dict[str, Any],
    store_id: str,
    project_root: Path,
    model=None,
    verbose: bool = True,
    visitor_seq: list[int] | None = None,
    reid_registry: CrossCameraRegistry | None = None,
) -> EventEmitter:
    clip_path = (project_root / camera["clip_path"]).resolve()
    if not clip_path.exists():
        raise FileNotFoundError(f"CCTV clip not found: {clip_path}")

    fps = float(camera["fps"])
    frame_interval = max(1, int(fps * SAMPLE_INTERVAL_SEC))
    zones = parse_zone_defs(camera)
    role = camera["role"]
    exclude = bool(camera.get("exclude_from_customer_metrics"))
    camera_id = camera["camera_id"]
    base_ts = camera["clip_base_timestamp"]
    entry_line = camera.get("entry_line")
    y_line = entry_line_y(entry_line) if entry_line else None
    conf = DETECT_CONF_STAFF_CAM if role == "STAFF" else DETECT_CONF

    if visitor_seq is None:
        visitor_seq = [0]

    emitter = EventEmitter(store_id, camera_id)
    if model is None:
        model = _load_model()

    cap = cv2.VideoCapture(str(clip_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {clip_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    clip_duration_sec = total_frames / fps
    dwell_emit_sec = _dwell_threshold(clip_duration_sec)
    last_timestamp = frame_to_timestamp(base_ts, total_frames - 1, fps)

    tracks: dict[int, TrackState] = {}
    frame_idx = 0
    processed = 0

    if verbose:
        print(
            f"  Processing {clip_path.name} ({camera_id}, every {frame_interval} frames, "
            f"dwell>={dwell_emit_sec}s)..."
        )

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if MAX_FRAMES and frame_idx >= MAX_FRAMES:
            break

        if frame_idx % frame_interval != 0:
            frame_idx += 1
            continue

        processed += 1
        video_sec = frame_idx / fps
        timestamp = frame_to_timestamp(base_ts, frame_idx, fps)

        if role == "STAFF":
            _process_staff_hog_frame(
                emitter,
                tracks,
                frame=frame,
                zones=zones,
                timestamp=timestamp,
                video_sec=video_sec,
                det_conf_floor=conf,
                dwell_emit_sec=dwell_emit_sec,
                visitor_seq=visitor_seq,
            )
            frame_idx += 1
            continue

        results = model.track(
            frame,
            persist=True,
            classes=[PERSON_CLASS_ID],
            conf=conf,
            verbose=False,
        )
        boxes = results[0].boxes
        active_ids: set[int] = set()

        if boxes is None or len(boxes) == 0 or boxes.id is None:
            _update_missing_tracks(emitter, tracks, active_ids, role=role, timestamp=timestamp)
            frame_idx += 1
            continue

        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        track_ids = boxes.id.cpu().numpy().astype(int)

        for i, tid in enumerate(track_ids):
            tid = int(tid)
            active_ids.add(tid)
            x1, y1, x2, y2 = xyxy[i]
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            det_conf = float(confs[i])

            if tid not in tracks:
                is_staff, _ = classify_staff(role, exclude, frame, (x1, y1, x2, y2))
                ts_dt = parse_event_ts(timestamp)
                app_hist = None if is_staff else appearance_histogram(frame, x1, y1, x2, y2)
                matched_id = None
                if reid_registry is not None and not is_staff:
                    matched_id = reid_registry.match_or_none(
                        timestamp=ts_dt,
                        camera_id=camera_id,
                        appearance=app_hist,
                        is_staff=is_staff,
                    )
                if matched_id:
                    visitor_id = matched_id
                else:
                    visitor_seq[0] += 1
                    visitor_id = new_visitor_id(visitor_seq[0])
                tracks[tid] = TrackState(
                    track_id=tid,
                    visitor_id=visitor_id,
                    is_staff=is_staff,
                )
                if reid_registry is not None:
                    reid_registry.register(
                        visitor_id,
                        camera_id=camera_id,
                        timestamp=ts_dt,
                        is_staff=is_staff,
                        appearance=app_hist,
                        has_entry=False,
                    )

            state = tracks[tid]
            if reid_registry is not None and not state.is_staff:
                reid_registry.register(
                    state.visitor_id,
                    camera_id=camera_id,
                    timestamp=parse_event_ts(timestamp),
                    is_staff=False,
                    appearance=appearance_histogram(frame, x1, y1, x2, y2),
                    has_entry=state.entry_emitted or state.inside_store,
                )

            # First customer detection on non-entry cameras (entry cam uses line/zone logic)
            if (
                role not in ("STAFF", "ENTRY")
                and not exclude
                and not state.is_staff
                and not state.entry_emitted
            ):
                _emit_entry_or_reentry(
                    emitter, state, timestamp, det_conf, is_reentry=False
                )
                state.entry_emitted = True
                state.inside_store = True

            # Same track reappears after EXIT / lost frames
            if (
                role == "ENTRY"
                and state.has_exited
                and not state.inside_store
                and state.frames_missing >= TRACK_GONE_FRAMES
            ):
                _emit_entry_or_reentry(
                    emitter, state, timestamp, det_conf, is_reentry=True
                )
                state.inside_store = True
                state.has_exited = False

            state.frames_missing = 0
            state.last_cx = cx
            state.last_cy = cy
            det_conf = det_conf * (0.85 if state.is_staff else 1.0)

            _handle_entry_camera(
                emitter, state,
                role=role, zones=zones, y_line=y_line,
                cx=cx, cy=cy, timestamp=timestamp, det_conf=det_conf,
            )
            state.prev_cy = cy

            hit_zones = zones_at_point(cx, cy, zones)
            _handle_zones(
                emitter, state, tracks,
                role=role, zones=zones, hit_zones=hit_zones,
                timestamp=timestamp, video_sec=video_sec,
                det_conf=det_conf, dwell_emit_sec=dwell_emit_sec,
            )

        _update_missing_tracks(emitter, tracks, active_ids, role=role, timestamp=timestamp)
        frame_idx += 1

    cap.release()
    if role == "ENTRY":
        _finalize_clip(emitter, tracks, role=role, timestamp=last_timestamp)

    if verbose:
        print(f"    -> {len(emitter.events)} events from {processed} sampled frames")
    return emitter


def run_pipeline(
    layout_path: Path,
    output_path: Path,
    project_root: Path | None = None,
    include_staff_camera: bool = True,
    *,
    apply_pos_filter: bool = True,
    apply_reid: bool = True,
) -> dict[str, int]:
    project_root = project_root or layout_path.parent.parent
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    store = layout["stores"][0]
    store_id = store.get("event_store_id") or store.get("store_id") or EVENT_STORE_ID
    target_date = datetime.fromisoformat(
        store["cameras"][0]["clip_base_timestamp"].replace("Z", "+00:00")
    ).date()

    print(f"Store: {store_id} — {store.get('store_name', '')}")
    print(f"Output: {output_path}\n")

    from pipeline.config import REID_ENABLED, REID_POST_PASS

    model = _load_model()
    all_events: list[dict[str, Any]] = []
    stats: dict[str, int] = {}
    visitor_seq = [0]
    reid_registry = CrossCameraRegistry() if (apply_reid and REID_ENABLED) else None

    cameras = sorted(
        store["cameras"],
        key=lambda c: (0 if c.get("role") == "ENTRY" else 1, c.get("camera_id", "")),
    )

    for cam in cameras:
        if cam.get("exclude_from_customer_metrics") and not include_staff_camera:
            print(f"  SKIP: {cam['camera_id']}")
            continue
        try:
            emitter = process_camera(
                cam,
                store_id,
                project_root,
                model=model,
                visitor_seq=visitor_seq,
                reid_registry=reid_registry,
            )
            all_events.extend(emitter.events)
            stats[cam["camera_id"]] = len(emitter.events)
        except FileNotFoundError as exc:
            print(f"  ERROR: {exc}")
            stats[cam["camera_id"]] = 0

    if apply_reid and REID_ENABLED and REID_POST_PASS:
        before = len({e["visitor_id"] for e in all_events if not e.get("is_staff")})
        all_events = merge_visitor_ids_post(all_events)
        after = len({e["visitor_id"] for e in all_events if not e.get("is_staff")})
        if after < before:
            print(f"  Re-ID post-pass: {before} -> {after} unique visitor IDs")

    all_events = filter_false_billing_abandons(
        all_events, store_id, target_date, enabled=apply_pos_filter
    )
    abandon_n = sum(1 for e in all_events if e.get("event_type") == "BILLING_QUEUE_ABANDON")
    write_jsonl(all_events, output_path)
    staff_n = sum(1 for e in all_events if e.get("is_staff"))
    print(
        f"\nWrote {len(all_events)} events to {output_path} "
        f"({staff_n} staff, {abandon_n} BILLING_QUEUE_ABANDON)"
    )
    return stats


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="CCTV -> events.jsonl")
    parser.add_argument("--layout", default="data/store_layout.json")
    parser.add_argument("--output", default="data/events.jsonl")
    parser.add_argument("--root", default=None, help="Project root (store-intelligence/)")
    parser.add_argument(
        "--no-pos-filter",
        action="store_true",
        help="Keep all BILLING_QUEUE_ABANDON events (no POS false-positive removal)",
    )
    parser.add_argument("--no-reid", action="store_true", help="Disable cross-camera visitor merge")
    args = parser.parse_args()

    root = Path(args.root) if args.root else Path(__file__).resolve().parents[1]
    run_pipeline(
        root / args.layout,
        root / args.output,
        root,
        apply_pos_filter=not args.no_pos_filter,
        apply_reid=not args.no_reid,
    )


if __name__ == "__main__":
    main()
