"""Export all accepted original-row contributors for one saved path anchor."""
import runtime
from runtime import output_guard,js
import argparse,json
from pathlib import Path
import numpy as np

def query(unit,view,segment,output):
    p=json.loads((unit/'PROTOCOL.json').read_text());file=unit/'results'/view/'path_support.npz'
    with np.load(file) as z:d={k:z[k] for k in z.files}
    found=np.flatnonzero(d['segment_index']==segment)
    if not len(found):raise ValueError('segment was not sampled; available: '+str(d['segment_index'].tolist()))
    k=int(found[0]);lo,hi=d['offsets'][k:k+2]
    info=dict(source_sha256=p['source']['sha256'],view=view,segment_index=segment,stroke_id=int(d['stroke_id'][k]),
        region_id=int(d['region_id'][k]),proxy_face=int(d['face'][k]),bary=d['bary'][k].tolist(),
        state=str(d['state'][k]),accepted_contributors=int(hi-lo),retained_mass=float(d['retained_mass'][k]),
        rejected_mass=float(d['rejected_mass'][k]),retained_fraction=float(d['retained_fraction'][k]))
    output=output_guard(output);output.mkdir(exist_ok=False)
    with (output/'contributors.csv').open('w') as f:
        f.write('source_index,alphaT_weight,camera_z,depth_eligible\n')
        for i in range(lo,hi):f.write(f'{d["source_index"][i]},{d["weight"][i]:.17g},{d["contributor_depth"][i]:.17g},{int(d["eligible"][i])}\n')
    js(output/'ANCHOR.json',info);print(json.dumps(info),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True);p.add_argument('--view',default='orbit_0_65_4.7')
    p.add_argument('--segment-index',type=int,default=0);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    query(a.unit,a.view,a.segment_index,a.output)
