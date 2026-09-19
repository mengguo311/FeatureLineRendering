"""Stage-confined execution of the preregistered generator and re-estimations."""
import argparse,ctypes,json,os,pathlib,sys,time,datetime
import numpy as np
import cc
from cc_io import write_json,read_json,sha,seal,verify_seal,scene_inputs
from src.foundation import restrict_filesystem
from src.corrected_qualification import reference
from src.corrected_layers import AreaLayers
O=pathlib.Path(__file__).resolve().parents[1];R=O.parents[1];P=R/'out/multiscene_foundation_corrected'
BINARIES=[R/'out/multiscene_foundation/setup/layers.so',P/'setup/area_layers.so']

def stage_plan(cfg,scene,task,asset):
    if scene not in cfg['scene_order'] or not cfg['scenes'][scene]['eligibility']['eligible']:raise ValueError('no eligible scene')
    if asset not in cfg['scenes'][scene]['assets']:raise ValueError('unqualified asset')
    if task not in ['primary','cross','repeat']:raise ValueError('invalid stage')
    if task!='repeat' and asset!='seed_1729':raise ValueError('primary parent fixed')
    split='C' if task=='cross' else 'F';info=scene_inputs(cfg,scene,split)
    if task=='repeat':info['photos']=[]
    info.update(split=split,requires_F_seal=task!='primary',layers={i:str(P/f'local/{scene}/layers/{asset}/view_{i:03d}.npz') for i in cfg['splits'][split]})
    return info

def primary_arm_names(cfg):
    names=['image_only','gs','shifted','shifted_gs','random_graph','random_graph_gs','pairwise','pairwise_gs','no_order','no_order_gs']
    return names+[f'loo_{i:03d}{suffix}' for i in cfg['splits']['F'] for suffix in ['', '_gs']]

def confine(inputs,output):
    runtime=[pathlib.Path(sys.prefix),pathlib.Path('/usr'),pathlib.Path('/lib'),pathlib.Path('/lib64'),pathlib.Path('/etc'),pathlib.Path('/proc'),pathlib.Path('/sys')]
    readonly=[pathlib.Path(p).resolve() for p in inputs]+[p.resolve() for p in runtime if p.exists()]
    restrict_filesystem(readonly,[output,'/dev'])

class LazyLayers:
    def __init__(self,paths):self.paths=paths;self.cache={}
    def __contains__(self,k):return k in self.paths
    def __getitem__(self,k):
        if k not in self.cache:self.cache[k]=AreaLayers.load(self.paths[k])
        return self.cache[k]

def arm(output,name,result,curves,cameras,layers,delta,cfg):
    write_json(output/f'{name}.json.gz',result)
    gs,detail=cc.apply_gs(result['accepted'],cameras,layers,delta,cfg['fit'],cfg['controls']['pairwise_min_views'] if result.get('pairwise') else None)
    gsname='gs' if name=='image_only' else name+'_gs'
    write_json(output/f'{gsname}.json.gz',dict(accepted=gs,support=detail,identity_hypotheses=result['identity_hypotheses'],source_arm=name,rejected_image_fit=len(result['rejected'])))
    print('arm',name,'identities',result['identity_hypotheses'],'image',len(result['accepted']),'gs',len(gs),'rejected',len(result['rejected']),flush=True)
    return {name:len(result['accepted']),gsname:len(gs)}

def run(args):
    cfg=read_json(O/'config.json');assert sha(O/'config.json')==(O/'config.json.sha256').read_text().strip();assert sha(O/'PREREG.md')==cfg['prereg_sha256']
    plan=stage_plan(cfg,args.scene,args.task,args.asset);info=cfg['scenes'][args.scene];delta=info['eligibility']['delta'];box=info['eligibility']['box']
    directory=O/'scenes'/args.scene;output=directory/('F' if args.task=='primary' else 'C' if args.task=='cross' else 'repeats/'+args.asset);output.mkdir(parents=True,exist_ok=False)
    scientific=[*plan['photos'],*plan['layers'].values()];extra=[]
    if plan['requires_F_seal']:
        frozen=read_json(directory/'F/frozen.json')
        if not verify_seal(directory/'F',frozen):raise ValueError('F freeze mismatch')
        if args.task=='repeat':extra=[directory/'F/image_only.json.gz']
    sources=[*list((O/'code').glob('*.py')),*list((R/'src').glob('*.py'))]
    for p in BINARIES:ctypes.CDLL(str(p))
    inventory=read_json(O/'input_hashes.json');expected={p:inventory[p]['sha256'] for p in scientific}
    # Hash every input before decoding; exact paths are in the native audit.
    observed={p:sha(p) for p in scientific}
    if expected!=observed:raise ValueError('inherited input hash mismatch')
    readonly=[*scientific,*extra,*sources,*BINARIES]
    runtime=[str(pathlib.Path(sys.prefix).resolve()),'/usr','/lib','/lib64','/etc','/proc','/sys']
    policy=dict(task=args.task,scene=args.scene,asset=args.asset,split=plan['split'],readonly=[str(pathlib.Path(p).resolve()) for p in readonly]+runtime,writable=[str(output),'/dev'],photo_inputs=plan['photos'],input_hashes=observed,source_hashes={str(p):sha(p) for p in sources},config_sha256=sha(O/'config.json'),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    write_json(output/'allowlist.json',policy);confine(readonly,output);start=time.monotonic();layers=LazyLayers(plan['layers']);cameras=plan['cameras'];counts={}
    if args.task=='repeat':
        primary=read_json(extra[0]);gs,detail=cc.apply_gs(primary['accepted'],cameras,layers,delta,cfg['fit'])
        write_json(output/'gs.json.gz',dict(accepted=gs,support=detail,identity_hypotheses=primary['identity_hypotheses'],source_arm='F/image_only',identity_reused_because_GS_is_veto_only=True))
        counts={'gs':len(gs)};print(args.scene,args.asset,counts,flush=True)
    else:
        curves={};summaries=[]
        for i,c in cameras.items():
            rgb,alpha=reference(c);ex=cc.extract(rgb[1],i,cfg)
            write_json(output/f'extraction_{i:03d}.json.gz',{k:v for k,v in ex.items() if k not in ['edge','field']})
            np.savez_compressed(output/f'field_{i:03d}.npz',**ex['field'])
            for curve in ex['curves']:curves[curve['id']]=curve
            summaries.append(dict(view=i,edge_pixels=int(ex['edge'].sum()),curves=len(ex['curves']),rejected_pieces=len(ex['rejected']),junctions=len(ex['graph']['junctions'])))
            print(args.scene,plan['split'],'extracted',summaries[-1],flush=True)
        write_json(output/'extraction_summary.json',summaries)
        edges,stats=cc.match_all(curves,cameras,box,cfg['matching']);write_json(output/'candidates.json.gz',edges);write_json(output/'candidate_summary.json',stats)
        print(args.scene,plan['split'],'pairs',stats,flush=True)
        primary=cc.reconstruct(curves,cameras,edges,box,delta,cfg);counts.update(arm(output,'image_only',primary,curves,cameras,layers,delta,cfg))
        if args.task=='primary':
            shifted=cc.shift_curves(curves,list(cameras),cfg['controls']);se,ss=cc.match_all(shifted,cameras,box,cfg['matching']);write_json(output/'shifted_candidates.json.gz',se);write_json(output/'shifted_candidate_summary.json',ss)
            counts.update(arm(output,'shifted',cc.reconstruct(shifted,cameras,se,box,delta,cfg),shifted,cameras,layers,delta,cfg))
            re=cc.random_graph([e for e in edges if e['selected']],curves,cfg['controls']['random_seed']);write_json(output/'random_graph_edges.json.gz',re)
            counts.update(arm(output,'random_graph',cc.reconstruct(curves,cameras,re,box,delta,cfg),curves,cameras,layers,delta,cfg))
            counts.update(arm(output,'pairwise',cc.reconstruct(curves,cameras,edges,box,delta,cfg,pairwise=True),curves,cameras,layers,delta,cfg))
            ne,ns=cc.match_all(curves,cameras,box,cfg['matching'],False);write_json(output/'no_order_candidates.json.gz',ne);write_json(output/'no_order_candidate_summary.json',ns)
            counts.update(arm(output,'no_order',cc.reconstruct(curves,cameras,ne,box,delta,cfg,enforce_order=False),curves,cameras,layers,delta,cfg))
            for omitted in cameras:
                selected={v:c for v,c in cameras.items() if v!=omitted};subcurves={k:c for k,c in curves.items() if c['view']!=omitted};subedges=[e for e in edges if e['a'] in subcurves and e['b'] in subcurves]
                counts.update(arm(output,f'loo_{omitted:03d}',cc.reconstruct(subcurves,selected,subedges,box,delta,cfg),subcurves,selected,layers,delta,cfg))
        write_json(output/'curves.json.gz',curves)
    elapsed=time.monotonic()-start
    if elapsed>cfg['budget']['scientific_seconds_per_scene']:raise TimeoutError('scientific stage budget exceeded')
    write_json(output/'complete.json',dict(scene=args.scene,task=args.task,asset=args.asset,counts=counts,elapsed_seconds=elapsed,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    write_json(output/'frozen.json',seal(output));print('SEALED',output,elapsed,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scene',required=True);p.add_argument('--task',required=True);p.add_argument('--asset',default='seed_1729');run(p.parse_args())
