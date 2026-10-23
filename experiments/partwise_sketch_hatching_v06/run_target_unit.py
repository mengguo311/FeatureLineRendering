"""Unit008: explicitly larger authored target, original-row links, frozen style.

v06-only adaptation of run_completion_unit and run_contour_unit. No v05 runtime
or producer is imported. Old snapshots are immutable inputs.
"""
import runtime
from runtime import ACTIVE_UNIT as UNIT,output_guard,sha,js,now
from pathlib import Path
import argparse,json,shutil
import numpy as np
from scipy import ndimage
from PIL import Image
from geometry import mesh_data,ray_surface
from membership import accumulate,resolve,save_binding,load_binding
from hybrid import region_strength,paper_copy,compose,edit_metrics
from appearance_completion import RegionFootprintRenderer,completion_selection,categories,THRESHOLDS
from link_renderer import Renderer,validate_trace
from run_hybrid import read_npz,png,panel,array_hashes
from target_completion import visible_additions,remap_regions,extend_paths,render_pair
import base_model as base

HERE=Path(__file__).resolve().parent
ROOT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units')
U4=ROOT/'unit_004';U7=ROOT/'unit_007'
OLD=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_005')
ARMS=('old','new')

def fresh(path):
    path=output_guard(path)
    if UNIT not in path.parents:raise ValueError('unit008 output only')
    path.mkdir(parents=True,exist_ok=False);return path

def original_asset():
    p=json.loads((OLD/'PROTOCOL.json').read_text());s=p['scenes']['lego'];asset=Path(s['asset'])
    m=read_npz(asset/'mesh.npz');mesh=mesh_data(m['vertices'],m['faces'],m['face_regions'])
    return p,s,mesh,read_npz(asset/'region_4.npz'),json.loads((asset/'asset.json').read_text())

def author():
    assert UNIT.name=='unit_008'
    p,s,mesh,old,meta=original_asset();out=fresh(UNIT/'asset')
    # Manually drawn on the saved BUILD source/proxy inspection, before outputs.
    view='orbit_57_35_4.9';polygon=[[106,88],[134,107],[136,132],[119,143],[79,138]]
    hit=read_npz(UNIT/'authoring'/view/'FIRST_HIT.npz')
    ids=visible_additions(hit['face'],mesh['regions'],polygon)
    assert len(ids)>0 and (mesh['regions'][ids]==3).all()
    labels=mesh['regions'].copy();labels[ids]=4
    full,added=extend_paths(mesh,old,ids,meta['styles']['4'])
    for k in old:np.testing.assert_array_equal(full[k][:len(old[k])],old[k])
    np.savez_compressed(out/'TARGET.npz',added_faces=ids,old_face_regions=mesh['regions'],face_regions=labels,
        vertices=mesh['vertices'],faces=mesh['faces'])
    np.savez_compressed(out/'OLD_PATHS.npz',**old);np.savez_compressed(out/'ADDED_PATHS.npz',**added)
    np.savez_compressed(out/'PATHS.npz',**full)
    area=.5*np.linalg.norm(np.cross(mesh['tri'][:,1]-mesh['tri'][:,0],mesh['tri'][:,2]-mesh['tri'][:,0]),axis=1)
    images=[];titles=[];checks=[]
    for e in s['evidence_sources'][:4]:
        c=e['camera'];folder=UNIT/'authoring'/c['view'];h=read_npz(folder/'FIRST_HIT.npz');face=h['face'][1::2,1::2]
        oldmask=h['regions'][1::2,1::2]==4;addmask=np.isin(face,ids)
        source=np.asarray(Image.open(folder/'source.png').convert('RGB'))/255.
        overlay=np.asarray(Image.open(folder/'proxy.png').convert('RGB'))/255.
        overlay[oldmask]=[1,.32,.4];overlay[addmask]=[.05,.7,1]
        images += [source,overlay];titles += [c['view']+' | BUILD source','Old target pink / added faces cyan']
        checks.append(dict(view=c['view'],old_pixels=int(oldmask.sum()),added_pixels=int(addmask.sum())))
    panel(UNIT/'authoring/SELECTION_CHECK.png',images,titles,'Manual BUILD-only visible-face addition; no hidden expansion; whole triangles may extend outside polygon',columns=4)
    record=dict(asset_name='bucket_surface_completion_v1',utc=now(),selection_camera=view,polygon=polygon,source_region=3,
        old_faces=int((mesh['regions']==4).sum()),added_faces=len(ids),new_faces=int((labels==4).sum()),
        old_area_world=float(area[mesh['regions']==4].sum()),added_area_world=float(area[ids].sum()),
        old_segments=len(old['points']),old_strokes=len(np.unique(old['stroke_id'])),added_segments=len(added['points']),
        added_strokes=len(np.unique(added['stroke_id'])),build_projection=checks,
        author='Assistant manual selection after four BUILD source/proxy inspections; no user clicks or semantic truth',
        rule='Only source-region3 frontmost2x ray-hit whole faces inside polygon; no connected/hidden expansion or geometry repair',
        intent='Complete a verified omitted bucket inner-side patch; not a complete physical/semantic bucket guarantee',
        path_rule='Old arrays exact. Generate only added faces using unchanged world cutting planes/style/gap; new disjoint stroke IDs; old/new masks union before resolve',
        source_asset=s['asset'],style=meta['styles']['4'],files={f.name:sha(f) for f in out.iterdir()})
    js(out/'AUTHORING.json',record);print('AUTHORED',record,flush=True)

def freeze():
    assert UNIT.name=='unit_008' and not (UNIT/'PROTOCOL.json').exists()
    d=json.loads((UNIT/'DECISION.json').read_text());assert d['action']=='continue'
    old,s,_,_,meta=original_asset();prev=json.loads((U7/'PROTOCOL.json').read_text())
    files=[UNIT/'DECISION.json',OLD/'PROTOCOL.json',OLD/'REPORT_ZH.md',U7/'PROTOCOL.json',U7/'REPORT_ZH.md',
        Path(s['source']['original_ply']),OLD/'results/lego/SOURCE_BINDING.npz',U4/'SELECTION.npz',U4/'SELECTION.json',
        UNIT/'authoring/INSPECTION.json',UNIT/'authoring/SELECTION_CHECK.png']
    files+=list((UNIT/'asset').iterdir())
    files += [Path(s['asset'])/n for n in ('mesh.npz','region_4.npz','asset.json')]
    evidence=s['evidence_sources']
    for e in evidence:files += [Path(e['trace']),Path(e['baseline']),U4/'footprints'/e['camera']['view']/'FOOTPRINT.npz']
    views=[]
    for v in json.loads((U7/'CAMERAS.json').read_text())['views']:
        c=v['camera'];ref=U7/'build_match'/(c['view']+'.npz') if v['kind']=='build' else U7/v['kind']/c['view']/'FRAME.npz'
        views.append(dict(kind=v['kind'],camera=c,reference_cache=str(ref)));files.append(ref)
    locks={str(f):sha(f) for f in files};assert locks[s['source']['original_ply']]==s['source']['sha256']
    snap=UNIT/'source_snapshot';shutil.copytree(HERE,snap,ignore=shutil.ignore_patterns('__pycache__'))
    js(UNIT/'INPUT_LOCK.json',dict(files=locks));js(UNIT/'SOURCE_LOCK.json',dict(files={f.name:sha(f) for f in snap.iterdir() if f.is_file()}))
    js(UNIT/'CAMERAS.json',dict(evidence=evidence,views=views,scope='Same12 BUILD evidence;4 original BUILD budget;4 exposed DEV plus9 exposed arc.'))
    p=dict(unit='unit_008',frozen_utc=now(),decision_sha256=sha(UNIT/'DECISION.json'),scene=prev['scene'],
        question='Does an explicitly expanded authored bucket patch make the linked NPR operation visibly more complete?',
        changed_variable=d['changed_variable'],falsification=d['falsification'],membership=old['membership'],thresholds=THRESHOLDS,
        sampling='Exact saved twelve BUILD trace sample pixels/weights/depth eligibility; remap via saved proxy_face only',
        paths='Old351 strokes/1904 segments and old visibility unchanged; added-face strokes only, constant old crosshatch; no unit005/006/007 added mechanisms',
        matching='One global ink RGB L1 scale per arm from4 BUILD, same expanded target domain; budget=min natural ink total; natural paper fixed per arm. No DEV fitting. Source edit effect separately reported; target scope differs.',
        target='asset/TARGET.npz, manually expanded region4; old target and added patch reported separately; no semantic completeness claim',
        paper=[.95,.95,.95],ink_color=.03,supersample=2,fps=4,
        acceptance='Whole-object patch becomes visibly paper-and-hatched, less partial style; weak view and other parts not visibly degraded. Quantities alone insufficient. No default promotion without visual benefit.',
        scope='Original-GS color override plus original-ID-linked proxy ink, CPU replica, exposed diagnostics; not native Gaussian hatching, physical labels, generalization or H1/H2/H3.',
        negatives='All v05 sparse failures8.044%/4.49% and v06 units001-007 remain unchanged',
        fixed='Original310475 rows/order/geometry/covariance/opacity/SH/source PLY, proxy geometry,12views,thresholds,style,.004 visibility,2px evaluation band',
        frozen_files={n:sha(UNIT/n) for n in ('INPUT_LOCK.json','SOURCE_LOCK.json','CAMERAS.json')},
        resources=dict(serial=True,CPU_affinity=2,numeric_threads=1,GPU=False),deadline_jst='2026-10-23T20:58:34+09:00')
    js(UNIT/'PROTOCOL.json',p);js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json')))
    js(UNIT/'STATUS.json',dict(execution_state='partial',stage='frozen_target_before_links_and_evaluation',scientific_verdict='pending',
        gaussian_link_progress='Author target frozen; links not yet recomputed',scientific_seal=False,blockers=[]))
    print('FROZEN',len(locks),'inputs',sha(UNIT/'PROTOCOL.json'),flush=True)

def protocol():
    p=json.loads((UNIT/'PROTOCOL.json').read_text());assert p['unit']==UNIT.name=='unit_008'
    assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    assert sha(UNIT/'DECISION.json')==p['decision_sha256']
    for n,h in p['frozen_files'].items():assert sha(UNIT/n)==h,n
    for n,h in json.loads((UNIT/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(HERE/n)==h,n
    p.update(json.loads((UNIT/'CAMERAS.json').read_text()));p['input_hashes']=json.loads((UNIT/'INPUT_LOCK.json').read_text())['files']
    return p

def locked(p,path):
    path=Path(path);assert sha(path)==p['input_hashes'][str(path)],str(path);return path

def asset(p):
    t=read_npz(locked(p,UNIT/'asset/TARGET.npz'))
    old=mesh_data(t['vertices'],t['faces'],t['old_face_regions']);new=mesh_data(t['vertices'],t['faces'],t['face_regions'])
    return old,new,read_npz(locked(p,UNIT/'asset/OLD_PATHS.npz')),read_npz(locked(p,UNIT/'asset/ADDED_PATHS.npz')),json.loads(locked(p,Path(p['scene']['asset'])/'asset.json').read_text())

def source(p):
    s=p['scene'];a=base.load_source(locked(p,s['source']['original_ply']),s['source']['sha256']);a['source_index']=np.arange(len(a['means']),dtype=np.int64)
    assert len(a['means'])==310475;return a

def binding():
    p=protocol();oldmesh,newmesh,_,_,_=asset(p);m=p['membership'];n=310475
    old,_=load_binding(locked(p,OLD/'results/lego/SOURCE_BINDING.npz'),p['scene']['source']['sha256'],n)
    scores=[];checks=[]
    for i,e in enumerate(p['evidence']):
        tr=read_npz(locked(p,e['trace']));oldreg=remap_regions(tr,oldmesh['regions']);newreg=remap_regions(tr,newmesh['regions'])
        np.testing.assert_array_equal(oldreg,tr['proxy_region'])
        score,_,_=accumulate(n,tr,oldreg,tr['proxy_depth'],tr['sample_eligible'],tr['sampling_weight'],m['contributor_proxy_z_tolerance'])
        np.testing.assert_array_equal(score,old['per_view_score'][i])
        score,_,diag=accumulate(n,tr,newreg,tr['proxy_depth'],tr['sample_eligible'],tr['sampling_weight'],m['contributor_proxy_z_tolerance']);scores.append(score)
        checks.append(dict(view=e['camera']['view'],changed_sample_regions=int((oldreg!=newreg).sum()),old_score_exact=True,events=len(tr['weight']),mass=diag))
        print('M1',checks[-1]['view'],checks[-1]['changed_sample_regions'],flush=True)
    pv=np.stack(scores);new=resolve(pv,m['min_exposure'],m['min_views'],m['min_fraction'],m['view_mass'])
    null=resolve(old['per_view_score'],m['min_exposure'],m['min_views'],m['min_fraction'],m['view_mass'])
    for k in null:np.testing.assert_array_equal(null[k],old[k])
    save_binding(UNIT/'SOURCE_BINDING.npz',dict(new,per_view_score=pv),dict(source_sha256=p['scene']['source']['sha256'],source_count=n,
        protocol_sha256=sha(UNIT/'PROTOCOL.json'),method='Same saved original-row trace, new labels from saved proxy_face; unchanged sampling/depth/M1 gates'))
    js(UNIT/'BINDING.json',dict(utc=now(),old_unknown=int(old['unknown'].sum()),new_unknown=int(new['unknown'].sum()),
        old_target_rows=int((region_strength(old)>0).sum()),new_target_rows=int((region_strength(new)>0).sum()),
        old_conflict=int(old['conflict'].sum()),new_conflict=int(new['conflict'].sum()),checks=checks,null_addition_exact=True,
        sha256=sha(UNIT/'SOURCE_BINDING.npz')))

def footprints():
    p=protocol();_,mesh,_,_,_=asset(p);a=source(p);before=array_hashes(a);r=RegionFootprintRenderer(UNIT/'build')
    for i,e in enumerate(p['evidence']):
        c=e['camera'];folder=fresh(UNIT/'footprints'/c['view']);prior=read_npz(locked(p,e['baseline']))
        z,_,reg,_=ray_surface(mesh,c,2);z=z[1::2,1::2];reg=reg[1::2,1::2];cat=categories(reg)
        valid=np.isfinite(z)&(prior['alpha']>=.5)&(np.abs(z-prior['median_camera_z'])<=.08)
        f,_,mass=r.footprint(a,c,cat,z,valid)
        np.testing.assert_array_equal(f['rgb'],prior['rgb']);np.testing.assert_array_equal(f['alpha'],prior['alpha'])
        np.testing.assert_allclose(mass[:,1:4].sum(1),mass[:,0],rtol=1e-12,atol=1e-10)
        np.savez_compressed(folder/'FOOTPRINT.npz',source_index=a['source_index'],mass=mass,regions=reg,category=cat)
        js(folder/'COMPLETED.json',dict(camera=c,sha256=sha(folder/'FOOTPRINT.npz'),source_exact=True,target_pixels=int((reg==4).sum())))
        print('FOOTPRINT',i,c['view'],int((reg==4).sum()),flush=True)
    assert before==array_hashes(a);js(UNIT/'SOURCE_ARRAYS.json',before)

def select():
    p=protocol();b,_=load_binding(UNIT/'SOURCE_BINDING.npz',p['scene']['source']['sha256'],310475)
    assert sha(UNIT/'SOURCE_BINDING.npz')==json.loads((UNIT/'BINDING.json').read_text())['sha256']
    new=[];old=[]
    for e in p['evidence']:
        root=UNIT/'footprints'/e['camera']['view'];assert sha(root/'FOOTPRINT.npz')==json.loads((root/'COMPLETED.json').read_text())['sha256']
        new.append(read_npz(root/'FOOTPRINT.npz')['mass']);old.append(read_npz(locked(p,U4/'footprints'/e['camera']['view']/'FOOTPRINT.npz'))['mass'])
    result=completion_selection(np.stack(new),b)
    oldb,_=load_binding(locked(p,OLD/'results/lego/SOURCE_BINDING.npz'),p['scene']['source']['sha256'],310475)
    null=completion_selection(np.stack(old),oldb);prior=read_npz(locked(p,U4/'SELECTION.npz'))
    for k in null:np.testing.assert_array_equal(null[k],prior[k])
    np.savez_compressed(UNIT/'SELECTION.npz',**result,old_ink_strength=prior['original_strength'],old_paper_strength=prior['completed_strength'])
    js(UNIT/'SELECTION.json',dict(utc=now(),old_ink_rows=20122,new_ink_rows=int((result['original_strength']>0).sum()),
        old_paper_rows=39474,new_paper_rows=int((result['completed_strength']>0).sum()),
        new_appearance_only_rows=int((result['appearance_completion_strength']>0).sum()),old_unknown=195600,new_unknown=int(b['unknown'].sum()),
        appearance_does_not_relabel_UNKNOWN=True,null_addition_exact=True,sha256=sha(UNIT/'SELECTION.npz')))
    print('SELECTION',json.loads((UNIT/'SELECTION.json').read_text()),flush=True)

def selection():
    assert sha(UNIT/'SELECTION.npz')==json.loads((UNIT/'SELECTION.json').read_text())['sha256'];return read_npz(UNIT/'SELECTION.npz')

def cache(p,v):
    f=read_npz(locked(p,v['reference_cache']))
    if v['kind']=='build':return dict(source=f['source'],paper=f['paper'],support=f['support'],ink=f['hatch_ink'],alpha=f['old_alpha'],regions=f['regions'])
    return dict(source=f['source'],paper=f['paper'],support=f['support'],ink=f['hatch_ink'],alpha=f['hatch_raw_alpha'],regions=f['regions'],hybrid=f['hatch_raw'])

def spatial_metrics(source_image,image,regions,oldregions):
    out=edit_metrics(source_image,image,regions)
    raw=np.abs(image-source_image).sum(2);clip=np.abs(np.clip(image,0,1)-np.clip(source_image,0,1)).sum(2)
    for label,mask in [('old_target',oldregions==4),('added_target',(regions==4)&(oldregions!=4))]:
        for suffix,area in [('',mask),('_interior',ndimage.binary_erosion(mask,iterations=2))]:
            n=int(area.sum());out[label+suffix]=dict(pixels=n,raw_L1_sum=float(raw[area].sum(dtype=float)),
                clipped_L1_sum=float(clip[area].sum(dtype=float)),raw_L1_mean=float(raw[area].mean()) if n else None,
                visible_fraction_1_255=float((clip[area]>1/255).mean()) if n else None,
                useful_fraction_0_05=float((clip[area]>=.05).mean()) if n else None)
    return out

def compute_frame(p,v,r,a,sel):
    c=v['camera'];ref=cache(p,v);oldmesh,newmesh,old,added,meta=asset(p);pair,hi=render_pair(oldmesh,newmesh,old,added,meta,c)
    np.testing.assert_array_equal(pair['old'],ref['ink']);np.testing.assert_array_equal(hi['old_regions'],ref['regions'])
    yy,xx=np.mgrid[:c['height'],:c['width']];sample=(hi['regions']==4)|((xx%7==1)&(yy%7==1));xy=np.column_stack([xx[sample],yy[sample]])
    f,tr=r.render(a,c,xy,sel['original_strength']);np.testing.assert_array_equal(f['rgb'],ref['source']);tc=validate_trace(a,c,xy,f,tr)
    paper,_=r.render(paper_copy(a,c,sel['completed_strength'],p['paper']),c)
    out=dict(source=f['rgb'],source_alpha=f['alpha'],old_paper=ref['paper'],new_paper=paper['rgb'],old_support=ref['support'],new_support=f['contribution'],
        old_ink=pair['old'],new_ink=pair['new'],added_ink=hi['added_ink'],old_regions=hi['old_regions'],regions=hi['regions'],proxy=hi['proxy'])
    for arm in ARMS:
        im,alpha=compose(out[arm+'_paper'],out[arm+'_ink'],out[arm+'_support'],True,ink_color=p['ink_color']);out[arm+'_raw']=im;out[arm+'_raw_alpha']=alpha
    np.testing.assert_array_equal(out['old_raw_alpha'],ref['alpha'])
    if 'hybrid' in ref:np.testing.assert_array_equal(out['old_raw'],ref['hybrid'])
    return out,dict(tr,xy=xy),tc

def build():
    p=protocol();sel=selection();a=source(p);before=array_hashes(a);r=Renderer(UNIT/'build');out=fresh(UNIT/'build_match')
    totals={k:0. for k in ARMS};records=[]
    for v in (v for v in p['views'] if v['kind']=='build'):
        f,tr,tc=compute_frame(p,v,r,a,sel);target=f['regions']==4;row=dict(view=v['camera']['view'])
        for arm in ARMS:
            value=float(np.abs(f[arm+'_raw']-f[arm+'_paper'])[target].sum(dtype=float));totals[arm]+=value;row[arm]=value
        np.savez_compressed(out/(v['camera']['view']+'.npz'),**f);records.append(row);print('BUDGET',row,flush=True)
    budget=min(totals.values());scales={k:budget/v for k,v in totals.items()};checks={k:0. for k in ARMS}
    for v in (v for v in p['views'] if v['kind']=='build'):
        f=read_npz(out/(v['camera']['view']+'.npz'));target=f['regions']==4
        for arm in ARMS:
            im,_=compose(f[arm+'_paper'],f[arm+'_ink'],f[arm+'_support'],True,scales[arm],p['ink_color']);checks[arm]+=float(np.abs(im-f[arm+'_paper'])[target].sum(dtype=float))
    assert max(abs(x-budget)/budget for x in checks.values())<1e-5;assert before==array_hashes(a)
    js(UNIT/'BUILD_MATCH.json',dict(records=records,natural_target_ink_L1=totals,budget=budget,scales=scales,actual_matched_target_ink_L1=checks,
        common_domain='expanded target in both arms',source_array_hashes=before))
    js(UNIT/'BUILD_LOCK.json',dict(files={str(f.relative_to(UNIT)):sha(f) for f in list(out.iterdir())+[UNIT/'BUILD_MATCH.json']}))
    print('MATCHED',totals,scales,flush=True)

def match():
    locks=json.loads((UNIT/'BUILD_LOCK.json').read_text())['files'];assert sha(UNIT/'BUILD_MATCH.json')==locks['BUILD_MATCH.json']
    return json.loads((UNIT/'BUILD_MATCH.json').read_text())

def evaluate(kind,index):
    p=protocol();m=match();sel=selection();v=[v for v in p['views'] if v['kind']==kind][index];c=v['camera']
    folder=fresh(UNIT/kind/c['view']);a=source(p);before=array_hashes(a);r=Renderer(UNIT/'build');f,tr,tc=compute_frame(p,v,r,a,sel)
    metrics={};ink={};support={};paper_residual={};coverage={}
    regions=f['regions'];oldregions=f['old_regions'];masks=dict(old_target=oldregions==4,added_target=(regions==4)&(oldregions!=4),target=regions==4,
        interior=ndimage.binary_erosion(regions==4,iterations=2))
    for arm in ARMS:
        im,alpha=compose(f[arm+'_paper'],f[arm+'_ink'],f[arm+'_support'],True,m['scales'][arm],p['ink_color']);f[arm+'_matched']=im;f[arm+'_matched_alpha']=alpha
        metrics[arm+'_paper']=spatial_metrics(f['source'],f[arm+'_paper'],regions,oldregions)
        d=np.abs(np.clip(f[arm+'_paper'],0,1)-np.asarray(p['paper'])).sum(2)
        paper_residual[arm]={n:dict(pixels=int(mask.sum()),mean=float(d[mask].mean()) if mask.any() else None,sum=float(d[mask].sum(dtype=float))) for n,mask in masks.items()}
        support[arm]={n:dict(pixels=int(mask.sum()),mean=float(f[arm+'_support'][mask].mean()) if mask.any() else None,
            fraction_above_0_05=float((f[arm+'_support'][mask]>.05).mean()) if mask.any() else None) for n,mask in masks.items()}
        for mode in ('raw','matched'):
            key=arm+'_'+mode;metrics[key]=spatial_metrics(f['source'],f[key],regions,oldregions);ink[key]=spatial_metrics(f[arm+'_paper'],f[key],regions,oldregions)
            coverage[key]={n:dict(pixels=int(mask.sum()),visible_ink_pixels=int(((f[key+'_alpha']>.05)&mask).sum()),
                visible_ink_fraction=float((f[key+'_alpha'][mask]>.05).mean()) if mask.any() else None) for n,mask in masks.items()}
    changes={mode:spatial_metrics(f['old_'+mode],f['new_'+mode],regions,oldregions) for mode in ('raw','matched')}
    intent=np.repeat(f['proxy'][:,:,None],3,axis=2);intent[oldregions==4]=[1,.32,.4];intent[masks['added_target']]=[.05,.7,1];f['intent']=intent
    assert before==array_hashes(a)==m['source_array_hashes']
    np.savez_compressed(folder/'FRAME.npz',**f);np.savez_compressed(folder/'TRACE.npz',**tr)
    js(folder/'EVALUATION.json',dict(camera=c,metrics=metrics,ink=ink,coverage=coverage,support=support,paper_residual=paper_residual,
        changes=changes,trace=tc,old_hatch_exact=True,original_source_exact=True,scope=p['scope']))
    for key in ('source','intent','old_paper','new_paper','old_raw','new_raw','old_matched','new_matched'):png(folder/(key+'.png'),f[key])
    for key in ('old_raw','new_raw','old_matched','new_matched'):png(folder/(key+'_ink.png'),1-f[key+'_alpha'])
    panel(folder/'COMPARISON.png',[f[k] for k in ('source','intent','old_paper','new_paper','old_raw','new_raw','old_matched','new_matched')],
        ['Original GS','Old pink / added cyan','Old GS paper','New GS paper','Old target / natural','Expanded target / natural','Old / BUILD ink matched','Expanded / BUILD ink matched'],
        c['view']+' | Explicit new target; same original Gaussian rows; proxy-carried ink',columns=4)
    js(folder/'COMPLETED.json',dict(utc=now(),files={f.name:sha(f) for f in folder.iterdir() if f.is_file()}))
    print('EVAL',kind,c['view'],'added',int(masks['added_target'].sum()),'coverage',coverage['new_raw']['added_target'],flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['author','freeze','binding','footprints','select','build','dev','arc']);ap.add_argument('--index',type=int,default=0);args=ap.parse_args()
    if args.stage in ('dev','arc'):evaluate(args.stage,args.index)
    else:globals()[args.stage]()
