#!/usr/bin/env bash
# STEP 2 matrix. Every arm uses the IDENTICAL pull/prune/eval code path (run_hybrid.py),
# so the only difference between an ungated f-arm and a gated arm is the seed set.
set -u
cd ~/3dgs_line/tier1
R="python -u scripts/run_hybrid.py --scene chair"

echo "=========== ARM A: ungated f-sweep (control frontier) ==========="
for f in 0.30 0.26 0.22 0.18 0.15 0.12; do
  $R --no_seed_gate --f $f --dt vanilla_gated --tag _ctl_f$f || echo "FAILED f=$f"
done

echo "=========== ARM B: 2dgs_chair / gradn q90 / r0 / vote sweep ==========="
for v in 0.25 0.5 0.75 1.0; do
  $R --model out/2dgs_chair --signal gradn --tau_q 90 --r 0 --vote $v \
     --dt vanilla_gated --tag _b_gradn90_r0_v$v || echo "FAILED vote=$v"
done

echo "=========== ARM B2: 2dgs_chair / gradn q95 / r0-r1 ==========="
$R --model out/2dgs_chair --signal gradn --tau_q 95 --r 1 --vote 0.5 --dt vanilla_gated --tag _b_gradn95_r1_v0.5
$R --model out/2dgs_chair --signal gradn --tau_q 80 --r 0 --vote 0.75 --dt vanilla_gated --tag _b_gradn80_r0_v0.75

echo "=========== ARM C: 2dgs_chair / dihedral tau=8 / r0 (STEP-A validated signal) ==========="
for v in 0.5 0.75; do
  $R --model out/2dgs_chair --signal dihedral --tau 8 --r 0 --vote $v \
     --dt vanilla_gated --tag _c_dih8_r0_v$v || echo "FAILED dih vote=$v"
done

echo "=========== ARM D: 2dgs_chair_dist (the model named in the spec) ==========="
$R --model out/2dgs_chair_dist --signal gradn --tau_q 95 --r 1 --vote 0.5 --dt vanilla_gated --tag _d_dist_gradn95_r1_v0.5
$R --model out/2dgs_chair_dist --signal gradn --tau_q 90 --r 0 --vote 0.5 --dt vanilla_gated --tag _d_dist_gradn90_r0_v0.5
echo "ALL DONE"
