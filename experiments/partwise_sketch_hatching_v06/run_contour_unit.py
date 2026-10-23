"""Unit007: owner-aware view contours, with fixed original-GS paper and S.

Adapted from unit006 run_tone_unit; old arrays are read-only inputs.
"""
import runtime
from runtime import ACTIVE_UNIT as UNIT,output_guard,sha,js,now
from pathlib import Path
import argparse
import json
import shutil
import numpy as np
from scipy import ndimage
from geometry import mesh_data
from hybrid import compose,edit_metrics,ink_metrics
from layer_ablation import ink_shape
from run_hybrid import read_npz,png,panel

HERE=Path(__file__).resolve().parent
PREV=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_006')
ARMS=('hatch','outlined')


def fresh(path):
    path=output_guard(path)
    if UNIT not in path.parents:raise ValueError('current unit output only')
    path.mkdir(parents=True,exist_ok=False);return path


def freeze():
    assert UNIT.name=='unit_007'
    if (UNIT/'PROTOCOL.json').exists():raise FileExistsError('already frozen')
    d=json.loads((UNIT/'DECISION.json').read_text());assert d['action']=='continue'
    prev=json.loads((PREV/'PROTOCOL.json').read_text())
    assert sha(PREV/'PROTOCOL.json')==json.loads((PREV/'PROTOCOL_LOCK.json').read_text())['sha256']
    locks=json.loads((PREV/'INPUT_LOCK.json').read_text())['files'].copy()
    for f,h in locks.items():assert sha(f)==h,f
    names=['DECISION.json','PROTOCOL.json','PROTOCOL_LOCK.json','CAMERAS.json','INPUT_LOCK.json','SOURCE_LOCK.json',
           'STATUS.json','REPORT_ZH.md','NEXT.json','BUILD_LOCK.json','BUILD_MATCH.json','ASSET_LOCK.json']
    for name in names:locks[str(PREV/name)]=sha(PREV/name)
    locks[str(UNIT/'DECISION.json')]=sha(UNIT/'DECISION.json')
    views=[];bl=json.loads((PREV/'BUILD_LOCK.json').read_text())['files']
    for old in json.loads((PREV/'CAMERAS.json').read_text())['views']:
        v=dict(old);name=v['camera']['view']
        ref=PREV/'build_match'/(name+'.npz') if v['kind']=='build' else PREV/v['kind']/name/'FRAME.npz'
        expected=bl[str(ref.relative_to(PREV))] if v['kind']=='build' else json.loads((ref.parent/'COMPLETED.json').read_text())['files']['FRAME.npz']
        assert sha(ref)==expected;locks[str(ref)]=expected;v['reference_cache']=str(ref);views.append(v)
    snap=UNIT/'source_snapshot';shutil.copytree(HERE,snap,ignore=shutil.ignore_patterns('__pycache__'))
    assert not (snap/'linked_contours.py').exists(),'RED snapshot must precede implementation'
    js(UNIT/'CAMERAS.json',dict(views=views,scope='4 BUILD + 4 exposed DEV + 9 exposed arc; DEV/arc12 distinct settings'))
    js(UNIT/'INPUT_LOCK.json',dict(files=locks))
    js(UNIT/'SOURCE_LOCK.json',dict(files={f.name:sha(f) for f in snap.iterdir() if f.is_file()},
        provenance='Unchanged v06 helpers; unit007 runner/audit/media/tests adapted from unit006. Initial immutable pre-implementation TDD snapshot.'))
    p=dict(unit='unit_007',frozen_utc=now(),decision_sha256=sha(UNIT/'DECISION.json'),scene=prev['scene'],
        source_selection=prev['source_selection'],region_id=4,paper=[.95,.95,.95],ink_color=.03,supersample=2,fps=4,
        question='Do foreground-owned view contours improve whole-object linked NPR at the old natural visible ink budget?',
        changed_variable=d['changed_variable'],arms=list(ARMS),
        contour=dict(depth_jump=.035,strength=.85,silhouette='hit minus binary erosion(hit, iterations=2), foreground side',
            depth_edge='Nonwrapping 4-neighbor pairs; finite depth jump >.035 assigned only to nearer pixel; keep owner region4',
            limitations='Heuristic proxy depth edges, including reconstruction holes/slope artifacts; not confirmed structural curves.'),
        raster='Old high-resolution hatch unchanged; max(hatch,owned contour) at2x, average resolve, multiply fixed original-row S, fixed GS paper',
        matching=dict(domain='Four BUILD target hybrid-paper raw RGB L1 sum',budget='100% of old constant natural ink',
            parameter='hatch scale1; outlined one global scale=old total/outlined total; natural arms retained; no DEV fitting'),
        acceptance=d['falsification'],metrics=dict(boundary_pixels=2,visible_ink_alpha=.05,visible_change_RGB_L1=.05),
        fixed='Old351 strokes/1904 segments; region4,paths,width,angles,spacing,.004 visibility,S,paper,M1/UNKNOWN, original310475 rows/geometry/covariance/opacity/SH',
        source_link='39474 original rows authorize fixed paper; unchanged20122-row weighted alpha*T responsibility S controls all ink. Proxy stroke and view-contour identities are not source IDs.',
        scope='Exposed diagnostic cameras, manual proxy intent, CPU GS replica; no native Gaussian ink, semantic/physical ownership, H1/H2/H3 or temporal certification',
        negatives='v05 sparse8.044%/4.49%; units001-006 negative comparisons and all interruptions preserved',
        tdd_source_policy='Freeze protocol/inputs/cameras/test and all orchestration source first; preserve RED missing linked_contours.py; add only that implementation in immutable source_snapshot_002 and lock before GREEN/BUILD. No outcome tuning.',
        frozen_files={name:sha(UNIT/name) for name in ('CAMERAS.json','INPUT_LOCK.json','SOURCE_LOCK.json')},
        resources=dict(serial=True,CPU_affinity=2,numeric_threads=1,GPU=False),deadline_jst='2026-10-23T20:36:05+09:00')
    js(UNIT/'PROTOCOL.json',p);js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json'),utc=now()))
    js(UNIT/'STATUS.json',dict(execution_state='partial',stage='frozen_before_TDD',scientific_verdict='pending',
        gaussian_link_progress='Owner-aware contour switch protocol frozen; no experimental result',scientific_seal=False,blockers=[]))
    print('FROZEN',sha(UNIT/'PROTOCOL.json'),len(locks),'inputs',flush=True)


def activate():
    assert UNIT.name=='unit_007'
    red=json.loads((UNIT/'logs/tdd_red_001.receipt.json').read_text());assert red['returncode']==1
    initial=json.loads((UNIT/'SOURCE_LOCK.json').read_text())['files']
    current={f.name:sha(f) for f in HERE.iterdir() if f.is_file()}
    assert set(current)-set(initial)=={'linked_contours.py'}
    for name,h in initial.items():assert current[name]==h,name
    snap=UNIT/'source_snapshot_002';shutil.copytree(HERE,snap,ignore=shutil.ignore_patterns('__pycache__'))
    js(UNIT/'EXECUTION_SOURCE_LOCK.json',dict(utc=now(),snapshot=snap.name,files=current,
        initial_source_lock_sha256=sha(UNIT/'SOURCE_LOCK.json'),added=['linked_contours.py'],changed_existing=[],
        reason='Predeclared TDD implementation addition after preserved missing-module RED; before GREEN and any BUILD comparison.'))
    print('IMPLEMENTATION_LOCKED',len(current),'files',flush=True)


def protocol():
    p=json.loads((UNIT/'PROTOCOL.json').read_text());assert p['unit']==UNIT.name=='unit_007'
    assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    assert sha(UNIT/'DECISION.json')==p['decision_sha256']
    for name,h in p['frozen_files'].items():assert sha(UNIT/name)==h,name
    lock=json.loads((UNIT/'EXECUTION_SOURCE_LOCK.json').read_text())
    assert lock['initial_source_lock_sha256']==sha(UNIT/'SOURCE_LOCK.json')
    for name,h in lock['files'].items():assert sha(HERE/name)==h,name
    p['views']=json.loads((UNIT/'CAMERAS.json').read_text())['views']
    p['input_hashes']=json.loads((UNIT/'INPUT_LOCK.json').read_text())['files']
    return p


def locked(p,path):
    path=Path(path);assert sha(path)==p['input_hashes'][str(path)],str(path);return path


def asset(p):
    root=Path(p['scene']['asset']);m=read_npz(locked(p,root/'mesh.npz'))
    return mesh_data(m['vertices'],m['faces'],m['face_regions']),read_npz(locked(p,root/'region_4.npz')),json.loads(locked(p,root/'asset.json').read_text())


def export_asset():
    p=protocol();mesh,paths,meta=asset(p);out=fresh(UNIT/'asset')
    assert len(paths['points'])==1904 and len(np.unique(paths['stroke_id']))==351
    np.savez_compressed(out/'PATHS.npz',**paths)
    sel=read_npz(locked(p,p['source_selection']));np.testing.assert_array_equal(sel['source_index'],np.arange(310475))
    np.savez_compressed(out/'SOURCE_LINK.npz',**{k:sel[k] for k in ('source_index','original_strength','completed_strength','unknown_unchanged','region_id_unchanged','conflict_unchanged')})
    js(out/'ASSET.json',dict(strokes=351,segments=1904,source_count=310475,contour=p['contour'],
        path_sha256=p['input_hashes'][str(Path(p['scene']['asset'])/'region_4.npz')],source_link=p['source_link']))
    js(UNIT/'ASSET_LOCK.json',dict(files={str(f.relative_to(UNIT)):sha(f) for f in out.iterdir()}))
    print('ASSET_EXPORTED',flush=True)


def saved_asset():
    for name,h in json.loads((UNIT/'ASSET_LOCK.json').read_text())['files'].items():assert sha(UNIT/name)==h,name
    return read_npz(UNIT/'asset/SOURCE_LINK.npz')


def cache(p,v):
    ref=read_npz(locked(p,v['reference_cache']))
    if v['kind']=='build':
        return dict(source=ref['source'],paper=ref['paper'],support=ref['support'],regions=ref['regions'],
            old_alpha=ref['old_alpha'],old_ink=ref['constant_ink'])
    metadata=json.loads(locked(p,v['metadata']).read_text())
    for k in ('extrinsic','width','height','fx','fy','cx','cy'):np.testing.assert_array_equal(v['camera'][k],metadata['camera'][k])
    return dict(source=ref['source'],paper=ref['paper'],support=ref['support'],regions=ref['regions'],
        old_alpha=ref['constant_raw_alpha'],old_hybrid=ref['constant_raw'],alpha=ref['source_alpha'],old_ink=ref['constant_ink'])


def build():
    from linked_contours import render_contours
    p=protocol();mesh,paths,meta=asset(p);saved_asset();out=fresh(UNIT/'build_match')
    totals={k:0. for k in ARMS};records=[]
    for v in (v for v in p['views'] if v['kind']=='build'):
        c=v['camera'];a=cache(p,v);pair,hi=render_contours(mesh,paths,meta,c)
        np.testing.assert_array_equal(hi['regions'],a['regions']);np.testing.assert_array_equal(pair['hatch'],a['old_ink'])
        target=a['regions']==4;row=dict(view=c['view'])
        for arm in ARMS:
            im,alpha=compose(a['paper'],pair[arm],a['support'],True,ink_color=p['ink_color'])
            if arm=='hatch':np.testing.assert_array_equal(alpha,a['old_alpha'])
            row[arm]=float(np.abs(im-a['paper'])[target].sum(dtype=float));totals[arm]+=row[arm]
        np.savez_compressed(out/(c['view']+'.npz'),**a,**{k+'_ink':value for k,value in pair.items()},contour_ink=hi['contour_ink'])
        records.append(row);print('BUILD',row,flush=True)
    budget=totals['hatch'];assert budget>0 and totals['outlined']>=budget
    scales=dict(hatch=1.,outlined=budget/totals['outlined']);checks={k:0. for k in ARMS}
    for v in (v for v in p['views'] if v['kind']=='build'):
        a=read_npz(out/(v['camera']['view']+'.npz'));target=a['regions']==4
        for arm in ARMS:
            im,_=compose(a['paper'],a[arm+'_ink'],a['support'],True,scales[arm],p['ink_color'])
            checks[arm]+=float(np.abs(im-a['paper'])[target].sum(dtype=float))
    assert max(abs(x-budget)/budget for x in checks.values())<1e-5
    js(UNIT/'BUILD_MATCH.json',dict(utc=now(),records=records,natural_target_ink_L1=totals,budget=budget,scales=scales,
        budget_fraction_of_constant_natural=1.,actual_matched_target_ink_L1=checks))
    js(UNIT/'BUILD_LOCK.json',dict(files={str(f.relative_to(UNIT)):sha(f) for f in list(out.iterdir())+[UNIT/'BUILD_MATCH.json']}))
    print('MATCH',totals,scales,checks,flush=True)


def match():
    for name,h in json.loads((UNIT/'BUILD_LOCK.json').read_text())['files'].items():assert sha(UNIT/name)==h,name
    return json.loads((UNIT/'BUILD_MATCH.json').read_text())


def evaluate(kind,index):
    from linked_contours import render_contours
    p=protocol();m=match();v=[v for v in p['views'] if v['kind']==kind][index];c=v['camera'];a=cache(p,v)
    mesh,paths,meta=asset(p);saved_asset();out=fresh(UNIT/kind/c['view'])
    pair,hi=render_contours(mesh,paths,meta,c);regions=hi['regions']
    np.testing.assert_array_equal(regions,a['regions']);np.testing.assert_array_equal(pair['hatch'],a['old_ink'])
    images=dict(source=a['source'],paper=a['paper']);alphas={};metrics={};inks={};shapes={};ink_regions={}
    for arm in ARMS:
        for mode,scale in [('raw',1.),('matched',m['scales'][arm])]:
            name=arm+'_'+mode;im,alpha=compose(a['paper'],pair[arm],a['support'],True,scale,p['ink_color'])
            images[name]=im;alphas[name]=alpha;metrics[name]=edit_metrics(a['source'],im,regions)
            ink_regions[name]=edit_metrics(a['paper'],im,regions)
            inks[name]=ink_metrics(a['paper'],im,alpha,pair['hatch'],regions);shapes[name]=ink_shape(alpha,regions==4)
    np.testing.assert_array_equal(alphas['hatch_raw'],a['old_alpha']);np.testing.assert_array_equal(images['hatch_raw'],a['old_hybrid'])
    images['intent']=np.repeat(hi['proxy'][:,:,None],3,axis=2);images['intent'][regions==4]=[1.,.32,.40]
    changes={mode:edit_metrics(images['hatch_raw'],images['outlined_'+mode],regions) for mode in ('raw','matched')}
    metrics['paper']=edit_metrics(a['source'],a['paper'],regions)
    contour_image,contour_alpha=compose(a['paper'],hi['contour_ink'],a['support'],True,ink_color=p['ink_color'])
    target=regions==4;inner=ndimage.binary_erosion(target,iterations=2)
    support={name:dict(pixels=int(mask.sum()),mean=float(a['support'][mask].mean()),mass=float(a['support'][mask].sum(dtype=float)),
        fraction_above_0_05=float((a['support'][mask]>.05).mean())) for name,mask in [('target',target),('interior',inner)]}
    contour=dict(before_S=ink_shape(hi['contour_ink'],target),after_S=ink_shape(contour_alpha,target),
        target_mass_before_S=float(hi['contour_ink'][target].sum(dtype=float)),target_mass_after_S=float(contour_alpha[target].sum(dtype=float)),
        effect=edit_metrics(a['paper'],contour_image,regions),diagnostics=hi['diagnostics'])
    np.savez_compressed(out/'FRAME.npz',**images,**{k+'_alpha':value for k,value in alphas.items()},
        **{k+'_ink':value for k,value in pair.items()},support=a['support'],source_alpha=a['alpha'],regions=regions,
        contour_ink=hi['contour_ink'],contour_alpha=contour_alpha,silhouette_ink=hi['silhouette_ink'],occlusion_ink=hi['occlusion_ink'])
    np.savez_compressed(out/'RASTER.npz',**hi['raster'])
    js(out/'EVALUATION.json',dict(camera=c,metrics=metrics,ink=inks,ink_regions=ink_regions,shape=shapes,changes=changes,
        support=support,contour=contour,hatch_result_exact=True,paper_and_S_fixed=True,scope=p['scope']))
    for name,img in images.items():png(out/(name+'.png'),img)
    for name,alpha in alphas.items():png(out/(name+'_ink.png'),1-alpha)
    png(out/'contour_only.png',1-contour_alpha);png(out/'contour_before_S.png',1-hi['contour_ink'])
    panel(out/'COMPARISON.png',[images[k] for k in ('source','intent','paper','hatch_raw','outlined_raw','outlined_matched')],
        ['Original GS / full SH3','Fixed authored region4','Fixed GS paper','Old hatch / natural','Hatch + owned contour / natural','Hatch + owned contour / matched'],c['view']+' | Fixed original-ID S; fixed351 proxy strokes',columns=3)
    panel(out/'LAYERS.png',[1-alphas['hatch_raw'],1-hi['contour_ink'],1-contour_alpha,1-alphas['outlined_raw'],1-alphas['outlined_matched'],images['outlined_matched']],
        ['Old linked hatch','Proxy contour before S','Linked contour only','Combined ink natural','Combined ink matched','Actual matched hybrid'],
        'Contour is view-dependent proxy ink; S is accepted original-ID responsibility',columns=3)
    js(out/'COMPLETED.json',dict(utc=now(),files={f.name:sha(f) for f in out.iterdir() if f.is_file()}))
    print('EVAL',kind,c['view'],{k:dict(ink=inks[k]['target_visible_ink_L1'],pixels=shapes[k]['visible']['pixels']) for k in inks},flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','activate','export_asset','build','dev','arc']);ap.add_argument('--index',type=int,default=0);args=ap.parse_args()
    if args.stage in ('dev','arc'):evaluate(args.stage,args.index)
    else:globals()[args.stage]()
