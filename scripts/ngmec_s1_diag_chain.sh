#!/usr/bin/env bash
# DIAGNOSTIC (not the frozen gate): the epipolar gate applied to the PERMISSIVE un-blurred
# Canny instead of to TEED.  TRACK M measured that a selectivity mask on an ALREADY-selective
# detector buys ~nothing (+0.004) while the same mask on a permissive one buys +0.2408.  TEED
# is already selective, so gating TEED is structurally the first case.  This measures the
# second, which is the only way to tell "epipolar consensus is a weak selectivity device"
# apart from "epipolar consensus was applied where selectivity was already present".
set -u
cd ~/3dgs_line/tier1
until grep -q "NGMEC M1B DONE lego" logs/ngmec_s1_lego.log 2>/dev/null; do sleep 30; done
source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True MESH_ORACLE_MAX_ELEMS=2000000
python -u scripts/ngmec_s1_build_prop.py --scene chair --prop cannysharplow
python - <<'PY'
import json, os
arms={}
for tg in ["t1.5_r0_m2","t1.5_r0_m3","t1.5_r0_m4","t2.5_r0_m3"]:
    arms[f"epiSL_{tg}"]={"source":"teed_epi","key":"native","thr":0.5,"nms":False,
                         "cache":os.path.abspath(f"out/epi_edges_chair_cannysharplow_{tg}")}
json.dump(arms, open("out/ngmec_arms_chair_sharplow.json","w"), indent=1)
PY
python -u scripts/recall_trackC_seeds.py --scene chair --sources teed --thrs 0.5 \
  --arms_json out/ngmec_arms_chair_sharplow.json --tag _ngmecSL
for f in 0.40 0.30 0.22; do
  cp -f out/m1b_chair_tc_cannysharplow_f${f}.json out/m1b_chair_ngsl_slbase_f${f}.json 2>/dev/null || true
done
for sc in epiSL_t1.5_r0_m2 epiSL_t1.5_r0_m3 epiSL_t1.5_r0_m4 epiSL_t2.5_r0_m3; do
  for f in 0.40 0.30 0.22; do
    sp="scripts/explore/syn/finalscore_overall_chair__${sc}.npy"
    out="out/m1b_chair_ngsl_${sc}_f${f}.json"
    [ -f "$sp" ] || { echo "MISSING $sp"; continue; }
    [ -f "$out" ] && continue
    echo "=================== chair DIAG ARM ${sc} f=${f} ==================="
    python -u scripts/run_m1b.py --scene chair --gate --eval_split test --no_viz \
      --score "$sp" --f "$f" --tag "_ngsl_${sc}_f${f}"
  done
done
echo "NGMEC DIAG DONE"
