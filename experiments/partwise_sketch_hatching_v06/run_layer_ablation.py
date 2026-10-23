"""Unit002: immutable, BUILD-matched direction-layer ablation and actual GS arc."""
import runtime
from runtime import ACTIVE_UNIT as UNIT, output_guard, js, sha, now
from pathlib import Path
import argparse
import json
import shutil
import time
import numpy as np
from geometry import mesh_data,orbit_camera
from hybrid import compose,paper_copy,edit_metrics,ink_metrics,region_strength
from layer_ablation import render_pair,match_scales,ink_shape,projected_length
from run_hybrid import read_npz,png,panel,array_hashes

PREV=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_001')
HERE=Path(__file__).resolve().parent

def fresh(path):
    path=output_guard(path);path.mkdir(parents=True,exist_ok=False);return path

def freeze():
    if (UNIT/'PROTOCOL.json').exists():raise FileExistsError('protocol exists')
    decision=json.loads((UNIT/'DECISION.json').read_text());assert decision['action']=='continue'
    old=json.loads((PREV/'PROTOCOL.json').read_text());s=old['scenes']['lego'];asset=Path(s['asset'])
    files=[UNIT/'DECISION.json',PREV/'PROTOCOL.json',PREV/'STATUS.json',PREV/'REPORT_ZH.md',PREV/'NEXT.json',
           Path(s['source']['original_ply']),Path(s['binding']),asset/'mesh.npz',asset/'region_4.npz',asset/'asset.json',
           PREV/'results/lego/SELECTION.npz',PREV/'results/lego/BINDING_LOCK.json',PREV/'results/lego/BUILD_MATCH.json']
    for c in s['build_cameras']: files.append(PREV/'results/lego/build_views'/c['view']/'BUILD.npz')
    for c in s['evaluation_cameras']:
        files += [PREV/'results/lego'/c['view']/n for n in ('FRAME.npz','EVALUATION.json')]
    for c in old['scenes']['chair']['evaluation_cameras']:
        files.append(PREV/'results/chair'/c['view']/'hybrid_gated.png')
    locks={str(f):sha(f) for f in files}
    assert locks[s['source']['original_ply']]==s['source']['sha256']
    for f in (asset/'mesh.npz',asset/'region_4.npz',asset/'asset.json',Path(s['binding'])):
        assert locks[str(f)]==old['input_hashes'][str(f)]
    arc=[dict(orbit_camera(231+2.5*i,24,5.3,384),split='frozen_diagnostic_arc_not_blind',azimuth=231+2.5*i,elevation=24,distance=5.3) for i in range(9)]
    p=dict(unit='unit_002',frozen_utc=now(),decision_sha256=locks[str(UNIT/'DECISION.json')],previous=str(PREV),
        question='Does fixed layer0 improve whole-object bucket readability over cross hatching at equal BUILD visible ink?',
        changed_variable='Saved direction layers {0,1} versus {0}; fixed M1, original rows, source paper, S, geometry, paths, width, visibility, 2x sampling.',
        scene=s,arc_cameras=arc,region_id=4,paper=old['paper'],ink_color=old['ink_color'],supersample=2,
        matching=dict(domain='Authored full region4, raw actual hybrid minus paper RGB L1 summed over four original BUILD cameras',
            budget='0.95 * min(unscaled_cross,unscaled_base)',parameter='One global alpha attenuation per arm; no evaluation fitting'),
        arms=['cross_raw','base_raw','cross_matched','base_matched'],
        compositor='Original-ID S multiplies each downsampled ink; union is max at 2x BEFORE averaging, identical to unit001',
        metric_rules=dict(boundary_pixels=2,visible_ink_alpha=.05,component_connectivity=8,small_component_pixels_max=4,
            length='Fixed projected centerlines at <=0.5px intervals sampled against actual alpha>.05; overlaps can credit other strokes; not independent visibility GT',
            quality='Judge whole-object readability jointly with ink coverage and raw/matched effect. Fewer crosses alone is not improvement.'),
        scope='Original-GS source paper plus fixed proxy ink. Authored intent, CPU replica; no native/semantic/physical/H1/H2/H3 or general temporal claim.',
        old_failures='v05 sparse-path Lego241/24 far8.044% unchanged; unit001 gating benefit unestablished; original exit143/UNKNOWN receipts and media failure unchanged.',
        source_invariants='Original PLY rows/order, means,covariance,opacity,SH fixed. Private evaluated-color overrides only.',
        input_hashes=locks,chair_reference=[str(PREV/'results/chair'/c['view']/'hybrid_gated.png') for c in old['scenes']['chair']['evaluation_cameras']],
        resources=dict(serial=True,CPU_affinity=2,numeric_threads=1,GPU=False),fps=4)
    snap=UNIT/'source_snapshot';shutil.copytree(HERE,snap,ignore=shutil.ignore_patterns('__pycache__'))
    p['source_hashes']={f.name:sha(f) for f in snap.iterdir() if f.is_file()}
    js(UNIT/'PROTOCOL.json',p);js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json'),utc=now()))
    print('FROZEN',sha(UNIT/'PROTOCOL.json'),len(locks),'inputs',flush=True)

def protocol():
    p=json.loads((UNIT/'PROTOCOL.json').read_text())
    assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    assert sha(UNIT/'DECISION.json')==p['decision_sha256']
    for n,h in p['source_hashes'].items():assert sha(HERE/n)==h,n
    return p

def locked(p,path):
    path=Path(path);assert sha(path)==p['input_hashes'][str(path)],str(path)
    return path

def asset(p):
    root=Path(p['scene']['asset']);m=read_npz(locked(p,root/'mesh.npz'))
    mesh=mesh_data(m['vertices'],m['faces'],m['face_regions'])
    paths=read_npz(locked(p,root/'region_4.npz'));meta=json.loads(locked(p,root/'asset.json').read_text())
    np.testing.assert_allclose(np.einsum('nij,njk->nik',paths['bary'],mesh['tri'][paths['face']]),paths['points'],rtol=0,atol=1e-9)
    return mesh,paths,meta

def build():
    p=protocol();mesh,paths,meta=asset(p);root=fresh(UNIT/'build_match')
    masses=dict(cross=0.,base=0.);records=[]
    for c in p['scene']['build_cameras']:
        old=read_npz(locked(p,PREV/'results/lego/build_views'/c['view']/'BUILD.npz'))
        pair,hi=render_pair(mesh,paths,meta,c)
        np.testing.assert_array_equal(pair['cross'],old['ink'])
        np.testing.assert_array_equal(hi['regions'],old['regions'])
        target=hi['regions']==4;row=dict(view=c['view'],legacy_cross_exact=True)
        for arm in masses:
            image,_=compose(old['paper'],pair[arm],old['support'],True,ink_color=p['ink_color'])
            mass=float(np.abs(image-old['paper'])[target].sum(dtype=float));masses[arm]+=mass;row[arm]=mass
        np.savez_compressed(root/(c['view']+'.npz'),cross=pair['cross'],base=pair['base'],paper=old['paper'],support=old['support'],regions=old['regions'])
        records.append(row);print('BUILD',row,flush=True)
    scales,budget=match_scales(masses);checks={k:0. for k in masses}
    for c in p['scene']['build_cameras']:
        a=read_npz(root/(c['view']+'.npz'));target=a['regions']==4
        for arm in masses:
            image,_=compose(a['paper'],a[arm],a['support'],True,scales[arm],p['ink_color'])
            checks[arm]+=float(np.abs(image-a['paper'])[target].sum(dtype=float))
    relative={k:abs(v-budget)/budget for k,v in checks.items()};assert max(relative.values())<1e-5
    data=dict(utc=now(),records=records,unscaled_target_visible_ink_L1=masses,scales=scales,budget=budget,
        actual_matched_target_visible_ink_L1=checks,relative_errors=relative,
        path_segments=len(paths['points']),stroke_ids=len(np.unique(paths['stroke_id'])),
        layer_segments={str(k):int((paths['layer_id']==k).sum()) for k in (0,1)},
        layer_stroke_ids={str(k):len(np.unique(paths['stroke_id'][paths['layer_id']==k])) for k in (0,1)})
    js(UNIT/'BUILD_MATCH.json',data)
    js(UNIT/'BUILD_LOCK.json',dict(files={str(f.relative_to(UNIT)):sha(f) for f in list(root.glob('*.npz'))+[UNIT/'BUILD_MATCH.json']}))
    print('MATCH',data,flush=True)

def match():
    lock=json.loads((UNIT/'BUILD_LOCK.json').read_text())
    for f,h in lock['files'].items():assert sha(UNIT/f)==h,f
    return json.loads((UNIT/'BUILD_MATCH.json').read_text())

def actual_source(p,c,folder):
    import base_model as base
    from link_renderer import Renderer,validate_trace
    from membership import load_binding
    s=p['scene'];a=base.load_source(str(locked(p,s['source']['original_ply'])),s['source']['sha256'])
    a['source_index']=np.arange(len(a['means']),dtype=np.int64)
    b,_=load_binding(locked(p,s['binding']),s['source']['sha256'],len(a['means']))
    selection=read_npz(locked(p,PREV/'results/lego/SELECTION.npz'))
    primary=region_strength(b);np.testing.assert_array_equal(primary,selection['primary'])
    np.testing.assert_array_equal(a['source_index'],selection['source_index'])
    before=array_hashes(a);r=Renderer(UNIT/'build')
    yy,xx=np.mgrid[3:c['height']:15,3:c['width']:15];xy=np.column_stack([xx.ravel(),yy.ravel()])
    source,tr=r.render(a,c,xy,primary);paper,_=r.render(paper_copy(a,c,primary,p['paper']),c)
    check=validate_trace(a,c,xy,source,tr)
    ids=tr['source_index'];sid=tr['sample_index'];w=tr['weight'];n=len(xy)
    colors=base.source_colors(a,c);t=primary[ids]
    colors=colors[ids]*(1-t[:,None])+np.array(p['paper'])*t[:,None]
    recon=np.repeat((1-np.bincount(sid,w,minlength=n))[:,None],3,axis=1)
    for j in range(3):recon[:,j]+=np.bincount(sid,w*colors[:,j],minlength=n)
    xx,yy=xy.T;sp=np.bincount(sid,w*t,minlength=n)
    check.update(paper_error=float(np.max(np.abs(recon-paper['rgb'][yy,xx]))),support_error=float(np.max(np.abs(sp-source['contribution'][yy,xx]))))
    assert check['paper_error']<1e-6 and check['support_error']<1e-6
    assert array_hashes(a)==before
    np.testing.assert_array_equal(source['alpha'],paper['alpha'])
    np.savez_compressed(folder/'TRACE.npz',**tr,xy=xy)
    return dict(source=source['rgb'],paper=paper['rgb'],support=source['contribution'],alpha=source['alpha']),dict(kind='new_complete_original_GS_renders',trace=check,source_array_hashes=before,source_arrays_unchanged=True)

def evaluate(kind,index):
    p=protocol();m=match();mesh,paths,meta=asset(p)
    c=(p['scene']['evaluation_cameras'] if kind=='dev' else p['arc_cameras'])[index]
    folder=fresh(UNIT/kind/c['view'])
    cached=(kind=='dev' or (kind=='arc' and index==4))
    if cached:
        old=read_npz(locked(p,PREV/'results/lego'/c['view']/'FRAME.npz'))
        a={k:old[k] for k in ('source','paper','support','alpha')}
        provenance=dict(kind='immutable_unit001_complete_original_GS_cache',file=str(PREV/'results/lego'/c['view']/'FRAME.npz'),sha256=p['input_hashes'][str(PREV/'results/lego'/c['view']/'FRAME.npz')])
        if kind=='arc':
            existing=p['scene']['evaluation_cameras'][1]
            np.testing.assert_array_equal(c['extrinsic'],existing['extrinsic'])
    else: a,provenance=actual_source(p,c,folder)
    pair,hi=render_pair(mesh,paths,meta,c);regions=hi['regions'];target=regions==4
    if cached:
        np.testing.assert_array_equal(pair['cross'],old['reference_ink'])
        np.testing.assert_array_equal(regions,old['proxy_regions'])
    images={k:a[k] for k in ('source','paper')};alphas={};metrics={};inks={};shapes={};lengths={}
    for arm in ('cross','base'):
        for level,scale in [('raw',1.),('matched',m['scales'][arm])]:
            key=arm+'_'+level
            im,alpha=compose(a['paper'],pair[arm],a['support'],True,scale,p['ink_color'])
            images[key]=im;alphas[key]=alpha
            metrics[key]=edit_metrics(a['source'],im,regions)
            inks[key]=ink_metrics(a['paper'],im,alpha,pair['cross'],regions)
            shapes[key]=ink_shape(alpha,target)
            lengths[key]=projected_length(paths,c,alpha,(0,1) if arm=='cross' else (0,))
    if cached:np.testing.assert_array_equal(images['cross_raw'],old['hybrid_gated'])
    images['intent']=np.repeat(hi['proxy'][:,:,None],3,axis=2);images['intent'][target]=[1.,.32,.40]
    for key,value in images.items():png(folder/(key+'.png'),value)
    for key,alpha in alphas.items():png(folder/(key+'_ink.png'),1-alpha)
    np.savez_compressed(folder/'FRAME.npz',**images,**{k+'_alpha':v for k,v in alphas.items()},
        support=a['support'],source_alpha=a['alpha'],regions=regions,proxy_depth=hi['depth'],cross_ink=pair['cross'],base_ink=pair['base'],second_ink=pair['second'])
    metrics['paper']=edit_metrics(a['source'],a['paper'],regions)
    row=dict(camera=c,provenance=provenance,legacy_cross_exact=cached,metrics=metrics,ink=inks,shape=shapes,
        length_proxy=lengths,support_target_mean=float(a['support'][target].mean()),scope=p['scope'])
    js(folder/'EVALUATION.json',row)
    panel(folder/'COMPARISON.png',[images[k] for k in ('source','intent','paper','cross_raw','cross_matched','base_matched')],
        ['Original GS / full SH3','Authored region4 / fixed','Actual GS paper / fixed','Cross / unit001 strength','Cross / BUILD ink matched','Single direction / BUILD ink matched'],
        c['view']+' | Original-GS paper + proxy ink; fixed original IDs; exposed DEV / diagnostic arc')
    panel(folder/'INK_COMPARISON.png',[1-alphas[k] for k in ('cross_raw','base_raw','cross_matched','base_matched')],
        ['Cross / raw ink','Single / raw ink','Cross / matched ink','Single / matched ink'],
        'Same 3D paths and visibility. Ink effects reported separately from paper.',columns=2)
    js(folder/'COMPLETED.json',dict(utc=now(),files={f.name:sha(f) for f in folder.iterdir() if f.is_file()}))
    print('EVAL',kind,index,c['view'],json.dumps({k:dict(ink=v['target_visible_ink_L1'],pixels=shapes[k]['visible']['pixels'],components=shapes[k]['visible']['components']) for k,v in inks.items()}),flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','build','dev','arc']);ap.add_argument('--index',type=int,default=0)
    args=ap.parse_args();started=time.monotonic()
    if args.stage=='freeze':freeze()
    elif args.stage=='build':build()
    else:evaluate(args.stage,args.index)
    print('DONE',args.stage,args.index,round(time.monotonic()-started,3),'seconds',flush=True)

if __name__=='__main__':main()
