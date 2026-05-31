"""Parse drawing1.xml for zone labels and approximate positions."""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

SI_ROOT = Path(__file__).resolve().parents[2]
drawing_path = SI_ROOT / "data" / "layout" / "drawing1.xml"
drawing = drawing_path.read_text(encoding="utf-8")

texts = re.findall(r"<a:t>([^<]+)</a:t>", drawing)
print("All drawing text labels:")
for i, t in enumerate(texts):
    print(f"  {i+1:2}. {t}")

print("\nShape count:", drawing.count("<xdr:sp "))
print("Picture count:", drawing.count("<xdr:pic"))
print("TwoCellAnchor count:", drawing.count("<xdr:twoCellAnchor"))

root = ET.fromstring(drawing)
NS = {
    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}

items = []
for anchor in root.findall(".//xdr:twoCellAnchor", NS):
    from_el = anchor.find("xdr:from", NS)
    if from_el is None:
        continue
    col = from_el.find("xdr:col", NS)
    row = from_el.find("xdr:row", NS)
    texts_in = [t.text for t in anchor.findall(".//a:t", NS) if t.text]
    label = " ".join(texts_in).strip()
    if label:
        items.append(
            {
                "col": int(col.text) if col is not None else None,
                "row": int(row.text) if row is not None else None,
                "label": label,
            }
        )

print("\nText anchors with grid position:")
for it in sorted(items, key=lambda x: (x["row"], x["col"])):
    print(f"  row={it['row']:2} col={it['col']:2}  {it['label']}")
