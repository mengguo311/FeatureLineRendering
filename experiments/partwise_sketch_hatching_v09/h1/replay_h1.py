"""Cold reload one frozen frame in a new process and compare actual arrays."""
import runtime
from runtime import ROOT as UNIT,js
import json,argparse
from pathlib import Path
import numpy as np
from linked_asset import npz
from run_h1 import locks,Runner,plan

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference-key',default='012',choices=[r['key'] for r in plan()])
    p.add_argument('--output-name',default='REPLAY_012')
    args=p.parse_args()
    if Path(args.output_name).name!=args.output_name:p.error('one new directory name required')
    locks();row=dict(next(r for r in plan() if r['key']==args.reference_key));reference=row['key'];row['key']=args.output_name
    if row['key'] in [r['key'] for r in plan()]:p.error('output must not be a scientific frame name')
    Runner().frame(row);checks=[]
    for name in ['COMMON.npz','CENTERLINES.npz','B0_PATHS.npz','CONVENTIONAL.npz']+[f'{m}/{a}/FRAME.npz' for m in ('natural','matched') for a in ('B0','B1')]:
        a=npz(UNIT/'renders'/reference/name);b=npz(UNIT/'renders'/row['key']/name);assert set(a)==set(b)
        for k in a:np.testing.assert_array_equal(a[k],b[k])
        checks.append(dict(file=name,arrays=len(a),exact=True))
    result=dict(reference=reference,output_name=args.output_name,cold_original_GS=True,B0_regenerated_from_frozen_config=True,checks=checks)
    locks();js(UNIT/'renders'/args.output_name/'REPLAY_CHECK.json',result)
    if args.output_name=='REPLAY_012':js(UNIT/'REPLAY_CHECK.json',result)
    print(json.dumps(dict(reference=reference,exact_files=len(checks))))
if __name__=='__main__':main()
