"""Frozen before replay: path progress/termination and unchanged-control audit."""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "2"
os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
from collections import Counter
import json
from pathlib import Path
import numpy as np
from PIL import Image
import core
import run_p0

W = Path(__file__).resolve().parents[2]
R = Path("/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_002")
P = R.parent/"round_001"
CFG = json.loads((W/"docs/partwise_sketch_hatching/round_001/PROTOCOL.json").read_text())


def path_records(root, name, mesh):
    z = np.load(root/"strokes"/(name+".npz"))
    records = []
    anchors = {}
    for i, (a, b) in enumerate(zip(z["offsets"][:-1], z["offsets"][1:])):
        f, bary = z["faces"][a:b], z["bary"][a:b]
        xyz = np.einsum("ni,nij->nj", bary, mesh["tri"][f])
        segment = np.linalg.norm(np.diff(xyz, axis=0), axis=1)
        arc = np.r_[0., np.cumsum(segment)]
        indices = np.flatnonzero(np.r_[True, np.diff(f) != 0])
        transitions = f[indices]
        backward = transitions[:-2] == transitions[2:]
        short_cycle = backward & ((arc[indices[2:]]-arc[indices[:-2]]) < 1e-6)
        face_changes = np.flatnonzero(np.diff(f) != 0)
        gap = np.linalg.norm(xyz[face_changes+1]-xyz[face_changes], axis=1)
        expected = CFG["strokes"]["length_by_part"][str(z["parts"][i])]
        records.append({
            "id": str(z["ids"][i]), "part": int(z["parts"][i]), "samples": len(f),
            "length_world": float(arc[-1]), "requested_length_world": expected,
            "shortfall_world": max(0., expected-float(arc[-1])),
            "full_requested_length": abs(float(arc[-1])-expected) <= 1e-9,
            "adjacent_face_backtracks": int(backward.sum()),
            "short_edge_cycles": int(short_cycle.sum()),
            "part_mismatches": int(np.count_nonzero(mesh["parts"][f] != z["parts"][i])),
            "min_bary": float(bary.min()),
            "max_bary_sum_error": float(abs(bary.sum(axis=1)-1).max()),
            "max_crossing_gap_world": float(gap.max()) if len(gap) else 0.,
            "self_proxy_max_world": float(abs(np.sum((xyz-mesh["tri"][f, 0]) *
                                                    mesh["normals"][f], axis=1)).max())})
        anchors[str(z["ids"][i])] = (f, bary)
    def summary(items):
        return {"stroke_count": len(items), "total_samples": sum(s["samples"] for s in items),
                "max_samples": max(s["samples"] for s in items),
                "total_length_world": sum(s["length_world"] for s in items),
                "length_world": run_p0.stats([s["length_world"] for s in items]),
                "shortened_strokes": sum(not s["full_requested_length"] for s in items),
                "strokes_with_100plus_backtracks": sum(s["adjacent_face_backtracks"] >= 100 for s in items),
                "short_edge_cycles": sum(s["short_edge_cycles"] for s in items),
                "max_crossing_gap_world": max(s["max_crossing_gap_world"] for s in items),
                "self_proxy_max_world": max(s["self_proxy_max_world"] for s in items)}
    return {"summary": summary(records),
            "parts": {str(k): summary([s for s in records if s["part"] == k]) for k in (1, 2, 3)},
            "all_strokes": records}, anchors


def main():
    assert not (R/"REPAIR_AUDIT.json").exists(), "Preserve completed audit"
    z = np.load(R/"assets/lamp_mesh.npz")
    mesh = core.finalize_mesh(z["vertices"], z["faces"], z["parts"])
    results = {}
    old_anchors = {}
    for name in ("mixed", "parallel", "cross", "mixed_shade_edit35"):
        old, old_anchors[name] = path_records(P, name, mesh)
        new, _ = path_records(R, name, mesh)
        assert [x["id"] for x in old["all_strokes"]] == [x["id"] for x in new["all_strokes"]]
        results[name] = {"old": old, "new": new, "seed_layer_ids_identical": True}
    terminations = {}
    seed_mismatches = []
    for path in sorted((R/"walk_traces").glob("*.json")):
        records = json.loads(path.read_text())
        counts = Counter(h["reason"] for s in records for h in s["halves"])
        half_arcs = [h["arc_world"] for s in records for h in s["halves"]]
        terminations[path.stem] = {"counts": dict(counts), "half_paths": len(half_arcs),
                                  "arc_world": run_p0.stats(half_arcs),
                                  "max_iterations": max(h["iterations"] for s in records for h in s["halves"]),
                                  "max_remaining_world": max(h["remaining_world"] for s in records for h in s["halves"])}
        style = path.stem.split("_")[0]
        if "_part1_" in path.stem:
            style = "mixed_shade_edit35"
        for s in records:
            f, b = old_anchors[style][s["id"]]
            match = (f == s["seed_face"]) & (np.max(abs(b-np.array(s["seed_bary"])), axis=1) < 1e-12)
            if not match.any():
                seed_mismatches.append({"style": style, "id": s["id"]})
    views = []
    entries = []
    for style in ("mixed", "parallel", "cross"):
        for v in CFG["splits"]["test"]:
            a = v["azimuth_deg"]; filename = f"{style}_az{a:03d}.png"
            old = np.asarray(Image.open(P/"stills"/filename), float)/255.
            new = np.asarray(Image.open(R/"stills"/filename), float)/255.
            parts = np.load(R/"references"/f"analytic_az{a:03d}.npz")["parts"]
            foreground = parts > 0
            views.append({"style": style, "azimuth_deg": a,
                          "old_total_ink": float((1-old).sum()), "new_total_ink": float((1-new).sum()),
                          "old_foreground_mean_ink": float((1-old[foreground]).mean()),
                          "new_foreground_mean_ink": float((1-new[foreground]).mean()),
                          "old_ink_support_pixels": int(np.count_nonzero((1-old) > .04)),
                          "new_ink_support_pixels": int(np.count_nonzero((1-new) > .04)),
                          "absolute_image_delta": float(abs(new-old).sum())})
            entries.extend([(f"Old | {style} | azimuth {a}", P/"stills"/filename),
                            (f"Repaired | {style} | azimuth {a}", R/"stills"/filename)])
    run_p0.contact_sheet(entries, R/"figures/old_new_all_views.png", columns=4)
    oldm = json.loads((P/"metrics.json").read_text())
    newm = json.loads((R/"metrics.json").read_text())
    depth_identical = all(a["analytic_depth_abs_error_world"] == b["analytic_depth_abs_error_world"]
                          for a, b in zip(oldm["per_view"], newm["per_view"]))
    reference_identical = True
    for view in CFG["splits"]["test"]:
        name = f"analytic_az{view['azimuth_deg']:03d}.npz"
        a, b = np.load(P/"references"/name), np.load(R/"references"/name)
        reference_identical &= all(np.array_equal(a[k], b[k]) for k in ("depth", "parts"))
    new_records = [s for x in results.values() for s in x["new"]["all_strokes"]]
    no_caps = all(t["counts"].get("iteration_cap", 0) == 0 for t in terminations.values())
    no_stalls = all(not any(t["counts"].get(k, 0) for k in ("no_progress", "no_progress_cycle"))
                    for t in terminations.values())
    gates = {
        "original_nine_gates": all(newm["gates"].values()),
        "no_short_edge_cycles": all(s["short_edge_cycles"] == 0 for s in new_records),
        "no_iteration_cap": no_caps, "no_stalled_half_paths": no_stalls,
        "seed_layer_ids_identical": all(x["seed_layer_ids_identical"] for x in results.values()),
        "seed_anchors_identical": not seed_mismatches,
        "part_ownership": all(s["part_mismatches"] == 0 for s in new_records),
        "barycentric_valid": all(s["min_bary"] >= -1e-10 and s["max_bary_sum_error"] <= 1e-9 for s in new_records),
        "self_proxy_attachment": all(s["self_proxy_max_world"] <= 1e-9 for s in new_records),
        "crossings_are_exact_edge_points": all(s["max_crossing_gap_world"] <= 1e-9 for s in new_records),
        "depth_and_reference_unchanged": depth_identical and reference_identical,
        "edit_non_target_paths_identical": newm["non_target_strokes_identical"]}
    result = {"scope": "Engineering repair replay; descriptive old/new image and arc audit, not quality superiority",
              "styles": results, "terminations": terminations, "seed_mismatches": seed_mismatches,
              "image_ink_coverage": views, "gates": gates, "engineering_repair_go": all(gates.values()),
              "depth_audit_retained_from_round_001": json.loads((P/"DEPTH_AUDIT.json").read_text()),
              "independent_temporal_stability": "UNMEASURED",
              "sampling_note": "Zero-length edge ownership duplicates are valid. No-progress A-B-A cycles use actual cumulative arc <1e-6 world. Sample-based attachment means are not uniform-length estimates."}
    run_p0.write_json(R/"REPAIR_AUDIT.json", result)
    print(json.dumps({"gates": gates, "terminations": terminations,
                      "styles": {k: {"old": x["old"]["summary"], "new": x["new"]["summary"]}
                                 for k, x in results.items()}}, indent=2))


if __name__ == "__main__":
    main()
