"""Replay frozen round_001 controls with only the versioned walk repair."""
import run_p0 as runner  # Sets CUDA visibility/threads/affinity before NumPy.
import argparse
import datetime
import json
import shutil
import subprocess
import time
from pathlib import Path
import numpy as np
import core_walk_v2 as repaired

W = runner.WORK
R = Path("/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_002")
P = R.parent/"round_001"
D = W/"docs/partwise_sketch_hatching/round_002"
runner.ROUND = R
runner.DOC = D
# Intentionally retain the exact original protocol path and parsed configuration.
runner.core = repaired
ORIGINAL_GENERATE = repaired.generate_strokes
START = time.monotonic()


def write_json(path, obj):
    def scalar(value):
        if isinstance(value, np.generic):
            return value.item()
        raise TypeError(type(value).__name__)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False,
                              default=scalar)+"\n")
    tmp.replace(path)


def status(stage, state="in_progress", verdict="UNMEASURED", extra=None):
    value = json.loads((R/"STATUS.json").read_text())
    value.update({"stage": stage, "execution_state": state, "scientific_verdict": verdict,
                  "updated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    if extra:
        value.update(extra)
    write_json(R/"STATUS.json", value)


def resource_check():
    r = runner.CFG["resources"]
    root = shutil.disk_usage("/").free
    hdd = shutil.disk_usage("/mnt/hdd1").free
    task_bytes = sum(p.stat().st_size for p in R.parent.parent.rglob("*") if p.is_file())
    runtime_bytes = sum(p.stat().st_size for p in (W/".runtime_p0").rglob("*") if p.is_file())
    if (root < r["root_free_min_bytes"] or hdd < r["hdd_free_min_bytes"] or
            task_bytes+runtime_bytes > r["output_cap_bytes"]):
        raise RuntimeError("Resource floor/output cap violated")
    if time.monotonic()-START > 570:
        raise RuntimeError("Invocation nearing ten-minute bound")
    deadline = datetime.datetime.fromisoformat("2026-10-21T04:42:34.798663+09:00")
    if datetime.datetime.now(datetime.timezone.utc) >= deadline:
        raise RuntimeError("Round wall deadline reached")
    return {"root_free_bytes": root, "hdd_free_bytes": hdd,
            "task_bytes": task_bytes, "isolated_dependency_bytes": runtime_bytes,
            "affinity": sorted(runner.os.sched_getaffinity(0)), "GPU": False}


def verify_lock():
    lock = json.loads((D/"ASSET_LOCK.json").read_text())
    for p, expected in lock["files"].items():
        assert runner.digest(W/p) == expected, "Unfrozen source/config: "+p
    assert runner.digest(lock["asset"]["path"]) == lock["asset"]["sha256"]
    assert runner.digest(P/"assets/lamp_mesh.npz") == lock["asset"]["sha256"]
    assert runner.digest(P/"SEAL.json") == lock["prior_seal_sha256"]
    path = "docs/partwise_sketch_hatching/round_002/ASSET_LOCK.json"
    subprocess.run(["git", "ls-files", "--error-unmatch", path],
                   cwd=W, capture_output=True, check=True)
    assert not subprocess.check_output(["git", "diff", "HEAD", "--", path], cwd=W)
    return lock


def prepare():
    resource_check()
    assert not (D/"ASSET_LOCK.json").exists(), "Do not replace a frozen lock"
    assert subprocess.check_output(["git", "branch", "--show-current"], cwd=W,
                                   text=True).strip() == "partwise-sketch-hatching-p0p1-v01"
    (R/"assets").mkdir(exist_ok=True)
    asset = R/"assets/lamp_mesh.npz"
    shutil.copyfile(P/"assets/lamp_mesh.npz", asset)
    old_lock = json.loads((W/"docs/partwise_sketch_hatching/round_001/ASSET_LOCK.json").read_text())
    assert runner.digest(asset) == old_lock["asset"]["sha256"]
    names = ["core.py", "run_p0.py", "test_p0.py", "core_walk_v2.py",
             "test_walk_progress.py", "run_round002.py", "test_original_with_v2.py",
             "audit_round002.py", "seal_round002.py"]
    paths = [W/"experiments/partwise_sketch_hatching"/name for name in names]
    paths += [runner.PROTO, D/"AMENDMENT.json",
              W/"docs/partwise_sketch_hatching/experiment_outline_v1.md"]
    lock = {"protocol_commit": "da8c8387", "amendment_commit": "f8827fd5",
            "implementation_commit": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                                             cwd=W, text=True).strip(),
            "prior_seal_sha256": runner.digest(P/"SEAL.json"),
            "asset": {**old_lock["asset"], "path": str(asset)},
            "files": {str(p.relative_to(W)): runner.digest(p) for p in paths},
            "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    write_json(D/"ASSET_LOCK.json", lock)
    status("assets_prepared_awaiting_lock_commit")
    print(json.dumps(lock, indent=2))


def generate_with_audit(mesh, cfg, style="mixed", only_part=None, angle=0., counts=None):
    strokes = ORIGINAL_GENERATE(mesh, cfg, style, only_part, angle, counts)
    records = [{"id": s["id"], "part": s["part"], "seed_face": s["seed_face"],
                "seed_bary": s["seed_bary"].tolist(), "halves": s["walk_audit"]}
               for s in strokes]
    name = f"{style}_part{only_part}_angle{angle:g}"
    write_json(R/"walk_traces"/(name+".json"), records)
    return strokes


runner.write_json = write_json
runner.status = status
runner.resource_check = resource_check
runner.verify_lock = verify_lock
repaired.generate_strokes = generate_with_audit

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run"))
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            prepare()
        else:
            runner.evaluate()
    except Exception as exc:
        status("interrupted_or_failed", "engineering_invalid", "INCOMPLETE",
               {"error": f"{type(exc).__name__}: {exc}"})
        raise
