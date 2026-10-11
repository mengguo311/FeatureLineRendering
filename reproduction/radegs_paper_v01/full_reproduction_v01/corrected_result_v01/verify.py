"""Read-only validation of the second complete training attempt."""
import sys,json,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'reproduction/radegs_paper_v01/stage2'))
from safety import verify_seal,sha256,atomic_json
h=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');state=h/'full_reproduction_v01/precision_v01/pilot_v02/state';c=json.loads((state/'runner_config.json').read_text())
out=h/'full_reproduction_v01/precision_v01/corrected_result_audit_v01'
mismatch=[p for p,v in c['immutable_files'].items() if sha256(p)!=v]
seals={s:verify_seal(state/(s+'.seal.json'),s,c['inputs']) for s in ['smoke','train','export']}
model=Path(c['model']);rows=[json.loads(x) for x in (model/'iteration_loss.jsonl').read_text().splitlines()]
r={'immutable_file_count':len(c['immutable_files']),'immutable_mismatches':mismatch,'seals':seals,'config_sha256':sha256(state/'runner_config.json'),'iteration_records':len(rows),'unique_iterations':len({x['iteration'] for x in rows}),'contiguous':set(x['iteration'] for x in rows)==set(range(1,30001)),'schedule_valid':all(x['geometry_active']==(x['iteration']>=15001) and x['wd']==(100 if x['geometry_active'] else 0) and x['wn']==(5 if x['geometry_active'] else 0) for x in rows),'last_iteration':rows[-1],'export_npz_count':len(list((model/'depth_normal').glob('*.npz'))),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'initial_audit_assertion_correction':'Initial audit incorrectly required logged effective wd/wn=100/5 during photo-only phase. Actual records correctly log 0/0 through15000. No training/source/output changes.'}
assert not mismatch and all(seals.values()) and r['schedule_valid'] and r['contiguous'] and len(rows)==30000
atomic_json(out/'VERIFICATION.json',r);print(json.dumps(r,indent=2))
