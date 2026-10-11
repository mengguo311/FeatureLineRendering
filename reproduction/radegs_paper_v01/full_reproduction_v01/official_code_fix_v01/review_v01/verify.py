"""Independent CPU re-hashing of the completed pilot, without editing its seals."""
import json, sys, time, shutil
from pathlib import Path
W = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(W/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json, sha256
O = Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01')
R = O/'review_v01'; C = O/'pilot/state/runner_config.json'
c = json.loads(C.read_text()); files = dict(c['immutable_files']); stages = {}
for stage in ('train','export','tsdf','eval'):
    p = O/'pilot/state'/(stage+'.seal.json'); d = json.loads(p.read_text())
    assert d['stage'] == stage and d['inputs'] == c['inputs'] and d['outputs']
    stages[stage] = {'seal_sha256':sha256(p), 'outputs':len(d['outputs'])}
    for f,h in d['outputs'].items():
        assert f not in files or files[f] == h
        files[f] = h
rows = []
for i,(p,h) in enumerate(files.items()):
    actual = sha256(p); assert actual == h, p
    rows.append({'path':p,'sha256':actual,'bytes':Path(p).stat().st_size})
    if i % 100 == 0: print('verified',i,flush=True)
records = [json.loads(x) for x in (Path(c['model'])/'iteration_loss.jsonl').read_text().splitlines()]
assert [r['iteration'] for r in records] == list(range(1,30001))
assert sum(r['geometry_active'] for r in records) == 15001
assert sum(r['optimizer_updated'] for r in records) == 29999
assert all((r['wd'],r['wn']) == ((100,.05) if r['iteration']>=15000 else (0,0)) for r in records)
result = {'status':'PASS','method_variant':'official_code_fix_v01','config_sha256':sha256(C),
          'immutable_inputs_count':len(c['immutable_files']),'distinct_files_verified':len(rows),
          'stages':stages,'records':len(records),'geometry_records':15001,'optimizer_updates':29999,
          'first_record':records[0],'last_record':records[-1],'files':rows,
          'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'scientificdone':False}
atomic_json(R/'REVERIFIED.json',result)
print({k:v for k,v in result.items() if k!='files'},flush=True)
