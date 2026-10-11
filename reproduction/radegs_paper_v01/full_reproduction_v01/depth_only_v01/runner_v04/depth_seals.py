import json,time
from pathlib import Path
from safety import sha256,atomic_json
STAGES=('smoke','train','export','depth_review')
def seal_stage(path,stage,inputs,outputs):
    if stage not in STAGES:raise ValueError('stage outside depth-only scope')
    files={str(Path(p).resolve()):sha256(p) for p in outputs}
    if not files:raise ValueError('empty outputs')
    atomic_json(path,{'schema':1,'workflow':'depth_only_v01','stage':stage,'inputs':inputs,'outputs':files,'sealed_unix':time.time()})
def verify_seal(path,stage,inputs):
    try:
        d=json.loads(Path(path).read_text())
        return stage in STAGES and d['schema']==1 and d['stage']==stage and d['inputs']==inputs and bool(d['outputs']) and all(sha256(p)==h for p,h in d['outputs'].items())
    except (OSError,ValueError,KeyError,TypeError):return False
