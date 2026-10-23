"""Frozen region-scale hybrid experiment; every output belongs to v06."""
import runtime
from runtime import ACTIVE_UNIT, OUTPUT_ROOT, output_guard, sha, js, now
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import time
import numpy as np
from scipy.spatial import cKDTree
from PIL import Image,ImageDraw
import base_model as base
from geometry import mesh_data
from membership import load_binding
from link_renderer import Renderer,validate_trace
from render import render as render_ink
from hybrid import region_strength,paper_copy,compose,edit_metrics,ink_metrics

OLD=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_005')

def read_npz(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k] for k in z.files}

def png(path,array):
    a=np.asarray(array)
    if a.ndim==2:a=np.repeat(a[:,:,None],3,axis=2)
    Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(output_guard(path))

def panel(path,images,labels,footer,columns=3):
    w=images[0].shape[1];h=images[0].shape[0];rows=(len(images)+columns-1)//columns
    canvas=Image.new('RGB',(w*columns,(h+24)*rows+36),'white');draw=ImageDraw.Draw(canvas)
    for i,(a,label) in enumerate(zip(images,labels)):
        if a.ndim==2:a=np.repeat(a[:,:,None],3,axis=2)
        x=(i%columns)*w;y=(i//columns)*(h+24)
        canvas.paste(Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)),(x,y+24))
        draw.text((x+6,y+4),label,fill='black')
    draw.text((6,(h+24)*rows+5),footer,fill='black')
    canvas.save(output_guard(path))

def array_hashes(a):
    return {k:hashlib.sha256(np.ascontiguousarray(a[k]).tobytes()).hexdigest()
            for k in ('means','covariance','precision','opacity','SH','source_index')}

def freeze(unit):
    if (unit/'PROTOCOL.json').exists():raise FileExistsError('already frozen')
    decision=json.loads((unit/'DECISION.json').read_text())
    if decision['action']!='continue':raise ValueError('decision does not authorize proposed route')
    previous=json.loads((OLD/'PROTOCOL.json').read_text())
    inputs={str(unit/'DECISION.json'):sha(unit/'DECISION.json')}
    for name in ('PROTOCOL.json','REPORT_ZH.md','STATUS.json','NEXT.json'):
        inputs[str(OLD/name)]=sha(OLD/name)
    scenes={}
    for name,s in previous['scenes'].items():
        binding=OLD/'results'/name/'SOURCE_BINDING.npz'
        inputs[str(binding)]=sha(binding)
        for filename,h in s['asset_hashes'].items():
            f=Path(s['asset'])/filename
            if sha(f)!=h:raise ValueError(f'asset changed: {f}')
            inputs[str(f)]=h
        ply=s['source']['original_ply']
        if sha(ply)!=s['source']['sha256']:raise ValueError('source PLY changed')
        inputs[ply]=s['source']['sha256']
        for c in s['cameras']:
            for filename in ('baseline.npz','VISIBILITY_READBACK.json'):
                f=OLD/'results'/name/c['view']/filename
                inputs[str(f)]=sha(f)
        scenes[name]=dict(source=s['source'],source_count=s['source_count'],asset=s['asset'],binding=str(binding),
            target=s['target_name'],build_cameras=s['budget_cameras'],
            evaluation_cameras=[dict(c,split='exposed_DEV') for c in s['cameras']])
    p=dict(unit='unit_001',frozen_utc=now(),decision_sha256=inputs[str(unit/'DECISION.json')],previous=str(OLD),
        question='Does original-row full-T responsibility gating improve a visibly useful region-level paper-and-ink hybrid over identical un-gated proxy ink?',
        scope='New complete authored region4 operation; NOT the old sparse 3px capsule task. CPU hybrid, not native Gaussian ink, semantic GT, physical ownership, or H1/H2/H3.',
        main_changed_variable='A=H4*S versus A=H4 on identical paper, paths, styles, cameras and frozen M1; additionally show BUILD ink-effect matched un-gated control.',
        scenes=scenes,input_hashes=inputs,region_id=4,paper=[.95,.95,.95],ink_color=.03,supersample=2,
        membership='s=q[:,4] only for nonUNKNOWN region_id4, complete original PLY rows; exact unit005 binding reused',
        support='S=sum accepted alpha*T*s, no selected-only rerender, no division by alpha or support threshold',
        arms=['gated','ungated','ungated_BUILD_ink_matched','nearest_proxy_gated','shuffled_ID_gated'],
        controls=dict(nearest='Original kernel center nearest saved proxy triangle centroid; source paper effect matched to fixed linked s on four original BUILD cameras when attainable.',
                      shuffled='Permute full M1 s in ten exposure bins, seed1729. Negative control; no forced effect or ink matching.',
                      null='Actual small original-kernel fixture with s=0; both source edit and gated ink must be zero.'),
        matching='Raw full-image actual RGB L1. Fixed primary s unchanged. Un-gated ink scalar equals BUILD gated/ungated ink L1. Nearest source scalar equals primary/nearest BUILD paper L1, clipped at1 and explicitly invalid if unattainable.',
        evaluation='All eight unit005 cameras retained and explicitly exposed DEV. No novel/held-out claim. No post-evaluation parameter tuning.',
        practical_screen=dict(interior_pixel_clipped_L1=.05,minimum_interior_changed_fraction=.5,minimum_target_ink_retention=.5,
                              far_damage_reference=.02,boundary_pixels=2,visual_review_required=True,
                              note='Separate practical screen and locality reference; no global stop from one imperfect local gate.'),
        fixed_camera_ink_ramp=dict(view_index=1,levels=[0.,1/3,2/3,1.],paper_fixed=True,fps=2),
        source_invariants='Original PLY, means, covariance, opacity, full SH, row count/order fixed. Render-time colors in private copy only.',
        resources=dict(CPU_affinity=2,numeric_threads=1,GPU=False,serial=True,output_limit_GiB=20),
        inherited_failures='unit005 7/8 sparse-path joint; Lego241/24 far8.044%, 4.49% region pixels changed; unit004 failures, Ficus NO_GO, native calibration gap and original interruptions unchanged.')
    snap=unit/'source_snapshot';shutil.copytree(Path(__file__).parent,snap,ignore=shutil.ignore_patterns('__pycache__'))
    p['source_hashes']={f.name:sha(f) for f in snap.iterdir() if f.is_file()}
    js(unit/'PROTOCOL.json',p)
    js(unit/'PROTOCOL_LOCK.json',dict(sha256=sha(unit/'PROTOCOL.json'),utc=now()))
    print('FROZEN',sha(unit/'PROTOCOL.json'),len(inputs),'inputs',flush=True)

def protocol(unit):
    p=json.loads((unit/'PROTOCOL.json').read_text())
    assert sha(unit/'PROTOCOL.json')==json.loads((unit/'PROTOCOL_LOCK.json').read_text())['sha256']
    for name,h in p['source_hashes'].items():assert sha(Path(__file__).parent/name)==h,name
    assert sha(unit/'DECISION.json')==p['decision_sha256']
    return p

def load_scene(unit,name):
    p=protocol(unit);s=p['scenes'][name]
    for path,h in p['input_hashes'].items():
        if path==s['binding'] or path.startswith(s['asset']+'/'):assert sha(path)==h,path
    a=base.load_source(s['source']['original_ply'],s['source']['sha256'])
    n=len(a['means']);assert n==s['source_count'];a['source_index']=np.arange(n,dtype=np.int64)
    b,_=load_binding(s['binding'],s['source']['sha256'],n)
    asset=Path(s['asset']);m=read_npz(asset/'mesh.npz')
    mesh=mesh_data(m['vertices'],m['faces'],m['face_regions'])
    paths=read_npz(asset/'region_4.npz');meta=json.loads((asset/'asset.json').read_text())
    np.testing.assert_allclose(np.einsum('nij,njk->nik',paths['bary'],mesh['tri'][paths['face']]),paths['points'],atol=1e-9,rtol=0)
    return p,s,a,b,mesh,paths,meta

def ink_frame(mesh,paths,meta,c,p):
    h=render_ink(mesh,{4:paths},meta['styles'],c,p['supersample'],meta.get('display'))
    return h['layers'][4],h

def build(unit,name):
    started=time.monotonic();p,s,a,b,mesh,paths,meta=load_scene(unit,name)
    out=output_guard(unit/'results'/name);out.mkdir(parents=True,exist_ok=False)
    r=Renderer(output_guard(unit/'build'));before=array_hashes(a)
    primary=region_strength(b)
    _,nearest=cKDTree(mesh['tri'].mean(1)).query(a['means'],workers=1)
    spatial=(mesh['regions'][nearest]==4).astype(float)
    shuffled=primary.copy();rng=np.random.default_rng(1729)
    observed=np.flatnonzero(b['exposure']>0)
    ordered=observed[np.argsort(b['exposure'][observed],kind='stable')]
    for ids in np.array_split(ordered,10):shuffled[ids]=primary[rng.permutation(ids)]
    records=[];sum_primary=0.;sum_nearest=0.;sum_gated=0.;sum_ungated=0.
    for c in s['build_cameras']:
        folder=out/'build_views'/c['view'];folder.mkdir(parents=True)
        original,_=r.render(a,c,strength=primary)
        paper,_=r.render(paper_copy(a,c,primary,p['paper']),c)
        other,_=r.render(paper_copy(a,c,spatial,p['paper']),c)
        h,hi=ink_frame(mesh,paths,meta,c,p)
        gated,_=compose(paper['rgb'],h,original['contribution'],True,ink_color=p['ink_color'])
        ungated,_=compose(paper['rgb'],h,original['contribution'],False,ink_color=p['ink_color'])
        d1=float(np.abs(paper['rgb']-original['rgb']).sum(dtype=float))
        d2=float(np.abs(other['rgb']-original['rgb']).sum(dtype=float))
        d3=float(np.abs(gated-paper['rgb']).sum(dtype=float));d4=float(np.abs(ungated-paper['rgb']).sum(dtype=float))
        sum_primary+=d1;sum_nearest+=d2;sum_gated+=d3;sum_ungated+=d4
        np.savez_compressed(folder/'BUILD.npz',source=original['rgb'],paper=paper['rgb'],support=original['contribution'],ink=h,regions=hi['regions'])
        records.append(dict(view=c['view'],primary_paper_L1=d1,nearest_paper_L1=d2,gated_ink_L1=d3,ungated_ink_L1=d4))
        print('BUILD',name,c['view'],records[-1],flush=True)
    nearest_scale=min(1.,sum_primary/max(sum_nearest,1e-30))
    ink_scale=min(1.,sum_gated/max(sum_ungated,1e-30))
    checks=[]
    for c in s['build_cameras']:
        f=read_npz(out/'build_views'/c['view']/'BUILD.npz')
        matched,_=r.render(paper_copy(a,c,spatial*nearest_scale,p['paper']),c)
        ungated,_=compose(f['paper'],f['ink'],f['support'],False,ink_scale,p['ink_color'])
        checks.append(dict(view=c['view'],nearest_actual_matched_L1=float(np.abs(matched['rgb']-f['source']).sum(dtype=float)),
                           ungated_actual_matched_ink_L1=float(np.abs(ungated-f['paper']).sum(dtype=float))))
    actual_nearest=sum(x['nearest_actual_matched_L1'] for x in checks)
    actual_ink=sum(x['ungated_actual_matched_ink_L1'] for x in checks)
    match=dict(build_records=records,actual_scaled_render_checks=checks,primary_paper_L1=sum_primary,
               nearest_paper_L1=sum_nearest,nearest_scale=nearest_scale,nearest_effect_match_valid=abs(actual_nearest-sum_primary)/max(sum_primary,1e-30)<.001,
               gated_ink_L1=sum_gated,ungated_ink_L1=sum_ungated,ungated_ink_scale=ink_scale,
               ink_effect_match_valid=abs(actual_ink-sum_gated)/max(sum_gated,1e-30)<.001,
               source_counts=dict(primary=int((primary>0).sum()),nearest=int((spatial>0).sum()),shuffled=int((shuffled>0).sum())),
               unknown_original_rows=int(b['unknown'].sum()),scope='BUILD only; fixed primary strength unchanged')
    assert match['ink_effect_match_valid']
    np.savez_compressed(out/'SELECTION.npz',source_index=a['source_index'],source_sha256=np.array(s['source']['sha256']),
                        primary=primary,nearest=spatial*nearest_scale,nearest_unscaled=spatial,shuffled=shuffled,unknown=b['unknown'],nearest_face=nearest)
    js(out/'BUILD_MATCH.json',match)
    assert before==array_hashes(a)
    js(out/'BINDING_LOCK.json',dict(utc=now(),files={n:sha(out/n) for n in ('SELECTION.npz','BUILD_MATCH.json')},
        source_array_hashes=before,paths_sha256=sha(Path(s['asset'])/'region_4.npz'),
        path_segments=len(paths['points']),stroke_ids=len(np.unique(paths['stroke_id'])),seconds=time.monotonic()-started))
    print('MATCH',name,match,flush=True)

def evaluate(unit,name,index):
    started=time.monotonic();p,s,a,b,mesh,paths,meta=load_scene(unit,name)
    out=unit/'results'/name;lock=json.loads((out/'BINDING_LOCK.json').read_text())
    for file,h in lock['files'].items():assert sha(out/file)==h
    selections=read_npz(out/'SELECTION.npz');match=json.loads((out/'BUILD_MATCH.json').read_text())
    np.testing.assert_array_equal(selections['primary'],region_strength(b))
    np.testing.assert_array_equal(selections['source_index'],a['source_index'])
    c=s['evaluation_cameras'][index];folder=out/c['view'];folder.mkdir(exist_ok=False)
    r=Renderer(output_guard(unit/'build'));before=array_hashes(a)
    yy,xx=np.mgrid[1:c['height']:7,1:c['width']:7];xy=np.column_stack([xx.ravel(),yy.ravel()])
    source,tr=r.render(a,c,xy,selections['primary'])
    trace_check=validate_trace(a,c,xy,source,tr)
    old_path=OLD/'results'/name/c['view']/'baseline.npz'
    assert sha(old_path)==p['input_hashes'][str(old_path)]
    old=read_npz(old_path)
    np.testing.assert_array_equal(source['rgb'],old['rgb'])
    np.testing.assert_array_equal(source['alpha'],old['alpha'])
    del old
    paper,_=r.render(paper_copy(a,c,selections['primary'],p['paper']),c)
    nearest,_=r.render(paper_copy(a,c,selections['nearest'],p['paper']),c,strength=selections['nearest'])
    shuffled,_=r.render(paper_copy(a,c,selections['shuffled'],p['paper']),c,strength=selections['shuffled'])
    unknown,_=r.render(a,c,strength=b['unknown'].astype(float))
    np.testing.assert_array_equal(unknown['rgb'],source['rgb'])
    np.testing.assert_array_equal(paper['alpha'],source['alpha'])
    h,hi=ink_frame(mesh,paths,meta,c,p);regions=hi['regions'];support=source['contribution']
    gated,ga=compose(paper['rgb'],h,support,True,ink_color=p['ink_color'])
    ungated,ua=compose(paper['rgb'],h,support,False,ink_color=p['ink_color'])
    matched,ma=compose(paper['rgb'],h,support,False,match['ungated_ink_scale'],p['ink_color'])
    nh,na=compose(nearest['rgb'],h,nearest['contribution'],True,ink_color=p['ink_color'])
    sh,sa=compose(shuffled['rgb'],h,shuffled['contribution'],True,ink_color=p['ink_color'])
    # Independently reconstruct actual paper RGB and full-T S at saved trace pixels.
    ids=tr['source_index'];sid=tr['sample_index'];weight=tr['weight'];n=len(xy)
    col=base.source_colors(a,c);ss=selections['primary'][ids]
    override=col[ids]*(1-ss[:,None])+np.asarray(p['paper'])*ss[:,None]
    recon=np.repeat((1-np.bincount(sid,weight,minlength=n))[:,None],3,axis=1)
    for j in range(3):recon[:,j]+=np.bincount(sid,weight*override[:,j],minlength=n)
    sp=np.bincount(sid,weight*ss,minlength=n);xx,yy=xy.T
    rgb_error=float(np.max(np.abs(recon-paper['rgb'][yy,xx])))
    support_error=float(np.max(np.abs(sp-support[yy,xx])))
    assert rgb_error<1e-6 and support_error<1e-6
    trace_check.update(paper_RGB_max_error=rgb_error,support_max_error=support_error,old_source_RGB_alpha_exact=True)
    images=dict(source=source['rgb'],paper=paper['rgb'],ink=1-ga,hybrid_gated=gated,hybrid_ungated=ungated,
                hybrid_ungated_matched=matched,nearest_paper=nearest['rgb'],nearest_hybrid=nh,shuffled_paper=shuffled['rgb'],shuffled_hybrid=sh)
    intent=np.repeat(hi['proxy'][:,:,None],3,axis=2);intent[regions==4]=[1.,.32,.40]
    images['intent']=intent
    for key,value in images.items():png(folder/(key+'.png'),value)
    np.savez_compressed(folder/'FRAME.npz',**images,alpha=source['alpha'],support=support,unknown_support=unknown['contribution'],
        reference_ink=h,gated_alpha=ga,ungated_alpha=ua,matched_alpha=ma,nearest_alpha=na,shuffled_alpha=sa,
        nearest_support=nearest['contribution'],shuffled_support=shuffled['contribution'],proxy_regions=regions,proxy_depth=hi['depth'])
    np.savez_compressed(folder/'TRACE.npz',**tr,xy=xy)
    metrics={}
    for arm in ('paper','hybrid_gated','hybrid_ungated','hybrid_ungated_matched','nearest_paper','nearest_hybrid','shuffled_paper','shuffled_hybrid'):
        metrics[arm]=edit_metrics(source['rgb'],images[arm],regions)
    inks={k:ink_metrics(pa,im,ia,h,regions) for k,pa,im,ia in [
        ('gated',paper['rgb'],gated,ga),('ungated',paper['rgb'],ungated,ua),('matched',paper['rgb'],matched,ma),
        ('nearest',nearest['rgb'],nh,na),('shuffled',shuffled['rgb'],sh,sa)]}
    target=regions==4;total_mass=float(source['alpha'][target].sum())
    inner_fraction=metrics['hybrid_gated']['target_interior']['useful_fraction_0_05']
    screen=bool(inner_fraction is not None and inner_fraction>=.5 and inks['gated']['retained_target_ink_fraction']>=.5)
    row=dict(camera=c,metrics=metrics,ink=inks,practical_screen=screen,
        support=dict(target_mean=float(support[target].mean()),target_source_mass=total_mass,
                     target_unknown_mass_fraction=float(unknown['contribution'][target].sum()/max(total_mass,1e-30))),
        trace=trace_check,seconds=time.monotonic()-started,scope=p['scope'])
    js(folder/'EVALUATION.json',row)
    panel(folder/'COMPARISON.png',[source['rgb'],intent,paper['rgb'],1-ga,gated,matched],
        ['Original GS / full SH3','Authored whole region 4','Actual GS paper substrate','Ink only / original-ID gated','Hybrid / responsibility gated','Hybrid / ungated BUILD ink matched'],
        name+' '+c['view']+' | Exposed DEV; proxy ink + original-GS paper, not native Gaussian hatching')
    panel(folder/'CONTROLS.png',[ungated,gated,matched,nh,sh,1-h],
        ['Ungated / original ink strength','Gated / original ink strength','Ungated / BUILD ink matched','Nearest-proxy / source matched','Shuffled original IDs / negative','Original proxy region-4 ink'],
        'Source and ink effects reported separately; shuffled effect is not matched.')
    if index==p['fixed_camera_ink_ramp']['view_index']:
        ramp=folder/'ink_ramp';ramp.mkdir()
        frames=[]
        for j,level in enumerate(p['fixed_camera_ink_ramp']['levels']):
            image,_=compose(paper['rgb'],h,support,True,level,p['ink_color']);frames.append(image)
            png(ramp/f'frame_{j:03d}.png',image)
        panel(ramp/'CONTACT.png',frames,[f'Ink strength {x:.2f}' for x in p['fixed_camera_ink_ramp']['levels']],
              'Fixed camera; paper fixed; real ink-alpha edit, not an orbit.',columns=4)
    assert before==array_hashes(a)==lock['source_array_hashes']
    js(folder/'COMPLETED.json',dict(utc=now(),files={f.name:sha(f) for f in folder.iterdir() if f.is_file()},
        source_arrays_unchanged=True,decision_sha256=p['decision_sha256']))
    print('EVALUATED',name,c['view'],'practical',screen,'paper_far',metrics['paper']['far_raw_fraction'],
          'ink_retained',inks['gated']['retained_target_ink_fraction'],'useful_fraction',inner_fraction,flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','build','evaluate'])
    ap.add_argument('--unit',type=Path,default=ACTIVE_UNIT);ap.add_argument('--scene',choices=['chair','lego']);ap.add_argument('--index',type=int)
    args=ap.parse_args();unit=output_guard(args.unit)
    if args.stage=='freeze':freeze(unit)
    elif args.stage=='build':build(unit,args.scene)
    else:evaluate(unit,args.scene,args.index)

if __name__=='__main__':main()
