"""Local-probe records, frozen controls and determinate machine decisions."""
from collections import Counter
import hashlib,json
from pathlib import Path
from .linelet import init_linelets
import numpy as np
from scipy.spatial import cKDTree
from .foundation import freeze_json
from .multiscene_probe import (ImageEvidence,infer_queries,edge_field,sample_queries,
    shift_field as inherited_shift,axial_angle,match_outputs)


def shift_field(field,view_number,cfg):
    result=inherited_shift(field,view_number,cfg)
    d=cfg['controls']['shift_pixels'];dx=d*((view_number%3)-1);dy=d*(((view_number+1)%3)-1)
    h,w=field['domain'].shape
    result['nearest_uv']=(result['nearest_uv']+np.array([dx,dy]))%[w,h]
    return result


def _json(value):
    if isinstance(value,np.ndarray):return _json(value.tolist())
    if isinstance(value,dict):return {k:_json(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [_json(v) for v in value]
    if isinstance(value,(np.integer,np.bool_)):return value.item()
    if isinstance(value,(float,np.floating)):return float(value) if np.isfinite(value) else None
    return value


def save_probe(directory,result):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    profiles=result['profiles'];offsets=np.cumsum([0]+[len(p['depths']) for p in profiles])
    arrays=dict(offsets=offsets,depths=np.concatenate([p['depths'] for p in profiles]) if profiles else np.array([]),
        cost=np.concatenate([p['cost'] for p in profiles]) if profiles else np.array([]),
        origin=np.array([p['origin'] for p in profiles]),direction=np.array([p['direction'] for p in profiles]))
    with (directory/'profiles.npz').open('xb') as f:np.savez_compressed(f,**arrays)
    meta=[{k:v for k,v in p.items() if k not in ['depths','cost','origin','direction']} for p in profiles]
    freeze_json(directory/'profiles_metadata.json',_json(meta))
    freeze_json(directory/'modes.json',_json(result['modes']))
    freeze_json(directory/'accepted.json',_json(result['accepted']))
    counter=Counter(reason for m in result['modes'] for reason in m['reasons'])
    summary=dict(query_count=result['query_count'],mode_count=len(result['modes']),raw_accepted_count=sum(m['accepted'] for m in result['modes']),accepted_count=len(result['accepted']),rejected_count=sum(not m['accepted'] for m in result['modes']),ambiguous_count=sum('multimodal' in m['reasons'] or 'wide_plateau' in m['reasons'] for m in result['modes']),resolution_ok=result['resolution_ok'],rejection_reasons=dict(counter))
    for key in ['elapsed_seconds','arm','split','source_hashes']:
        if key in result:summary[key]=result[key]
    freeze_json(directory/'summary.json',_json(summary));return summary


def load_probe(directory):
    directory=Path(directory)
    return dict(**json.loads((directory/'summary.json').read_text()),accepted=json.loads((directory/'accepted.json').read_text()),modes=json.loads((directory/'modes.json').read_text()))


def evaluate_positions(accepted,evidence):
    if not accepted:return []
    points=np.array([r['point'] for r in accepted]);axes=np.array([r['axis'] for r in accepted])
    rows=[dict(query=r['query'],views=[]) for r in accepted]
    for o in evidence.observations(points):
        projected=np.einsum('nij,nj->ni',o['J'],axes)
        valid=o['visible']&np.isfinite(o['tangent']).all(1)&(np.linalg.norm(projected,axis=1)*evidence.delta>=evidence.cfg['probe']['foreshortening_pixels'])
        angles=axial_angle(projected,o['tangent'])
        for i,row in enumerate(rows):
            row['views'].append(dict(view=o['view'],inside=bool(o['inside'][i]),visible=bool(o['visible'][i]),classification=int(o['classification'][i]),supported=bool(o['support'][i]),direction_evaluable=bool(valid[i]),dt=float(o['dt'][i]),angle=float(angles[i]) if valid[i] else None))
    return rows


def prediction_summary(rows,cfg,views=None):
    g=cfg['gates'];n=len(rows);evaluable=joint=0;views={str(i):dict(total=n,evaluable=0,joint=0) for i in (views or [])}
    for row in rows:
        good=[v for v in row['views'] if v['direction_evaluable']]
        supported=[v for v in good if v['dt']<=g['G2_dt_max'] and v['angle']<=g['G2_angle_max']]
        evaluable+=len(good)>=g['G2_min_views'];joint+=(len(good)>=g['G2_min_views'] and len(supported)>=g['G2_min_views'])
        for v in row['views']:
            record=views.setdefault(str(v['view']),dict(total=n,evaluable=0,joint=0))
            record['evaluable']+=v['direction_evaluable']
            record['joint']+=bool(v['direction_evaluable'] and v['dt']<=g['G2_dt_max'] and v['angle']<=g['G2_angle_max'])
    coverage=evaluable/n if n else 0.;fraction=joint/evaluable if evaluable else 0.
    return dict(denominator=n,evaluable=evaluable,joint=joint,coverage=coverage,joint_fraction=fraction,per_view=views,passed=bool(n and coverage>=g['G2_coverage_min'] and fraction>=g['G2_joint_min']))


def pca_control(asset,evidence,cfg):
    mu=asset['mu'];scores=np.zeros(len(mu));counts=np.zeros(len(mu),int)
    for start in range(0,len(mu),16384):
        end=min(start+16384,len(mu));sumscore=np.zeros(end-start);count=np.zeros(end-start,int)
        for o in evidence.observations(mu[start:end]):
            count+=o['visible'];sumscore+=np.where(o['visible'],np.exp(-o['dt']**2/(2*cfg['controls']['pca_dt_sigma']**2)),0)
        scores[start:end]=sumscore/np.maximum(count,1);counts[start:end]=count
    eligible=np.flatnonzero(counts>=cfg['probe']['min_views'])
    hashes=[hashlib.sha256(f"{cfg['queries']['seed']}:pca:{i}".encode()).hexdigest() for i in range(len(mu))]
    order=sorted(eligible,key=lambda i:(-scores[i],hashes[i]));chosen=np.array(order[:int(len(order)*cfg['controls']['pca_seed_fraction'])],int)
    rows=[]
    if len(chosen)>=3:
        L=init_linelets(mu[chosen],mu,asset['scale'],k_scale=cfg['controls']['pca_k_scale'],pca_radius_mult=cfg['controls']['pca_radius_mult'])
        for j,i in enumerate(chosen):
            if L['t_valid'][j]:rows.append(dict(query=hashes[i],point=L['p0'][j].tolist(),axis=L['t'][j].tolist(),score=float(scores[i]),row=int(i)))
    return dict(accepted=rows,selected_count=len(chosen),eligible_center_count=len(eligible),total_centers=len(mu),undefined_direction_count=len(chosen)-len(rows),original_positions=True,F_only=True)


def random_control(rows,cfg):
    axes=np.random.default_rng(cfg['controls']['random_seed']).normal(size=(len(rows),3))
    axes/=np.maximum(np.linalg.norm(axes,axis=1,keepdims=True),1e-30)
    return [dict(query=r['query'],point=r['point'],axis=t.tolist()) for r,t in zip(rows,axes)]


def glyph_samples(rows,delta):
    if not rows:return np.empty((0,3)),np.empty((0,3))
    points=np.array([r['point'] for r in rows]);axes=np.array([r['axis'] for r in rows])
    samples=(points[:,None,:]+np.linspace(-1,1,5)[None,:,None]*delta*axes[:,None,:]).reshape(-1,3)
    tangents=np.repeat(axes,5,axis=0);cells=np.floor(samples/(delta*.5)).astype('i8')
    _,indices=np.unique(cells,axis=0,return_index=True)
    return samples[indices],tangents[indices]


def glyph_coverage(base,other,delta,cfg):
    a,ta=glyph_samples(base,delta);b,tb=glyph_samples(other,delta)
    def direction(x,tx,y,ty):
        if not len(x) or not len(y):return dict(covered=0,total=len(x),fraction=0.)
        tree=cKDTree(y);neighbors=tree.query_ball_point(x,cfg['gates']['G3_distance_delta_max']*delta)
        good=sum(bool(js) and np.any(axial_angle(tx[i],ty[js])<=cfg['gates']['G3_angle_max']) for i,js in enumerate(neighbors))
        return dict(covered=int(good),total=len(x),fraction=good/len(x))
    f=direction(a,ta,b,tb);r=direction(b,tb,a,ta)
    return dict(forward=f['fraction'],backward=r['fraction'],forward_counts=f,backward_counts=r,base_raw=len(base),other_raw=len(other),base_samples=len(a),other_samples=len(b))


def machine_decision(eligible,gates,image_only_pivot=False):
    if not eligible:return 'INSUFFICIENT_POSTERIOR_QUALITY'
    if not gates.get('G0',False):return 'ENGINEERING_NOT_READY'
    if image_only_pivot:return 'PIVOT_IMAGE_ONLY'
    if all(gates.get(g,False) for g in ['G1','G2_machine','G3','G4_machine']):return 'MACHINE_FOUNDATION_GO_MANUAL_PENDING'
    return 'STOP_B'
