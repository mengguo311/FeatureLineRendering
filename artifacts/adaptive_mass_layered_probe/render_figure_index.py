"""Link every reviewed official figure without selecting or altering panels."""
import json,struct,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];art=ROOT/'artifacts/adaptive_mass_layered_probe';out=ROOT/'out/adaptive_mass_layered_probe'
read=lambda n:json.loads((art/n).read_text());g0=read('G0_VISUAL_REVIEW.json');g1=read('G1_VISUAL_REVIEW.json')
lines=['# Complete figure index','','All 76 unique official G0/G1 figures are linked below. Each G1 comparison contains all four fixed TRAIN views, six controls per group, uncapped soft responses, both raw hysteresis grids and both pairwise matched masks. Original panels are native800. Full native arrays remain available alongside the figures. Independent rerun copies are verified separately; see VERIFICATION.json and G1_VERIFICATION.json.','','G1 control group0: full, expected_depth, front_depth, median_depth, no_ids, uniform. Group1: shuffled_ids, shuffled_depths, density, rgb_canny, k4, k8. Group2: k16, tau95_128, tau90_32, tau90_64, tau95_32, tau95_64.','','All figures received complete-overview inspection. The 24 exact-pixel enlarged comparison crops are linked after the official figures; this is not a claim of native-resolution inspection of every panel. No scientific arrays, metrics or original PNGs were changed for this index.','']
for stage,run,items in [('G0','run',[(k,h,'See G0_VISUAL_REVIEW.json') for k,h in g0['figures'].items()]),('G1','g1_run',[(k,d['sha256'],d['findings']) for k,d in g1['figures'].items()])]:
 lines += ['## '+stage,'','| Complete figure | Pixels | Review finding |','|---|---:|---|']
 for name,h,note in sorted(items):
  p=out/run/name
  with p.open('rb') as f:head=f.read(24)
  assert hashlib.sha256(p.read_bytes()).hexdigest()==h;w,height=struct.unpack('>II',head[16:24]);lines.append(f'| [{name}]({p}) | {w}×{height} | {note.replace(chr(124),chr(47))} |')
 lines.append('')
lines += ['## Enlarged fixed-view comparisons','','These are exact-pixel horizontal crops of group0, retaining all six controls and all five comparison columns. Provenance: INSPECTION_CROPS.json.','']
for p in sorted((out/'inspection').glob('*.png')):lines.append(f'- [{p.stem}]({p})')
(art/'FIGURES.md').write_text('\n'.join(lines)+'\n');print('76 official figures and24 exact-pixel crops indexed')
