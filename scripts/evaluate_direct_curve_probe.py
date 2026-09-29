"""Complete F/C census and sealed-domain video evidence."""
import json,hashlib,subprocess,time
from pathlib import Path
import numpy as np
import torch
import cv2
from PIL import Image
from src.direct_curve import bezier,project,visibility
from src.direct_curve_eval import evaluate_drawing,disagreement,temporal,scene_gate,motion_defects,stroke_ink,ambiguity_from_pairs
from src.foundation import freeze_json,load_asset
from scripts.run_direct_curve_probe import prepare_view,save_view,sha
from scripts.render_adaptive_g1 import save_npz


def comparison_sheet(rows,labels,size=800):
    tiles=[]
    for row in rows:
        panels=[]
        for image,label in zip(row,labels):
            tile=np.full((size+28,size,3),255,'u1');tile[28:]=cv2.resize(image,(size,size),interpolation=cv2.INTER_AREA)
            cv2.putText(tile,str(label),(8,20),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,0,0),1,cv2.LINE_AA);panels.append(tile)
        tiles.append(np.concatenate(panels,1))
    return np.concatenate(tiles,0)


def video(path,frames):
    h,w=frames[0].shape[:2]
    import imageio_ffmpeg
    cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-nostdin','-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}','-r','12','-i','pipe:0','-an','-c:v','libx264','-threads','1','-preset','fast','-crf','16','-pix_fmt','yuv420p','-movflags','+faststart',str(path)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    for frame in frames:proc.stdin.write(np.ascontiguousarray(frame).tobytes())
    proc.stdin.close();error=proc.stderr.read();proc.stderr.close();code=proc.wait()
    if code:raise RuntimeError(error.decode())


def quick_ink(control,active,camera,maps,diagonal):
    p=torch.tensor(control,dtype=torch.float64);xyz=bezier(p,257)
    uv,z=project(xyz,torch.tensor(camera['native_K'],dtype=p.dtype),torch.tensor(camera['w2c'],dtype=p.dtype))
    v,_,_=visibility(uv,z,torch.tensor(maps.transpose(2,0,1)[None],dtype=p.dtype),diagonal);xy=uv.numpy();v=v.numpy().astype(bool)
    return stroke_ink(xy,v,active)



def read_view(fitdir,index,camera):
    with np.load(fitdir/'native'/f'{index}.npz') as f:
        out={k:f[k] for k in ['rgb','gs_rgb','maps','alpha','depth']}
        out['evidence']={arm:{k:f[arm+'.'+k] for k in ['xy','tangent','sides','native_edge']} for arm in ['D','I']}
    out.update(view=index,camera=camera);return out


def aggregate(rows):
    targets=sum(r['targets'] for r in rows);visible=sum(r['visible_length'] for r in rows);known=sum(r['evaluable_length'] for r in rows);supported=sum(r['supported_length'] for r in rows)
    out=dict(targets=targets,coverage=sum(r['covered'] for r in rows)/max(1,targets),unsupported_fraction=(visible-supported)/visible if visible else None,precision=supported/known if known else None,beyond4_fraction=sum(r['beyond4_length'] for r in rows)/visible if visible else None,actual_ink=sum(r['actual_ink'] for r in rows)/max(1,len(rows)),visible_length=visible,unknown_length=sum(r['unknown_length'] for r in rows),occluded_length=sum(r['occluded_length'] for r in rows),active_curves=rows[0]['active_curves'])
    for s in ['outline','interior','background','foreground']:
        nt=sum(r['strata'][s]['targets'] for r in rows);out[s+'_coverage']=sum(r['strata'][s]['covered'] for r in rows)/nt if nt else None
    return out


def run_evaluation(cfg,scene,fitdir,output):
    started=time.monotonic();seal=json.loads((fitdir/'SEAL.json').read_text());s=cfg['scenes'][scene];diagonal=float(np.linalg.norm(np.diff(s['box'],axis=0)));assets={}
    for key,h in seal['assets'].items():
        assert sha(fitdir/(key+'.npz'))==h
        with np.load(fitdir/(key+'.npz')) as f:assets[key]={k:f[k] for k in ['control','active']}
    for d in ['native','figures','frames','arrays','metrics','videos','ambiguity']:(output/d).mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(20260922);order=list(rng.permutation(['D','I','L','depth2d']));labels=['RGB']+[f'Method {chr(65+i)}' for i in range(4)]
    freeze_json(output/'REVIEW_KEY.json',dict(order=order,seed=20260922,review='internal model review; key not in figures/videos'))
    gs=load_asset(s['checkpoint']['path']);metrics={split:{a:[] for a in ['D','I','L']} for split in ['F','C']};cells={split:{a:[] for a in ['D','I','L']} for split in ['F','C']};Fviews=[];reserved=[];Crows=[]
    def draw(view,key):
        a=assets[key];return evaluate_drawing(a['control'],a['active'],view['camera'],view['maps'],view['evidence']['I'],diagonal)
    def depth_image(view):
        mask=view['evidence']['D']['native_edge'];ink=cv2.dilate(mask.astype('u1'),np.ones((2,2),'u1'));return np.repeat(((1-ink)*255)[:,:,None],3,axis=2)
    def process(view,name,split=None):
        results={a:draw(view,seal['chosen'][a]) for a in ['D','I','L']}
        pictures={a:r['image'] for a,r in results.items()};pictures['depth2d']=depth_image(view)
        row=[np.round(np.clip(view['rgb'],0,1)*255).astype('u1')]+[pictures[a] for a in order]
        for a,r in results.items():
            save_npz(output/'arrays'/f'{name}_{a}.npz',r['arrays']);freeze_json(output/'metrics'/f'{name}_{a}.json',dict(metrics=r['metrics'],cells=r['cells']))
            if split:
                metrics[split][a].append(r['metrics']);cells[split][a].extend([dict(view=view['view'],**c) for c in r['cells']])
        if split=='C':Crows.append(row)
        if split=='C' or split is None:
            # Keep every alternate rendering for ambiguity; sealed geometry only.
            inks={}
            for key,a in assets.items():
                arm=key.split('_')[0]
                inks[key]=results[arm]['arrays']['ink'] if key==seal['chosen'][arm] else quick_ink(a['control'],a['active'],view['camera'],view['maps'],diagonal)
            save_npz(output/'ambiguity'/f'{name}.npz',inks)
            from itertools import combinations
            differences={key:disagreement(ink,inks[seal['chosen'][key.split('_')[0]]]) for key,ink in inks.items()}
            pairs={}
            for arm in ['D','I','L']:
                for first,second in combinations(sorted(k for k in inks if k.startswith(arm+'_')),2):
                    value=differences[second] if first==seal['chosen'][arm] else (differences[first] if second==seal['chosen'][arm] else disagreement(inks[first],inks[second]))
                    pairs[first+'|'+second]=value
            reserved.append(dict(frame=name,disagreements=differences,pairwise_disagreements=pairs))
        return row,results
    for split in ['F','C']:
        for index in cfg[split]:
            camera=s['cameras'][str(index)]
            if split=='F' and (fitdir/'native'/f'{index}.npz').exists():v=read_view(fitdir,index,camera)
            else:v=prepare_view(gs,camera,index,camera['path']);save_view(output/'native',v)
            if split=='F':Fviews.append(v)
            name=f'{split}_{index}';row,_=process(v,name,split)
            Image.fromarray(comparison_sheet([row],labels)).save(output/'figures'/f'{name}.png')
            print('EVALUATED',scene,name,flush=True)
    Image.fromarray(comparison_sheet(Crows,labels)).save(output/'figures'/'C_COMPLETE.png')
    arc_results=[]
    for arc_index,arc in enumerate(s['arcs']):
        rows=[];frames=[];states={a:[] for a in ['D','I','L']};summary=[];previous=None;motion={a:[] for a in ['D','I','L','depth2d']}
        for index,camera in enumerate(arc['frames']):
            name=f'arc{arc_index}_{index:03d}';v=prepare_view(gs,camera,name,None);save_view(output/'native',v)
            row,results=process(v,name);rows.append(row);frame=comparison_sheet([row],[f'{x} | arc{arc_index} frame{index}' for x in labels]);frames.append(frame)
            Image.fromarray(frame).save(output/'frames'/f'{name}.png')
            for a,r in results.items():states[a].append(r['arrays'])
            current_inks={a:r['arrays']['ink'] for a,r in results.items()};current_inks['depth2d']=1-depth_image(v)[:,:,0].astype('f4')/255
            if previous is not None:
                pv,pi=previous
                for a in motion:motion[a].append(motion_defects(pi[a],current_inks[a],pv['maps'],pv['camera'],camera))
            previous=(v,current_inks)
            summary.append({a:r['metrics'] for a,r in results.items()})
            print('ARC_FRAME',scene,name,flush=True)
        video(output/'videos'/f'arc{arc_index}_complete.mp4',frames)
        quartiles=np.unique(np.rint(np.linspace(0,len(rows)-1,5)).astype(int));Image.fromarray(comparison_sheet([rows[i] for i in quartiles],labels)).save(output/'figures'/f'arc{arc_index}_quartiles.png')
        # All frames retained in six-frame pages; no successful-frame selection.
        for page,start in enumerate(range(0,len(rows),6)):
            Image.fromarray(comparison_sheet(rows[start:start+6],labels,400)).save(output/'figures'/f'arc{arc_index}_allframes_{page}.png')
        temporal_rows={a:temporal(v) for a,v in states.items()}
        arc_results.append(dict(arc=arc_index,endpoints=arc['endpoints'],frames=len(rows),temporal=temporal_rows,motion_defects=motion,frame_metrics=summary))
        del rows,frames,states
    arm_summary={a:aggregate(metrics['C'][a]) for a in ['D','I','L']}
    for a in ['D','I','L']:
        nonempty=[c['strata']['interior'] for c in cells['C'][a] if c['strata']['interior']['targets']]
        arm_summary[a]['equal_cell_interior_coverage']=float(np.mean([r['coverage'] for r in nonempty])) if nonempty else None
        arm_summary[a]['equal_cell_coverage']=float(np.mean([c['coverage'] for c in cells['C'][a] if c['targets']])) if any(c['targets'] for c in cells['C'][a]) else None
    pairs=[(i['strata']['interior'],d['strata']['interior']) for i,d in zip(cells['C']['I'],cells['C']['D']) if i['strata']['interior']['targets']]
    arm_summary['I']['improved_cell_fraction']=sum(i['coverage']>d['coverage'] for i,d in pairs)/len(pairs) if pairs else 0.
    # Three-start ambiguity: data residual only, never regularization-induced uniqueness.
    ambiguity={}
    for a in ['D','I','L']:
        keys=[k for k in assets if k.startswith(a+'_full_')]
        # LOO final residuals remain explicit; compare only same 7-view objective.
        loo=[k for k in assets if k.startswith(a+'_loo93_')];common=None
        if loo:
            from scripts.run_direct_curve_probe import tensor_data
            from src.direct_curve import view_loss
            primary=assets[seal['chosen'][a]];device='cuda' if torch.cuda.is_available() else 'cpu';vals=[]
            with torch.no_grad():
                for v in Fviews:
                    if v['view']==93:continue
                    d={k:(x.to(device) if torch.is_tensor(x) else x) for k,x in tensor_data(v,a).items()}
                    val=view_loss(torch.tensor(primary['control'],device=device),torch.tensor(primary['active'].astype('f4'),device=device),d,a,2.,diagonal);vals.append(float(val['data']))
            common=float(np.mean(vals))
        pairs={k:max(r['pairwise_disagreements'][k] for r in reserved) for k in reserved[0]['pairwise_disagreements']} if reserved else {}
        ambiguity[a]=ambiguity_from_pairs({k:seal['objective_components'][k]['data'] for k in keys},seal['chosen'][a],{k:seal['objective_components'][k]['data'] for k in loo},common,pairs)
    elapsed=time.monotonic()-started;budget=elapsed+seal['elapsed_seconds']<=43200
    gates=scene_gate(arm_summary,ambiguity['I']['failed'],False,budget)
    result=dict(scene=scene,arms=arm_summary,F={a:aggregate(metrics['F'][a]) for a in ['D','I','L']},gates=gates,ambiguity=ambiguity,arcs=arc_results,census_cells_per_arm=64*(len(cfg['F'])+len(cfg['C'])),elapsed_seconds=elapsed,fit_seconds=seal['elapsed_seconds'],visual_review='PENDING_INTERNAL_REVIEW',scientific_verdict='NECESSARY_NUMERIC_NO_GO' if not all(gates[k] for k in ['precision','retain_depth','extra_rgb','global_coupling','unambiguous']) else 'VISUAL_REVIEW_REQUIRED',domain='F/C TRAIN + frozen GS interpolation arcs; no unseen real imagery')
    freeze_json(output/'RESULTS.json',result);freeze_json(output/'CENSUS.json',cells);freeze_json(output/'AMBIGUITY_FRAMES.json',reserved)
    assert all(sha(fitdir/(k+'.npz'))==h for k,h in seal['assets'].items())
    print('EVALUATION_COMPLETE',scene,flush=True)
