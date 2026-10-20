"""Recover only final JSON serialization from complete, preserved partial records."""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "2"
os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import numpy as np

W = Path(__file__).resolve().parents[2]
D = W / "docs/partwise_sketch_hatching/round_001"
R = Path("/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_001")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    assert not (R / "metrics.json").exists(), "Never overwrite a final result"
    cfg = json.loads((D / "PROTOCOL.json").read_text())
    lock = json.loads((D / "ASSET_LOCK.json").read_text())
    for path, expected in lock["files"].items():
        assert sha(W / path) == expected, path
    assert sha(lock["asset"]["path"]) == lock["asset"]["sha256"]
    m = json.loads((R / "metrics_partial.json").read_text())
    trajectories = json.loads((R / "camera_trajectories.json").read_text())
    assert len(m["per_view"]) == 4
    assert len(m["frame_seconds_raw"]) == 100
    assert json.loads((R / "TESTS_GREEN.json").read_text())["returncode"] == 0
    for name in ("orbit", "zoom", "edit"):
        expected = cfg["videos"][name]["frames"]
        assert m["videos"][name]["decoded_frames"] == expected
        assert m["videos"][name]["decode_returncode"] == 0
        assert len(trajectories[name]) == expected
        assert len(list((R / "frames" / name).glob("*.png"))) == expected
    views = m["per_view"]
    gates = {
        "determinism": bool(m["deterministic_regeneration"]),
        "part_isolation": bool(m["non_target_strokes_identical"]),
        "attachment_self_proxy": bool(m["attachment_self_proxy_world"]["max"] <= cfg["go_no_go"]["barycentric_max_residual"]),
        "nonzero_target_edit": all(v["edit"]["inside_delta"] > 10 for v in views),
        "far_non_target_leakage": all(v["edit"]["far_other_parts_fraction"] <= .02 for v in views),
        "analytic_depth": all(v["analytic_depth_abs_error_world"]["p95"] <= .01 for v in views),
        "injected_leakage_response": all(v["injected_leak"]["outside_fraction"] > v["edit"]["outside_fraction"] for v in views),
        "injected_drift_response": all(v["injected_6px_drift_support"]["mean_px"] > v["render_support"]["mean_px"] for v in views),
        "video_decode": all(v["decoded_frames"] == cfg["videos"][k]["frames"] and v["distinct_decoded_frames"] >= 2 for k, v in m["videos"].items()),
    }
    times = np.asarray(m["frame_seconds_raw"])
    resources = {
        "root_free_bytes": shutil.disk_usage("/").free,
        "hdd_free_bytes": shutil.disk_usage("/mnt/hdd1").free,
        "round_bytes": sum(p.stat().st_size for p in R.rglob("*") if p.is_file()),
        "affinity": sorted(os.sched_getaffinity(0)),
    }
    assert resources["root_free_bytes"] >= cfg["resources"]["root_free_min_bytes"]
    assert resources["hdd_free_bytes"] >= cfg["resources"]["hdd_free_min_bytes"]
    assert resources["round_bytes"] < cfg["resources"]["output_cap_bytes"]
    m.update({
        "evaluation_complete": True, "gates": gates, "engineering_go": all(gates.values()),
        "frame_seconds_summary": {"count": len(times), "mean": float(times.mean()), "median": float(np.median(times)), "p95": float(np.percentile(times, 95)), "max": float(times.max())},
        "resources_after": resources,
        "original_invocation_wall_seconds": None,
        "recovery": {
            "reason": "Final summary JSON serialization failure after complete rendering and video decoding",
            "partial_input_sha256": sha(R / "metrics_partial.json"),
            "source_sha256": sha(__file__),
            "amendment_sha256": sha(D / "RECOVERY_AMENDMENT.json"),
            "completed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "rendered_again": False, "thresholds_changed": False,
            "original_failure_retained": "FAILURE_INITIAL.json",
        },
        "overall_verdict": "P0_PARTIAL_ENGINEERING_SUCCESS; NO_GO_FOR_P1_PROMOTION_PENDING_FACE_WALK_REPAIR",
    })
    # All predicates are native Python bool after JSON rehydration.
    (R / "metrics.json").write_text(json.dumps(m, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"gates": gates, "timing": m["frame_seconds_summary"], "overall_verdict": m["overall_verdict"]}, indent=2))


if __name__ == "__main__":
    main()
