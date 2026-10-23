"""Unit006: fixed original-ID-linked strokes, change only their tone weights."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,output_guard,sha,js,now
from pathlib import Path
import argparse
import json
import shutil
import numpy as np
from scipy import ndimage
from geometry import mesh_data
from stroke_tone import stroke_tones,render_tones,ARMS
from hybrid import compose,edit_metrics,ink_metrics
from layer_ablation import ink_shape
from run_hybrid import read_npz,png,panel

HERE=Path(__file__).resolve().parent
PREV=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_005')


def fresh(path):
    path=output_guard(path)
    if UNIT not in path.parents:raise ValueError('unit006 output only')
    path.mkdir(parents=True,exist_ok=False);return path


def freeze():
    assert UNIT.name=='unit_006' and UNIT.parent.parent.name=='partwise_sketch_hatching_gaussian_link_v06'
    if (UNIT/'PROTOCOL.json').exists():raise FileExistsError('protocol already frozen')
    d=json.loads((UNIT/'DECISION.json').read_text());assert d['action']=='continue'
    previous=json.loads((PREV/'PROTOCOL.json').read_text())
    assert sha(PREV/'PROTOCOL.json')==json.loads((PREV/'PROTOCOL_LOCK.json').read_text())['sha256']
    locks=previous['input_hashes'].copy()
    for f,h in locks.items():assert sha(f)==h,f
    for name in ('DECISION.json','PROTOCOL.json','PROTOCOL_LOCK.json','STATUS.json','REPORT_ZH.md','NEXT.json','BUILD_LOCK.json','BUILD_MATCH.json'):
        f=PREV/name;locks[str(f)]=sha(f)
    locks[str(UNIT/'DECISION.json')]=sha(UNIT/'DECISION.json')
    views=[];bl=json.loads((PREV/'BUILD_LOCK.json').read_text())['files']
    for old in previous['views']:
        v=dict(old);name=v['camera']['view']
        if v['kind']=='build':
            ref=PREV/'build_match'/(name+'.npz');assert sha(ref)==bl[str(ref.relative_to(PREV))]
        else:
            ref=PREV/v['kind']/name/'FRAME.npz';receipt=json.loads((ref.parent/'COMPLETED.json').read_text())
            assert sha(ref)==receipt['files']['FRAME.npz']
        locks[str(ref)]=sha(ref);v['reference_cache']=str(ref);views.append(v)
    snap=UNIT/'source_snapshot';shutil.copytree(HERE,snap,ignore=shutil.ignore_patterns('__pycache__'))
    js(UNIT/'CAMERAS.json',dict(views=views,scope='4 BUILD + 4 exposed DEV + 9 exposed arc; 12 unique DEV/arc settings'))
    js(UNIT/'INPUT_LOCK.json',dict(files=locks))
    js(UNIT/'SOURCE_LOCK.json',dict(files={f.name:sha(f) for f in snap.iterdir() if f.is_file()},
        provenance='Tone rasterizer copies existing v06 render._coverage capsule/depth arithmetic; only visible fragment strength changes. Other helpers vendored in VENDOR_PROVENANCE.json.'))
    p=dict(unit='unit_006',frozen_utc=now(),decision_sha256=sha(UNIT/'DECISION.json'),scene=previous['scene'],
        source_selection=previous['source_selection'],region_id=4,paper=[.95,.95,.95],ink_color=.03,supersample=2,fps=4,
        question='Does fixed per-stroke surface-orientation tone improve whole-object linked NPR over constant and shuffled tone at matched visible ink?',
        changed_variable=d['changed_variable'],light=[-.4,-.6,.7],shuffle_seed=1729,
        weights='tau_s=.2+.8*(1-length_mean(abs(unit_face_normal dot normalized_world_light))); invalid face response=0 (tau1); zero-length stroke tau1; each stroke fixed across cameras',
        arms=list(ARMS),raster='Same visible capsule fragments and .004 depth rule; assign strength*tau_s; max at 2x then downsample, multiply original S, compose with fixed paper',
        matching=dict(domain='Sum actual target hybrid-paper raw RGB L1 over four original BUILD views',budget='.95*min(three natural totals)',
            parameter='One global attenuation per arm, no DEV tuning; report natural outputs and common budget / constant natural effect'),
        acceptance='Whole-object surface tone/readability must improve over BOTH constant and layer-shuffled weights at comparable ink, including weak241/24 without obvious other-view degradation. Metrics/self-normal agreement alone cannot promote.',
        metrics=dict(boundary_pixels=2,visible_ink_alpha=.05,visible_change_RGB_L1=.05,
            masks='Full/interior/boundary/far other/background; raw/clipped means/sums, actual ink effect and coverage, actual per-arm DEV budget ratios'),
        fixed='Legacy351 strokes/1904 segments; no unit005 filled gaps; region4,paths,width,angles,spacing,proxy,visibility,S,paper,M1/UNKNOWN and original310475 PLY rows/geometry/covariance/opacity/SH remain unchanged',
        source_link='39474-row appearance permission controls actual original-GS paper; unchanged20122-row weighted alpha*T responsibility S controls proxy ink. Full source-index mapping stored separately from stroke IDs.',
        scope='Exposed diagnostic cameras, manual proxy intent, CPU GS replica; not native Gaussian hatching, physical/semantic truth, H1/H2/H3 or temporal certification',
        negatives='Preserve v05 sparse8.044%/4.49%, v06 units001-005 negative comparisons, unit005 cache failure and historical interruptions; no default promotion assumed',
        frozen_files={name:sha(UNIT/name) for name in ('CAMERAS.json','INPUT_LOCK.json','SOURCE_LOCK.json')},
        resources=dict(serial=True,CPU_affinity=2,numeric_threads=1,GPU=False),deadline_jst='2026-10-23T20:17:11+09:00')
    js(UNIT/'PROTOCOL.json',p);js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json'),utc=now()))
    js(UNIT/'STATUS.json',dict(execution_state='partial',stage='frozen_before_BUILD',scientific_verdict='pending',
        gaussian_link_progress='Single per-stroke tone comparison frozen; no result yet',scientific_seal=False,blockers=[]))
    print('FROZEN',sha(UNIT/'PROTOCOL.json'),len(locks),'inputs',flush=True)


def protocol():
    p=json.loads((UNIT/'PROTOCOL.json').read_text())
    assert p['unit']==UNIT.name=='unit_006'
    assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    assert sha(UNIT/'DECISION.json')==p['decision_sha256']
    for name,h in p['frozen_files'].items():assert sha(UNIT/name)==h,name
    p['views']=json.loads((UNIT/'CAMERAS.json').read_text())['views']
    p['input_hashes']=json.loads((UNIT/'INPUT_LOCK.json').read_text())['files']
    for name,h in json.loads((UNIT/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(HERE/name)==h,name
    return p


def locked(p,path):
    path=Path(path);assert sha(path)==p['input_hashes'][str(path)],str(path);return path


def asset(p):
    root=Path(p['scene']['asset']);m=read_npz(locked(p,root/'mesh.npz'))
    mesh=mesh_data(m['vertices'],m['faces'],m['face_regions'])
    paths=read_npz(locked(p,root/'region_4.npz'));meta=json.loads(locked(p,root/'asset.json').read_text())
    return mesh,paths,meta


def weights():
    p=protocol();mesh,paths,meta=asset(p);out=fresh(UNIT/'asset')
    w,stats=stroke_tones(mesh,paths,light=np.asarray(p['light']),seed=p['shuffle_seed'])
    assert stats['segments']==1904 and stats['strokes']==351
    np.savez_compressed(out/'STROKE_TONES.npz',**w);np.savez_compressed(out/'PATHS.npz',**paths)
    sel=read_npz(locked(p,p['source_selection']))
    np.testing.assert_array_equal(sel['source_index'],np.arange(310475))
    np.savez_compressed(out/'SOURCE_LINK.npz',**{k:sel[k] for k in ('source_index','original_strength','completed_strength','unknown_unchanged','region_id_unchanged','conflict_unchanged')})
    js(out/'WEIGHTS.json',dict(stats,path_sha256=p['input_hashes'][str(Path(p['scene']['asset'])/'region_4.npz')],
        original_source_sha256=p['scene']['source']['sha256'],source_link=p['source_link'],identity='stroke_id identifies proxy strokes; source_index separately preserves every original PLY row'))
    js(UNIT/'ASSET_LOCK.json',dict(files={str(f.relative_to(UNIT)):sha(f) for f in out.iterdir()}))
    print('WEIGHTS',stats,flush=True)


def saved_asset():
    lock=json.loads((UNIT/'ASSET_LOCK.json').read_text())
    for name,h in lock['files'].items():assert sha(UNIT/name)==h,name
    return read_npz(UNIT/'asset/STROKE_TONES.npz'),read_npz(UNIT/'asset/SOURCE_LINK.npz')


def cache(p,v):
    ref=read_npz(locked(p,v['reference_cache']))
    if v['kind']=='build':
        a=read_npz(locked(p,v['paper_cache']));b=read_npz(locked(p,v['legacy_cache']))
        np.testing.assert_array_equal(a['source'],b['source']);np.testing.assert_array_equal(a['regions'],b['regions'])
        _,alpha=compose(a['completed_paper'],b['legacy_ink'],b['support'],True,ink_color=p['ink_color'])
        for name,value in [('source',a['source']),('paper',a['completed_paper']),('support',b['support']),('old_alpha',alpha)]:np.testing.assert_array_equal(ref[name],value)
        return dict(source=a['source'],paper=a['completed_paper'],support=b['support'],regions=a['regions'],old_alpha=alpha,old_ink=ref['old_ink'])
    metadata=json.loads(locked(p,v['metadata']).read_text())
    for k in ('extrinsic','width','height','fx','fy','cx','cy'):np.testing.assert_array_equal(v['camera'][k],metadata['camera'][k])
    a=read_npz(locked(p,v['cache']))
    for name,value in [('source',a['source']),('paper',a['completed_paper']),('support',a['support']),('old_raw',a['completed_hybrid']),('old_raw_alpha',a['fixed_ink_alpha'])]:np.testing.assert_array_equal(ref[name],value)
    return dict(source=a['source'],paper=a['completed_paper'],support=a['support'],regions=a['regions'],
        old_alpha=a['fixed_ink_alpha'],old_hybrid=a['completed_hybrid'],alpha=a['alpha'],old_ink=ref['old_ink'])


def build():
    p=protocol();mesh,paths,meta=asset(p);w,link=saved_asset();out=fresh(UNIT/'build_match')
    totals={k:0. for k in ARMS};records=[]
    for v in (v for v in p['views'] if v['kind']=='build'):
        c=v['camera'];a=cache(p,v);pair,hi=render_tones(mesh,paths,meta,c,w)
        np.testing.assert_array_equal(hi['regions'],a['regions']);np.testing.assert_array_equal(pair['constant'],a['old_ink'])
        target=a['regions']==4;row=dict(view=c['view'])
        for arm in ARMS:
            im,alpha=compose(a['paper'],pair[arm],a['support'],True,ink_color=p['ink_color'])
            if arm=='constant':np.testing.assert_array_equal(alpha,a['old_alpha'])
            row[arm]=float(np.abs(im-a['paper'])[target].sum(dtype=float));totals[arm]+=row[arm]
        np.savez_compressed(out/(c['view']+'.npz'),**a,**{k+'_ink':value for k,value in pair.items()});records.append(row)
        print('BUILD',row,flush=True)
    budget=.95*min(totals.values());assert budget>0;scales={k:budget/v for k,v in totals.items()};checks={k:0. for k in ARMS}
    for v in (v for v in p['views'] if v['kind']=='build'):
        a=read_npz(out/(v['camera']['view']+'.npz'));target=a['regions']==4
        for arm in ARMS:
            im,_=compose(a['paper'],a[arm+'_ink'],a['support'],True,scales[arm],p['ink_color'])
            checks[arm]+=float(np.abs(im-a['paper'])[target].sum(dtype=float))
    assert max(abs(x-budget)/budget for x in checks.values())<1e-5
    js(UNIT/'BUILD_MATCH.json',dict(utc=now(),records=records,natural_target_ink_L1=totals,budget=budget,scales=scales,
        budget_fraction_of_constant_natural=budget/totals['constant'],actual_matched_target_ink_L1=checks))
    js(UNIT/'BUILD_LOCK.json',dict(files={str(f.relative_to(UNIT)):sha(f) for f in list(out.iterdir())+[UNIT/'BUILD_MATCH.json']}))
    print('MATCH',totals,scales,checks,flush=True)


def match():
    lock=json.loads((UNIT/'BUILD_LOCK.json').read_text())
    for name,h in lock['files'].items():assert sha(UNIT/name)==h,name
    return json.loads((UNIT/'BUILD_MATCH.json').read_text())


def evaluate(kind,index):
    p=protocol();m=match();v=[v for v in p['views'] if v['kind']==kind][index];c=v['camera'];a=cache(p,v)
    mesh,paths,meta=asset(p);w,link=saved_asset();out=fresh(UNIT/kind/c['view'])
    pair,hi=render_tones(mesh,paths,meta,c,w);regions=hi['regions']
    np.testing.assert_array_equal(regions,a['regions']);np.testing.assert_array_equal(pair['constant'],a['old_ink'])
    images=dict(source=a['source'],paper=a['paper']);alphas={};metrics={};inks={};shapes={};ink_regions={}
    for arm in ARMS:
        for mode,scale in [('raw',1.),('matched',m['scales'][arm])]:
            name=arm+'_'+mode;im,alpha=compose(a['paper'],pair[arm],a['support'],True,scale,p['ink_color'])
            images[name]=im;alphas[name]=alpha;metrics[name]=edit_metrics(a['source'],im,regions)
            ink_regions[name]=edit_metrics(a['paper'],im,regions)
            inks[name]=ink_metrics(a['paper'],im,alpha,pair['constant'],regions);shapes[name]=ink_shape(alpha,regions==4)
    np.testing.assert_array_equal(alphas['constant_raw'],a['old_alpha']);np.testing.assert_array_equal(images['constant_raw'],a['old_hybrid'])
    images['intent']=np.repeat(hi['proxy'][:,:,None],3,axis=2);images['intent'][regions==4]=[1.,.32,.40]
    changes={arm+'_'+mode:edit_metrics(images['constant_'+mode],images[arm+'_'+mode],regions)
             for arm in ('tone','shuffled') for mode in ('raw','matched')}
    metrics['paper']=edit_metrics(a['source'],a['paper'],regions)
    target=regions==4;inner=ndimage.binary_erosion(target,iterations=2)
    support={name:dict(pixels=int(mask.sum()),mean=float(a['support'][mask].mean()),
        mass=float(a['support'][mask].sum(dtype=float)),fraction_above_0_05=float((a['support'][mask]>.05).mean())) for name,mask in [('target',target),('interior',inner)]}
    np.savez_compressed(out/'FRAME.npz',**images,**{k+'_alpha':value for k,value in alphas.items()},
        **{k+'_ink':value for k,value in pair.items()},support=a['support'],source_alpha=a['alpha'],regions=regions,
        stroke_visible_fragments=hi['stroke_visible_fragments'])
    js(out/'EVALUATION.json',dict(camera=c,metrics=metrics,ink=inks,ink_regions=ink_regions,shape=shapes,changes=changes,
        support=support,raster_diagnostics=hi['diagnostics'],constant_result_exact=True,paper_and_S_fixed=True,
        cache_sha256=p['input_hashes'][v['cache']],scope=p['scope']))
    for name,img in images.items():png(out/(name+'.png'),img)
    for name,alpha in alphas.items():png(out/(name+'_ink.png'),1-alpha)
    panel(out/'COMPARISON.png',[images[k] for k in ('source','intent','paper','constant_raw','tone_raw','shuffled_raw')],
        ['Original GS / full SH3','Fixed authored region4','Fixed completed GS paper','Constant ink / natural','Surface tone / natural','Shuffled tone / natural'],c['view']+' | Fixed original-ID S; fixed351 proxy strokes',columns=3)
    keys=[arm+'_matched' for arm in ARMS]
    panel(out/'MATCHED_COMPARISON.png',[images[k] for k in keys]+[1-alphas[k] for k in keys],
        ['Constant / matched','Surface tone / matched','Shuffled / matched','Constant ink only','Surface tone ink only','Shuffled ink only'],
        'Actual visible RGB ink matched on four BUILD views; no per-view fitting',columns=3)
    js(out/'COMPLETED.json',dict(utc=now(),files={f.name:sha(f) for f in out.iterdir() if f.is_file()}))
    print('EVAL',kind,c['view'],{k:dict(ink=inks[k]['target_visible_ink_L1'],pixels=shapes[k]['visible']['pixels']) for k in inks},flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','weights','build','dev','arc']);ap.add_argument('--index',type=int,default=0);args=ap.parse_args()
    if args.stage in ('freeze','weights','build'):globals()[args.stage]()
    else:evaluate(args.stage,args.index)
