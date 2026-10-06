"""Independent analytic moving-interface lag/ghost evaluation, no score labels."""
import json,sys
from pathlib import Path
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/image_space_edge_foundation_v1/src'))
from runtime import ART,OUT,atomic_json
from presentation import panel_sheet
from boundary import ink

def run():
    records=[];panels=[]
    for i in range(7):
        z=np.load(OUT/'synthetic'/f'moving_{i}.npz');s=z['spatial'];t=z['temporal'];im=z['rgb'];row=dict(frame=i,edges=[])
        if i<6:
            for name,known in [('left',20.5+8*i),('right',54.5+8*i)]:
                x=np.arange(s.shape[1]);inside=abs(x-known)<=4
                def center(a):
                    mass=a[35:45,inside].sum(axis=0);return float((mass*x[inside]).sum()/mass.sum())
                cs,ct=center(s),center(t)
                row['edges'].append(dict(name=name,analytic_center=known,spatial_center=cs,temporal_center=ct,
                     spatial_absolute_error=abs(cs-known),temporal_absolute_error=abs(ct-known),temporal_minus_spatial=ct-cs))
        else:row['disappearance_max_soft']=float(t.max())
        jump=z['truth_jump'];from scipy.ndimage import distance_transform_edt
        permitted=distance_transform_edt(~jump)<=3 if jump.any() else np.zeros_like(jump)
        row['ghost_mass_outside_truth_3px']=float(t[~permitted].sum()/max(float(t.sum()),1.))
        records.append(row)
        roi=(slice(25,55),slice(10,120))
        # Native pixels enlarged only for the explicit moving-interface control.
        a=np.ones((128,128,3),np.float32);a[49:79,9:119]=im[roi]
        b=np.ones_like(a);b[49:79,9:119]=ink(s)[roi]
        c=np.ones_like(a);c[49:79,9:119]=ink(t)[roi]
        panels.extend([(str(i)+' moving RGB band',a),(str(i)+' spatial OFF',b),(str(i)+' temporal ON',c)])
    edges=[e for r in records for e in r['edges']]
    result=dict(records=records,max_temporal_minus_spatial_center=float(max(abs(e['temporal_minus_spatial']) for e in edges)),
         spatial_MAE=float(np.mean([e['spatial_absolute_error'] for e in edges])),temporal_MAE=float(np.mean([e['temporal_absolute_error'] for e in edges])),
         ghost_mass_max=max(r['ghost_mass_outside_truth_3px'] for r in records),
         scope='analytic 2D translating rectangle, occluder below measured band, final full disappearance; not physical scene correspondence')
    atomic_json(ART/'tests/TEMPORAL_CONTROL_AUDIT.json',result)
    panel_sheet(panels,ART/'synthetic/moving_edge_lag_band.png',columns=3,size=256,title='Independent known edge centers; band y35..45 remains unoccluded')
    print(json.dumps(result,indent=2))
if __name__=='__main__':run()
