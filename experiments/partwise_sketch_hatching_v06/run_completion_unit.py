"""Unit004: only original-GS paper support is changed; all ink alpha is frozen."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,output_guard,sha,js,now
from pathlib import Path
import argparse
import json
import shutil
import time
import numpy as np
from geometry import mesh_data
from render import render as render_ink
from membership import load_binding
from hybrid import paper_copy,edit_metrics,region_strength
from appearance_completion import RegionFootprintRenderer,completion_selection,categories,apply_fixed_ink,paper_residual,THRESHOLDS
from link_renderer import Renderer,validate_trace
from run_hybrid import read_npz,png,panel,array_hashes
import base_model as base

HERE=Path(__file__).resolve().parent
ROOT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units')
U1=ROOT/'unit_001';U2=ROOT/'unit_002';U3=ROOT/'unit_003'
OLD=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_005')


def fresh(path):
    path=output_guard(path);path.mkdir(parents=True,exist_ok=False);return path


def freeze():
    if (UNIT/'PROTOCOL.json').exists():raise FileExistsError('already frozen')
    d=json.loads((UNIT/'DECISION.json').read_text());assert d['action']=='continue'
    previous=json.loads((U3/'PROTOCOL.json').read_text());scene=previous['scene']
    old=json.loads((OLD/'PROTOCOL.json').read_text())['scenes']['lego'];asset=Path(scene['asset'])
    cpp=OLD/'source_snapshot/source_ewa_footprint.cpp'
    files=[UNIT/'DECISION.json',U3/'PROTOCOL.json',U3/'REPORT_ZH.md',U3/'STATUS.json',OLD/'PROTOCOL.json',
           Path(scene['source']['original_ply']),Path(scene['binding']),cpp,
           asset/'mesh.npz',asset/'region_4.npz',asset/'asset.json',
           U1/'results/lego/SELECTION.npz',U1/'results/lego/BINDING_LOCK.json']
    builds=[]
    for i,e in enumerate(old['evidence_sources']):
        c=e['camera'];item=dict(index=i,camera=c,old_source_cache=e['baseline'],role=e['role'])
        files.append(Path(e['baseline']))
        if i<4:
            cache=U3/'build'/c['view']/'FRAME.npz';files.append(cache);item['legacy_cache']=str(cache)
        builds.append(item)
    views=[]
    for v in previous['views']:
        if v['kind']=='build':continue
        folder=U3/v['kind']/v['camera']['view'];files += [folder/'FRAME.npz',folder/'EVALUATION.json']
        views.append(dict(kind=v['kind'],camera=v['camera'],cache=str(folder/'FRAME.npz'),metadata=str(folder/'EVALUATION.json')))
    hashes={str(f):sha(f) for f in files}
    assert hashes[scene['source']['original_ply']]==scene['source']['sha256']
    assert sha(HERE/'source_ewa_region_footprint.cpp')==hashes[str(cpp)]
    for f in (asset/'mesh.npz',asset/'region_4.npz',asset/'asset.json',Path(scene['binding'])):
        assert hashes[str(f)]==previous['input_hashes'][str(f)]
    snap=UNIT/'source_snapshot';shutil.copytree(HERE,snap,ignore=shutil.ignore_patterns('__pycache__'))
    p=dict(unit='unit_004',frozen_utc=now(),decision_sha256=hashes[str(UNIT/'DECISION.json')],scene=scene,
        build_views=builds,views=views,thresholds=THRESHOLDS,
        question='Can BUILD full-footprint appearance permissions for UNKNOWN original rows materially remove residual photo texture without far damage?',
        changed_variable=d['changed_variable'],appearance_permission='Original selected q remains fixed. Add strength1 only to UNKNOWN, nonconflicting rows passing frozen region footprint gates. Labels/UNKNOWN/depth evidence unchanged.',
        footprint='All accepted alpha*T over every native pixel; target=unchanged author region4, boundary=2px scipy binary dilation outside target, far=remaining image. Proxy regions sampled from existing 2x renderer. Fifth depth-accepted channel is diagnostic only, never selection input.',
        matching='Four original BUILD views only; global full-source raw RGB L1 budget=.85*minimum natural effect. Both natural-strength outputs retained. Every matched paper is actually rerendered. No DEV tuning.',
        ink='Exact unit003 legacy_raw_alpha and support retained, including in matched-paper arms. Ink opacity/paths/width/visibility are not refit; visible ink RGB contrast may change with paper and is reported.',
        screen=dict(interior_paper_residual_reduction=.20,required_dev_views=3,weak_view_required='orbit_241_24_5.3',far_fraction_reference=.02,visual_review_required=True),
        promotion='Requires visible whole-object texture reduction and acceptable off-target effects; count, white-pixel or L1 improvement alone is insufficient.',
        provenance=dict(footprint_cpp_source=str(cpp),sha256=hashes[str(cpp)],copy='byte-identical C++ accumulator; v06-only Python adapter and runtime'),
        scope='Exposed DEV and short arc only; author proxy intent is not semantic/physical GT. CPU original-GS paper plus fixed original-ID-linked proxy ink, not native Gaussian hatching or H1/H2/H3.',
        source_invariants='Original PLY,310475 row identities/order,geometry,covariance,opacity,SH unchanged. New render-time evaluated full-SH3 colors only.',
        inherited_negatives='v05 sparse far8.044%/region visible4.49%; unit001 gate negative; unit002 layer negative; unit003 minor support/no whole-object quality gain; old143/UNKNOWN and quota logs unchanged.',
        input_hashes=hashes,source_hashes={f.name:sha(f) for f in snap.iterdir() if f.is_file()},
        paper=[.95,.95,.95],ink_color=.03,supersample=2,fps=4,
        resources=dict(serial=True,CPU_affinity=2,numeric_threads=1,GPU=False),
        deadline_jst='2026-10-23T19:12:25+09:00')
    js(UNIT/'PROTOCOL.json',p);js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json'),utc=now()))
    js(UNIT/'STATUS.json',dict(execution_state='partial',stage='frozen_before_BUILD',scientific_verdict='pending',gaussian_link_progress='Protocol frozen; no evaluation yet.',scientific_seal=False,blockers=[]))
    print('FROZEN',sha(UNIT/'PROTOCOL.json'),len(hashes),'inputs',flush=True)


def protocol():
    p=json.loads((UNIT/'PROTOCOL.json').read_text())
    assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    assert sha(UNIT/'DECISION.json')==p['decision_sha256']
    for name,h in p['source_hashes'].items():assert sha(HERE/name)==h,name
    return p


def locked(p,path):
    path=Path(path);assert sha(path)==p['input_hashes'][str(path)],str(path);return path


def load_scene(p,with_mesh=False):
    s=p['scene'];a=base.load_source(locked(p,s['source']['original_ply']),s['source']['sha256'])
    n=len(a['means']);assert n==310475;a['source_index']=np.arange(n,dtype=np.int64)
    b,_=load_binding(locked(p,s['binding']),s['source']['sha256'],n)
    if not with_mesh:return a,b
    asset=Path(s['asset']);m=read_npz(locked(p,asset/'mesh.npz'));mesh=mesh_data(m['vertices'],m['faces'],m['face_regions'])
    paths=read_npz(locked(p,asset/'region_4.npz'));meta=json.loads(locked(p,asset/'asset.json').read_text())
    np.testing.assert_allclose(np.einsum('nij,njk->nik',paths['bary'],mesh['tri'][paths['face']]),paths['points'],atol=1e-9,rtol=0)
    return a,b,mesh,paths,meta


def get_cache(p,v):
    metadata=json.loads(locked(p,v['metadata']).read_text());c=v['camera']
    for k in ('extrinsic','width','height','fx','fy','cx','cy'):np.testing.assert_array_equal(c[k],metadata['camera'][k])
    a=read_npz(locked(p,v['cache']))
    np.testing.assert_array_equal(apply_fixed_ink(a['paper'],a['legacy_raw_alpha']),a['legacy_raw'])
    return a


def footprint(index):
    p=protocol();v=p['build_views'][index];c=v['camera'];folder=fresh(UNIT/'footprints'/c['view'])
    a,b,mesh,paths,meta=load_scene(p,True);before=array_hashes(a)
    h=render_ink(mesh,{4:paths},meta['styles'],c,2,meta.get('display'));cat=categories(h['regions'])
    prior=read_npz(locked(p,v['old_source_cache']))
    valid=np.isfinite(h['depth'])&(prior['alpha']>=.5)&(np.abs(h['depth']-prior['median_camera_z'])<=.08)
    r=RegionFootprintRenderer(UNIT/'build');frame,_,mass=r.footprint(a,c,cat,h['depth'],valid)
    np.testing.assert_array_equal(frame['rgb'],prior['rgb']);np.testing.assert_array_equal(frame['alpha'],prior['alpha'])
    np.testing.assert_allclose(mass[:,1:4].sum(1),mass[:,0],rtol=1e-12,atol=1e-10)
    assert abs(mass[:,0].sum()-frame['alpha'].sum(dtype=float))<.001
    if 'legacy_cache' in v:
        cache=read_npz(locked(p,v['legacy_cache']))
        np.testing.assert_array_equal(cache['regions'],h['regions']);np.testing.assert_array_equal(cache['source'],frame['rgb'])
    np.savez_compressed(folder/'FOOTPRINT.npz',source_index=a['source_index'],mass=mass,source=frame['rgb'],alpha=frame['alpha'],
                        regions=h['regions'],proxy_depth=h['depth'],category=cat,proxy_depth_eligibility=valid)
    assert before==array_hashes(a)
    js(folder/'COMPLETED.json',dict(camera=c,original_array_hashes=before,source_exact=True,alpha_exact=True,
        total_mass=float(mass[:,0].sum()),target_pixels=int((cat==0).sum()),files={'FOOTPRINT.npz':sha(folder/'FOOTPRINT.npz')}))
    print('FOOTPRINT',index,c['view'],'pixels',int((cat==0).sum()),'mass',float(mass[:,0].sum()),flush=True)


def select():
    p=protocol();s=p['scene'];b,_=load_binding(locked(p,s['binding']),s['source']['sha256'],310475)
    blocks=[];locks={}
    for v in p['build_views']:
        folder=UNIT/'footprints'/v['camera']['view'];meta=json.loads((folder/'COMPLETED.json').read_text())
        f=folder/'FOOTPRINT.npz';assert sha(f)==meta['files']['FOOTPRINT.npz']
        a=read_npz(f);np.testing.assert_array_equal(a['source_index'],b['source_index']);blocks.append(a['mass'])
        locks[str(f.relative_to(UNIT))]=sha(f);locks[str((folder/'COMPLETED.json').relative_to(UNIT))]=sha(folder/'COMPLETED.json')
    per_view=np.stack(blocks);result=completion_selection(per_view,b)
    old=read_npz(locked(p,U1/'results/lego/SELECTION.npz'))
    np.testing.assert_array_equal(result['original_strength'],old['primary'])
    assert int((result['original_strength']>0).sum())==20122
    np.savez_compressed(UNIT/'SELECTION.npz',**result,per_view_mass=per_view)
    added=result['appearance_completion_strength']>0
    summary=dict(utc=now(),original_selected=20122,added_original_rows=int(added.sum()),
        final_selected=int((result['completed_strength']>0).sum()),M1_unknown_unchanged=int(b['unknown'].sum()),
        added_by_M1_reason={str(k):int(((b['reason']==k)&added).sum()) for k in np.unique(b['reason'])},
        gate_individual_pass_counts=result['eligibility_gates'].sum(0).tolist(),
        gate_order=['UNKNOWN_and_no_conflict','target_mass','target_views','target_fraction','far_fraction','worst_far_fraction'],
        thresholds=p['thresholds'],scope='Appearance permission only; no row relabeled and depth rejection retained.')
    js(UNIT/'SELECTION.json',summary)
    locks.update({f:sha(UNIT/f) for f in ('SELECTION.npz','SELECTION.json')});js(UNIT/'SELECTION_LOCK.json',dict(files=locks))
    print('SELECT',summary,flush=True)


def selection():
    lock=json.loads((UNIT/'SELECTION_LOCK.json').read_text())
    for name in ('SELECTION.npz','SELECTION.json'):assert sha(UNIT/name)==lock['files'][name]
    return read_npz(UNIT/'SELECTION.npz')


def budget():
    p=protocol();sel=selection();a,b=load_scene(p);before=array_hashes(a);r=Renderer(UNIT/'build')
    out=fresh(UNIT/'budget');totals=dict(original=0.,completed=0.);records=[]
    for v in p['build_views'][:4]:
        c=v['camera'];cache=read_npz(locked(p,v['legacy_cache']));folder=fresh(out/c['view']);arrays=dict(source=cache['source'],regions=cache['regions'])
        row=dict(view=c['view'])
        for arm in totals:
            frame,_=r.render(paper_copy(a,c,sel[arm+'_strength'],p['paper']),c)
            arrays[arm+'_paper']=frame['rgb']
            if arm=='original':np.testing.assert_array_equal(frame['rgb'],cache['paper'])
            value=float(np.abs(frame['rgb']-cache['source']).sum(dtype=float));totals[arm]+=value;row[arm]=value
        np.savez_compressed(folder/'NATURAL.npz',**arrays);records.append(row)
    common=.85*min(totals.values());assert common>0;scales={arm:common/value for arm,value in totals.items()};checks={k:0. for k in totals}
    for v in p['build_views'][:4]:
        c=v['camera'];folder=out/c['view'];cache=read_npz(folder/'NATURAL.npz');arrays={}
        for arm in totals:
            frame,_=r.render(paper_copy(a,c,sel[arm+'_strength']*scales[arm],p['paper']),c)
            arrays[arm+'_paper']=frame['rgb'];checks[arm]+=float(np.abs(frame['rgb']-cache['source']).sum(dtype=float))
        np.savez_compressed(folder/'MATCHED.npz',**arrays)
    assert max(abs(v-common)/common for v in checks.values())<1e-5
    assert before==array_hashes(a)
    js(UNIT/'BUILD_MATCH.json',dict(records=records,natural_source_RGB_L1=totals,budget=common,scales=scales,actual_matched_RGB_L1=checks,original_array_hashes=before))
    js(UNIT/'BUILD_LOCK.json',dict(files={str(f.relative_to(UNIT)):sha(f) for f in list(out.rglob('*.npz'))+[UNIT/'BUILD_MATCH.json']}))
    print('MATCH',totals,scales,checks,flush=True)


def match():
    lock=json.loads((UNIT/'BUILD_LOCK.json').read_text())
    assert sha(UNIT/'BUILD_MATCH.json')==lock['files']['BUILD_MATCH.json']
    return json.loads((UNIT/'BUILD_MATCH.json').read_text())


def reconstruct_trace(a,c,trace,xy,strength,color):
    sid=trace['sample_index'];ids=trace['source_index'];w=trace['weight'];n=len(xy)
    col=base.source_colors(a,c);ss=strength[ids];override=col[ids]*(1-ss[:,None])+np.asarray(color)*ss[:,None]
    rgb=np.repeat((1-np.bincount(sid,w,minlength=n))[:,None],3,axis=1)
    for j in range(3):rgb[:,j]+=np.bincount(sid,w*override[:,j],minlength=n)
    return rgb


def evaluate(kind,index):
    p=protocol();m=match();sel=selection();v=[v for v in p['views'] if v['kind']==kind][index];c=v['camera'];cache=get_cache(p,v)
    folder=fresh(UNIT/kind/c['view']);a,b=load_scene(p);before=array_hashes(a);r=Renderer(UNIT/'build')
    yy,xx=np.mgrid[:c['height'],:c['width']];sample=(cache['regions']==4)|((xx%7==1)&(yy%7==1));xy=np.column_stack([xx[sample],yy[sample]])
    original,trace=r.render(a,c,xy,sel['appearance_completion_strength'])
    np.testing.assert_array_equal(original['rgb'],cache['source']);tc=validate_trace(a,c,xy,original,trace)
    regions=cache['regions'];fixed=cache['legacy_raw_alpha'];images=dict(source=cache['source'],intent=cache['intent'],original_paper=cache['paper'])
    metrics={};residual={};trace_errors={};ink_effect={}
    for arm in ('original','completed'):
        for mode in ('natural','matched'):
            key=arm if mode=='natural' else arm+'_matched';strength=sel[arm+'_strength']*(1 if mode=='natural' else m['scales'][arm])
            if key=='original':paper=cache['paper']
            else:
                rendered,_=r.render(paper_copy(a,c,strength,p['paper']),c);paper=rendered['rgb']
                np.testing.assert_array_equal(rendered['alpha'],original['alpha'])
            recon=reconstruct_trace(a,c,trace,xy,strength,p['paper']);error=float(np.abs(recon-paper[xy[:,1],xy[:,0]]).max());assert error<1e-6
            trace_errors[key]=error;images[key+'_paper']=paper;hybrid=apply_fixed_ink(paper,fixed);images[key+'_hybrid']=hybrid
            metrics[key+'_paper']=edit_metrics(images['source'],paper,regions);metrics[key+'_hybrid']=edit_metrics(images['source'],hybrid,regions)
            residual[key]=paper_residual(paper,regions,p['paper'])
            ink_effect[key]=dict(target_visible_RGB_L1=float(np.abs(hybrid-paper)[regions==4].sum(dtype=float)),
                                 total_visible_RGB_L1=float(np.abs(hybrid-paper).sum(dtype=float)))
    np.testing.assert_array_equal(images['original_hybrid'],cache['legacy_raw'])
    reductions={}
    for mode,suffix in [('natural',''),('matched','_matched')]:
        reductions[mode]={}
        for area in ('target_full','target_interior'):
            old=residual['original'+suffix][area]['clipped_L1_sum'];new=residual['completed'+suffix][area]['clipped_L1_sum']
            reductions[mode][area]=float(1-new/max(old,1e-30))
    target=regions==4;added=original['contribution'];support=cache['support'];combined=support+added
    np.savez_compressed(folder/'FRAME.npz',**images,regions=regions,alpha=original['alpha'],fixed_ink_alpha=fixed,
                        support=support,added_support=added,completed_support=combined)
    np.savez_compressed(folder/'TRACE.npz',**trace,xy=xy)
    assert before==array_hashes(a)==m['original_array_hashes']
    e=dict(camera=c,metrics=metrics,paper_residual=residual,residual_reduction=reductions,ink_effect=ink_effect,
           support=dict(original_target_mean=float(support[target].mean()),added_target_mean=float(added[target].mean()),
                        completed_target_mean=float(combined[target].mean()),target_pixels=int(target.sum()),
                        added_mass=float(added[target].sum(dtype=float)),M1_unknown_count=int(b['unknown'].sum()),
                        interpretation='Added support comes exclusively from rows still labeled UNKNOWN.'),
           trace=dict(tc,paper_RGB_max_errors=trace_errors),fixed_ink_exact=True,original_source_exact=True,source_arrays_unchanged=True,
           scope=p['scope'])
    js(folder/'EVALUATION.json',e)
    for key,value in images.items():png(folder/(key+'.png'),value)
    png(folder/'fixed_ink.png',1-fixed)
    panel(folder/'COMPARISON.png',[images[k] for k in ('source','intent','original_paper','completed_paper','original_hybrid','completed_hybrid')],
          ['Original GS / full SH3','Unchanged authored region4','Original GS paper / natural','Completed GS paper / natural','Original paper + fixed ink','Completed paper + same ink'],
          c['view']+' | Appearance permissions only; M1 UNKNOWN and proxy ink unchanged')
    panel(folder/'MATCHED_COMPARISON.png',[images[k] for k in ('original_matched_paper','completed_matched_paper','original_matched_hybrid','completed_matched_hybrid')],
          ['Original paper / source matched','Completed paper / source matched','Original matched + fixed ink','Completed matched + fixed ink'],
          'Global source RGB effect matched on four BUILD views; no DEV fitting; fixed ink alpha',columns=2)
    js(folder/'COMPLETED.json',dict(utc=now(),files={f.name:sha(f) for f in folder.iterdir() if f.is_file()}))
    print('EVAL',kind,c['view'],'residual reduction',reductions,'added support',float(added[target].mean()),
          'natural far',metrics['completed_paper']['far_raw_fraction'],flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','footprint','select','budget','dev','arc']);ap.add_argument('--index',type=int,default=0);args=ap.parse_args()
    if args.stage in ('freeze','select','budget'):globals()[args.stage]()
    elif args.stage=='footprint':footprint(args.index)
    else:evaluate(args.stage,args.index)
