"""Frozen Lego A/B: identical carrier, seed tangents and stroke length budgets."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT as ROOT,HERE,sha,js,now,output_guard
from pathlib import Path
import argparse,json,shutil,collections
import numpy as np
from scipy import ndimage
from PIL import Image,ImageDraw
from geometry import mesh_data
from target_completion import render_pair
from hybrid import compose,edit_metrics
from surface_walk import regenerate,adjacency
from visibility_intervals import endpoint_records,compare_visibility,sample_support

OLD=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_010')
PACKAGE=ROOT/'replay_package/data/lego'
ARMS=('A_linked','B_linked','A_ungated','B_ungated')

def npz(path):
    with np.load(path,allow_pickle=False) as z: return {k:z[k] for k in z.files}
def save(path,**arrays): np.savez_compressed(output_guard(path),**arrays)
def fresh(path):
    path=output_guard(path);path.mkdir(parents=True,exist_ok=False);return path
def png(path,array):
    if array.ndim==2: array=np.repeat(array[:,:,None],3,axis=2)
    Image.fromarray(np.uint8(np.clip(array,0,1)*255+.5)).save(output_guard(path))
def panel(path,arrays,titles,columns=None):
    columns=columns or len(arrays);h,w=arrays[0].shape[:2];rows=(len(arrays)+columns-1)//columns
    canvas=Image.new('RGB',(columns*w,rows*(h+34)),(255,255,255));draw=ImageDraw.Draw(canvas)
    for i,(array,title) in enumerate(zip(arrays,titles)):
        if array.ndim==2:array=np.repeat(array[:,:,None],3,axis=2)
        x=(i%columns)*w;y=(i//columns)*(h+34)
        draw.text((x+5,y+5),title,fill=(0,0,0))
        canvas.paste(Image.fromarray(np.uint8(np.clip(array,0,1)*255+.5)),(x,y+34))
    canvas.save(output_guard(path))
def freeze():
    assert not (UNIT/'PROTOCOL.json').exists()
    decision=json.loads((UNIT/'DECISION.json').read_text());assert decision['action']=='continue'
    bs=json.loads((UNIT/'BOOTSTRAP_STATUS.json').read_text());assert len(bs['stages'])==4 and all(x['returncode']==0 for x in bs['stages'])
    views=[]
    for v in json.loads((OLD/'CAMERAS.json').read_text())['views']:
        kind=v['kind'];c=v['camera']
        if kind=='arc' and c['view'] not in ('orbit_231_24_5.3','orbit_241_24_5.3','orbit_251_24_5.3'):continue
        cache=OLD/'build_match'/(c['view']+'.npz') if kind=='build' else OLD/kind/c['view']/'FRAME.npz'
        views.append(dict(kind=kind,camera=c,cache=str(cache)))
    inputs=[UNIT/'DECISION.json',OLD/'PROTOCOL.json',OLD/'CAMERAS.json',OLD/'BUILD_LOCK.json',UNIT/'BOOTSTRAP_INPUTS.json']
    inputs += [p for p in PACKAGE.rglob('*') if p.is_file()]
    inputs += [Path(v['cache']) for v in views]
    inputs += [UNIT/'cold_hybrid/RELOAD_RECEIPT.json',UNIT/'cold_hybrid/FRAME.npz',UNIT/'cold_source/RELOAD_RECEIPT.json']
    js(UNIT/'INPUT_LOCK.json',dict(files={str(p):sha(p) for p in inputs}))
    js(UNIT/'CAMERAS.json',dict(views=views,scope='4 exposed BUILD;4 exposed DEV;3 exposed rear arc, with 241/24 duplicate;6 unique evaluation cameras'))
    original_diag=OLD/'source_snapshot/visibility_intervals.py'
    js(UNIT/'DIAGNOSTIC_VENDOR.json',dict(source=str(original_diag),sha256=sha(original_diag),copied_sha256=sha(HERE/'vendor/visibility_intervals.py'),
       use='Legacy visibility attribution only; interval candidate is NOT used for A/B output'))
    source=UNIT/'source_snapshot';shutil.copytree(HERE,source,ignore=shutil.ignore_patterns('__pycache__'))
    js(UNIT/'SOURCE_LOCK.json',dict(files={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()}))
    p=dict(unit='unit_001',frozen_utc=now(),decision_sha256=sha(UNIT/'DECISION.json'),
      question='Can straightest surface continuation improve hatch readability on the EXACT SAME frozen carrier?',
      changed_variable=decision['changed_variable'],falsification=decision['falsification'],
      A='Exact saved unit010 local old/added partitions; no default promotion',
      B='Per A stroke: arclength midpoint seed, same initial tangent, half original length in each direction; unfold only across true shared edges; new IDs = parent+100000000000',
      stopping='Requested length, mesh/partition boundary, nonmanifold/degenerate edge, exact vertex ambiguity, 10000-step engineering guard; no redistribution after early stop',
      controls='Same original geometry/topology, old2030/added91 partitions, paper/S/M1/UNKNOWN/310475 source rows, renderer .004, AA2, width1, masks band2. No PCA/angle/white scans.',
      matching='One factor per A/B linked/ungated arm from four BUILD target abs(hybrid-paper) RGB sums. Common budget=min of four natural totals. Preserve natural results. No DEV refit.',
      visibility='Unmodified packaged render.py; copied legacy diagnostic only; zero S must give paper',
      cache_policy='Reuse hash-fixed unit010 source/paper/S/regions. Render actual new ink in every distinct view. One independent full cold GS/bootstrap already completed.',
      carrier_source='Covariance-plane CPU depth proxy of frozen vanilla GS; not RaDe-trained or GT mesh',
      scope='Original-GS paper plus original-ID region-S-gated proxy strokes; new per-path original-Gaussian ownership is NOT certified; all cameras exposed.',
      negatives='All old v05/v06 files and failures preserved; no retroactive pass; no scientific seal',
      resources=dict(CPU_affinity=2,numeric_threads=1,GPU=False,serial=True),
      frozen={name:sha(UNIT/name) for name in ('INPUT_LOCK.json','SOURCE_LOCK.json','CAMERAS.json')})
    js(UNIT/'PROTOCOL.json',p);js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json')))
    js(UNIT/'STATUS.json',dict(execution_state='partial',stage='protocol_frozen',scientific_verdict='pending',
       gaussian_link_progress='Cold original-GS source/paper/S/ink/hybrid replay exact; scientific A/B pending',scientific_seal=False))
    print('FROZEN',len(inputs),'inputs',len(views),'camera records',flush=True)
def protocol():
    p=json.loads((UNIT/'PROTOCOL.json').read_text())
    assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    assert sha(UNIT/'DECISION.json')==p['decision_sha256']
    for name,h in p['frozen'].items(): assert sha(UNIT/name)==h,name
    for name,h in json.loads((UNIT/'SOURCE_LOCK.json').read_text())['files'].items(): assert sha(HERE/name)==h,name
    p['views']=json.loads((UNIT/'CAMERAS.json').read_text())['views'];return p
def load_assets():
    t=npz(PACKAGE/'unit_008_asset/TARGET.npz')
    oldmesh=mesh_data(t['vertices'],t['faces'],t['old_face_regions']);mesh=mesh_data(t['vertices'],t['faces'],t['face_regions'])
    a=[npz(PACKAGE/'unit_010_asset'/name) for name in ('LOCAL_OLD_PARTITION.npz','LOCAL_ADDED_PARTITION.npz')]
    meta=json.loads((PACKAGE/'asset.json').read_text());return oldmesh,mesh,a,meta
def path_stats(paths):
    p=paths['points'];lengths=np.linalg.norm(p[:,1]-p[:,0],axis=1);turns=[];gaps=0
    for sid in np.unique(paths['stroke_id']):
        ix=np.flatnonzero(paths['stroke_id']==sid)
        if len(ix)>1:
            gaps+=int((np.linalg.norm(p[ix[:-1],1]-p[ix[1:],0],axis=1)>1e-8).sum())
            d=(p[ix,1]-p[ix,0])/lengths[ix,None]
            turns.extend(np.rad2deg(np.arccos(np.clip((d[:-1]*d[1:]).sum(1),-1,1))).tolist())
    return dict(strokes=len(np.unique(paths['stroke_id'])),segments=len(p),length=float(lengths.sum()),internal_gaps=gaps,
                world_turn_degrees_quantiles=np.quantile(turns,[.5,.9,.95,1]).tolist() if turns else [])
def derive():
    protocol();out=fresh(UNIT/'asset');oldmesh,mesh,a,meta=load_assets()
    allowed=[oldmesh['regions']==4,(mesh['regions']==4)&(oldmesh['regions']!=4)]
    records=[];stats={};ends={}
    for name,m,old,mask in zip(('old','added'),(oldmesh,mesh),a,allowed):
        new,rec=regenerate(m,old,mask)
        save(out/('A_'+name+'.npz'),**old);save(out/('B_'+name+'.npz'),**new)
        records.extend([dict(partition=name,**x) for x in rec]);stats[name]={'A':path_stats(old),'B':path_stats(new)}
        labeled=dict(m,regions=np.where(mask,4,1));ends[name]=endpoint_records(labeled,old)
    links=npz(PACKAGE/'SOURCE_LINK.npz');binding=npz(PACKAGE/'SOURCE_BINDING.npz')
    np.testing.assert_array_equal(links['source_index'],np.arange(310475));assert int(binding['unknown'].sum())==195279
    assert int((links['paper_strength']>0).sum())==41058 and int((links['ink_strength']>0).sum())==21006
    edges=adjacency(mesh);adjacent=[v for v in edges.values() if len(v)==2 and (mesh['regions'][v]==4).all()]
    dots=[abs(float(mesh['normals'][x]@mesh['normals'][y])) for x,y in adjacent]
    geometry=dict(target_faces=int((mesh['regions']==4).sum()),vertices=len(mesh['vertices']),faces=len(mesh['faces']),
                  target_shared_edge_normal_angle_quantiles=np.quantile(np.rad2deg(np.arccos(np.clip(dots,0,1))),[.5,.9,.95,1]).tolist(),
                  note='Proxy-only unsigned normal changes; real shape edges and noise are NOT separated')
    js(out/'SEEDS_AND_STOPS.json',records);js(out/'A_ENDPOINTS.json',ends)
    summary=dict(partitions=stats,geometry=geometry,requested_length=sum(x['requested_length'] for x in records),actual_length=sum(x['actual_length'] for x in records),
       stops=dict(collections.Counter(x[k] for x in records for k in ('minus_stop','plus_stop'))),
       early_stopped_strokes=sum(x['actual_length']<x['requested_length']-1e-9 for x in records),
       changed_stroke_ids=True,source_index_unchanged=True,source_count=310475,paper_rows=41058,ink_rows=21006,UNKNOWN=195279)
    js(out/'ASSET.json',summary);js(UNIT/'ASSET_LOCK.json',dict(files={str(p.relative_to(UNIT)):sha(p) for p in out.iterdir()}))
    print('ASSET',json.dumps(summary),flush=True)
def check_assets():
    for name,h in json.loads((UNIT/'ASSET_LOCK.json').read_text())['files'].items():assert sha(UNIT/name)==h,name
def compute(v):
    ref=npz(v['cache']);oldmesh,mesh,_,meta=load_assets()
    f={k:ref[k].copy() for k in ('source','paper','support','regions','old_regions')}
    for arm in ('A','B'):
        paths=[npz(UNIT/'asset'/(arm+'_'+part+'.npz')) for part in ('old','added')]
        ink,hi=render_pair(oldmesh,mesh,*paths,meta,v['camera'])
        np.testing.assert_array_equal(hi['regions'],ref['regions']);np.testing.assert_array_equal(hi['old_regions'],ref['old_regions'])
        f[arm+'_preS']=ink['new']
        if arm=='A':np.testing.assert_array_equal(ink['new'],ref['local_ink'])
        for link in ('linked','ungated'):
            key=arm+'_'+link
            f[key+'_natural'],f[key+'_natural_alpha']=compose(f['paper'],ink['new'],f['support'],link=='linked')
        if arm=='A':np.testing.assert_array_equal(f['A_linked_natural'],ref['local_raw'])
    return f
def build():
    p=protocol();check_assets();out=fresh(UNIT/'build');totals={arm:0. for arm in ARMS};records=[]
    for v in (v for v in p['views'] if v['kind']=='build'):
        f=compute(v);target=f['regions']==4;row=dict(view=v['camera']['view'])
        for arm in ARMS:
            mass=float(np.abs(f[arm+'_natural']-f['paper'])[target].sum(dtype=float));totals[arm]+=mass;row[arm]=mass
        save(out/(v['camera']['view']+'.npz'),**f);records.append(row);print('BUILD',row,flush=True)
    assert min(totals.values())>0;budget=min(totals.values());scales={k:budget/v for k,v in totals.items()};actual={k:0. for k in ARMS}
    for v in (v for v in p['views'] if v['kind']=='build'):
        f=npz(out/(v['camera']['view']+'.npz'));target=f['regions']==4
        for arm in ARMS:
            a=arm[0];im,alpha=compose(f['paper'],f[a+'_preS'],f['support'],arm.endswith('linked') and not arm.endswith('ungated'),scales[arm])
            actual[arm]+=float(np.abs(im-f['paper'])[target].sum(dtype=float))
    assert max(abs(x-budget)/budget for x in actual.values())<1e-5
    js(UNIT/'BUILD_MATCH.json',dict(records=records,natural_totals=totals,budget=budget,scales=scales,actual_matched=actual))
    js(UNIT/'BUILD_LOCK.json',dict(files={str(x.relative_to(UNIT)):sha(x) for x in [*out.iterdir(),UNIT/'BUILD_MATCH.json']}))
    print('MATCH',totals,scales,flush=True)
def matched(f,scales):
    for arm in ARMS:
        f[arm+'_matched'],f[arm+'_matched_alpha']=compose(f['paper'],f[arm[0]+'_preS'],f['support'],arm.split('_')[1]=='linked',scales[arm])
    return f
def measure(f):
    regions=f['regions'];target=regions==4;inner=ndimage.binary_erosion(target,iterations=2)
    result=dict(source_edit={},ink_effect={},coverage={},delta={},support={},preS={})
    for arm in ARMS:
        for mode in ('natural','matched'):
            key=arm+'_'+mode;alpha=f[key+'_alpha']
            result['source_edit'][key]=edit_metrics(f['source'],f[key],regions)
            result['ink_effect'][key]=edit_metrics(f['paper'],f[key],regions)
            result['coverage'][key]={n:dict(pixels=int(mask.sum()),ink_pixels=int((alpha[mask]>.05).sum()),fraction=float((alpha[mask]>.05).mean())) for n,mask in [('target',target),('interior',inner)]}
    for mode in ('natural','matched'):
        for link in ('linked','ungated'):result['delta'][link+'_'+mode]=edit_metrics(f['A_'+link+'_'+mode],f['B_'+link+'_'+mode],regions)
    for n,mask in [('target',target),('interior',inner)]:
        result['support'][n]=dict(pixels=int(mask.sum()),mean=float(f['support'][mask].mean()),above_005=float((f['support'][mask]>.05).mean()))
    for arm in ('A','B'):
        result['preS'][arm]=dict(target_ink_pixels=int((f[arm+'_preS'][target]>.05).sum()),target_mass=float(f[arm+'_preS'][target].sum()),
                                 global_overlap_note='Raster union/max; not a per-stroke continuity metric')
    return result
def evaluate():
    p=protocol();check_assets();scales=json.loads((UNIT/'BUILD_MATCH.json').read_text())['scales'];summary=[]
    for name,h in json.loads((UNIT/'BUILD_LOCK.json').read_text())['files'].items():assert sha(UNIT/name)==h,name
    for v in (v for v in p['views'] if v['kind']!='build'):
        kind=v['kind'];view=v['camera']['view'];out=fresh(UNIT/kind/view)
        duplicate=kind=='arc' and view=='orbit_241_24_5.3'
        if duplicate:
            prior=UNIT/'dev'/view
            for file in prior.iterdir():
                if file.is_file():shutil.copyfile(file,out/file.name)
            js(out/'REUSE.json',dict(source=str(prior),same_camera=True,not_independent_sample=True));f=npz(out/'FRAME.npz');m=json.loads((out/'EVALUATION.json').read_text())['measurements']
        else:
            f=matched(compute(v),scales);m=measure(f);save(out/'FRAME.npz',**f)
            js(out/'EVALUATION.json',dict(camera=v['camera'],measurements=m,A_exact=True,source_paper_support_fixed=True))
            for key in ('source','paper'):png(out/(key+'.png'),f[key])
            for arm in ('A','B'):png(out/(arm+'_preS_ink.png'),1-f[arm+'_preS'])
            for arm in ARMS:
                for mode in ('natural','matched'):
                    key=arm+'_'+mode;png(out/(key+'.png'),f[key]);png(out/(key+'_ink.png'),1-f[key+'_alpha'])
            keys=['source','paper','A_linked_matched','B_linked_matched','A_ungated_matched','B_ungated_matched']
            titles=['Original GS','Fixed GS paper','A slice | linked matched','B walk | linked matched','A slice | ungated matched','B walk | ungated matched']
            panel(out/'COMPARISON.png',[f[k] for k in keys],[view+' | '+t for t in titles],columns=3)
            panel(out/'INK_LAYERS.png',[1-f[k] for k in ('A_preS','B_preS','A_linked_matched_alpha','B_linked_matched_alpha')],
                ['A before S | natural','B before S | natural','A after S | matched','B after S | matched'],columns=2)
            panel(out/'NATURAL.png',[f[k] for k in ('paper','A_linked_natural','B_linked_natural')],['Fixed GS paper','A natural linked','B natural linked'])
        row=dict(kind=kind,view=view,duplicate=duplicate,target_pixels=m['support']['target']['pixels'])
        for arm in ARMS:
            key=arm+'_matched';q=m['source_edit'][key]
            row[arm]=dict(ink_L1=m['ink_effect'][key]['target_full']['raw_L1_sum'],coverage=m['coverage'][key]['target']['fraction'],
                         interior_coverage=m['coverage'][key]['interior']['fraction'],far_other=q['far_other']['raw_L1_sum'],background=q['far_background']['raw_L1_sum'])
        summary.append(row);print('EVAL',json.dumps(row),flush=True)
    js(UNIT/'SUMMARY.json',summary)
    for label,filename,keys in [('ALL_DEV_MATCHED','matched',['source','paper','A_linked_matched','B_linked_matched']),
                               ('ALL_DEV_NATURAL','natural',['source','paper','A_linked_natural','B_linked_natural'])]:
        arrays=[];titles=[]
        for v in (v for v in p['views'] if v['kind']=='dev'):
            f=npz(UNIT/'dev'/v['camera']['view']/'FRAME.npz')
            for key in keys:arrays.append(f[key]);titles.append(v['camera']['view']+' | '+key)
        panel(UNIT/(label+'.png'),arrays,titles,columns=4)
    arrays=[];titles=[]
    for v in (v for v in p['views'] if v['kind']=='arc'):
        f=npz(UNIT/'arc'/v['camera']['view']/'FRAME.npz')
        for key in ('A_linked_matched','B_linked_matched'):arrays.append(f[key]);titles.append(v['camera']['view']+' | '+key)
    panel(UNIT/'REAR_CAMERA_SEQUENCE.png',arrays,titles,columns=2)
def attribution():
    p=protocol();scales=json.loads((UNIT/'BUILD_MATCH.json').read_text())['scales'];oldmesh,mesh,_,meta=load_assets();out=fresh(UNIT/'attribution')
    selected=[v for v in p['views'] if v['kind']=='dev' and v['camera']['view'] in ('orbit_61_24_5.3','orbit_241_24_5.3')]
    summaries=[]
    for v in selected:
        view=v['camera']['view'];folder=fresh(out/view);f=npz(UNIT/'dev'/view/'FRAME.npz')
        for arm in ('A','B'):
            totals=collections.Counter(); partition_ink=[]
            for part,m in [('old',oldmesh),('added',mesh)]:
                paths=npz(UNIT/'asset'/(arm+'_'+part+'.npz'))
                r=compare_visibility(m,paths,meta['styles'],v['camera']);s=r['samples'];support=sample_support(s,f['support'])
                save(folder/(arm+'_'+part+'_SAMPLES.npz'),**s,original_ID_S=support)
                visible=s['status']==0;w=s['length_weight'];alpha=s['legacy_alpha']
                totals['projected_length']+=float(w.sum());totals['proxy_visible_length']+=float(w[visible].sum())
                for code in (1,2,3,4):totals['rejected_status_'+str(code)]+=float(w[s['status']==code].sum())
                for mode,a in [('preS',alpha),('linked_natural',alpha*support),('linked_matched',alpha*support*scales[arm+'_linked'])]:
                    totals[mode+'_own_visible_missing_length']+=float(w[visible&(a<=.05)].sum())
                partition_ink.append(np.maximum.reduce(list(r['coverage']['legacy'].values())).astype(np.float32)*meta['styles']['4'].get('ink_strength',.8))
            high=np.maximum(*partition_ink);low=high.reshape(v['camera']['height'],2,v['camera']['width'],2).mean((1,3))
            np.testing.assert_array_equal(low,f[arm+'_preS'])
            row=dict(view=view,arm=arm,**dict(totals),scope='Per-stroke own-raster sampling, no overlap credit; proxy visibility, not physical truth; no interval backend change')
            summaries.append(row);print('ATTRIBUTION',json.dumps(row),flush=True)
    js(out/'SUMMARY.json',summaries)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','derive','build','evaluate','attribution']);args=ap.parse_args();globals()[args.stage]()
