#!/usr/bin/env bash
# One sequential runner for everything still owed by teed_gen_spec.md.
# Sequential by construction: GPU 1 is shared and had ~4 GB free, and the lego MeshOracle
# (971k crease points) already OOM'd once with a second job resident.  No pgrep guards --
# they matched lingering tool-call wrapper shells and deadlocked.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd ~/3dgs_line/tier1
SYN=scripts/explore/syn
say () { echo; echo "################################################ $* ################################################"; echo; }

m1b () {   # m1b <scene> <prefix> <score> <f>
  local sn="$1" px="$2" sc="$3" f="$4"
  local sp="$SYN/finalscore_overall_${sn}__${sc}.npy"
  local out="out/m1b_${sn}_${px}_${sc}_f${f}.json"
  [ -f "$sp" ] || { echo "MISSING $sp"; return; }
  [ -f "$out" ] && { echo "HAVE ${out##*/}"; return; }
  echo "=================== ${sn}/${px} ARM ${sc} f=${f} ==================="
  python -u scripts/run_m1b.py --scene "$sn" --gate --eval_split test --no_viz \
    --score "$sp" --f "$f" --tag "_${px}_${sc}_f${f}"
}

say "STEP 1  lego M1b frontier EXTENSION (canny's P rises with f, so the dial must be swept up to f=1.0)"
for f in 0.60 0.70 0.85 1.00; do m1b lego tc canny "$f"; done
for f in 0.60 0.70; do m1b lego tc teed_native_0.5 "$f"; done
for sc in cannysharplow cannysharp teed_native_0.9 union_native_0.5; do m1b lego tc "$sc" 0.50; done
for f in 0.60 0.70; do m1b lego tc cannysharplow "$f"; done

say "STEP 2  lego 2D DETECTOR metrics (recall / miss-set recovery / purity / FP triage)"
python -u scripts/recall_trackC_detector.py --scene lego --canny_variants \
  > logs/teedgen_L_detector_lego.log 2>&1 && echo "detector OK" || echo "detector FAILED"
tail -40 logs/teedgen_L_detector_lego.log

say "STEP 3  lego VIZ + TEMPORAL no-regress"
for F in 0.40 0.30; do
  python -u scripts/recall_trackC_viz.py --scene lego \
    --canny "linelets_lego_tc_canny_f${F}.npz" \
    --teed  "linelets_lego_tc_teed_native_0.5_f${F}.npz" \
    --views 0 5 25 --out_prefix "teed_lego_f${F}" || true
done
cp -f out/teed_lego_f0.40_v0.png  out/teed_lego_v0.png  2>/dev/null || true
cp -f out/teed_lego_f0.40_v25.png out/teed_lego_v25.png 2>/dev/null || true
for F in 0.40 0.30; do
  T=$(echo $F | tr -d '.')
  cp -f out/linelets_lego_tc_canny_f${F}.npz           out/linelets_lego_tccanny${T}_test.npz
  cp -f out/linelets_lego_tc_teed_native_0.5_f${F}.npz out/linelets_lego_tcteed${T}_test.npz
  cp -f out/linelets_lego_tc_cannysharplow_f${F}.npz   out/linelets_lego_tcsharplow${T}_test.npz 2>/dev/null || true
  for V in tccanny${T} tcteed${T} tcsharplow${T}; do
    [ -f "out/linelets_lego_${V}_test.npz" ] || continue
    echo "---------- temporal lego $V ----------"
    python -u scripts/m1b_stroke_temporal.py --scenes lego --variant "$V" \
      --frames 30 60 120 240 --view_a 5 --view_b 15 --tag "_tcL_${V}" || true
  done
done

say "STEP 4  TRACK M chair EXTENSION: shifted-mask control + f=0.45/0.50"
python -u scripts/recall_trackC_seeds.py --scene chair --sources teed --thrs 0.5 \
  --arms_json out/trackM_arms_chair2.json --tag _trackM2
for f in 0.40 0.35 0.30; do m1b chair tm m3_shift15_d2 "$f"; m1b chair tm m3_shift40_d2 "$f"; done
for f in 0.50 0.45; do
  for sc in m3_masksharplow_d2 m1_soft_g1.0 m2_cc25 m2_cc10 m3_maskM1a_d2; do m1b chair tm "$sc" "$f"; done
done

say "STEP 5  TRACK M on LEGO (does the mechanism decomposition transfer?)"
python -u scripts/recall_trackC_seeds.py --scene lego --sources teed --thrs 0.5 \
  --arms_json out/trackM_arms_lego.json --tag _trackM
for f in 0.50 0.40 0.30 0.22; do
  for sc in m3_masksharplow_d2 m3_maskM1a_d2 m1_soft_g1.0 m2_cc25; do m1b lego tm "$sc" "$f"; done
done
say "QUEUE COMPLETE"
