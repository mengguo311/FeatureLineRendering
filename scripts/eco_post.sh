#!/usr/bin/env bash
# ECO — the remaining spec-mandated controls: transferable veto ablation, paired per-view
# significance, temporal no-regress.  --out / --tag / --viz_tag are passed everywhere so no
# manifest-protected file is touched (out/teedgen_perview_*.json, out/m1b_stroke_temporal_table.*
# and the eight out/m1b_vector_* figures are all IN the 332-file protected manifest).
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export MESH_ORACLE_MAX_ELEMS=2000000
cd ~/3dgs_line/tier1
SYN=scripts/explore/syn

m1b () {
  local sn="$1" sc="$2" f="$3"
  local sp="$SYN/finalscore_overall_${sn}__${sc}.npy"
  local out="out/m1b_${sn}_ec_${sc}_f${f}.json"
  [ -f "$sp" ] || { echo "MISSING $sp"; return; }
  [ -f "$out" ] && { echo "HAVE ${out##*/}"; return; }
  echo "=== ${sn} ARM ${sc} f=${f} ==="
  python -u scripts/run_m1b.py --scene "$sn" --gate --eval_split test --no_viz \
    --score "$sp" --f "$f" --tag "_ec_${sc}_f${f}"
}
echo "########## quantile-anchored veto (transferable ablation) ##########"
for sn in chair lego; do
  for f in 0.50 0.45 0.40 0.35 0.30 0.22 0.15; do m1b "$sn" eco_dex_vetoq0p2_K3 "$f"; done
done

echo "########## paired PER-VIEW significance at matched f=0.40 ##########"
python -u scripts/teedgen_perview.py --scene chair --out out/eco_perview_chair.json --pairs \
  ec_eco_dex_add_l0p25_K3_f0.40:tc_dexined_native_0.7_f0.40 \
  ec_eco_dex_add_l0p25_K1_f0.40:tc_dexined_native_0.7_f0.40 \
  ec_eco_dex_add_l0p25_K5_f0.40:tc_dexined_native_0.7_f0.40 \
  ec_eco_dex_veto_c0p9_K3_f0.40:tc_dexined_native_0.7_f0.40 \
  ec_eco_teed_add_l0p25_K3_f0.40:tc_teed05_f0.40
python -u scripts/teedgen_perview.py --scene lego --out out/eco_perview_lego.json --pairs \
  ec_eco_dex_add_l0p25_K3_f0.40:tc_dexined_native_0.7_f0.40 \
  ec_eco_dex_add_l0p25_K1_f0.40:tc_dexined_native_0.7_f0.40 \
  ec_eco_dex_add_l0p25_K5_f0.40:tc_dexined_native_0.7_f0.40 \
  ec_eco_dex_veto_c0p9_K3_f0.40:tc_dexined_native_0.7_f0.40 \
  ec_eco_teed_add_l0p25_K3_f0.40:tc_teed_native_0.5_f0.40

echo "########## temporal no-regress (chair f=0.30, lego f=0.40; bar is P_pop ratio >= 8x) ##########"
tmp () {  # tmp <scene> <f> <variant>
  local sn="$1" f="$2" vr="$3"
  local src="out/linelets_${sn}_ec_eco_dex_add_l0p25_K3_f${f}.npz"
  [ -f "$src" ] || { echo "MISSING $src"; return; }
  [ -f "out/m1b_stroke_temporal_table_${vr}.json" ] && { echo "HAVE ${vr}"; return; }
  cp -f "$src" "out/linelets_${sn}_${vr}_test.npz"
  python -u scripts/m1b_stroke_temporal.py --scenes "$sn" --variant "$vr" \
    --frames 30 60 120 240 --view_a 5 --view_b 15 --tag "_${vr}" --viz_tag "_${vr}"
}
tmp chair 0.30 eco_chair
tmp lego  0.40 eco_lego
echo "ECO POST DONE"
