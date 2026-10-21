"""Seal unit002 only; historical outputs and orchestration are read-only."""
from common import *
from datetime import datetime,timezone
import subprocess
OUT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_002')
assert not (OUT/'SEAL.json').exists()
status=json.loads((OUT/'STATUS.json').read_text());assert status['execution_state']=='complete'
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
files=[]
for path in sorted(OUT.rglob('*')):
    if not path.is_file() or 'runtime' in path.relative_to(OUT).parts or path.name in ('SEAL.json','SHA256_MANIFEST.json'):continue
    files.append({'root':'unit','path':str(path.relative_to(OUT)),'bytes':path.stat().st_size,'sha256':sha(path)})
sources=list((WORK/'experiments/partwise_sketch_hatching_v02').glob('*.py'))
sources+=list((WORK/'docs/partwise_sketch_hatching_v02').glob('*unit002*'))
sources+=[WORK/'experiments/partwise_sketch_hatching/core.py',WORK/'experiments/partwise_sketch_hatching/core_walk_v2.py']
for path in sorted(set(sources)):
    files.append({'root':'worktree','path':str(path.relative_to(WORK)),'bytes':path.stat().st_size,'sha256':sha(path)})
manifest={'source_commit':commit,'created_at_utc':datetime.now(timezone.utc).isoformat(),'roots':{'unit':str(OUT),'worktree':str(WORK)},
          'exclusions':['runtime stdout/stderr (receipts retain hashes)','manifest and seal self references'],'files':files}
write_json(OUT/'SHA256_MANIFEST.json',manifest)
seal={'manifest_path':str(OUT/'SHA256_MANIFEST.json'),'manifest_sha256':sha(OUT/'SHA256_MANIFEST.json'),
      'file_count':len(files),'total_bytes':sum(f['bytes'] for f in files),'source_commit':commit,
      'scientific_verdict':status['scientific_verdict'],'verification':'Producer seal; separate independent artifact/media/all-frame audits retained.',
      'created_at_utc':datetime.now(timezone.utc).isoformat()}
write_json(OUT/'SEAL.json',seal)
print(json.dumps(native(seal),ensure_ascii=False))
