"""Post-hoc engineering diagnostic; no tuning or confirmatory gate changes."""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'): os.environ[key]='2'
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
from pathlib import Path
import json
import numpy as np

ROOT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_001')
m=np.load(ROOT/'assets/lamp_mesh.npz');tri=m['vertices'][m['faces']]
result={'scope':'Post-hoc implementation pathology audit of frozen output, not a new scientific comparison; thresholds/gates untouched','styles':{}}
for file in sorted((ROOT/'strokes').glob('*.npz')):
    d=np.load(file);faces=d['faces'];bary=d['bary'];offsets=d['offsets'];records=[]
    for i,(start,end) in enumerate(zip(offsets[:-1],offsets[1:])):
        f=faces[start:end];b=bary[start:end];x=np.einsum('ni,nij->nj',b,tri[f])
        distance=np.linalg.norm(np.diff(x,axis=0),axis=1)
        transitions=f[np.r_[True,f[1:]!=f[:-1]]]
        reversals=int(np.count_nonzero(transitions[:-2]==transitions[2:]))
        records.append({'id':str(d['ids'][i]),'part':int(d['parts'][i]),'samples':len(f),
                        'length_world':float(distance.sum()),'sub_microunit_steps':int(np.count_nonzero(distance<1e-6)),
                        'adjacent_face_backtracks':reversals})
    result['styles'][file.stem]={'stroke_count':len(records),'total_samples':int(len(faces)),
        'max_samples':max(x['samples'] for x in records),
        'strokes_with_100plus_backtracks':sum(x['adjacent_face_backtracks']>=100 for x in records),
        'all_strokes':records}
(ROOT/'PATH_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
for name,value in result['styles'].items(): print(name,{k:v for k,v in value.items() if k!='all_strokes'})
