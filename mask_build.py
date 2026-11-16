#!/usr/bin/env python3
"""Minimal mask-build example using KLayout's Python API.

Reads a manifest of designs, places each one on a reticle, adds an alignment
mark, runs basic checks, writes one merged GDS plus a build record
(inputs + SHA-256 hashes) so the build is reproducible and traceable.

    python3 mask_build.py --demo          # makes sample inputs, then builds
    python3 mask_build.py manifest.json   # builds from your own manifest
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import klayout.db as db

ALIGN_LAYER = db.LayerInfo(100, 0)   # example layer numbers, not a real process
FRAME_LAYER = db.LayerInfo(101, 0)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def add_alignment_mark(layout, top, x_um, y_um, size_um=50.0):
    """Cross-shaped mark made of two boxes, at (x, y) in microns."""
    layer = layout.layer(ALIGN_LAYER)
    dbu = layout.dbu
    s, w = int(size_um / dbu), int(5 / dbu)
    cx, cy = int(x_um / dbu), int(y_um / dbu)
    top.shapes(layer).insert(db.Box(cx - s, cy - w, cx + s, cy + w))
    top.shapes(layer).insert(db.Box(cx - w, cy - s, cx + w, cy + s))


def build(manifest_path, out_gds, record_path):
    manifest = json.loads(Path(manifest_path).read_text())
    reticle_w, reticle_h = manifest["reticle_um"]

    layout = db.Layout()
    layout.dbu = 0.001
    top = layout.create_cell(manifest["top_cell"])
    dbu = layout.dbu
    reticle = db.Box(0, 0, int(reticle_w / dbu), int(reticle_h / dbu))
    errors, record = [], {"top_cell": manifest["top_cell"], "designs": []}

    for d in manifest["designs"]:
        src = db.Layout()
        src.read(d["gds"])
        src_cell = src.cell(d["cell"])
        if src_cell is None:
            errors.append(f"{d['name']}: cell '{d['cell']}' not found in {d['gds']}")
            continue

        # Copy the design's hierarchy into the merged layout under a unique name.
        new_cell = layout.create_cell(f"{d['name']}_{d['cell']}")
        new_cell.copy_tree(src_cell)

        # Place it at the reserved site and check it fits on the reticle.
        x, y = int(d["x_um"] / dbu), int(d["y_um"] / dbu)
        top.insert(db.CellInstArray(new_cell.cell_index(), db.Trans(x, y)))
        placed = new_cell.bbox().moved(x, y)
        if not reticle.contains(placed.p1) or not reticle.contains(placed.p2):
            errors.append(f"{d['name']}: placed bbox {placed} is outside the reticle")

        record["designs"].append({
            "name": d["name"], "gds": d["gds"], "sha256": sha256(d["gds"]),
            "x_um": d["x_um"], "y_um": d["y_um"],
        })

    # Check no two placed designs overlap.
    boxes = [(i.cell.name, i.bbox()) for i in top.each_inst()]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if boxes[i][1].overlaps(boxes[j][1]):
                errors.append(f"overlap: {boxes[i][0]} and {boxes[j][0]}")

    for x_um, y_um in manifest.get("alignment_marks_um", []):
        add_alignment_mark(layout, top, x_um, y_um)

    if errors:
        print("BUILD FAILED:", *errors, sep="\n  ", file=sys.stderr)
        return 1

    layout.write(out_gds)
    record["output"] = {"gds": out_gds, "sha256": sha256(out_gds)}
    Path(record_path).write_text(json.dumps(record, indent=2))
    print(f"OK: wrote {out_gds} ({len(record['designs'])} designs) and {record_path}")
    return 0


def make_demo(folder):
    """Create two tiny sample designs and a manifest for them."""
    folder = Path(folder)
    folder.mkdir(exist_ok=True)
    manifest = {"top_cell": "RETICLE_TOP", "reticle_um": [2000, 1000],
                "alignment_marks_um": [[100, 100], [1900, 900]], "designs": []}
    for n, (w, h, x) in enumerate([(300, 200, 200), (400, 250, 800)], start=1):
        ly = db.Layout()
        ly.dbu = 0.001
        c = ly.create_cell(f"DEVICE{n}")
        c.shapes(ly.layer(1, 0)).insert(db.Box(0, 0, w * 1000, h * 1000))
        path = str(folder / f"design{n}.gds")
        ly.write(path)
        manifest["designs"].append({"name": f"D{n}", "gds": path, "cell": f"DEVICE{n}",
                                    "x_um": x, "y_um": 300})
    mpath = folder / "manifest.json"
    mpath.write_text(json.dumps(manifest, indent=2))
    return str(mpath)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", nargs="?")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--out", default="mask_out.gds")
    ap.add_argument("--record", default="build_record.json")
    a = ap.parse_args()
    manifest = make_demo("demo_inputs") if a.demo else a.manifest
    if not manifest:
        ap.error("give a manifest path or use --demo")
    sys.exit(build(manifest, a.out, a.record))
