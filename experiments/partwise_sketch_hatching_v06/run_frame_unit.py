"""Unit010 single BUILD-derived cutting frame versus exact legacy XZ frame.

Immutable unit008 original-GS paper/S caches are reused; the changed proxy ink
is rasterized anew. audit_frame_unit provides a full-GS cold replay control.
"""
import runtime
from runtime import ACTIVE_UNIT as UNIT,output_guard,js,sha,now
from pathlib import Path
import argparse,json,shutil
import numpy as np
from scipy import ndimage
from geometry import mesh_data
from local_frame import fit_frame,direction_diagnostic,regenerate_partitions
from target_completion import render_pair
from hybrid import compose,edit_metrics
from run_hybrid import read_npz,png,panel

HERE=Path(__file__).resolve().parent
OLD=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_008')
PREVIOUS=OLD.parent/'unit_009'
ARMS=('xz','local')

def fresh(path):
    assert UNIT.name=='unit_010'
    path=output_guard(path)
    if UNIT not in path.parents:raise ValueError('unit010 output required')
    path.mkdir(parents=True,exist_ok=False);return path

def freeze():
    assert UNIT.name=='unit_010' and not (UNIT/'PROTOCOL.json').exists()
    d=json.loads((UNIT/'DECISION.json').read_text());assert d['action']=='continue'
    old=json.loads((OLD/'PROTOCOL.json').read_text());scene=old['scene']
    files=[UNIT/'DECISION.json',PREVIOUS/'REPORT_ZH.md',PREVIOUS/'STATUS.json',PREVIOUS/'PROTOCOL.json',
           OLD/'PROTOCOL.json',OLD/'PROTOCOL_LOCK.json',OLD/'CAMERAS.json',OLD/'SELECTION.npz',OLD/'SOURCE_BINDING.npz',
           OLD/'INPUT_LOCK.json',OLD/'SOURCE_LOCK.json',Path(scene['asset'])/'asset.json',Path(scene['source']['original_ply'])]
    files += [f for f in (OLD/'asset').iterdir() if f.is_file()]
    views=[]
    for v in json.loads((OLD/'CAMERAS.json').read_text())['views']:
        c=v['camera'];kind=v['kind'];cache=OLD/'build_match'/(c['view']+'.npz') if kind=='build' else OLD/kind/c['view']/'FRAME.npz'
        item=dict(kind=kind,camera=c,cache=str(cache));files.append(cache)
        if kind=='build':item['first_hit']=str(OLD/'authoring'/c['view']/'FIRST_HIT.npz');files.append(Path(item['first_hit']))
        else:item['trace']=str(OLD/kind/c['view']/'TRACE.npz');files.append(Path(item['trace']))
        views.append(item)
    locks={str(f):sha(f) for f in files};assert locks[scene['source']['original_ply']]==scene['source']['sha256']
    prior=json.loads((PREVIOUS/'INPUT_LOCK.json').read_text())['files']
    for f,h in locks.items():
        if f in prior:assert h==prior[f],f
    (UNIT/'scratch').mkdir(exist_ok=True)
    snap=UNIT/'source_snapshot';shutil.copytree(HERE,snap,ignore=shutil.ignore_patterns('__pycache__'))
    js(UNIT/'INPUT_LOCK.json',dict(files=locks));js(UNIT/'SOURCE_LOCK.json',dict(files={f.name:sha(f) for f in snap.iterdir() if f.is_file()}))
    js(UNIT/'CAMERAS.json',dict(views=views,camera_scope='4 BUILD;4 exposed DEV;9 exposed rear arc;12 unique evaluation cameras, no independent generalization'))
    p=dict(unit='unit_010',frozen_utc=now(),decision_sha256=sha(UNIT/'DECISION.json'),scene=scene,
        question='Does a BUILD-only macroscopic tangent reference frame improve visible original-ID-linked partwise hatching?',
        changed_variable=d['changed_variable'],falsification=d['falsification'],paper=old['paper'],ink_color=.03,fps=4,
        frame_rule='Unique BUILD first-hit target faces; area-weighted normal dyads; exact triangle-area position covariance projected into dominant tangent plane; fixed signs; no search.',
        degeneracy_rule='normal relative eigengap<=1e-6 refuses frame; tangent eigengap<=1e-6 uses most projected world axis, deterministic x/y/z tie; no result-dependent fallback',
        slicing='Angles35/95; spacing.06/.075;length.12;gap.035;width1;world origin0;phase.1732050807568877;old2030/added91 groups generated separately',
        matching='Four BUILD target raw RGB ink L1; minimum natural total; one global attenuation per arm; both natural and matched results; no DEV fitting',
        fixed='Original310475 rows/order/geometry/covariance/opacity/fullSH;target2121;paper41058 same unit008 weights;ink21006 same weights;M1 UNKNOWN195279;visibility.004;AA2;band2',
        cache_policy='Reuse hashed unit008 full original-GS paper/S/source; new paths actually rendered; validate original-ID traces and cold full-GS replay independently',
        scope=old['scope'],acceptance='Clearer whole-object surface direction and cleaner part style in most DEV including weak241/24 without material coverage or other-part degradation; numbers alone insufficient',
        negatives='All unit001-009 negatives, interruptions and v05 far8.044%/region visible4.49% preserved; no retroactive pass',
        frozen_files={n:sha(UNIT/n) for n in ('INPUT_LOCK.json','SOURCE_LOCK.json','CAMERAS.json')},
        resources=dict(serial=True,CPU_affinity=2,numeric_threads=1,GPU=False),deadline_jst='2026-10-23T21:45:00+09:00')
    js(UNIT/'PROTOCOL.json',p);js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json')))
    js(UNIT/'STATUS.json',dict(execution_state='partial',stage='frozen_before_frame_derivation_and_evaluation',scientific_verdict='pending',
        gaussian_link_progress='Source rows and original-ID responsibility fixed; no visual result yet',scientific_seal=False,blockers=[]))
    print('FROZEN',len(locks),'inputs',sha(UNIT/'PROTOCOL.json'),flush=True)

def protocol():
    p=json.loads((UNIT/'PROTOCOL.json').read_text());assert p['unit']==UNIT.name=='unit_010'
    assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    assert sha(UNIT/'DECISION.json')==p['decision_sha256']
    for n,h in p['frozen_files'].items():assert sha(UNIT/n)==h,n
    for n,h in json.loads((UNIT/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(HERE/n)==h,n
    p.update(json.loads((UNIT/'CAMERAS.json').read_text()));p['inputs']=json.loads((UNIT/'INPUT_LOCK.json').read_text())['files'];return p

def locked(p,path):
    path=Path(path);assert sha(path)==p['inputs'][str(path)],str(path);return path

def original_asset(p):
    t=read_npz(locked(p,OLD/'asset/TARGET.npz'))
    oldmesh=mesh_data(t['vertices'],t['faces'],t['old_face_regions']);newmesh=mesh_data(t['vertices'],t['faces'],t['face_regions'])
    old=read_npz(locked(p,OLD/'asset/OLD_PATHS.npz'));added=read_npz(locked(p,OLD/'asset/ADDED_PATHS.npz'))
    meta=json.loads(locked(p,Path(p['scene']['asset'])/'asset.json').read_text())
    return oldmesh,newmesh,old,added,meta

def derive():
    p=protocol();oldmesh,mesh,old,added,meta=original_asset(p);out=fresh(UNIT/'asset');visible=[]
    for v in (v for v in p['views'] if v['kind']=='build'):
        face=read_npz(locked(p,v['first_hit']))['face'];ids=np.unique(face[face>=0]);visible.append(ids[mesh['regions'][ids]==4])
    ids=np.unique(np.concatenate(visible));frame=fit_frame(mesh,ids)
    js(out/'FRAME.json',frame);np.savez_compressed(out/'BUILD_FACES.npz',face_ids=ids)
    diagnostics={}
    for arm,basis in [('xz',[[1,0,0],[0,0,1]]),('local',frame['basis'])]:
        arrays,summary=direction_diagnostic(mesh,ids,basis);np.savez_compressed(out/(arm+'_DIRECTION.npz'),**arrays);diagnostics[arm]=summary
    # Explicit legacy branch must reconstruct all old arrays including IDs/masks.
    a,b=regenerate_partitions(oldmesh,mesh,old,added,meta['styles']['4'],[[1,0,0],[0,0,1]],revision=False)
    for actual,expected in [(a,old),(b,added)]:
        for key in expected:np.testing.assert_array_equal(actual[key],expected[key])
    a,b=regenerate_partitions(oldmesh,mesh,old,added,meta['styles']['4'],frame['basis'])
    np.savez_compressed(out/'LOCAL_OLD_PARTITION.npz',**a);np.savez_compressed(out/'LOCAL_ADDED_PARTITION.npz',**b)
    assert not np.isin(np.concatenate([a['stroke_id'],b['stroke_id']]),np.concatenate([old['stroke_id'],added['stroke_id']])).any()
    for paths,mask in [(a,oldmesh['regions']==4),(b,(mesh['regions']==4)&(oldmesh['regions']!=4))]:
        assert mask[paths['face']].all()
        np.testing.assert_allclose(paths['points'],np.einsum('nij,njk->nik',paths['bary'],mesh['tri'][paths['face']]),rtol=0,atol=1e-10)
    sel=read_npz(locked(p,OLD/'SELECTION.npz'));binding=read_npz(locked(p,OLD/'SOURCE_BINDING.npz'))
    np.testing.assert_array_equal(sel['source_index'],np.arange(310475));assert int(binding['unknown'].sum())==195279
    assert int((sel['completed_strength']>0).sum())==41058 and int((sel['original_strength']>0).sum())==21006
    np.savez_compressed(out/'SOURCE_LINK.npz',source_index=sel['source_index'],paper_strength=sel['completed_strength'],ink_strength=sel['original_strength'])
    def stats(x,y):return dict(strokes=int(len(np.unique(np.concatenate([x['stroke_id'],y['stroke_id']])))),segments=len(x['points'])+len(y['points']),
        world_length=float(sum(np.linalg.norm(z['points'][:,1]-z['points'][:,0],axis=1).sum() for z in (x,y))))
    js(out/'ASSET.json',dict(frame=frame,diagnostics=diagnostics,xz=stats(old,added),local=stats(a,b),
        target_reference=str(OLD/'asset/TARGET.npz'),old_paths=[str(OLD/'asset/OLD_PATHS.npz'),str(OLD/'asset/ADDED_PATHS.npz')],
        M1_reference=str(OLD/'SOURCE_BINDING.npz'),source_count=310475,paper_rows=41058,ink_rows=21006,UNKNOWN=195279,
        target_faces=2121,legacy_reconstruction_exact=True,scope=p['scope']))
    js(UNIT/'ASSET_LOCK.json',dict(files={str(f.relative_to(UNIT)):sha(f) for f in out.iterdir()}))
    print('FRAME',frame,flush=True);print('DIRECTION',diagnostics,flush=True);print('PATHS',stats(old,added),stats(a,b),flush=True)

def asset(p):
    locks=json.loads((UNIT/'ASSET_LOCK.json').read_text())['files']
    for n,h in locks.items():assert sha(UNIT/n)==h,n
    oldmesh,mesh,old,added,meta=original_asset(p)
    return oldmesh,mesh,read_npz(UNIT/'asset/LOCAL_OLD_PARTITION.npz'),read_npz(UNIT/'asset/LOCAL_ADDED_PARTITION.npz'),meta

def compute(p,v):
    ref=read_npz(locked(p,v['cache']));oldmesh,mesh,old,added,meta=asset(p)
    ink,hi=render_pair(oldmesh,mesh,old,added,meta,v['camera'])
    np.testing.assert_array_equal(hi['regions'],ref['regions']);np.testing.assert_array_equal(hi['old_regions'],ref['old_regions'])
    f=dict(source=ref['source'],paper=ref['new_paper'],support=ref['new_support'],regions=ref['regions'],old_regions=ref['old_regions'],
        xz_ink=ref['new_ink'],local_ink=ink['new'])
    if 'source_alpha' in ref:f['source_alpha']=ref['source_alpha']
    intent=np.repeat(hi['proxy'][:,:,None],3,axis=2);intent[f['regions']==4]=[1,.32,.4];f['intent']=intent
    for arm in ARMS:
        f[arm+'_raw'],f[arm+'_raw_alpha']=compose(f['paper'],f[arm+'_ink'],f['support'],True,ink_color=p['ink_color'])
    np.testing.assert_array_equal(f['xz_raw'],ref['new_raw']);np.testing.assert_array_equal(f['xz_raw_alpha'],ref['new_raw_alpha'])
    return f

def build():
    p=protocol();out=fresh(UNIT/'build_match');records=[];totals={k:0. for k in ARMS}
    for v in (v for v in p['views'] if v['kind']=='build'):
        f=compute(p,v);target=f['regions']==4;row=dict(view=v['camera']['view'])
        for arm in ARMS:row[arm]=float(np.abs(f[arm+'_raw']-f['paper'])[target].sum(dtype=float));totals[arm]+=row[arm]
        np.savez_compressed(out/(v['camera']['view']+'.npz'),**f);records.append(row);print('BUILD',row,flush=True)
    assert min(totals.values())>0;budget=min(totals.values());scales={k:budget/v for k,v in totals.items()};checks={k:0. for k in ARMS}
    for v in (v for v in p['views'] if v['kind']=='build'):
        f=read_npz(out/(v['camera']['view']+'.npz'));target=f['regions']==4
        for arm in ARMS:
            im,_=compose(f['paper'],f[arm+'_ink'],f['support'],True,scales[arm],p['ink_color']);checks[arm]+=float(np.abs(im-f['paper'])[target].sum(dtype=float))
    assert max(abs(v-budget)/budget for v in checks.values())<1e-5
    js(UNIT/'BUILD_MATCH.json',dict(records=records,natural_target_ink_L1=totals,budget=budget,scales=scales,actual_matched_target_ink_L1=checks))
    js(UNIT/'BUILD_LOCK.json',dict(files={str(f.relative_to(UNIT)):sha(f) for f in list(out.iterdir())+[UNIT/'BUILD_MATCH.json']}))
    print('MATCH',totals,scales,flush=True)

def match():
    assert sha(UNIT/'BUILD_MATCH.json')==json.loads((UNIT/'BUILD_LOCK.json').read_text())['files']['BUILD_MATCH.json']
    return json.loads((UNIT/'BUILD_MATCH.json').read_text())

def measure(f):
    regions=f['regions'];target=regions==4;inner=ndimage.binary_erosion(target,iterations=2)
    metrics={};ink={};coverage={}
    for arm in ARMS:
        for mode in ('raw','matched'):
            key=arm+'_'+mode;metrics[key]=edit_metrics(f['source'],f[key],regions);ink[key]=edit_metrics(f['paper'],f[key],regions)
            coverage[key]={n:dict(pixels=int(mask.sum()),ink_pixels=int(((f[key+'_alpha']>.05)&mask).sum()),
                ink_fraction=float((f[key+'_alpha'][mask]>.05).mean()) if mask.any() else None) for n,mask in [('target',target),('interior',inner)]}
    support={n:dict(pixels=int(mask.sum()),mean=float(f['support'][mask].mean()) if mask.any() else None,
        fraction_above_0_05=float((f['support'][mask]>.05).mean()) if mask.any() else None) for n,mask in [('target',target),('interior',inner)]}
    changes={mode:edit_metrics(f['xz_'+mode],f['local_'+mode],regions) for mode in ('raw','matched')}
    return dict(metrics=metrics,ink=ink,coverage=coverage,support=support,changes=changes,paper=edit_metrics(f['source'],f['paper'],regions))

def evaluate(kind,index):
    p=protocol();m=match();v=[v for v in p['views'] if v['kind']==kind][index];c=v['camera'];folder=fresh(UNIT/kind/c['view']);f=compute(p,v)
    for arm in ARMS:f[arm+'_matched'],f[arm+'_matched_alpha']=compose(f['paper'],f[arm+'_ink'],f['support'],True,m['scales'][arm],p['ink_color'])
    measurements=measure(f);np.savez_compressed(folder/'FRAME.npz',**f)
    js(folder/'EVALUATION.json',dict(camera=c,**measurements,legacy_exact=True,paper_and_original_ID_support_fixed=True,scope=p['scope']))
    for key in ('source','paper','intent','xz_raw','local_raw','xz_matched','local_matched'):png(folder/(key+'.png'),f[key])
    for key in ('xz_raw','local_raw','xz_matched','local_matched'):png(folder/(key+'_ink.png'),1-f[key+'_alpha'])
    panel(folder/'COMPARISON.png',[f[k] for k in ('source','intent','paper','xz_raw','local_raw','xz_matched','local_matched')],
        ['Original GS','Fixed authored target','Fixed original-GS paper','World XZ natural','Local frame natural','XZ BUILD ink matched','Local BUILD ink matched'],
        c['view']+' | Fixed original-ID links; different proxy stroke assets',columns=4)
    js(folder/'COMPLETED.json',dict(utc=now(),files={f.name:sha(f) for f in folder.iterdir() if f.is_file()}))
    print('EVAL',kind,c['view'],{k:measurements['ink'][k]['target_full']['raw_L1_sum'] for k in measurements['ink']},flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','derive','build','dev','arc']);ap.add_argument('--index',type=int,default=0);args=ap.parse_args()
    if args.stage in ('dev','arc'):evaluate(args.stage,args.index)
    else:globals()[args.stage]()
