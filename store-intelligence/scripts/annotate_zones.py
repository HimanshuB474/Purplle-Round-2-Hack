"""Draw zone polygons on CCTV sample frames for verification."""
import json
from pathlib import Path

import cv2

ROOT = Path(r"d:\purple hack\store-intelligence")
LAYOUT = json.loads((ROOT / "data" / "store_layout.json").read_text(encoding="utf-8"))
SAMPLES = ROOT / "data" / "layout" / "cctv_samples"
OUT = ROOT / "data" / "layout" / "cctv_annotated"
OUT.mkdir(parents=True, exist_ok=True)

COLORS = {
    "ENTRY": (0, 255, 255),
    "SKIN": (0, 200, 0),
    "MAKEUP": (255, 105, 180),
    "HAIR": (0, 165, 255),
    "FRAGRANCE": (255, 0, 255),
    "PERSONAL_CARE": (255, 255, 0),
    "BILLING": (0, 0, 255),
    "STAFF_BACK": (128, 128, 128),
    "BATH_BODY": (200, 200, 0),
}

store = LAYOUT["stores"][0]
cam_to_sample = {
    "CAM 3.mp4": "cam3_mid.jpg",
    "CAM 1.mp4": "cam1_mid.jpg",
    "CAM 2.mp4": "cam2_mid.jpg",
    "CAM 5.mp4": "cam5_mid.jpg",
    "CAM 4.mp4": "cam4_mid.jpg",
}


def draw_camera(cam: dict) -> None:
    sample = cam_to_sample.get(cam["source_file"])
    if not sample:
        return
    img_path = SAMPLES / sample
    if not img_path.exists():
        print(f"Missing sample: {img_path}")
        return

    img = cv2.imread(str(img_path))
    if img is None:
        return

    # Entry line
    if "entry_line" in cam:
        p1, p2 = cam["entry_line"]
        cv2.line(img, tuple(p1), tuple(p2), (0, 255, 255), 3)
        cv2.putText(
            img,
            "ENTRY LINE",
            (p1[0], p1[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2,
        )

    for zone in cam.get("zones", []):
        zid = zone["zone_id"]
        pts = zone["polygon"]
        color = COLORS.get(zid, (255, 255, 255))
        arr = __import__("numpy").array(pts, dtype=__import__("numpy").int32)
        cv2.polylines(img, [arr], True, color, 2)
        overlay = img.copy()
        cv2.fillPoly(overlay, [arr], color)
        cv2.addWeighted(overlay, 0.15, img, 0.85, 0, img)
        cx = sum(p[0] for p in pts) // len(pts)
        cy = sum(p[1] for p in pts) // len(pts)
        label = zid
        if zone.get("sku_zone"):
            label += f" ({zone['sku_zone']})"
        cv2.putText(img, label, (cx - 80, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

    title = f"{cam['camera_id']} | {cam['role']} | {cam['source_file']}"
    cv2.putText(img, title, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(img, title, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 1)

    out_path = OUT / f"annotated_{cam['camera_id']}.jpg"
    cv2.imwrite(str(out_path), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    for cam in store["cameras"]:
        draw_camera(cam)
    print("\nCamera role summary:")
    for k, v in store["camera_role_summary"].items():
        print(f"  {k} -> {v}")
