"""Data-only validation after the final stdout print failed; never re-render."""
import run_round002 as replay
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
from PIL import Image

R, D, W = replay.R, replay.D, replay.W


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    assert not (R/"VALIDATION.json").exists(), "Do not overwrite validation evidence"
    replay.verify_lock()
    lock = json.loads((D/"VALIDATION_LOCK.json").read_text())
    for path, digest in lock["files"].items():
        assert sha(W/path) == digest, path
    for path, digest in lock["evidence"].items():
        assert sha(R/path) == digest, path
    relative = "docs/partwise_sketch_hatching/round_002/VALIDATION_LOCK.json"
    subprocess.run(["git", "ls-files", "--error-unmatch", relative], cwd=W,
                   capture_output=True, check=True)
    assert not subprocess.check_output(["git", "diff", "HEAD", "--", relative], cwd=W)
    receipt = json.loads((R/"EXECUTION.json").read_text())
    failure = json.loads((R/"FAILURE_PRINT.json").read_text())
    assert receipt["returncode"] == 1 and failure["actual_returncode"] == 1
    text = (R/"runtime/replay.log").read_text()
    assert 'run_p0.py", line 223, in evaluate' in text
    assert "Object of type bool is not JSON serializable" in text
    assert sha(R/"metrics.json") == failure["metrics_sha256"]
    m = json.loads((R/"metrics.json").read_text())
    cfg = replay.runner.CFG
    assert m["evaluation_complete"] and len(m["frame_seconds_raw"]) == 100
    assert len(m["per_view"]) == 4
    assert m["stroke_counts"] == {"mixed": 608, "parallel": 458, "cross": 916}
    views = m["per_view"]
    gates = {
        "determinism": m["deterministic_regeneration"],
        "part_isolation": m["non_target_strokes_identical"],
        "attachment_self_proxy": m["attachment_self_proxy_world"]["max"] <= cfg["go_no_go"]["barycentric_max_residual"],
        "nonzero_target_edit": all(v["edit"]["inside_delta"] > 10 for v in views),
        "far_non_target_leakage": all(v["edit"]["far_other_parts_fraction"] <= .02 for v in views),
        "analytic_depth": all(v["analytic_depth_abs_error_world"]["p95"] <= .01 for v in views),
        "injected_leakage_response": all(v["injected_leak"]["outside_fraction"] > v["edit"]["outside_fraction"] for v in views),
        "injected_drift_response": all(v["injected_6px_drift_support"]["mean_px"] > v["render_support"]["mean_px"] for v in views),
        "video_decode": all(v["decoded_frames"] == cfg["videos"][k]["frames"] and
                            v["distinct_decoded_frames"] >= 2 for k, v in m["videos"].items())}
    assert m["gates"] == gates
    assert m["engineering_go"] == all(gates.values())
    trajectories = json.loads((R/"camera_trajectories.json").read_text())
    # Re-decode all compressed video bytes; compare every frame hash with the
    # original completed decode rather than merely trusting its frame count.
    sys.path.insert(0, str(W/".runtime_p0"))
    import imageio_ffmpeg
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    decoded = {}
    for kind, n in (("orbit", 36), ("zoom", 24), ("edit", 24)):
        assert len(trajectories[kind]) == n
        frames = sorted((R/"frames"/kind).glob("*.png"))
        assert len(frames) == n
        for path in frames:
            with Image.open(path) as im:
                assert im.size == (512, 512)
                im.verify()
        assert m["videos"][kind]["encode_returncode"] == 0
        assert m["videos"][kind]["decode_returncode"] == 0
        assert sha(exe) == m["videos"][kind]["ffmpeg_sha256"]
        cmd = [exe, "-hide_banner", "-loglevel", "error", "-threads", "2",
               "-i", str(R/"videos"/(kind+".mp4")), "-f", "rawvideo",
               "-pix_fmt", "rgb24", "-threads", "2", "pipe:1"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        hashes = []
        while True:
            frame = p.stdout.read(512*512*3)
            if not frame:
                break
            assert len(frame) == 512*512*3
            hashes.append(hashlib.sha256(frame).hexdigest())
        error = p.stderr.read().decode()
        assert p.wait(timeout=30) == 0, error
        assert hashes == m["videos"][kind]["decoded_frame_sha256"]
        assert len(hashes) == n
        decoded[kind] = {"frames": n, "all_frame_hashes_match": True,
                         "video_sha256": sha(R/"videos"/(kind+".mp4"))}
    assert sha(R/"metrics.json") == failure["metrics_sha256"]
    result = {"validation_complete": True, "original_process_returncode": 1,
              "metrics_sha256_unchanged": sha(R/"metrics.json"),
              "all_frozen_predicates_match": True, "gates": gates,
              "raw_frame_timings": 100, "fully_redecoded_videos": decoded,
              "rerendered": False, "rewrote_metrics": False, "thresholds_changed": False,
              "note": "Final stdout print failed; complete science artifacts validate independently.",
              "resources": replay.resource_check()}
    replay.write_json(R/"VALIDATION.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
