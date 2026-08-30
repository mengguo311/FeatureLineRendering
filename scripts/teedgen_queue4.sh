#!/usr/bin/env bash
# Remaining M1b work: TRACK M chair f-extension, then TRACK M replicated on lego.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export MESH_ORACLE_MAX_ELEMS=2000000
cd ~/3dgs_line/tier1
SYN=scripts/explore/syn
m1b () {
  local sn="$1" px="$2" sc="$3" f="$4"
  local sp="$SYN/finalscore_overall_${sn}__${sc}.npy"
  local out="out/m1b_${sn}_${px}_${sc}_f${f}.json"
  [ -f "$sp" ] || { echo "MISSING $sp"; return; }
  [ -f "$out" ] && { echo "HAVE ${out##*/}"; return; }
  echo "=================== ${sn}/${px} ARM ${sc} f=${f} ==================="
  python -u scripts/run_m1b.py --scene "$sn" --gate --eval_split test --no_viz \
    --score "$sp" --f "$f" --tag "_${px}_${sc}_f${f}"
}
echo "########## TRACK M chair: f=0.45/0.50 so R_max is read over the same f range as teed05 ##########"
for f in 0.50 0.45; do
  for sc in m3_masksharplow_d2 m1_soft_g1.0 m2_cc25 m2_cc10 m3_maskM1a_d2; do m1b chair tm "$sc" "$f"; done
done
echo "########## TRACK M on LEGO — does the mechanism decomposition transfer? ##########"
python -u scripts/recall_trackC_seeds.py --scene lego --sources teed --thrs 0.5 \
  --arms_json out/trackM_arms_lego.json --tag _trackM
for f in 0.50 0.40 0.30 0.22; do
  for sc in m3_masksharplow_d2 m3_maskM1a_d2 m1_soft_g1.0 m2_cc25; do m1b lego tm "$sc" "$f"; done
done
echo "QUEUE COMPLETE"
