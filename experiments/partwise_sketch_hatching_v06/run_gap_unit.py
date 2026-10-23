"""Unit005: bounded internal gap completion on fixed original-GS linked paper."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,output_guard,sha,js,now
from pathlib import Path
import argparse
import json
import shutil
import numpy as np
from geometry import mesh_data
from gap_completion import complete_gaps,render_gap_pair,gap_samples
from hybrid import compose,edit_metrics,ink_metrics
from layer_ablation import ink_shape
from run_hybrid import read_npz,png,panel

HERE=Path(__file__).resolve().parent
PREV=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_004')


def fresh(path):
    path=output_guard(path);path.mkdir(parents=True,exist_ok=False);return path


def freeze():
    assert UNIT.name=='unit_005' and UNIT.parent.parent.name=='partwise_sketch_hatching_gaussian_link_v06'
    if (UNIT/'PROTOCOL.json').exists():raise FileExistsError('protocol already frozen')
    decision=json.loads((UNIT/'DECISION.json').read_text());assert decision['action']=='continue'
    prev=json.loads((PREV/'PROTOCOL.json').read_text());s=prev['scene'];root=Path(s['asset'])
    files=[UNIT/'DECISION.json',PREV/'PROTOCOL.json',PREV/'REPORT_ZH.md',PREV/'STATUS.json',PREV/'NEXT.json',
           PREV/'SELECTION.npz',PREV/'SELECTION_LOCK.json',PREV/'BUILD_LOCK.json',
           Path(s['source']['original_ply']),Path(s['binding']),root/'mesh.npz',root/'region_4.npz',root/'asset.json']
    views=[]
    lock=json.loads((PREV/'BUILD_LOCK.json').read_text())['files']
    for v in prev['build_views'][:4]:
        f=PREV/'budget'/v['camera']['view']/'NATURAL.npz'
        assert sha(f)==lock[str(f.relative_to(PREV))]
        legacy=Path(v['legacy_cache']);assert sha(legacy)==prev['input_hashes'][str(legacy)]
        views.append(dict(kind='build',camera=v['camera'],paper_cache=str(f),legacy_cache=str(legacy)))
        files += [f,legacy]
    for v in prev['views']:
        folder=PREV/v['kind']/v['camera']['view'];receipt=json.loads((folder/'COMPLETED.json').read_text())
        for name in ('FRAME.npz','EVALUATION.json','TRACE.npz'):
            assert sha(folder/name)==receipt['files'][name];files.append(folder/name)
        views.append(dict(kind=v['kind'],camera=v['camera'],cache=str(folder/'FRAME.npz'),
                          metadata=str(folder/'EVALUATION.json'),trace=str(folder/'TRACE.npz')))
    locks={str(f):sha(f) for f in files}
    for f in (root/'mesh.npz',root/'region_4.npz',root/'asset.json',Path(s['binding']),Path(s['source']['original_ply'])):
        assert locks[str(f)]==prev['input_hashes'][str(f)]
    assert locks[str(PREV/'SELECTION.npz')]==json.loads((PREV/'SELECTION_LOCK.json').read_text())['files']['SELECTION.npz']
    snap=UNIT/'source_snapshot';shutil.copytree(HERE,snap,ignore=shutil.ignore_patterns('__pycache__'))
    p=dict(unit='unit_005',frozen_utc=now(),decision_sha256=locks[str(UNIT/'DECISION.json')],
        question='Can filling only bounded internal planned gaps improve whole-object linked NPR at equal visible ink?',
        changed_variable=decision['changed_variable'],scene={k:s[k] for k in ('source','source_count','asset','binding','target')},
        views=views,source_selection=str(PREV/'SELECTION.npz'),region_id=4,paper=[.95,.95,.95],ink_color=.03,supersample=2,
        mechanism='Retain exact legacy on-segments, period and phase. Append only OFF intervals bounded by two saved strokes on the same layer/plane/edge-connected chain. Exclude terminal OFF intervals and ambiguous edges. No gap bridging across holes or region boundaries.',
        source_link='Fixed unit004 completed original-row paper strengths. Ink still multiplied by unchanged old original-row S, not completed S. New gap segments have face/bary,chain,plane,period and parent stroke IDs; none are Gaussian IDs.',
        matching=dict(domain='Full authored region4 actual hybrid-paper raw RGB L1, summed over the four original BUILD views',
            budget='.95 * min(old natural,filled natural)',parameter='One global ink attenuation per arm; natural outputs retained; no DEV/arc tuning'),
        metric_rules=dict(boundary_pixels=2,visible_ink_alpha=.05,gap_sample_step_pixels=.25,
            gap_support='Added interval projected samples on exact proxy rays; gap-only union support and incremental raster coverage reported separately; not independent geometric truth',
            acceptance='Whole-object continuity and shape readability improve at comparable ink, including weak241/24; no obvious grid/cross-clutter degradation in other views or arc. Counts alone cannot promote.'),
        scope='Exposed diagnostic views, 4DEV+9arc with 12 unique camera settings; original-GS paper + original-ID-linked proxy hatches, not native Gaussian ink or H1/H2/H3, semantic/physical or temporal certification.',
        fixed='Original PLY,310475 row order/identity,means,covariance,opacity,SH,M1/UNKNOWN,region4,old paths,width,angles,spacing,2x sampling,.004 visibility and paper are fixed.',
        negatives='Preserve v05 sparse8.044%/4.49%, unit001 gate negative, unit002 direction-layer negative, unit003 limited visibility gain, unit004 matched-paper negative and all interruptions.',
        input_hashes=locks,source_hashes={f.name:sha(f) for f in snap.iterdir() if f.is_file()},fps=4,
        resources=dict(serial=True,CPU_affinity=2,numeric_threads=1,GPU=False),deadline_jst='2026-10-23T19:52:45+09:00')
    js(UNIT/'PROTOCOL.json',p);js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json'),utc=now()))
    js(UNIT/'STATUS.json',dict(execution_state='partial',stage='frozen_before_BUILD',scientific_verdict='pending',
        gaussian_link_progress='Single gap-style mechanism frozen; no outcome yet.',scientific_seal=False,blockers=[]))
    print('FROZEN',sha(UNIT/'PROTOCOL.json'),len(locks),'inputs',flush=True)


def protocol():
    p=json.loads((UNIT/'PROTOCOL.json').read_text())
    assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    assert sha(UNIT/'DECISION.json')==p['decision_sha256']
    source_hashes=p['source_hashes']
    revision=UNIT/'SOURCE_REVISION_002.json'
    if revision.exists():
        assert sha(revision)==json.loads((UNIT/'SOURCE_REVISION_002_LOCK.json').read_text())['sha256']
        amended=json.loads(revision.read_text());assert amended['protocol_sha256']==sha(UNIT/'PROTOCOL.json')
        source_hashes=amended['source_hashes']
    for name,h in source_hashes.items():assert sha(HERE/name)==h,name
    return p


def locked(p,path):
    path=Path(path);assert sha(path)==p['input_hashes'][str(path)],str(path);return path


def asset(p):
    root=Path(p['scene']['asset']);m=read_npz(locked(p,root/'mesh.npz'))
    mesh=mesh_data(m['vertices'],m['faces'],m['face_regions'])
    old=read_npz(locked(p,root/'region_4.npz'));meta=json.loads(locked(p,root/'asset.json').read_text())
    return mesh,old,meta


def paths():
    p=protocol();mesh,old,meta=asset(p);out=fresh(UNIT/'asset')
    filled,gaps,stats=complete_gaps(mesh,old,meta['styles']['4'])
    np.savez_compressed(out/'FILLED_PATHS.npz',**filled);np.savez_compressed(out/'GAPS.npz',**gaps)
    sel=read_npz(locked(p,p['source_selection']))
    np.testing.assert_array_equal(sel['source_index'],np.arange(310475))
    np.savez_compressed(out/'SOURCE_LINK.npz',**{k:sel[k] for k in ('source_index','original_strength','completed_strength','unknown_unchanged','region_id_unchanged','conflict_unchanged')})
    js(out/'PATHS.json',dict(stats,old_path_sha256=p['input_hashes'][str(Path(p['scene']['asset'])/'region_4.npz')],
        source_ply_sha256=p['scene']['source']['sha256'],new_revision='unit005_internal_gap_append',
        identity='Old arrays remain exact prefix. New stroke IDs>=9e9 identify gaps; parent IDs refer to proxy strokes; source_index is separately original PLY row.',
        selection='Both source color strengths and S strengths are immutable copies from unit004; S uses original_strength.'))
    js(UNIT/'ASSET_LOCK.json',dict(files={str(f.relative_to(UNIT)):sha(f) for f in out.iterdir()}))
    print('PATHS',stats,flush=True)


def new_asset():
    lock=json.loads((UNIT/'ASSET_LOCK.json').read_text())
    for name,h in lock['files'].items():assert sha(UNIT/name)==h,name
    return read_npz(UNIT/'asset/FILLED_PATHS.npz'),read_npz(UNIT/'asset/GAPS.npz'),read_npz(UNIT/'asset/SOURCE_LINK.npz')


def cache(p,v):
    if v['kind']=='build':
        a=read_npz(locked(p,v['paper_cache']));b=read_npz(locked(p,v['legacy_cache']))
        np.testing.assert_array_equal(a['source'],b['source']);np.testing.assert_array_equal(a['regions'],b['regions'])
        _,old_alpha=compose(a['completed_paper'],b['legacy_ink'],b['support'],True,ink_color=p['ink_color'])
        return dict(source=a['source'],paper=a['completed_paper'],support=b['support'],regions=a['regions'],old_alpha=old_alpha)
    metadata=json.loads(locked(p,v['metadata']).read_text());c=v['camera']
    for k in ('extrinsic','width','height','fx','fy','cx','cy'):np.testing.assert_array_equal(c[k],metadata['camera'][k])
    a=read_npz(locked(p,v['cache']))
    return dict(source=a['source'],paper=a['completed_paper'],support=a['support'],regions=a['regions'],
                old_alpha=a['fixed_ink_alpha'],old_hybrid=a['completed_hybrid'],alpha=a['alpha'])


def build():
    p=protocol();mesh,old,meta=asset(p);filled,gaps,link=new_asset();out=fresh(UNIT/'build_match')
    totals=dict(old=0.,filled=0.);records=[]
    for v in (v for v in p['views'] if v['kind']=='build'):
        c=v['camera'];a=cache(p,v);pair,hi=render_gap_pair(mesh,old,gaps,meta,c)
        np.testing.assert_array_equal(hi['regions'],a['regions']);target=a['regions']==4
        row=dict(view=c['view'])
        for arm in totals:
            im,alpha=compose(a['paper'],pair[arm],a['support'],True,ink_color=p['ink_color'])
            if arm=='old':np.testing.assert_array_equal(alpha,a['old_alpha'])
            row[arm]=float(np.abs(im-a['paper'])[target].sum(dtype=float));totals[arm]+=row[arm]
        np.savez_compressed(out/(c['view']+'.npz'),**a,**{k+'_ink':v for k,v in pair.items()});records.append(row)
        print('BUILD',row,flush=True)
    budget=.95*min(totals.values());assert budget>0;scales={k:budget/v for k,v in totals.items()};checks={k:0. for k in totals}
    for v in (v for v in p['views'] if v['kind']=='build'):
        a=read_npz(out/(v['camera']['view']+'.npz'));target=a['regions']==4
        for arm in totals:
            im,_=compose(a['paper'],a[arm+'_ink'],a['support'],True,scales[arm],p['ink_color'])
            checks[arm]+=float(np.abs(im-a['paper'])[target].sum(dtype=float))
    assert max(abs(x-budget)/budget for x in checks.values())<1e-5
    js(UNIT/'BUILD_MATCH.json',dict(utc=now(),records=records,natural_target_ink_L1=totals,budget=budget,scales=scales,actual_matched_target_ink_L1=checks))
    js(UNIT/'BUILD_LOCK.json',dict(files={str(f.relative_to(UNIT)):sha(f) for f in list(out.iterdir())+[UNIT/'BUILD_MATCH.json']}))
    print('MATCH',totals,scales,checks,flush=True)


def match():
    lock=json.loads((UNIT/'BUILD_LOCK.json').read_text())
    for name,h in lock['files'].items():assert sha(UNIT/name)==h,name
    return json.loads((UNIT/'BUILD_MATCH.json').read_text())


def evaluate(kind,index):
    p=protocol();m=match();v=[v for v in p['views'] if v['kind']==kind][index];c=v['camera'];a=cache(p,v)
    mesh,old,meta=asset(p);filled,gaps,link=new_asset();out=fresh(UNIT/kind/c['view'])
    pair,hi=render_gap_pair(mesh,old,gaps,meta,c);regions=hi['regions'];np.testing.assert_array_equal(regions,a['regions'])
    images=dict(source=a['source'],paper=a['paper']);alphas={};metrics={};inks={};shapes={}
    for arm in ('old','filled'):
        for mode,scale in [('raw',1.),('matched',m['scales'][arm])]:
            name=arm+'_'+mode;im,alpha=compose(a['paper'],pair[arm],a['support'],True,scale,p['ink_color'])
            images[name]=im;alphas[name]=alpha;metrics[name]=edit_metrics(a['source'],im,regions)
            inks[name]=ink_metrics(a['paper'],im,alpha,pair['old'],regions);shapes[name]=ink_shape(alpha,regions==4)
    np.testing.assert_array_equal(alphas['old_raw'],a['old_alpha']);np.testing.assert_array_equal(images['old_raw'],a['old_hybrid'])
    images['intent']=np.repeat(hi['proxy'][:,:,None],3,axis=2);images['intent'][regions==4]=[1.,.32,.40]
    samples,gap_summary=gap_samples(mesh,gaps,c,pair,a['support'],m['scales']['filled'])
    increment=alphas['filled_raw']-alphas['old_raw'];assert increment.min()>=-1e-7
    changed=edit_metrics(images['old_raw'],images['filled_raw'],regions)
    metrics['paper']=edit_metrics(a['source'],a['paper'],regions)
    np.savez_compressed(out/'FRAME.npz',**images,**{k+'_alpha':v for k,v in alphas.items()},
        **{k+'_ink':v for k,v in pair.items()},support=a['support'],source_alpha=a['alpha'],regions=regions,
        gap_alpha=pair['gap_only']*a['support'],increment_alpha=increment)
    np.savez_compressed(out/'GAP_SAMPLES.npz',**samples)
    js(out/'EVALUATION.json',dict(camera=c,metrics=metrics,ink=inks,shape=shapes,gap_support=gap_summary,
        changed_by_fill=changed,old_result_exact=True,paper_and_S_fixed=True,cache_sha256=p['input_hashes'][v['cache']],scope=p['scope']))
    for name,img in images.items():png(out/(name+'.png'),img)
    for name,alpha in alphas.items():png(out/(name+'_ink.png'),1-alpha)
    png(out/'added_gap_ink.png',1-pair['gap_only']*a['support']);png(out/'increment_ink.png',1-increment)
    panel(out/'COMPARISON.png',[images[k] for k in ('source','intent','paper','old_raw','filled_raw','filled_matched')],
        ['Original GS / full SH3','Fixed authored region4','Fixed completed GS paper','Old planned gaps / raw','Internal gaps filled / raw','Internal gaps filled / matched'],
        c['view']+' | Fixed source rows and S; new proxy style variant')
    panel(out/'MATCHED_COMPARISON.png',[images[k] for k in ('old_matched','filled_matched')]+[1-alphas[k] for k in ('old_matched','filled_matched')],
        ['Old / BUILD ink matched','Filled / BUILD ink matched','Old matched ink only','Filled matched ink only'],
        'Actual visible RGB ink matched on four BUILD views; no per-view fitting',columns=2)
    js(out/'COMPLETED.json',dict(utc=now(),files={f.name:sha(f) for f in out.iterdir() if f.is_file()}))
    print('EVAL',kind,c['view'],{k:dict(ink=inks[k]['target_visible_ink_L1'],pixels=shapes[k]['visible']['pixels']) for k in inks},'new_gap_L1',changed['target_full']['raw_L1_sum'],flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','paths','build','dev','arc']);ap.add_argument('--index',type=int,default=0);args=ap.parse_args()
    if args.stage in ('freeze','paths','build'):globals()[args.stage]()
    else:evaluate(args.stage,args.index)
