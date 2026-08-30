#!/usr/bin/env bash
# TRACK C.3 — full M1b (pull + chain + prune) on TEED-sourced seeds vs the Canny baseline.
#
# Every arm runs the IDENTICAL run_m1b.py code path with the IDENTICAL flags that produced
# the published baseline (out/m1b_chair_gated_test.json: --gate, edge=sharp, pull_split=train,
# eval_split=test, steps=100, lr=0.35, delta_max=5, len_thr=0.9).  The ONLY difference
# between arms is --score, i.e. which M1a OVERALL score ranks the gaussians -- and those
# scores differ only in the photometric edge detector that fed the DT.
#
# The canny arm is a REPRODUCTION control: its score was recomputed in this experiment and
# must return seg P@1.5 = 0.6573 / R@1.5 = 0.5959 (n_seeds 17065).  If it does not, the
# score-override plumbing is broken and no TEED number means anything.
#
# f is swept so the TEED arms are read against the Canny f-FRONTIER, not against a single
# Canny point -- the bar HYBRID_RESULTS.md established (a seed change that merely trades
# precision for recall is dominated by simply lowering f, and must be shown not to be).
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
cd ~/3dgs_line/tier1
SYN=scripts/explore/syn
COMMON="--scene chair --gate --eval_split test --no_viz"

run () {   # run <score_name> <f> <tag>
  local sc="$1" f="$2" tag="$3"
  local sp="$SYN/finalscore_overall_chair__${sc}.npy"
  if [ ! -f "$sp" ]; then echo "MISSING $sp — skipped"; return; fi
  echo "=================== ARM ${sc} f=${f} ==================="
  python -u scripts/run_m1b.py $COMMON --score "$sp" --f "$f" --tag "$tag"
}

for f in 0.35 0.30 0.22 0.15; do
  run canny "$f" "_tc_canny_f${f}"
done
for f in 0.35 0.30 0.22 0.15; do
  run teed_native_0.5 "$f" "_tc_teed05_f${f}"
done
for f in 0.30 0.22; do
  run teed_native_0.9 "$f" "_tc_teed09_f${f}"
  run union_native_0.5 "$f" "_tc_union05_f${f}"
done
echo "ALL M1b ARMS DONE"
