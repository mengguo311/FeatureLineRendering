"""Seal round_002 without modifying any prior source or science artifact."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
W = Path(__file__).resolve().parents[2]
R = Path("/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_002")
D = W/"docs/partwise_sketch_hatching/round_002"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(verify):
    if verify:
        m = json.loads((R/"SHA256_MANIFEST.json").read_text())
        for e in m["files"]:
            p = (W if e["root"] == "worktree" else R)/e["path"]
            assert p.stat().st_size == e["bytes"] and sha(p) == e["sha256"], str(p)
        seal = json.loads((R/"SEAL.json").read_text())
        assert sha(R/"SHA256_MANIFEST.json") == seal["manifest_sha256"]
        print(json.dumps({"verified_files": len(m["files"]), "returncode": 0}))
        return
    assert not (R/"SEAL.json").exists(), "Never overwrite a seal"
    assert subprocess.check_output(["git", "branch", "--show-current"], cwd=W, text=True).strip() == "partwise-sketch-hatching-p0p1-v01"
    assert json.loads((R/"metrics.json").read_text())["evaluation_complete"]
    assert json.loads((R/"EXECUTION.json").read_text())["returncode"] == 0
    assert json.loads((R/"STATUS.json").read_text())["execution_state"] == "complete"
    lock = json.loads((D/"ASSET_LOCK.json").read_text())
    for path, expected in lock["files"].items():
        assert sha(W/path) == expected, path
    paths = [("worktree", W/p) for p in lock["files"]]
    paths += [("worktree", p) for p in D.glob("*") if p.is_file()]
    paths += [("round", p) for p in R.rglob("*") if p.is_file()
              and p.name not in {"SEAL.json", "SHA256_MANIFEST.json"}
              and "runtime" not in p.relative_to(R).parts]
    files = []
    for root, p in sorted(set(paths)):
        base = W if root == "worktree" else R
        files.append({"root": root, "path": str(p.relative_to(base)),
                      "bytes": p.stat().st_size, "sha256": sha(p)})
    m = {"created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
         "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=W, text=True).strip(),
         "roots": {"round": str(R), "worktree": str(W)},
         "exclusions": ["runtime stdout/stderr", "SHA256_MANIFEST.json", "SEAL.json"],
         "files": files}
    (R/"SHA256_MANIFEST.json").write_text(json.dumps(m, indent=2)+"\n")
    seal = {"manifest_sha256": sha(R/"SHA256_MANIFEST.json"), "file_count": len(files),
            "total_bytes": sum(e["bytes"] for e in files), "source_commit": m["source_commit"],
            "scientific_verdict": json.loads((R/"STATUS.json").read_text())["scientific_verdict"]}
    (R/"SEAL.json").write_text(json.dumps(seal, indent=2)+"\n")
    print(json.dumps(seal, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--verify", action="store_true")
    main(p.parse_args().verify)
