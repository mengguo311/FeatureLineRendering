#!/usr/bin/env python3
"""Confined F/C fitting stages for frozen eligible scenes. No evaluator labels."""
import argparse,ctypes,hashlib,json,sys,time
from pathlib import Path
import numpy as np,cv2
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.foundation import freeze_json,verified_json,restrict_filesystem,load_asset
from src.corrected_qualification import reference
from src.corrected_layers import AreaLayers
from src.corrected_probe import (ImageEvidence,edge_field,sample_queries,shift_field,pca_control,random_control,evaluate_positions,_json,load_probe)
from src.corrected_execution import run_inference_arm,run_parallel_arms
from src.corrected_surface import contribution_weights

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--scene',required=True);p.add_argument('--asset',default='seed_1729');p.add_argument('--task',choices=['layers','primary','repeat','cross'],required=True);args=p.parse_args()
    root=ROOT/'out/multiscene_foundation_corrected';cfg=verified_json(root/'config.json',(root/'config.json.sha256').read_text().strip())
    prerequisites=verified_json(root/f'scenes/{args.scene}/eligibility.json',(root/f'scenes/{args.scene}/eligibility.json.sha256').read_text().strip())
    if not prerequisites['eligible']:raise ValueError('no eligible route')
    assets=['seed_1729']+(['seed_2718'] if prerequisites['route_a'] else [])+(prerequisites['qualified_doses'] if prerequisites['route_b'] else [])
    if args.asset not in assets:raise ValueError('asset outside eligible routes')
    local=root/'local'/args.scene;split='C' if args.task=='cross' else 'F';views=cfg['splits']['TRAIN'] if args.task=='layers' else cfg['splits'][split]
    cameras={i:cfg['scenes'][args.scene]['cameras'][f'train_{i:03d}'] for i in cfg['splits']['TRAIN']}
    if args.asset.startswith('seed_'):
        seed=int(args.asset[5:]);parameter_path=Path(cfg['frozen_posteriors'][f'{args.scene}_{seed}']['path'])
        parameter_sha=cfg['frozen_posteriors'][f'{args.scene}_{seed}']['sha256']
        states={i:root/f'quality/{args.scene}/{args.asset}/measurements/native/state_{i:03d}.npz' for i in views}
    else:
        parameter_path=root/f'controlled/{args.scene}/measurements/native/{args.asset}_parameters.npz';parameter_sha=sha(parameter_path)
        states={i:root/f'controlled/{args.scene}/measurements/native/{args.asset}_{i:03d}.npz' for i in views}
    layerpaths={i:local/f'layers/{args.asset}/view_{i:03d}.npz' for i in views}
    output=local/(f'layers/{args.asset}' if args.task=='layers' else ('F' if args.task=='primary' else 'C' if args.task=='cross' else f'repeats/{args.asset}'))
    output.mkdir(parents=True,exist_ok=False)
    querypath=local/'F/queries.json'
    query_data=None
    if args.task in ['cross','repeat']:
        # Only the query geometry artifact is read. No F mode, loss, direction,
        # depth initialization, or acceptance reaches the C generator.
        freeze=verified_json(local/'F/frozen.json',(local/'F/frozen.json.sha256').read_text().strip())
        query_data=verified_json(querypath,freeze['queries_sha256'])
    photos=[] if args.task=='layers' else [cameras[i]['path'] for i in views]
    inputs=[parameter_path,*states.values()] if args.task=='layers' else [parameter_path,*layerpaths.values(),*photos]
    if args.task in ['cross','repeat']:inputs+=[querypath]
    sources=[Path(__file__).resolve(),*list((ROOT/'src').glob('*.py'))]
    binaries=[ROOT/'out/multiscene_foundation/setup/layers.so',root/'setup/area_layers.so',root/'setup/surface.so']
    for binary in binaries:ctypes.CDLL(str(binary))
    runtime=[Path(sys.prefix),Path('/usr'),Path('/lib'),Path('/lib64'),Path('/etc'),Path('/proc'),Path('/sys')]
    readonly=[*inputs,*sources,*binaries,*[r.resolve() for r in runtime if r.exists()]]
    allow=dict(scene=args.scene,asset=args.asset,task=args.task,split=split,readonly=[str(x) for x in readonly],writable=[str(output),'/dev'],photo_inputs=photos,input_hashes={str(x):sha(x) for x in inputs},source_hashes={str(x):sha(x) for x in sources},config_sha256=sha(root/'config.json'))
    freeze_json(output/'allowlist.json',allow);restrict_filesystem(readonly,[output,'/dev'])
    if sha(parameter_path)!=parameter_sha:raise ValueError('asset hash mismatch')
    asset=load_asset(parameter_path) if parameter_path.suffix=='.ply' else dict(np.load(parameter_path))
    delta,box=prerequisites['delta'],prerequisites['box'];start=time.monotonic()
    if args.task=='layers':
        weights=np.zeros(len(asset['mu']));cal=[]
        for i in views:
            with np.load(states[i]) as archive:state=dict(archive)
            layer=AreaLayers(state);layer.save(output/f'view_{i:03d}.npz')
            from src.corrected_sampling import area_downsample
            error=float(np.max(abs(layer.alpha()-area_downsample(1-state['final_T']))))
            if error>cfg['native']['calibration_max']:raise RuntimeError('area mass calibration failed')
            cal.append(dict(view=i,max_alpha_error=error))
            if i in cfg['splits']['F']:weights+=contribution_weights(state)*.25
            print('layers',args.asset,i,len(layer.depth),error,flush=True)
            del layer,state
        np.savez_compressed(output/'contribution_weights.npz',weights=weights)
        freeze_json(output/'complete.json',dict(asset=args.asset,calibration=cal,elapsed_seconds=time.monotonic()-start))
        return
    fields={};foreground={}
    for i in views:
        rgb,alpha=reference(cameras[i]);fields[i]=edge_field(rgb[1],cfg);foreground[i]=alpha>=cfg['native']['alpha_roi']
        np.savez_compressed(output/f'field_{i:03d}.npz',**fields[i])
    layers={i:AreaLayers.load(layerpaths[i]) for i in views}
    native_queries=[q for i in cfg['queries']['exchange' if split=='C' else 'primary'] for q in sample_queries(fields[i],i,cfg)]
    queries=query_data if query_data is not None else native_queries
    freeze_json(output/'queries.json',queries)
    jobs=[]
    def add(name,selected_fields=fields,selected_layers=layers,q=queries):
        jobs.append(dict(name=name,queries=q,fields=selected_fields,layers=selected_layers))
    add('gs')
    if args.task in ['primary','cross']:add('no_gs',selected_layers=None)
    if args.task=='primary':
        negatives=[q for i in cfg['queries']['primary'] for q in sample_queries(fields[i],i,cfg,negative=True,foreground=foreground[i])]
        freeze_json(output/'background_queries.json',negatives)
        shifted={i:shift_field(fields[i],j,cfg) for j,i in enumerate(views)}
        add('shifted',selected_fields=shifted);add('shifted_no_gs',selected_fields=shifted,selected_layers=None)
        for arm,use_layers in [('gs',layers),('no_gs',None)]:
            for omitted in views:
                selected={i:fields[i] for i in views if i!=omitted}
                selected_depth={i:layers[i] for i in selected} if use_layers is not None else None
                add(f'{arm}_loo_{omitted:03d}',selected,selected_depth)
    if args.task=='cross':
        freeze_json(output/'native_queries.json',native_queries)
        add('gs_native_queries',q=native_queries);add('no_gs_native_queries',selected_layers=None,q=native_queries)
    for dx,dy in cfg['probe']['detector_offsets'][1:]:
        offset_queries=[dict(q,pixel=[q['pixel'][0]+dx,q['pixel'][1]+dy]) for q in queries]
        add(f'gs_offset_{dx}_{dy}',q=offset_queries)
        if args.task in ['primary','cross']:add(f'no_gs_offset_{dx}_{dy}',selected_layers=None,q=offset_queries)
    run_parallel_arms(output,jobs,cameras,box,delta,cfg,split,workers=4)
    if args.task=='primary':
        main_result=load_probe(output/'gs');no_gs=load_probe(output/'no_gs')
        evidence=ImageEvidence(cameras,fields,layers,delta,cfg)
        pca=pca_control(asset,evidence,cfg);freeze_json(output/'pca.json',_json(pca))
        random=random_control(main_result['accepted'],cfg);freeze_json(output/'random.json',random)
        freeze_json(output/'F_predictions.json',_json({name:evaluate_positions(rows,evidence) for name,rows in [('gs',main_result['accepted']),('random',random),('no_gs',no_gs['accepted'])]}))
    frozen=dict(queries_sha256=sha(output/'queries.json'),artifacts={str(f.relative_to(output)):sha(f) for f in sorted(output.rglob('*')) if f.is_file()},elapsed_seconds=time.monotonic()-start,asset=args.asset,split=split)
    freeze_json(output/'frozen.json',frozen)

if __name__=='__main__':main()
