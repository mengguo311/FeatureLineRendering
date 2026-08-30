#!/usr/bin/env bash
# Post steps: lego cull-probe (does the SAME config cull true creases on lego?) and the
# paired per-view tests the spec asks for.
set -u
cd ~/3dgs_line/tier1
until grep -q "NGMEC DIAG DONE" logs/ngmec_s1_diag.log 2>/dev/null; do sleep 30; done
source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True MESH_ORACLE_MAX_ELEMS=1500000
python -u scripts/ngmec_s1_cullprobe.py --scene lego \
  --arms t1.5_r0_m2 t1.5_r0_m3 t1.5_r0_m4 t2.5_r0_m3 t1.5_r0.2_m4 t1.5_r7_m4
echo "########## paired per-view tests ##########"
python -u scripts/teedgen_perview.py --scene chair --pairs \
  ng_epi_t1.5_r0_m3_f0.45:tc_teed05_f0.45 \
  ng_epi_t1.5_r0_m3_f0.40:tc_teed05_f0.40 \
  ng_epi_t1.5_r0_m3_f0.30:tc_teed05_f0.30 \
  --out out/ngmec_s1_perview_chair.json
python -u scripts/teedgen_perview.py --scene lego --pairs \
  ng_epi_t1.5_r0.2_m4_f0.30:tc_teed_native_0.5_f0.30 \
  ng_epi_t1.5_r0_m3_f0.30:tc_teed_native_0.5_f0.30 \
  --out out/ngmec_s1_perview_lego.json
echo "NGMEC POST DONE"
