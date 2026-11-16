import hashlib
import json

import mask_build


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def run(tmp_path, manifest_path):
    out = str(tmp_path / "out.gds")
    rec = str(tmp_path / "record.json")
    return mask_build.build(manifest_path, out, rec), out, rec


def make_manifest(tmp_path):
    """Create the two demo designs and return the manifest as a dict."""
    path = mask_build.make_demo(tmp_path / "inputs")
    return json.loads(open(path).read())


def write_manifest(tmp_path, manifest):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    return str(path)


def test_valid_build_succeeds(tmp_path):
    manifest = make_manifest(tmp_path)
    code, out, rec = run(tmp_path, write_manifest(tmp_path, manifest))
    assert code == 0
    assert (tmp_path / "out.gds").exists()


def test_overlapping_designs_fail(tmp_path):
    manifest = make_manifest(tmp_path)
    manifest["designs"][1]["x_um"] = manifest["designs"][0]["x_um"]
    manifest["designs"][1]["y_um"] = manifest["designs"][0]["y_um"]
    code, _, _ = run(tmp_path, write_manifest(tmp_path, manifest))
    assert code == 1


def test_design_outside_reticle_fails(tmp_path):
    manifest = make_manifest(tmp_path)
    manifest["designs"][0]["x_um"] = 1900  # 300 um wide, reticle is 2000 um
    code, _, _ = run(tmp_path, write_manifest(tmp_path, manifest))
    assert code == 1


def test_missing_cell_fails(tmp_path):
    manifest = make_manifest(tmp_path)
    manifest["designs"][0]["cell"] = "NO_SUCH_CELL"
    code, _, _ = run(tmp_path, write_manifest(tmp_path, manifest))
    assert code == 1


def test_build_record_hashes_match(tmp_path):
    manifest = make_manifest(tmp_path)
    code, out, rec = run(tmp_path, write_manifest(tmp_path, manifest))
    record = json.loads(open(rec).read())
    assert record["output"]["sha256"] == sha(out)
    for entry in record["designs"]:
        assert entry["sha256"] == sha(entry["gds"])


def test_build_is_reproducible(tmp_path):
    manifest = make_manifest(tmp_path)
    mpath = write_manifest(tmp_path, manifest)
    _, out1, rec1 = run(tmp_path, mpath)
    first = sha(out1)
    _, out2, _ = run(tmp_path, mpath)
    assert sha(out2) == first
