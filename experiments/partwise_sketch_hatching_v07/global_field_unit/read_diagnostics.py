"""Post-evaluation saved-result readback only; does not change scientific assets."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT as ROOT,js
import numpy as np
import json

def npz(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}

def main():
    s=npz(UNIT/'asset/FIELDS.npz');m=npz(ROOT/'replay_package/data/lego/unit_008_asset/TARGET.npz')
    tri=m['vertices'][m['faces']];area=.5*np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)
    selected=s['selected_faces'];total=area[selected].sum();rows=[]
    for c,root in enumerate(s['anchors']):
        ix=np.flatnonzero(s['component']==c);faces=selected[ix]
        crossing=lambda a:np.rad2deg(np.arccos(np.clip(np.abs(np.sum(a[:,0]*a[:,1],axis=1)),0,1)))
        before=crossing(s['F0'][faces]);after=crossing(s['H'][faces])
        rows.append(dict(component=c,anchor_face=int(root),faces=len(faces),area_fraction=float(area[faces].sum()/total),
            anchor_F0_cross_angle=float(crossing(s['F0'][[root]])[0]),F0_cross_angle_quantiles=np.quantile(before,[0,.5,1]).tolist(),
            H_cross_angle_quantiles=np.quantile(after,[0,.5,1]).tolist(),amplitude_quantiles=np.quantile(s['amplitude'][ix],[0,.5,1]).tolist()))
    rows.sort(key=lambda r:(-r['area_fraction'],r['component']))
    js(UNIT/'COMPONENT_READBACK.json',dict(components=rows,scope='Saved-result diagnosis; near-parallel anchor layers can propagate through a whole graph component. No new style fitting.'))
    guards=[]
    for arm in ('F0','H'):
        for part in ('old','added'):
            records=json.loads((UNIT/'asset'/(arm+'_'+part+'_SEEDS.json')).read_text())
            for r in records:
                if any(r[k] not in ('requested_length','mesh_boundary','authored_region_boundary') for k in ('minus_stop','plus_stop')):
                    guards.append(dict(arm=arm,partition=part,**r))
    js(UNIT/'WALKER_GUARD_RECORD.json',dict(records=guards,policy='Original walker safeguard retained; no rerun, deletion, extension or threshold change.'))
    print(json.dumps(dict(dominant_components=rows[:3],guards=guards),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
