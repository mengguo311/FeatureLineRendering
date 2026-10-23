"""Unit009: same original-row support, weighted versus saturated paper.

Only v06/unit009 receives writes. Historical arrays are immutable inputs.
"""
import runtime
from runtime import ACTIVE_UNIT as UNIT,output_guard,js,sha,now
from pathlib import Path
import argparse,json,shutil
import numpy as np
from scipy import ndimage
from saturation import saturate,decompose_residual
from hybrid import paper_copy,edit_metrics
from appearance_completion import apply_fixed_ink,paper_residual
from link_renderer import Renderer,validate_trace
from run_hybrid import read_npz,png,panel,array_hashes
import base_model as base

HERE=Path(__file__).resolve().parent
OLD=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_008')
ARMS=('weighted','saturated')

def fresh(path):
    path=output_guard(path);path.mkdir(parents=True,exist_ok=False);return path

def freeze():
    assert UNIT.name=='unit_009' and not (UNIT/'PROTOCOL.json').exists()
    d=json.loads((UNIT/'DECISION.json').read_text());assert d['action']=='continue'
    old=json.loads((OLD/'PROTOCOL.json').read_text())
    files=[UNIT/'DECISION.json',OLD/'PROTOCOL.json',OLD/'PROTOCOL_LOCK.json',OLD/'CAMERAS.json',OLD/'REPORT_ZH.md',
           OLD/'STATUS.json',OLD/'SELECTION.npz',OLD/'SOURCE_BINDING.npz',OLD/'SOURCE_LOCK.json',OLD/'INPUT_LOCK.json',
           Path(old['scene']['source']['original_ply'])]
    files += [f for f in (OLD/'asset').iterdir() if f.is_file()]
    views=[]
    for v in json.loads((OLD/'CAMERAS.json').read_text())['views']:
        c=v['camera'];kind=v['kind']
        cache=OLD/'build_match'/(c['view']+'.npz') if kind=='build' else OLD/kind/c['view']/'FRAME.npz'
        item=dict(kind=kind,camera=c,cache=str(cache));files.append(cache)
        if kind!='build':
            item['trace']=str(OLD/kind/c['view']/'TRACE.npz');files.append(Path(item['trace']))
        views.append(item)
    locks={str(f):sha(f) for f in files};assert locks[old['scene']['source']['original_ply']]==old['scene']['source']['sha256']
    sel=read_npz(OLD/'SELECTION.npz');b=read_npz(OLD/'SOURCE_BINDING.npz');n=len(sel['source_index'])
    np.testing.assert_array_equal(sel['source_index'],np.arange(310475));assert n==310475
    saturated=saturate(sel['completed_strength']);assert int(saturated.sum())==41058
    assert int((sel['original_strength']>0).sum())==21006 and int(b['unknown'].sum())==195279
    asset=fresh(UNIT/'asset');np.savez_compressed(asset/'SOURCE_LINK.npz',source_index=sel['source_index'],
        weighted_strength=sel['completed_strength'],saturated_strength=saturated,ink_strength=sel['original_strength'])
    js(asset/'REFERENCES.json',dict(target=str(OLD/'asset/TARGET.npz'),paths=str(OLD/'asset/PATHS.npz'),
        binding=str(OLD/'SOURCE_BINDING.npz'),scope='Frozen unit008 target and paths; IDs belong to original PLY rows'))
    locks[str(asset/'SOURCE_LINK.npz')]=sha(asset/'SOURCE_LINK.npz');locks[str(asset/'REFERENCES.json')]=sha(asset/'REFERENCES.json')
    snap=UNIT/'source_snapshot';shutil.copytree(HERE,snap,ignore=shutil.ignore_patterns('__pycache__'))
    js(UNIT/'INPUT_LOCK.json',dict(files=locks));js(UNIT/'SOURCE_LOCK.json',dict(files={f.name:sha(f) for f in snap.iterdir() if f.is_file()}))
    js(UNIT/'CAMERAS.json',dict(views=views,scope='4 BUILD matching,4 exposed DEV,9 exposed rear arc; no new evaluation cameras'))
    p=dict(unit='unit_009',frozen_utc=now(),decision_sha256=sha(UNIT/'DECISION.json'),scene=old['scene'],
        question='Does separating fixed original-row permission from paper strength improve visible local NPR?',
        changed_variable=d['changed_variable'],falsification=d['falsification'],paper=old['paper'],ink_color=.03,fps=4,
        matching='Four BUILD full-frame raw RGB L1 source-paper effect; min natural budget; one global scale per arm. Ink alpha fixed from unit008 new_raw_alpha. Actual matched GS renders; no DEV fitting.',
        decomposition='Signed licensed-unreplaced, unlicensed and white-background terms before clipping; L1 only after vector addition. Dense target, sparse far; full renders for far damage. Endpoint is not optimal residual bound.',
        scope=old['scope'],fixed='unit008 target2121 faces,375 strokes/2004 segments,41058 paper rows,21006 ink rows,195279 UNKNOWN; same original310475 rows/geometry/opacity/fullSH.',
        acceptance='Whole-object cleaner usable local style, including weak241/24, without visible form/other-part degradation. Whiteness or count alone insufficient. Natural-only gains are intensity capacity, not matched-budget superiority.',
        negatives='v05 sparse far8.044%/visible4.49% and every v06 negative preserved; no scope relabeling',
        frozen_files={n:sha(UNIT/n) for n in ('INPUT_LOCK.json','SOURCE_LOCK.json','CAMERAS.json')},
        resources=dict(serial=True,CPU_affinity=2,numeric_threads=1,GPU=False),deadline_jst='2026-10-23T21:08:43+09:00')
    js(UNIT/'PROTOCOL.json',p);js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json')))
    js(UNIT/'STATUS.json',dict(execution_state='partial',stage='frozen_before_diagnostic_and_render',scientific_verdict='pending',
        gaussian_link_progress='Same original-row permission endpoint frozen; no result claimed',scientific_seal=False,blockers=[]))
    print('FROZEN',len(locks),'inputs',sha(UNIT/'PROTOCOL.json'),flush=True)

def protocol():
    p=json.loads((UNIT/'PROTOCOL.json').read_text());assert p['unit']==UNIT.name=='unit_009'
    assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    assert sha(UNIT/'DECISION.json')==p['decision_sha256']
    for name,h in p['frozen_files'].items():assert sha(UNIT/name)==h,name
    for name,h in json.loads((UNIT/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(HERE/name)==h,name
    p.update(json.loads((UNIT/'CAMERAS.json').read_text()));p['inputs']=json.loads((UNIT/'INPUT_LOCK.json').read_text())['files'];return p

def locked(p,path):
    path=Path(path);assert sha(path)==p['inputs'][str(path)],str(path);return path

def source(p):
    s=p['scene']['source'];a=base.load_source(locked(p,s['original_ply']),s['sha256'])
    a['source_index']=np.arange(len(a['means']),dtype=np.int64);assert len(a['means'])==310475;return a

def selection(p):return read_npz(locked(p,UNIT/'asset/SOURCE_LINK.npz'))
def cache(p,v):return read_npz(locked(p,v['cache']))

def signed_summary(d,mask):
    return {k:dict(signed_RGB_sum=v[mask].sum(0).tolist(),L1_sum=float(np.abs(v[mask]).sum(dtype=float)),
        L1_mean=float(np.abs(v[mask]).sum(1).mean()) if mask.any() else None) for k,v in d.items() if v.ndim==2}

def diagnose():
    p=protocol();sel=selection(p);a=source(p);out=fresh(UNIT/'decomposition');records=[]
    for v in (v for v in p['views'] if v['kind']=='dev'):
        c=v['camera'];f=cache(p,v);tr=read_npz(locked(p,v['trace']));xy=tr['xy'];xx,yy=xy.T
        tc=validate_trace(a,c,xy,dict(rgb=f['source'],alpha=f['source_alpha']),tr)
        d=decompose_residual(base.source_colors(a,c),sel['weighted_strength'],tr,len(xy),p['paper'])
        err=float(np.max(np.abs(d['old_residual']+p['paper']-f['new_paper'][yy,xx])));assert err<1e-6
        target=f['regions']==4;inner=ndimage.binary_erosion(target,iterations=2)
        assert int(target[yy,xx].sum())==int(target.sum())
        np.savez_compressed(out/(c['view']+'.npz'),xy=xy,**d)
        records.append(dict(view=c['view'],old_reconstruction_max_error=err,trace=tc,target_pixels=int(target.sum()),
            target=signed_summary(d,target[yy,xx]),interior=signed_summary(d,inner[yy,xx])))
        print('DECOMPOSE',c['view'],'old/saturated interior L1',records[-1]['interior']['old_residual']['L1_mean'],records[-1]['interior']['saturated_residual']['L1_mean'],flush=True)
    js(out/'SUMMARY.json',dict(records=records,warning='Component norms are not additive damage attribution; predictions use signed RGB sum. Far sampling incomplete.'))

def render_paper(r,a,c,s,p):return r.render(paper_copy(a,c,s,p['paper']),c)[0]['rgb']

def build():
    p=protocol();sel=selection(p);a=source(p);before=array_hashes(a);r=Renderer(UNIT/'build');out=fresh(UNIT/'build_match')
    totals={k:0. for k in ARMS};records=[]
    for v in (v for v in p['views'] if v['kind']=='build'):
        c=v['camera'];ref=cache(p,v);f=dict(source=ref['source'],regions=ref['regions'],alpha=ref['new_raw_alpha'],support=ref['new_support'])
        row=dict(view=c['view'])
        for arm in ARMS:
            im=render_paper(r,a,c,sel[arm+'_strength'],p);f[arm+'_paper']=im
            row[arm]=float(np.abs(im-f['source']).sum(dtype=float));totals[arm]+=row[arm]
        np.testing.assert_array_equal(f['weighted_paper'],ref['new_paper'])
        np.testing.assert_array_equal(apply_fixed_ink(f['weighted_paper'],f['alpha']),ref['new_raw'])
        np.savez_compressed(out/(c['view']+'.npz'),**f);records.append(row);print('BUILD natural',row,flush=True)
    budget=min(totals.values());scales={k:budget/totals[k] for k in ARMS};checks={k:0. for k in ARMS}
    for v in (v for v in p['views'] if v['kind']=='build'):
        c=v['camera'];f=read_npz(out/(c['view']+'.npz'));matched={}
        for arm in ARMS:
            im=render_paper(r,a,c,sel[arm+'_strength']*scales[arm],p);matched[arm+'_matched_paper']=im
            checks[arm]+=float(np.abs(im-f['source']).sum(dtype=float))
        np.savez_compressed(out/(c['view']+'_matched.npz'),**matched)
    assert max(abs(x-budget)/budget for x in checks.values())<1e-5;assert before==array_hashes(a)
    js(UNIT/'BUILD_MATCH.json',dict(records=records,natural_source_L1=totals,budget=budget,scales=scales,actual_matched_source_L1=checks,
        fixed_ink=True,domain='all pixels, raw RGB L1',original_array_hashes=before))
    js(UNIT/'BUILD_LOCK.json',dict(files={str(f.relative_to(UNIT)):sha(f) for f in list(out.iterdir())+[UNIT/'BUILD_MATCH.json']}))
    print('MATCHED',totals,scales,checks,flush=True)

def match():
    locks=json.loads((UNIT/'BUILD_LOCK.json').read_text())['files'];assert sha(UNIT/'BUILD_MATCH.json')==locks['BUILD_MATCH.json']
    return json.loads((UNIT/'BUILD_MATCH.json').read_text())

def evaluate(kind,index):
    p=protocol();m=match();v=[v for v in p['views'] if v['kind']==kind][index];c=v['camera'];sel=selection(p);a=source(p)
    before=array_hashes(a);ref=cache(p,v);folder=fresh(UNIT/kind/c['view']);r=Renderer(UNIT/'build')
    f=dict(source=ref['source'],source_alpha=ref['source_alpha'],alpha=ref['new_raw_alpha'],support=ref['new_support'],
        regions=ref['regions'],old_regions=ref['old_regions'],intent=ref['intent'],proxy_ink=ref['new_ink'])
    metrics={};residual={};ink={}
    for arm in ARMS:
        for mode,scale in [('raw',1.),('matched',m['scales'][arm])]:
            key=arm+'_'+mode;paper=render_paper(r,a,c,sel[arm+'_strength']*scale,p)
            f[key+'_paper']=paper;f[key]=apply_fixed_ink(paper,f['alpha'])
            metrics[key+'_paper']=edit_metrics(f['source'],paper,f['regions']);metrics[key]=edit_metrics(f['source'],f[key],f['regions'])
            residual[key]=paper_residual(paper,f['regions'],p['paper']);ink[key]=edit_metrics(paper,f[key],f['regions'])
    np.testing.assert_array_equal(f['weighted_raw_paper'],ref['new_paper']);np.testing.assert_array_equal(f['weighted_raw'],ref['new_raw'])
    tr=read_npz(locked(p,v['trace']));xx,yy=tr['xy'].T
    d=decompose_residual(base.source_colors(a,c),sel['weighted_strength'],tr,len(xx),p['paper'])
    np.testing.assert_allclose(d['saturated_residual']+p['paper'],f['saturated_raw_paper'][yy,xx],rtol=0,atol=1e-6)
    target=f['regions']==4;inner=ndimage.binary_erosion(target,iterations=2)
    coverage={name:dict(pixels=int(mask.sum()),ink_pixels=int(((f['alpha']>.05)&mask).sum()),
        ink_fraction=float((f['alpha'][mask]>.05).mean()) if mask.any() else None,
        support_mean=float(f['support'][mask].mean()) if mask.any() else None) for name,mask in [('target',target),('interior',inner)]}
    changes={mode:edit_metrics(f['weighted_'+mode],f['saturated_'+mode],f['regions']) for mode in ('raw','matched')}
    assert before==array_hashes(a)==m['original_array_hashes']
    np.savez_compressed(folder/'FRAME.npz',**f)
    js(folder/'EVALUATION.json',dict(camera=c,metrics=metrics,paper_residual=residual,ink=ink,coverage=coverage,changes=changes,
        old_source_and_hybrid_exact=True,ink_alpha_exact=True,same_support=True,signed_prediction_matches_render=True,scope=p['scope']))
    for key in ('source','intent','weighted_raw_paper','saturated_raw_paper','weighted_raw','saturated_raw','weighted_matched','saturated_matched'):
        png(folder/(key+'.png'),f[key])
    png(folder/'ink_only.png',1-f['alpha'])
    keys=['source','intent','weighted_raw_paper','saturated_raw_paper','weighted_raw','saturated_raw','weighted_matched','saturated_matched']
    panel(folder/'COMPARISON.png',[f[k] for k in keys],['Original GS','Fixed authored target','Weighted GS paper','Same-ID saturated paper','Weighted / fixed ink','Saturated / fixed ink','Weighted / source matched','Saturated / source matched'],
        c['view']+' | Same41058 original rows; fixed original-ID-linked proxy ink',columns=4)
    js(folder/'COMPLETED.json',dict(utc=now(),files={f.name:sha(f) for f in folder.iterdir() if f.is_file()}))
    print('EVAL',kind,c['view'],'interior residual',residual['weighted_raw']['target_interior']['clipped_L1_mean'],residual['saturated_raw']['target_interior']['clipped_L1_mean'],flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','diagnose','build','dev','arc']);ap.add_argument('--index',type=int,default=0);args=ap.parse_args()
    if args.stage in ('dev','arc'):evaluate(args.stage,args.index)
    else:globals()[args.stage]()
