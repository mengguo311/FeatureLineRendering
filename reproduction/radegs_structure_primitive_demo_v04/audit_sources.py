from common import *
guard();rows=[]
def check(p,expected=None,kind='source'):
    p=Path(p);s=sha(p)
    if expected:assert s==expected,str(p)
    rows.append({'path':str(p),'sha256':s,'bytes':p.stat().st_size,'kind':kind,'verified_against_prior':expected is not None})
for n,s in json.loads((T/'LITERATURE_SOURCE_HASHES.json').read_text()).items():check(T/'literature'/n,s,'primary_text_or_ledger')
for r in json.loads((V3/'RESULTS_MANIFEST.json').read_text())['files']:
    p=Path(r['path'])
    if p.name in ('FUSION_REDESIGN_ZH.md','ASTRA_DEEP_DIAGNOSIS_ZH.md','RESULTS.json','roi_skeleton_fitted.npz') or (p.parent.name=='roi_pilot' and p.suffix=='.png'):check(p,r['sha256'],'v03_negative')
m=json.loads((B/'SOURCE_MANIFEST.json').read_text());archive_provenance=[]
for arc in m['archives']:
    archive_provenance.append({k:v for k,v in arc.items() if k!='files'})
    for r in arc['files']:
        p=Path(r['path'])
        if p.name in [f"{arc['scene']}_{v}.npz" for v in BUILD+HOLD] or p.suffix!='.npz':check(p,r['sha256'],'construction' if p.stem[-4:] in BUILD else 'holdout_or_metadata')
check(B/'evidence/boundary.py','11bbb41a762f252d9eeb4ea3f0a8399ed026139d9490bb8cf161bc815e05dd30','unchanged_detector')
check(B/'build/libewa.so','0ab11c21f930446c699ae5fb9dc14f3fe2eefc563a4011b8a14ba9a1627807e3','verified_CPU_native')
for p in sorted(OLD.glob('*.py')):check(p,kind='readonly_utility')
check(OLD/'ewa.cpp')
for part in ['parent_detection_vs_gaussians','parent_strict_retry_v01']:
    a=json.loads((B/part/'MANIFEST.json').read_text());d=a.get('files',a.get('outputs',{}))
    for name,s in d.items():
        if (B/part/name).suffix in ('.jpg','.png'):check(B/part/name,s,'visual_evidence')
for scene in ('scan24','scan65','scan63'):
    p=O/'results_v2'/scene/'balanced_gaussians.npz';check(p,kind='old_balanced_comparator')
for p in [T/'ASTRA_PLAN_ZH.md',T/'CONFIG.json']:check(p,json.loads((T/'PLAN_FREEZE.json').read_text())[p.name],'frozen_plan')
js(T/'SOURCE_FREEZE.json',{'files':rows,'archive_provenance':archive_provenance,'archive_note':'raw selected bytes verified against delivery manifest; old archive bytes not recopied/rehashed this slice','holdout_use':'only hash now; content evaluation after model seal','coordinates':'integer center; raw camera-z; COLMAP scene units, not meters','shared_agent_lock_owner_pid':1879221})
print('SOURCE_FREEZE',len(rows),'records verified')
