#!/usr/bin/env python3
"""Real fixed-view outputs, failure profiles and a separately keyed review package."""
import argparse,ctypes,hashlib,json,os,sys,time,shutil
from pathlib import Path
import numpy as np,cv2,torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.foundation import freeze_json,verified_json,restrict_filesystem,load_asset,STOCK_SITE,qualification_metrics,project_jacobian
from src.corrected_layers import AreaLayers
from src.corrected_probe import ImageEvidence,edge_field,evaluate_positions,prediction_summary,load_probe,_json
from src.corrected_qualification import reference,calibrated_view
from src.corrected_visuals import glyph_image,spatial_order,ink_prefix,write_png,write_video,orbit_cameras
from src.corrected_review import blind_package
from src.multiscene_qualification import save_grid

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())

def main():
    p=argparse.ArgumentParser();p.add_argument('--scene',required=True);args=p.parse_args()
    root=ROOT/'out/multiscene_foundation_corrected';local=root/'local'/args.scene;cfg=verified_json(root/'config.json',(root/'config.json.sha256').read_text().strip())
    complete=read(local/'execution_complete.json');elig=read(root/f'scenes/{args.scene}/eligibility.json');machine=read(root/f'evaluation/{args.scene}/machine/machine.json');delta=elig['delta']
    output=root/f'evaluation/{args.scene}/visual';output.mkdir(parents=True,exist_ok=False)
    (output/'native').mkdir();(output/'full_resolution').mkdir();(output/'profiles').mkdir();(output/'prediction_rows').mkdir()
    os.environ['MPLCONFIGDIR']=str(output/'.mplconfig')
    import matplotlib
    matplotlib.use('Agg');import matplotlib.pyplot as plt
    upstream=ROOT/'out/multiscene_foundation/vendor/gaussian-splatting';sys.path[:0]=[str(STOCK_SITE),str(upstream)]
    import gaussian_renderer,diff_gaussian_rasterization
    torch.cuda.init()
    parameters={name:Path(cfg['frozen_posteriors'][f'{args.scene}_{name[5:]}']['path']) if name.startswith('seed_') else root/f'controlled/{args.scene}/measurements/native/{name}_parameters.npz' for name in complete['assets']}
    cameras={i:cfg['scenes'][args.scene]['cameras'][f'train_{i:03d}'] for i in cfg['splits']['TRAIN']+cfg['splits']['DEV']}
    photos=[cameras[i]['path'] for i in cfg['splits']['DEV']]
    quality=[root/f'quality/{args.scene}/seed_1729/measurements/native/train_{i:03d}.npz' for i in cfg['splits']['F']]
    sources=[Path(__file__).resolve(),*list((ROOT/'src').glob('*.py'))]
    binaries=[ROOT/'out/point_feature_foundation/setup/composite.so',ROOT/'out/multiscene_foundation/setup/layers.so',root/'setup/area_layers.so']
    for b in binaries:ctypes.CDLL(str(b))
    runtime=[Path(sys.prefix),Path('/home/u00134/bin/miniconda3/envs/ts_diffusion'),Path('/usr'),Path('/lib'),Path('/lib64'),Path('/etc'),Path('/proc'),Path('/sys'),STOCK_SITE,*[upstream/k for k in ['gaussian_renderer','utils','scene']]]
    readonly=[local,*parameters.values(),*photos,*quality,*sources,*binaries,root/'annotations',*[r.resolve() for r in runtime if r.exists()]]
    freeze_json(output/'allowlist.json',dict(scene=args.scene,task='visual',readonly=[str(x) for x in readonly],writable=[str(output),'/dev'],photo_inputs=photos,source_hashes={str(x):sha(x) for x in sources},input_hashes={str(x):sha(x) for x in [*photos,*parameters.values()]},config_sha256=sha(root/'config.json')))
    restrict_filesystem(readonly,[output,'/dev']);start=time.monotonic()
    def asset(name):
        path=parameters[name]
        return load_asset(path) if path.suffix=='.ply' else dict(np.load(path))
    parent=asset('seed_1729');layers={i:AreaLayers.load(local/f'layers/seed_1729/view_{i:03d}.npz') for i in cfg['splits']['F']}
    rgbs={};photo_rgbs={};dev_fields={};dev_base={};dev_calibration=[]
    for i in cfg['splits']['F']:
        with np.load(root/f'quality/{args.scene}/seed_1729/measurements/native/train_{i:03d}.npz') as archive:
            rgbs[i]=archive['rgb_1'];photo_rgbs[i]=archive['gt_1']
    for i in cfg['splits']['DEV']:
        camera=cameras[i];state,rgb,maps,cal=calibrated_view(parent,camera)
        dev_calibration.append(dict(asset='seed_1729',view=i,**cal));layers[i]=AreaLayers(state);layers[i].save(output/f'native/dev_layers_{i:03d}.npz')
        rgbs[i]=rgb[1];dev_base[i]=dict(rgb=rgb,roi=maps['alpha_native']>=.5)
        gt,alpha=reference(camera);photo_rgbs[i]=gt[1];dev_fields[i]=edge_field(gt[1],cfg)
        write_png(output/f'full_resolution/DEV_{i:03d}_reference.png',gt[1]);write_png(output/f'full_resolution/DEV_{i:03d}_stock.png',rgb[1])
    dev_rows=[]
    for name in complete['assets'][1:]:
        a=asset(name)
        for i in cfg['splits']['DEV']:
            state,rgb,maps,cal=calibrated_view(a,cameras[i]);dev_calibration.append(dict(asset=name,view=i,**cal))
            for bg in [0,1]:dev_rows.append(dict(asset=name,view=i,background=bg,**qualification_metrics(dev_base[i]['rgb'][bg],rgb[bg],dev_base[i]['roi'])))
        print('DEV equivalence',args.scene,name,flush=True)
    freeze_json(output/'DEV_render_equivalence.json',dict(rows=dev_rows,calibration=dev_calibration,scope='Post-output-freeze cameras; controlled DEV invariance only where all comparisons pass. Independent seeds are described, not held to synthetic 40dB.'))
    arms={};directories={}
    for group in [local/'F',local/'C',*sorted((local/'repeats').glob('*'))]:
        for d in sorted(group.glob('*')):
            if (d/'accepted.json').exists():
                name=str(d.relative_to(local)).replace('/','__');arms[name]=read(d/'accepted.json');directories[name]=d
    arms['pca']=read(local/'F/pca.json')['accepted'];arms['random']=read(local/'F/random.json')
    fixed=cfg['visuals']['fixed_train']+cfg['visuals']['fixed_dev'];F_cameras=[cameras[i] for i in cfg['splits']['F']]
    pca64=spatial_order(arms['pca'],delta)[:cfg['visuals']['glyph_count']]
    pca_ink=np.mean([glyph_image(pca64,c,delta,layers[c['index']])[1]['ink_area'] for c in F_cameras]);budget=float(pca_ink*cfg['visuals']['ink_fraction'])
    records={};files={};dev_summary={};subsets={}
    dev_evidence=ImageEvidence(cameras,dev_fields,{i:layers[i] for i in cfg['splits']['DEV']},delta,cfg)
    for name,rows in arms.items():
        directory=output/'full_resolution'/name;directory.mkdir();panels=[];files[name]={}
        matched,ink=ink_prefix(rows,F_cameras,delta,budget,cfg,layers);subsets[name]=matched
        selections={'native':rows,'fixed64':spatial_order(rows,delta)[:cfg['visuals']['glyph_count']],'matched_ink':matched}
        record=dict(native_count=len(rows),fixed64_count=len(selections['fixed64']),fixed64_comparable=len(rows)>=64,ink=ink,views=[])
        for i in fixed:
            files[name][i]={}
            for style,selected in selections.items():
                im,stats=glyph_image(selected,cameras[i],delta,layers[i]);path=directory/f'{style}_{i:03d}.png';write_png(path,im);files[name][i][style]=path
                record['views'].append(dict(view=i,style=style,**stats))
                if style=='native':panels.append((f'{i}: native n={len(rows)}',im))
            off,_=glyph_image(rows,cameras[i],delta);write_png(directory/f'occlusion_off_{i:03d}.png',off)
            overlay,_=glyph_image(rows,cameras[i],delta,layers[i],rgbs[i]);write_png(directory/f'RGB_glyphs_{i:03d}.png',overlay)
        save_grid(output/f'{name}_contact.png',[(t,cv2.resize(im,(200,200),interpolation=cv2.INTER_AREA)) for t,im in panels],4)
        dev_actual=float(np.mean([v['ink_area'] for v in record['views'] if v['style']=='matched_ink' and v['view'] in cfg['splits']['DEV']]))
        record['DEV_matched_ink_area']=dev_actual;records[name]=record
        if name in ['F__gs','F__no_gs','pca','random','F__shifted'] or name.endswith('__gs') and name.startswith('repeats'):
            rows_dev=evaluate_positions(rows,dev_evidence);dev_summary[name]=prediction_summary(rows_dev,cfg)
            freeze_json(output/f'prediction_rows/{name}_DEV.json',_json(rows_dev))
        print('glyphs',args.scene,name,len(rows),flush=True)
    pca_dev_budget=records['pca']['DEV_matched_ink_area']
    for record in records.values():
        record['DEV_ink_relative_error_to_PCA']=abs(record['DEV_matched_ink_area']-pca_dev_budget)/pca_dev_budget if pca_dev_budget else None
        record['DEV_ink_comparable']=bool(pca_dev_budget and record['DEV_ink_relative_error_to_PCA']<=cfg['visuals']['ink_tolerance'])
    freeze_json(output/'glyph_metrics.json',records);freeze_json(output/'DEV_detector_prediction.json',dict(rows=dev_summary,manual_precision='PENDING_INDEPENDENT_REVIEW',labels='detector self-consistency only; no independent span precision'))
    # Fixed lowest query hashes, before looking at their outcomes. All profiles are
    # retained in NPZ; these plots are a reproducible finite display sample.
    for name,d in directories.items():
        if name not in ['F__gs','F__no_gs','F__shifted'] and not(name.startswith('repeats') and name.endswith('__gs')):continue
        metadata=read(d/'profiles_metadata.json');profile=np.load(d/'profiles.npz');order=sorted(range(len(metadata)),key=lambda i:str(metadata[i]['query']))[:16]
        fig,axes=plt.subplots(4,4,figsize=(13,9),squeeze=False)
        for ax,i in zip(axes.ravel(),order):
            lo,hi=profile['offsets'][i:i+2];depth=profile['depths'][lo:hi];cost=profile['cost'][lo:hi]
            ax.plot(depth,np.where(np.isfinite(cost),cost,np.nan),lw=.8)
            for m in metadata[i]['modes']:
                if m['cost'] is not None:ax.plot(m['depth'],m['cost'],'.',ms=3,color='darkorange')
            ax.set_ylim(0,6.2);ax.set_title(str(metadata[i]['query'])[:9],fontsize=8);ax.set_xlabel('ray depth');ax.set_ylabel('RMS pixels')
        fig.suptitle(f'{args.scene} {name}: fixed query-hash profiles; all depth modes retained');fig.tight_layout();fig.savefig(output/f'profiles/{name}.png',dpi=120);plt.close(fig)
    baseline=load_probe(local/'F/gs');modes=baseline['modes'];panels=[]
    for i in fixed:
        canvas=np.ones((400,400,3),'u1')*255
        if modes:
            points=np.array([m['point'] for m in modes]);uv,z,_=project_jacobian(points,cameras[i]['K'],cameras[i]['w2c'])
            for m,pixel,zz in zip(modes,uv,z):
                if zz>0 and np.isfinite(pixel).all() and np.all((pixel>=0)&(pixel<400)):
                    color=(0,140,0) if m['accepted'] else (0,140,255) if 'multimodal' in m['reasons'] else (0,0,200)
                    cv2.circle(canvas,tuple(np.rint(pixel).astype(int)),1,color,-1)
        panels.append((f'{i}: green accepted / orange ambiguous / red rejected',canvas[:,:,::-1]/255.))
    save_grid(output/'all_modes_diagnostic.png',panels,4)
    counter=baseline['rejection_reasons'];fig,ax=plt.subplots(figsize=(10,5));ax.barh(list(counter),list(counter.values()));ax.set_xlabel('mode count (reasons overlap)');fig.tight_layout();fig.savefig(output/'failure_buckets.png',dpi=150);plt.close(fig)
    pairs=[];inventory=[]
    for style in ['native','fixed64','matched_ink']:
        for control in ['pca','F__no_gs','F__shifted','random']:
            for i in fixed:
                pairs.append(dict(name=f'{style}_view{i}',group=style+'_'+control,left=files['F__gs'][i][style],right=files[control][i][style]))
                inventory.append(dict(index=len(pairs)-1,style=style,view=i,comparison_status='INCOMPARABLE' if style=='matched_ink' and not(records['F__gs']['ink']['comparable'] and records[control]['ink']['comparable']) else 'COUNTS_INSUFFICIENT' if style=='fixed64' and not(records['F__gs']['fixed64_comparable'] and records[control]['fixed64_comparable']) else 'REVIEWABLE'))
    blind_package(output/'blinded_review',output/'review_identity_key.json',pairs)
    freeze_json(output/'blinded_review/inventory.json',inventory)
    for i in fixed:write_png(output/f'blinded_review/reference_{i:03d}.png',photo_rgbs[i])
    freeze_json(output/'blinded_review/references.json',[dict(view=i,source='frozen photograph; native RGBA composite on white followed by area400',source_sha256=cameras[i]['sha256']) for i in fixed])
    for p in (root/'annotations').glob(f'{args.scene}*'):shutil.copyfile(p,output/'blinded_review'/p.name)
    video_status=dict(reached=machine['video_trigger'],expected_frames=cfg['visuals']['video_frames'],generated=[])
    if machine['video_trigger']:
        target=np.mean(elig['box'],axis=0);radius=float(np.median([np.linalg.norm(np.linalg.inv(cameras[i]['w2c'])[:3,3]-target) for i in cfg['splits']['TRAIN']]))
        orbit=orbit_cameras(target,radius,cameras[cfg['splits']['F'][0]],cfg);freeze_json(output/'orbit.json',orbit)
        names=['F__gs','pca','F__no_gs','F__shifted','random'];frames={n:[] for n in names};(output/'frames').mkdir()
        for i,c in enumerate(orbit):
            state,rgb,maps,cal=calibrated_view(parent,c);layer=AreaLayers(state)
            if not cal['passed']:raise RuntimeError('orbit native calibration failed')
            write_png(output/f'frames/reference_{i:03d}.png',rgb[1])
            for name in names:
                im,_=glyph_image(subsets[name],c,delta,layer);frames[name].append(im);write_png(output/f'frames/{name}_{i:03d}.png',im)
        for name,ims in frames.items():
            path=output/f'{name}.mp4';write_video(path,ims,cfg);video_status['generated'].append(str(path))
            for first in range(0,120,30):save_grid(output/f'{name}_frames_{first:03d}.png',[(str(i),cv2.resize(ims[i],(100,100))) for i in range(first,first+30)],6)
    else:video_status['reason']='Per-scene G1 and G2 machine visual-stage trigger not satisfied; failure PNGs/profile plots remain mandatory and were generated.'
    freeze_json(output/'video_status.json',video_status)
    freeze_json(output/'complete.json',dict(scene=args.scene,arms=len(arms),fixed_views=fixed,manual='PENDING_INDEPENDENT_REVIEW',independent_reviewers=0,elapsed_seconds=time.monotonic()-start))

if __name__=='__main__':main()
