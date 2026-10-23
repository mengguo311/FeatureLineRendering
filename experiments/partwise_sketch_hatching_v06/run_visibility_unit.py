"""Unit003: fixed original-GS-linked substrate, one visibility mechanism."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,output_guard,js,sha,now
from pathlib import Path
import argparse
import json
import shutil
import numpy as np
from geometry import mesh_data
from visibility_intervals import compare_visibility,endpoint_records,stroke_readback
from hybrid import compose,edit_metrics,ink_metrics
from layer_ablation import ink_shape
from run_hybrid import read_npz,png,panel

ROOT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units')
U1=ROOT/'unit_001';U2=ROOT/'unit_002';HERE=Path(__file__).resolve().parent


def fresh(path):
    path=output_guard(path);path.mkdir(parents=True,exist_ok=False);return path


def freeze():
    if (UNIT/'PROTOCOL.json').exists():raise FileExistsError('already frozen')
    decision=json.loads((UNIT/'DECISION.json').read_text());assert decision['action']=='continue'
    prior=json.loads((U2/'PROTOCOL.json').read_text());scene=prior['scene'];asset=Path(scene['asset'])
    files=[UNIT/'DECISION.json',U1/'PROTOCOL.json',U2/'PROTOCOL.json',U2/'STATUS.json',U2/'REPORT_ZH.md',
           Path(scene['source']['original_ply']),Path(scene['binding']),asset/'mesh.npz',asset/'region_4.npz',asset/'asset.json',
           U1/'results/lego/SELECTION.npz',U1/'results/lego/BINDING_LOCK.json']
    views=[]
    for kind,cameras in [('build',scene['build_cameras']),('dev',scene['evaluation_cameras']),('arc',prior['arc_cameras'])]:
        for c in cameras:
            if kind=='build':cache=U1/'results/lego/build_views'/c['view']/'BUILD.npz';meta=U1/'PROTOCOL.json'
            else:cache=U2/kind/c['view']/'FRAME.npz';meta=U2/kind/c['view']/'EVALUATION.json'
            trace=(U1/'results/lego'/c['view']/'TRACE.npz' if kind=='dev' or (kind=='arc' and c['azimuth']==241) else U2/'arc'/c['view']/'TRACE.npz')
            files += [cache,meta]
            if kind!='build':files.append(trace)
            views.append(dict(kind=kind,camera=c,cache=str(cache),metadata=str(meta),trace=str(trace) if kind!='build' else None))
    hashes={str(f):sha(f) for f in files};assert hashes[scene['source']['original_ply']]==scene['source']['sha256']
    for f in (asset/'mesh.npz',asset/'region_4.npz',asset/'asset.json',Path(scene['binding'])):
        assert hashes[str(f)]==prior['input_hashes'][str(f)]
    snap=UNIT/'source_snapshot';shutil.copytree(HERE,snap,ignore=shutil.ignore_patterns('__pycache__'))
    p=dict(unit='unit_003',frozen_utc=now(),decision_sha256=hashes[str(UNIT/'DECISION.json')],scene=scene,views=views,
        question='Do exact centerline visible intervals reduce unintended fixed-stroke clipping and improve whole-object NPR at matched BUILD ink?',
        changed_variable='Visibility primitive only; fixed cross layers {0,1}, paths, 1px width, 2x samples, .004 tolerance, source IDs/weights/paper/S.',
        mechanism='Centerline proxy rays every <=0.25 native pixel; visible sampling cells form intervals; rasterize their capsules; retain unchanged region support and signed owner-plane foreground guard z_plane-z_front<=.004. Legacy uses abs(z_plane-z_front)<=.004 without centerline intervals.',
        interval_uncertainty='Cell endpoints bracket visibility only to <=0.25px; caps may overlap occlusion transitions. Foreground guard remains active. Not exact analytic occlusion.',
        matching='One global attenuation per arm, .95*min(BUILD target hybrid-paper raw RGB L1); both original-strength images retained; no DEV fitting.',
        sampling_reference='Per-stroke own ink coverage sampled at rounded native centerline pixels; no overlap credit from other strokes. Proxy ray visibility is not independent physical GT; grazing and occlusion transitions remain included.',
        endpoint_interpretation='Internal-face stored endpoints are generate_region planned length cuts; mesh/region boundary and ambiguous shared-edge endpoints separately retained. Never bridge different stroke IDs.',
        promotion='Requires actual whole-object readability benefit at matched ink with no foreground show-through; numeric missing-length gain alone insufficient.',
        scope='Exposed diagnostic cameras only. Original-GS paper + original-ID S-linked proxy ink, not native Gaussian hatching, semantics, physical attachment, H1/H2/H3 or temporal certification.',
        source_invariants='Original 310475 rows/order/geometry/covariance/opacity/fullSH fixed; primary selection 20122 and UNKNOWN unchanged. Cached source/paper/S exactly reused.',
        inherited_negatives='v05 241/24 sparse far8.044% and 4.49% coverage; unit001 gate benefit unestablished; unit002 single-layer negative and arc0 outer143/childUNKNOWN remain unchanged.',
        input_hashes=hashes,source_hashes={f.name:sha(f) for f in snap.iterdir() if f.is_file()},
        supersample=2,ink_color=.03,paper=[.95,.95,.95],fps=4,resources=dict(serial=True,CPU_affinity=2,numeric_threads=1,GPU=False))
    js(UNIT/'PROTOCOL.json',p);js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json'),utc=now()))
    print('FROZEN',sha(UNIT/'PROTOCOL.json'),len(hashes),'inputs',flush=True)


def protocol():
    p=json.loads((UNIT/'PROTOCOL.json').read_text())
    assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    assert sha(UNIT/'DECISION.json')==p['decision_sha256']
    for name,h in p['source_hashes'].items():assert sha(HERE/name)==h,name
    return p


def locked(p,path):
    path=Path(path);assert sha(path)==p['input_hashes'][str(path)],str(path);return path


def asset(p):
    root=Path(p['scene']['asset']);m=read_npz(locked(p,root/'mesh.npz'))
    mesh=mesh_data(m['vertices'],m['faces'],m['face_regions']);paths=read_npz(locked(p,root/'region_4.npz'))
    meta=json.loads(locked(p,root/'asset.json').read_text())
    np.testing.assert_allclose(np.einsum('nij,njk->nik',paths['bary'],mesh['tri'][paths['face']]),paths['points'],atol=1e-9,rtol=0)
    return mesh,paths,meta


def get_cache(p,v):
    meta=json.loads(locked(p,v['metadata']).read_text())
    expected=(next(c for c in meta['scenes']['lego']['build_cameras'] if c['view']==v['camera']['view']) if v['kind']=='build' else meta['camera'])
    for k in ('extrinsic','width','height','fx','fy','cx','cy'):np.testing.assert_array_equal(v['camera'][k],expected[k])
    a=read_npz(locked(p,v['cache']))
    if v['kind']=='build':a=dict(a,legacy_ink=a['ink'])
    else:a=dict(a,legacy_ink=a['cross_ink'])
    return a


def aggregate(rows):
    out={}
    for layer in ('all','0','1'):
        r=[x for x in rows if layer=='all' or str(x['layer'])==layer]
        a=dict(strokes=len(r),projected_length=sum(x['projected_length'] for x in r),proxy_visible_length=sum(x['proxy_visible_length'] for x in r),
               rejected_length={k:sum(x['rejected_length'][k] for x in r) for k in ('1','2','3','4')})
        for arm in ('legacy','interval'):
            for mode in ('before_S','raw','matched'):
                key=arm+'_'+mode
                a[key]={k:sum(x[key][k] for x in r) for k in ('visible_supported_length','visible_missing_length','occluded_supported_length','missing_runs','interior_missing_samples')}
        out[layer]=a
    return out


def build():
    p=protocol();mesh,paths,meta=asset(p);out=fresh(UNIT/'build');masses={a:0. for a in ('legacy','interval')};records=[]
    js(UNIT/'STORED_PATH_ENDPOINTS.json',dict(records=endpoint_records(mesh,paths),scope=p['endpoint_interpretation']))
    for v in [v for v in p['views'] if v['kind']=='build']:
        c=v['camera'];a=get_cache(p,v);r=compare_visibility(mesh,paths,meta['styles'],c);target=r['regions']==4
        np.testing.assert_array_equal(r['regions'],a['regions']);np.testing.assert_array_equal(r['ink']['legacy'],a['legacy_ink'])
        row=dict(view=c['view'],legacy_exact=True)
        for arm in masses:
            hybrid,alpha=compose(a['paper'],r['ink'][arm],a['support'],True)
            row[arm]=float(np.abs(hybrid-a['paper'])[target].sum(dtype=float));masses[arm]+=row[arm]
        folder=fresh(out/c['view'])
        np.savez_compressed(folder/'FRAME.npz',source=a['source'],paper=a['paper'],support=a['support'],regions=r['regions'],**{k+'_ink':x for k,x in r['ink'].items()})
        np.savez_compressed(folder/'SAMPLES.npz',**r['samples'])
        sr=stroke_readback(r['samples'],a['support'],dict(legacy=1.,interval=1.))
        js(folder/'ATTRIBUTION.json',dict(diagnostics=r['diagnostics'],aggregate=aggregate(sr),strokes=sr))
        records.append(row);print('BUILD',row,flush=True)
    budget=.95*min(masses.values());assert budget>0;scales={a:budget/v for a,v in masses.items()}
    checks={a:0. for a in masses}
    for v in [v for v in p['views'] if v['kind']=='build']:
        a=read_npz(out/v['camera']['view']/'FRAME.npz');target=a['regions']==4
        for arm in masses:
            image,_=compose(a['paper'],a[arm+'_ink'],a['support'],True,scales[arm])
            checks[arm]+=float(np.abs(image-a['paper'])[target].sum(dtype=float))
    assert max(abs(x-budget)/budget for x in checks.values())<1e-5
    js(UNIT/'BUILD_MATCH.json',dict(utc=now(),records=records,raw_target_visible_ink_L1=masses,budget=budget,scales=scales,actual_matched_L1=checks))
    js(UNIT/'BUILD_LOCK.json',dict(files={str(f.relative_to(UNIT)):sha(f) for f in list(out.rglob('*'))+[UNIT/'BUILD_MATCH.json',UNIT/'STORED_PATH_ENDPOINTS.json'] if f.is_file()}))
    print('MATCH',masses,scales,checks,flush=True)


def match():
    lock=json.loads((UNIT/'BUILD_LOCK.json').read_text())
    for f,h in lock['files'].items():assert sha(UNIT/f)==h,f
    return json.loads((UNIT/'BUILD_MATCH.json').read_text())


def evaluate(kind,index):
    p=protocol();m=match();v=[v for v in p['views'] if v['kind']==kind][index];c=v['camera'];folder=fresh(UNIT/kind/c['view'])
    mesh,paths,meta=asset(p);a=get_cache(p,v);r=compare_visibility(mesh,paths,meta['styles'],c)
    np.testing.assert_array_equal(r['ink']['legacy'],a['legacy_ink']);np.testing.assert_array_equal(r['regions'],a['regions'])
    images={k:a[k] for k in ('source','paper','support')};alphas={};metrics={};inks={};shapes={}
    for arm in ('legacy','interval'):
        for mode,scale in [('raw',1.),('matched',m['scales'][arm])]:
            key=arm+'_'+mode;image,alpha=compose(a['paper'],r['ink'][arm],a['support'],True,scale)
            images[key]=image;alphas[key+'_alpha']=alpha
            metrics[key]=edit_metrics(a['source'],image,r['regions']);inks[key]=ink_metrics(a['paper'],image,alpha,r['ink']['legacy'],r['regions'])
            shapes[key]=ink_shape(alpha,r['regions']==4)
    np.testing.assert_array_equal(images['legacy_raw'],a['cross_raw'])
    metrics['paper']=edit_metrics(a['source'],a['paper'],r['regions'])
    intent=a['source'].copy();intent[r['regions']==4]=[1.,.32,.40];images['intent']=intent
    np.savez_compressed(folder/'FRAME.npz',**images,**alphas,regions=r['regions'],proxy_depth=r['depth'],**{k+'_ink':x for k,x in r['ink'].items()})
    np.savez_compressed(folder/'SAMPLES.npz',**r['samples'])
    sr=stroke_readback(r['samples'],a['support'],m['scales']);ag=aggregate(sr)
    js(folder/'ATTRIBUTION.json',dict(diagnostics=r['diagnostics'],aggregate=ag,strokes=sr,scope=p['sampling_reference']))
    e=dict(camera=c,cache=v['cache'],cache_sha256=p['input_hashes'][v['cache']],legacy_exact=True,metrics=metrics,ink=inks,shape=shapes,attribution=ag,scope=p['scope'])
    js(folder/'EVALUATION.json',e)
    for key,value in images.items():
        if key!='support':png(folder/(key+'.png'),value)
    for key,alpha in alphas.items():png(folder/(key.replace('_alpha','')+'_ink.png'),1-alpha)
    panel(folder/'COMPARISON.png',[images[k] for k in ('source','intent','paper','legacy_raw','legacy_matched','interval_matched')],
          ['Original GS / full SH3','Authored region4','Actual GS paper / fixed','Legacy / original strength','Legacy / BUILD ink matched','Intervals / BUILD ink matched'],c['view']+' | Fixed cross paths, original-ID S; exposed diagnostic')
    panel(folder/'INK_COMPARISON.png',[1-alphas[k+'_alpha'] for k in ('legacy_raw','interval_raw','legacy_matched','interval_matched')],
          ['Legacy / raw','Intervals / raw','Legacy / matched','Intervals / matched'],'Actual proxy ink multiplied by original-ID S; no contrast boost',columns=2)
    js(folder/'COMPLETED.json',dict(utc=now(),files={f.name:sha(f) for f in folder.iterdir() if f.is_file()}))
    print('EVAL',kind,c['view'],'ink',inks['legacy_matched']['target_visible_ink_L1'],inks['interval_matched']['target_visible_ink_L1'],'own_visible_missing',ag['all']['legacy_matched']['visible_missing_length'],ag['all']['interval_matched']['visible_missing_length'],flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','build','dev','arc']);ap.add_argument('--index',type=int,default=0);args=ap.parse_args()
    if args.stage=='freeze':freeze()
    elif args.stage=='build':build()
    else:evaluate(args.stage,args.index)
