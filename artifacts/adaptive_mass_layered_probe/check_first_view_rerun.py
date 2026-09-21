"""Early byte comparison; the full independent stage audit remains required."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.verify_adaptive_mass_probe import sha
root=ROOT/'out/adaptive_mass_layered_probe'
names=[f'native/lego_1.{ext}' for ext in ['json','npz']]+[str(p.relative_to(root/'g1_run')) for p in sorted((root/'g1_run/raw').glob('lego_1_*'))]
assert len(names)==38
rows={name:{run:sha(root/run/name) for run in ['g1_run','g1_rerun']} for name in names}
passed=all(r['g1_run']==r['g1_rerun'] for r in rows.values())
(ROOT/'artifacts/adaptive_mass_layered_probe/G1_EARLY_DETERMINISM.json').write_text(json.dumps(dict(passed=passed,scope='First fixed TRAIN view native and all 18 raw controls only; final full rerun audit pending.',files=rows),sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(passed=passed,files=len(rows)),indent=2))
raise SystemExit(0 if passed else 1)
