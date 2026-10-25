"""Post-evaluation readback only: transition removals and rendered intervention."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT as ROOT,js,sha,HERE
import json,collections
import numpy as np

def load(p):return json.loads(p.read_text())
def npz(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}

def main():
    t=npz(ROOT/'replay_package/data/lego/unit_008_asset/TARGET.npz');v=t['vertices'];faces=t['faces']
    fields=npz(UNIT/'asset/FIELDS.npz');graph={tuple(sorted(map(int,p))) for p in fields['graph_pairs']};excluded={tuple(sorted(map(int,p))) for p in fields['excluded_pairs']}
    out={};counts={}
    for part in ('old','added'):
        for arm in ('A','B','C'):
            p=npz(UNIT/'asset'/(arm+'_'+part+'.npz'));groups={k:dict(world=[],intrinsic=[]) for k in ('graph','excluded','other')}
            for sid in np.unique(p['stroke_id']):
                ids=np.flatnonzero(p['stroke_id']==sid)
                for a,b in zip(ids[:-1],ids[1:]):
                    i,j=map(int,p['face'][[a,b]])
                    if i==j:continue
                    edge=sorted(set(faces[i])&set(faces[j]));assert len(edge)==2
                    axis=v[edge[1]]-v[edge[0]];axis/=np.linalg.norm(axis);inward=[]
                    for f in (j,i):
                        third=next(k for k in faces[f] if k not in edge);u=v[third]-v[edge[0]];u-=np.dot(u,axis)*axis;u/=np.linalg.norm(u);inward.append(u)
                    transport=np.outer(axis,axis)-np.outer(inward[0],inward[1])
                    directions=p['points'][[a,b],1]-p['points'][[a,b],0];directions/=np.linalg.norm(directions,axis=1,keepdims=True)
                    pair=tuple(sorted((i,j)));name='graph' if pair in graph else 'excluded' if pair in excluded else 'other'
                    groups[name]['world'].append(float(np.rad2deg(np.arccos(np.clip(directions[0]@directions[1],-1,1)))))
                    groups[name]['intrinsic'].append(float(np.rad2deg(np.arccos(np.clip((transport@directions[0])@directions[1],-1,1)))))
            out[arm+'_'+part]={k:dict(transitions=len(g['world']),world_quantiles=np.quantile(g['world'],[.5,.9,.95,1]).tolist() if g['world'] else [],
                intrinsic_quantiles=np.quantile(g['intrinsic'],[.5,.9,.95,1]).tolist() if g['intrinsic'] else [],obtuse_intrinsic=sum(x>90 for x in g['intrinsic'])) for k,g in groups.items()}
            counts[arm+'_'+part]=dict(layer0_strokes=len(np.unique(p['stroke_id'][p['layer_id']==0])),layer1_strokes=len(np.unique(p['stroke_id'][p['layer_id']==1])))
    guards=[]
    for part in ('old','added'):
        records=load(UNIT/'asset'/('A_'+part+'_SEEDS.json'));pairs={r['source_h_stroke_id']:r for r in load(UNIT/'asset'/(part+'_PAIRS.json'))}
        for r in records:
            if 'zero_step_cycle' in (r['minus_stop'],r['plus_stop']):guards.append(dict(part=part,original_H_record=r,paired_record=pairs[r['stroke_id']],scope='Original H guard result preserved, not repaired or hidden by cuts.'))
    far=load(UNIT/'FAR_READBACK.json');effects=load(UNIT/'VISIBLE_INTERVENTION.json')
    compact=dict(transitions=out,layer_counts=counts,original_H_guard_records=guards,
        maximum_linked_matched_far_pixel_L1=max(r[k]['max'] for r in far if r['mode']=='linked_matched' for k in ('other','background')),
        linked_matched_far_pixels_above_1_255=sum(r[k]['above_1_255'] for r in far if r['mode']=='linked_matched' for k in ('other','background')),
        BC_dev_effects=[r for r in effects if r['pair']=='B_C' and r['mode']=='linked_matched' and r['view'] in ('orbit_61_24_5.3','orbit_241_24_5.3','orbit_61_60_5.3','orbit_241_60_5.3')],
        scope='Post-evaluation descriptive readback; no new tuning/gate or physical/semantic truth.')
    for path,h in load(UNIT/'ENGINEERING_ADAPTER_LOCK.json')['files'].items():assert sha(path)==h
    js(UNIT/'BOUNDARY_READBACK.json',compact)
    print(json.dumps(compact),flush=True)

if __name__=='__main__':main()
