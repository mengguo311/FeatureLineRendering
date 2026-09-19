#!/usr/bin/env python3
"""One-way C/DEV evaluation, diagnostics, and review material after output freezing."""
import argparse,ctypes,hashlib,json,sys,time
from pathlib import Path
import numpy as np,cv2
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.foundation import freeze_json,verified_json,restrict_filesystem,load_asset,STOCK_SITE,qualification_metrics
from src.corrected_layers import AreaLayers
from src.corrected_probe import (ImageEvidence,edge_field,evaluate_positions,prediction_summary,load_probe,match_outputs,glyph_coverage,machine_decision,_json)
from src.corrected_evaluation import compute_machine_gates
from src.corrected_qualification import reference,calibrated_view
from src.corrected_surface import audit_asset
from src.corrected_visuals import glyph_image,spatial_order,ink_prefix,write_png,write_video,orbit_cameras
from src.multiscene_qualification import save_grid
from src.multiscene_probe import axial_angle

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())

def machine(output,local,cfg,elig,cameras,delta):
    fields={i:dict(np.load(local/f'C/field_{i:03d}.npz')) for i in cfg['splits']['C']}
    layers={i:AreaLayers.load(local/f'layers/seed_1729/view_{i:03d}.npz') for i in cfg['splits']['C']}
    evidence=ImageEvidence(cameras,fields,layers,delta,cfg)
    base=load_probe(local/'F/gs');nogs=load_probe(local/'F/no_gs');shifted=load_probe(local/'F/shifted')
    rows=evaluate_positions(base['accepted'],evidence);prediction=prediction_summary(rows,cfg,views=cfg['splits']['C'])
    (output/'prediction_rows').mkdir();freeze_json(output/'prediction_rows/gs_C.json',_json(rows))
    no_evidence=ImageEvidence(cameras,fields,None,delta,cfg)
    no_rows=evaluate_positions(nogs['accepted'],no_evidence);no_pred=prediction_summary(no_rows,cfg,views=cfg['splits']['C'])
    freeze_json(output/'prediction_rows/no_gs_C.json',_json(no_rows))
    for name,accepted in [('pca',read(local/'F/pca.json')['accepted']),('random',read(local/'F/random.json'))]:
        values=evaluate_positions(accepted,evidence);freeze_json(output/f'prediction_rows/{name}_C.json',_json(values));freeze_json(output/f'{name}_C_summary.json',prediction_summary(values,cfg,views=cfg['splits']['C']))
    repeats={};no_repeats={};offsets={}
    items=[('C_same_query',local/'C/gs')]+[(f'LOO_{i}',local/f'F/gs_loo_{i:03d}') for i in cfg['splits']['F']]
    items += [(p.name,p/'gs') for p in sorted((local/'repeats').glob('*')) if p.is_dir()]
    for name,path in items:
        other=load_probe(path);r=match_outputs(base['accepted'],other['accepted'],delta,cfg)
        r['glyph_cell_coverage']=glyph_coverage(base['accepted'],other['accepted'],delta,cfg);repeats[name]=r
    for name,path in [('C_same_query',local/'C/no_gs')]+[(f'LOO_{i}',local/f'F/no_gs_loo_{i:03d}') for i in cfg['splits']['F']]:
        no_repeats[name]=match_outputs(nogs['accepted'],load_probe(path)['accepted'],delta,cfg)
    for group in [local/'F',local/'C',*sorted((local/'repeats').glob('*'))]:
        reference_rows=load_probe(group/'gs')['accepted']
        for path in sorted(group.glob('gs_offset_*')):
            offsets[str(path.relative_to(local))]=match_outputs(reference_rows,load_probe(path)['accepted'],delta,cfg)
    F=read(local/'F/F_predictions.json');angles={key:[v['angle'] for row in F[key] for v in row['views'] if v['direction_evaluable']] for key in ['gs','random']}
    resolution=all(read(p)['resolution_ok'] for p in local.rglob('summary.json'))
    result=compute_machine_gates(base,prediction,repeats,shifted,angles,elig['valid_parent_geometry'] and resolution,cfg)
    result.update(scene=elig['scene'],eligible=True,route_a=elig['route_a'],route_b=elig['route_b'],invariance_scope='BOTH' if elig['route_a'] and elig['route_b'] else 'SEED_ONLY' if elig['route_a'] else 'CONTROLLED_ONLY',baseline_summary={k:v for k,v in base.items() if k not in ['modes','accepted']},C_prediction=prediction,repeats=repeats,detector_offsets=offsets,no_gs=dict(summary={k:v for k,v in nogs.items() if k not in ['modes','accepted']},C_prediction=no_pred,repeats=no_repeats,stable_machine=bool(nogs['accepted_count']>=cfg['gates']['G1_min_count'] and no_pred['passed'] and all(r['passed'] for r in no_repeats.values()))))
    # Independent visible-domain labels are absent. No detector proxy can certify
    # net GS benefit or a favorable image-only pivot by itself.
    result['verdict']=machine_decision(True,result['machine'],False)
    result['access_status']='PENDING_FINAL_NATIVE_OPEN_AUDIT'
    freeze_json(output/'machine.json',_json(result));print('machine',elig['scene'],result['verdict'],result['machine'],flush=True)


def surface(output,local,root,cfg,elig,cameras,delta):
    queries=read(local/'F/queries.json')+read(local/'F/background_queries.json');locations={}
    quantiles={}
    for q in queries:
        i=q['view']
        if i not in quantiles:quantiles[i]=AreaLayers.load(local/f'layers/seed_1729/view_{i:03d}.npz').quantiles()
        x,y=q['pixel'];camera=cameras[i];c2w=np.linalg.inv(camera['w2c']);direction=c2w[:3,:3]@np.linalg.solve(camera['K'],[x,y,1])
        for quantile,z in zip([.05,.5,.95],quantiles[i][y,x]):
            if z<=0:continue
            point=c2w[:3,3]+direction*z;cell=np.floor(point/(delta*.5)).astype('i8');key=hashlib.sha256((':'.join(map(str,cell))).encode()).hexdigest()
            row=dict(key=key,point=point.tolist(),query=q['query'],negative=q.get('negative',False),view=i,pixel=[x,y],quantile=quantile)
            if key not in locations:locations[key]=row
    locations=[locations[k] for k in sorted(locations)[:cfg['surface']['max_locations']]]
    freeze_json(output/'locations.json',locations)
    assets=read(local/'execution_complete.json')['assets'];all_records={}
    for name in assets:
        if name.startswith('seed_'):a=load_asset(cfg['frozen_posteriors'][f"{elig['scene']}_{name[5:]}"]['path'])
        else:a=dict(np.load(root/f"controlled/{elig['scene']}/measurements/native/{name}_parameters.npz"))
        weights=np.load(local/f'layers/{name}/contribution_weights.npz')['weights']
        records=audit_asset(a,weights,locations,delta,cfg);all_records[name]=records
        freeze_json(output/f'surface_{name}.json',_json(records));print('surface',elig['scene'],name,len(records),flush=True)
    from collections import Counter
    buckets=Counter();repeat_rows=[]
    baseline=all_records['seed_1729']
    for i,record in enumerate(baseline):
        per_scale=[]
        for j,a in enumerate(record['scales']):
            comparisons=[]
            for name in assets[1:]:
                b=all_records[name][i]['scales'][j]
                if 'equal_cell' not in a or 'equal_cell' not in b:comparisons.append(dict(asset=name,available=False));continue
                aa,bb=a['equal_cell'],b['equal_cell'];x=np.array(record['location']['point']);na=np.array(aa['normal']);nb=np.array(bb['normal']);nb*=1 if np.dot(na,nb)>=0 else -1
                offset=abs(np.dot(x-np.array(aa['center']),na)-np.dot(x-np.array(bb['center']),nb))
                comparisons.append(dict(asset=name,available=True,normal_angle=float(axial_angle(na,nb)),plane_offset_h=float(offset/a['radius']),other_sheet_local=b['sheet_local'],other_crease_local=b['crease_local']))
            adjacent=[v for k,v in enumerate(record['adjacent_scale_angles']) if k in [j-1,j] and v is not None]
            stable=bool(comparisons and all(r['available'] and r['normal_angle']<=cfg['surface']['normal_p90_max'] and r['plane_offset_h']<=cfg['surface']['p90_h_max'] for r in comparisons) and adjacent and min(adjacent)<=cfg['surface']['normal_p90_max'])
            bucket=('sheet' if a['sheet_local'] and stable and all(r.get('other_sheet_local') for r in comparisons) else 'plausible_crease' if a['crease_local'] and stable and all(r.get('other_crease_local') for r in comparisons) else 'unstable' if a['sheet_local'] or a['crease_local'] else a['bucket'])
            buckets[bucket]+=1;per_scale.append(dict(radius=a['radius'],bucket=bucket,repeatability=comparisons))
        repeat_rows.append(dict(key=record['location']['key'],scales=per_scale))
    freeze_json(output/'surface_summary.json',dict(diagnostic_only=True,locations=len(locations),neighborhoods=len(locations)*3,buckets=dict(buckets),repeats=repeat_rows,never_generator=True))


def main():
    p=argparse.ArgumentParser();p.add_argument('--scene',required=True);p.add_argument('--task',choices=['machine','surface'],required=True);args=p.parse_args()
    root=ROOT/'out/multiscene_foundation_corrected';cfg=verified_json(root/'config.json',(root/'config.json.sha256').read_text().strip());local=root/'local'/args.scene
    if not (local/'execution_complete.json').exists():raise RuntimeError('all local arms must finish')
    elig=read(root/f'scenes/{args.scene}/eligibility.json');delta=elig['delta'];cameras={i:cfg['scenes'][args.scene]['cameras'][f'train_{i:03d}'] for i in cfg['splits']['TRAIN']}
    # No original photograph enters these evaluators. C fields are sealed outputs
    # of the independent C process; surface fitting consumes only approved assets.
    assets=read(local/'execution_complete.json')['assets'];parameters=[]
    for name in assets:
        parameters.append(Path(cfg['frozen_posteriors'][f'{args.scene}_{name[5:]}']['path']) if name.startswith('seed_') else root/f'controlled/{args.scene}/measurements/native/{name}_parameters.npz')
    output=root/f'evaluation/{args.scene}/{args.task}';output.mkdir(parents=True,exist_ok=False)
    sources=[Path(__file__).resolve(),*list((ROOT/'src').glob('*.py'))]
    binaries=[ROOT/'out/multiscene_foundation/setup/layers.so',root/'setup/area_layers.so',root/'setup/surface.so']
    for binary in binaries:ctypes.CDLL(str(binary))
    runtime=[Path(sys.prefix),Path('/usr'),Path('/lib'),Path('/lib64'),Path('/etc'),Path('/proc'),Path('/sys')]
    readonly=[local,*parameters,*sources,*binaries,*[r.resolve() for r in runtime if r.exists()]]
    freeze_json(output/'allowlist.json',dict(scene=args.scene,task=args.task,readonly=[str(x) for x in readonly],writable=[str(output),'/dev'],photo_inputs=[],source_hashes={str(x):sha(x) for x in sources},config_sha256=sha(root/'config.json')))
    restrict_filesystem(readonly,[output,'/dev']);start=time.monotonic()
    if args.task=='machine':machine(output,local,cfg,elig,cameras,delta)
    else:surface(output,local,root,cfg,elig,cameras,delta)
    freeze_json(output/'complete.json',dict(task=args.task,elapsed_seconds=time.monotonic()-start))

if __name__=='__main__':main()
