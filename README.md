# photonic-mask-build

![CI](https://github.com/<your-username>/photonic-mask-build/actions/workflows/ci.yml/badge.svg)

A small Python tool that assembles individual chip designs (GDS files) onto a
single reticle layout, runs basic checks, and writes a build record so every
build is reproducible and traceable. Built with the KLayout Python API.

## What it does

1. Reads a JSON manifest listing each design: its GDS file, top cell, and
   placement on the reticle.
2. Copies each design into one merged layout and places it at its site.
3. Fails the build if a design falls outside the reticle, overlaps another
   design, or references a cell that doesn't exist.
4. Adds alignment marks.
5. Writes the merged GDS and `build_record.json`, which lists the SHA-256 hash
   of every input and the output.

## Quick start

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 mask_build.py --demo
```

This creates two sample designs, builds them, and writes `mask_out.gds` and
`build_record.json`. Open the GDS in [KLayout](https://www.klayout.de) to view it.

To build from your own manifest:

```
python3 mask_build.py manifest.json --out mask_out.gds --record build_record.json
```

### Manifest format

```json
{
  "top_cell": "RETICLE_TOP",
  "reticle_um": [2000, 1000],
  "alignment_marks_um": [[100, 100], [1900, 900]],
  "designs": [
    {"name": "D1", "gds": "design1.gds", "cell": "DEVICE1", "x_um": 200, "y_um": 300}
  ]
}
```

## Tests and CI

```
pytest -v
```

The tests cover a valid build, overlap and out-of-bounds failures, a missing
cell, hash correctness in the build record, and build reproducibility.
GitHub Actions runs the tests and the demo build on every push and pull
request, and uploads the output files as a downloadable artifact.

## Limitations

- Layer numbers (alignment marks on 100/0) are placeholders, not a real
  process layer map.
- Checks are limited to placement. There is no DRC, density, or fill step yet.
- Placement is by cell origin, so a cell with geometry at negative coordinates
  extends left of and below its site.

## Possible next steps

- Add a KLayout DRC check (minimum width and spacing) that fails the build.
- Use GDSFactory-generated photonic components as the input designs.
- Run a scheduled nightly build in CI.
