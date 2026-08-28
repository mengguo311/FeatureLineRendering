#!/usr/bin/env bash
# CMEPI — full M1b (pull + chain + prune) for the NON-TEED frozen learned detectors.
#
# Every arm runs the IDENTICAL run_m1b.py code path with the IDENTICAL flags that produced
# the published TEED and Canny arms (out/m1b_{chair,lego}_gated_test.json: --gate, edge=sharp,
# pull_split=train, eval_split=test, steps=100, lr=0.35, delta_max=5, len_thr=0.9).
# The ONLY difference between arms is --score, i.e. which per-gaussian ranking vector is used
# -- and those scores differ ONLY in which frozen 2D detector fed the M1a photometric DT.
#
# Arms are tagged under the EXISTING _tc_ prefix on purpose: teedgen_verdict.py globs
# m1b_<scene>_tc_*.json and reads every LIFT_P against the Canny f-frontier already swept and
# densified out to f=1.00 under that prefix (chair 14 pts, lego 16 pts).  A private prefix
# would have no Canny frontier and the verdict would refuse to run.
#
# THRESHOLD PROTOCOL (frozen before any TEST number was read).  key=native is fixed for every
# detector, matching the TEED headline arm, so threshold is the only tuned degree of freedom.
# It was selected on CHAIR VAL ONLY (out/trackC_seeds_chair_cmepi.json) and then transferred
# to lego UNCHANGED -- exactly what TEED did (chair VAL picked 0.5, lego reused 0.5 zero-shot).
#   chair VAL selection: pidinet 0.9, dexined 0.7
# Also run at the nominal 0.5 for direct parity with the published TEED headline arm, and on
# lego additionally at pidinet 0.7 so lego's OWN VAL pick is covered as a sensitivity arm.
#
# f is swept on the SAME 7-point grid as the published TEED control (0.15..0.50) so the GO
# band f in [0.30,0.50] has 5 points and the NO-GO leg (hardcoded f<=0.30 in the verdict) is
# populated by 0.15/0.22/0.30 rather than being vacuously unfirable.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export MESH_ORACLE_MAX_ELEMS=2000000
cd ~/3dgs_line/tier1
SYN=scripts/explore/syn

m1b () {   # m1b <scene> <score_name> <f>
  local sn="$1" sc="$2" f="$3"
  local sp="$SYN/finalscore_overall_${sn}__${sc}.npy"
  local out="out/m1b_${sn}_tc_${sc}_f${f}.json"
  [ -f "$sp" ] || { echo "MISSING $sp — skipped"; return; }
  [ -f "$out" ] && { echo "HAVE ${out##*/} — skipped"; return; }
  echo "=================== ${sn} ARM ${sc} f=${f} ==================="
  python -u scripts/run_m1b.py --scene "$sn" --gate --eval_split test --no_viz \
    --score "$sp" --f "$f" --tag "_tc_${sc}_f${f}"
}

FS="0.50 0.45 0.40 0.35 0.30 0.22 0.15"

echo "############################ CHAIR ############################"
for sc in dexined_native_0.7 pidinet_native_0.9 dexined_native_0.5 pidinet_native_0.5; do
  for f in $FS; do m1b chair "$sc" "$f"; done
done

echo "############################ LEGO ############################"
for sc in dexined_native_0.5 pidinet_native_0.7 dexined_native_0.7 pidinet_native_0.9 pidinet_native_0.5; do
  for f in $FS; do m1b lego "$sc" "$f"; done
done

echo "ALL CMEPI M1b ARMS DONE"
