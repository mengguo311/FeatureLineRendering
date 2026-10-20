"""Bind source/config/reports and completed output bytes; keep runtime logs outside."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
W = Path(__file__).resolve().parents[2]
R = Path("/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_001")
D = W / "docs/partwise_sketch_hatching/round_001"
EXCLUDED = {"SHA256_MANIFEST.json", "SEAL.json"}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main(verify):
    if verify:
        manifest = json.loads((R / "SHA256_MANIFEST.json").read_text())
        for entry in manifest["files"]:
            root = W if entry["root"] == "worktree" else R
            path = root / entry["path"]
            assert path.stat().st_size == entry["bytes"], str(path)
            assert sha(path) == entry["sha256"], str(path)
        seal = json.loads((R / "SEAL.json").read_text())
        assert sha(R / "SHA256_MANIFEST.json") == seal["manifest_sha256"]
        print(json.dumps({"verified_files": len(manifest["files"]), "manifest_sha256": seal["manifest_sha256"], "returncode": 0}))
        return
    assert not (R / "SEAL.json").exists(), "Never rewrite a completed seal"
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=W, text=True).strip()
    assert branch == "partwise-sketch-hatching-p0p1-v01"
    m = json.loads((R / "metrics.json").read_text())
    assert m["evaluation_complete"]
    assert json.loads((R / "EXECUTION_RECOVERY.json").read_text())["returncode"] == 0
    paths = [("worktree", p) for p in sorted(D.glob("*")) if p.is_file()]
    paths += [("worktree", p) for p in sorted((W / "experiments/partwise_sketch_hatching").glob("*.py"))]
    paths += [("worktree", W / ".gitignore"), ("worktree", W / "docs/partwise_sketch_hatching/experiment_outline_v1.md")]
    paths += [("round", p) for p in sorted(R.rglob("*")) if p.is_file()
              and p.name not in EXCLUDED and "runtime" not in p.relative_to(R).parts]
    entries = []
    for root, path in paths:
        base = W if root == "worktree" else R
        entries.append({"root": root, "path": str(path.relative_to(base)), "bytes": path.stat().st_size, "sha256": sha(path)})
    manifest = {
        "schema": 1, "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=W, text=True).strip(),
        "roots": {"worktree": str(W), "round": str(R)},
        "exclusions": ["runtime/ stdout and stderr", "SHA256_MANIFEST.json (self)", "SEAL.json (manifest receipt)"],
        "files": entries,
    }
    (R / "SHA256_MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    seal = {"manifest_sha256": sha(R / "SHA256_MANIFEST.json"), "file_count": len(entries),
            "total_bytes": sum(e["bytes"] for e in entries), "source_commit": manifest["source_commit"],
            "scientific_verdict": m["overall_verdict"], "runtime_logs_outside_seal": True}
    (R / "SEAL.json").write_text(json.dumps(seal, indent=2) + "\n")
    print(json.dumps(seal, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    main(parser.parse_args().verify)
