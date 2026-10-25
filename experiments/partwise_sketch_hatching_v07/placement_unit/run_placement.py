"""Unit004: fixed carrier, field and lengths; original versus surface seeds."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT as ROOT,HERE,VENDOR,sha,js,now,output_guard
from pathlib import Path
import argparse,json,shutil,collections
import numpy as np
from scipy import ndimage
from PIL import Image,ImageDraw
from geometry import mesh_data
from hybrid import compose,edit_metrics
from fixed_render import _coverage
from visibility_fixed import compare_visibility,sample_support
from line_field import regenerate
from placement import place,DEFAULTS

OLD=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_010')
PREV=ROOT/'units/unit_001'
FIELD=ROOT/'units/unit_003'
PACKAGE=ROOT/'replay_package/data/lego'
ARMS=('G0_linked','G1_linked','G0_ungated','G1_ungated')

def freeze():
    assert not (UNIT/'PROTOCOL.json').exists()
    decision=json.loads((UNIT/'DECISION.json').read_text());assert decision['action']=='continue'
    boot=json.loads((PREV/'BOOTSTRAP_STATUS.json').read_text());assert all(x['returncode']==0 for x in boot['stages'])
    js(UNIT/'CAMERAS.json',json.loads((PREV/'CAMERAS.json').read_text()))
    views=json.loads((UNIT/'CAMERAS.json').read_text())['views']
    inputs=[UNIT/'DECISION.json',OLD/'asset/FRAME.json']
    for folder in (PREV,ROOT/'units/unit_002',FIELD,PACKAGE):inputs.extend(p for p in folder.rglob('*') if p.is_file())
    inputs.extend(Path(v['cache']) for v in views)
    meta=json.loads((PACKAGE/'asset.json').read_text());inputs.append(Path(meta['original']['original_ply']))
    js(UNIT/'INPUT_LOCK.json',dict(files={str(p):sha(p) for p in sorted(set(inputs))}))
    source=fresh(UNIT/'source_snapshot');files={};snapshots={}
    for origin in (HERE,VENDOR):
        for p in origin.iterdir():
            if not p.is_file() or p.suffix not in ('.py','.cpp','.json','.md'):continue
            relative=Path('own' if origin==HERE else 'vendor')/p.name;dest=source/relative;dest.parent.mkdir(exist_ok=True);shutil.copyfile(p,dest)
            files[str(p)]=sha(p);snapshots[str(relative)]=sha(dest)
    js(UNIT/'SOURCE_LOCK.json',dict(files=files,snapshots=snapshots))
    p=dict(unit='unit_004',frozen_utc=now(),decision_sha256=sha(UNIT/'DECISION.json'),
        question='Does same-layer whole-path-aware surface seed placement improve readability at unchanged field, counts and lengths?',
        changed_variable=decision['changed_variable'],falsification=decision['falsification'],placement=DEFAULTS,
        field='Exact saved unit003 F0, original carrier, no regularization or denoising.',
        metric='Manifold shared-edge midpoint portals; straight within-triangle links; source paths connect at point-to-segment distances; exact same-face sample-to-segment fallback. Upper bound on intrinsic distance, NOT exact geodesic. Whole paths sampled at <=.01 world spacing, trapezoid arclength weights.',
        selection='One ascending parent-ID coordinate replacement pass.12 independent area-uniform candidates per stroke/component using PCG64(seed20261025+parentID). Same layer and component only. Max lexicographic(min capped path clearance, weighted mean). Caps .06/.075. Original feasible seed first; ties retain original. Reject alternatives not reaching both half-length budgets; never delete/shorten strokes.',
        identities='G0 parent+500000000000; G1 parent+600000000000; no Gaussian ownership implied.',
        controls='Original310475 GS rows/geometry/fullSH/opacity, paper41058 and weights,ink21006 and weights,M1/UNKNOWN195279,2121 target faces,old2030/added91 stops,1px/AA2,tolerance.004,masks band2; component/layer stroke quotas and per-parent lengths fixed.',
        matching='One scalar per G0/G1 linked/ungated from four fixed BUILD absolute hybrid-paper RGB L1; common minimum natural budget. Natural retained; no DEV fit.',
        cache_policy='Reuse verified source/paper/S; actually rasterize G0/G1 every distinct camera; no repeat bootstrap.',
        scope='CPU original-GS paper plus optional original-ID regional S-linked proxy ink; no true surface, per-path Gaussian attachment or temporal certification.',
        resources=dict(CPU_affinity=2,numeric_threads=1,GPU=False,serial=True),
        frozen={name:sha(UNIT/name) for name in ('INPUT_LOCK.json','SOURCE_LOCK.json','CAMERAS.json')})
    js(UNIT/'PROTOCOL.json',p);js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json')))
    js(UNIT/'STATUS.json',dict(execution_state='partial',stage='frozen_before_real_generation_and_eval',scientific_verdict='pending',gaussian_link_progress='Verified original-GS layers reused; placement comparison pending',scientific_seal=False))
    print('FROZEN',len(set(inputs)),'inputs',flush=True)

def protocol():
    p=json.loads((UNIT/'PROTOCOL.json').read_text());assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    assert sha(UNIT/'DECISION.json')==p['decision_sha256']
    for name,h in p['frozen'].items():assert sha(UNIT/name)==h,name
    for path,h in json.loads((UNIT/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(path)==h,path
    p['views']=json.loads((UNIT/'CAMERAS.json').read_text())['views'];return p

def load_assets():
    t=npz(PACKAGE/'unit_008_asset/TARGET.npz')
    oldmesh=mesh_data(t['vertices'],t['faces'],t['old_face_regions']);mesh=mesh_data(t['vertices'],t['faces'],t['face_regions'])
    a=[npz(PREV/'asset'/('A_'+part+'.npz')) for part in ('old','added')]
    return oldmesh,mesh,a,json.loads((PACKAGE/'asset.json').read_text())

def derive():
    p=protocol();out=fresh(UNIT/'asset');oldmesh,mesh,old,meta=load_assets()
    field=npz(FIELD/'asset/FIELDS.npz');f0=field['F0'];partitions=field['partitions'];save(out/'FIELDS.npz',**field)
    stats={};records={};placement={}
    for part,previous,label in zip(('old','added'),old,(1,2)):
        allowed=partitions==label;save(out/('A_'+part+'.npz'),**previous)
        control,rec0=regenerate(mesh,previous,allowed,f0,500_000_000_000)
        historical=npz(FIELD/'asset'/('F0_'+part+'.npz'))
        for key in ('points','bary','face','layer_id','visibility_mask','parent_stroke_id'):np.testing.assert_array_equal(control[key],historical[key])
        new,rec1,diag=place(mesh,previous,allowed,f0,600_000_000_000,p['placement'])
        placement[part]={k:v for k,v in diag.items() if k not in ('before','after')}
        js(out/('PLACEMENT_'+part+'.json'),diag)
        for arm,paths,rec in [('G0',control,rec0),('G1',new,rec1)]:
            save(out/(arm+'_'+part+'.npz'),**paths);js(out/(arm+'_'+part+'_SEEDS.json'),rec)
            stats[arm+'_'+part]=path_stats(paths)
            records[arm+'_'+part]=dict(seeds=len(rec),stops=dict(collections.Counter(r[k] for r in rec for k in ('minus_stop','plus_stop'))),
                requested_length=sum(r['requested_length'] for r in rec),actual_length=sum(r['actual_length'] for r in rec))
        print('PART',part,placement[part]['moved_strokes'],stats['G1_'+part],flush=True)
    links=npz(PACKAGE/'SOURCE_LINK.npz');binding=npz(PACKAGE/'SOURCE_BINDING.npz')
    np.testing.assert_array_equal(links['source_index'],np.arange(310475));assert int(binding['unknown'].sum())==195279
    assert int((links['paper_strength']>0).sum())==41058 and int((links['ink_strength']>0).sum())==21006
    result=dict(placement=placement,paths=stats,seeds=records,original_carrier_unchanged=True,source_rows=310475,paper_rows=41058,ink_rows=21006,UNKNOWN=195279)
    js(out/'ASSET.json',result);js(out/'PROVENANCE.json',dict(source_carrier=str(PACKAGE/'unit_008_asset/TARGET.npz'),
        fixed_field=str(FIELD/'asset/FIELDS.npz'),original_paths=str(PREV/'asset'),placement_config=p['placement'],scope=p['scope']))
    js(UNIT/'ASSET_LOCK.json',dict(files={str(x.relative_to(UNIT)):sha(x) for x in out.iterdir()}))

def check_assets():
    for path,h in json.loads((UNIT/'ASSET_LOCK.json').read_text())['files'].items():assert sha(UNIT/path)==h,path

def render_pair(meshes,paths,meta,camera):
    ink=[];rasters=[]
    for m,path in zip(meshes,paths):
        r=_coverage(m,{4:path},meta['styles'],camera,2)
        ink.append(np.maximum.reduce(list(r['coverage'][4].values())).astype(np.float32)*meta['styles']['4'].get('ink_strength',.8));rasters.append(r)
    high=np.maximum(*ink);low=high.reshape(camera['height'],2,camera['width'],2).mean((1,3))
    layers={}
    for layer in (0,1):
        merged=np.maximum(*[r['coverage'][4].get(layer,np.zeros_like(ink[0],bool)).astype(np.float32)*meta['styles']['4'].get('ink_strength',.8) for r in rasters])
        layers[layer]=merged.reshape(camera['height'],2,camera['width'],2).mean((1,3))
    return low,rasters,layers

def compute(v):
    ref=npz(v['cache']);oldmesh,mesh,_,meta=load_assets()
    f={k:ref[k].copy() for k in ('source','paper','support','regions','old_regions')}
    for arm in ('G0','G1'):
        paths=[npz(UNIT/'asset'/(arm+'_'+part+'.npz')) for part in ('old','added')]
        ink,rasters,layers=render_pair((oldmesh,mesh),paths,meta,v['camera']);f[arm+'_preS']=ink
        for layer,value in layers.items():f[arm+'_layer'+str(layer)+'_preS']=value
        np.testing.assert_array_equal(rasters[0]['regions'],ref['old_regions']);np.testing.assert_array_equal(rasters[1]['regions'],ref['regions'])
        f[arm+'_fragment_diagnostics']=np.asarray([[r['diagnostics']['4'][key] for key in ('covered_fragments','accepted_fragments','region_rejected','depth_rejected')] for r in rasters],np.int64)
        if arm=='G0':np.testing.assert_array_equal(ink,ref['local_ink'])
        for link in ('linked','ungated'):
            key=arm+'_'+link;f[key+'_natural'],f[key+'_natural_alpha']=compose(f['paper'],ink,f['support'],link=='linked')
        if arm=='G0':np.testing.assert_array_equal(f['G0_linked_natural'],ref['local_raw'])
    return f

def attribution():
    p=protocol();scales=json.loads((UNIT/'BUILD_MATCH.json').read_text())['scales'];oldmesh,mesh,_,meta=load_assets();out=fresh(UNIT/'attribution');summaries=[]
    for v in (v for v in p['views'] if v['kind']=='dev' and v['camera']['view'] in ('orbit_61_24_5.3','orbit_241_24_5.3')):
        view=v['camera']['view'];folder=fresh(out/view);f=npz(UNIT/'dev'/view/'FRAME.npz')
        for arm in ('G0','G1'):
            totals=collections.Counter();partition_ink=[]
            for part,m in zip(('old','added'),(oldmesh,mesh)):
                paths=npz(UNIT/'asset'/(arm+'_'+part+'.npz'));r=compare_visibility(m,paths,meta['styles'],v['camera']);s=r['samples'];support=sample_support(s,f['support'])
                save(folder/(arm+'_'+part+'_SAMPLES.npz'),**s,original_ID_S=support)
                visible=s['status']==0;w=s['length_weight'];alpha=s['legacy_alpha'];totals['projected_length']+=float(w.sum());totals['proxy_visible_length']+=float(w[visible].sum())
                for code in (1,2,3,4):totals['rejected_status_'+str(code)]+=float(w[s['status']==code].sum())
                for mode,a in [('preS',alpha),('linked_natural',alpha*support),('linked_matched',alpha*support*scales[arm+'_linked'])]:totals[mode+'_own_visible_missing_length']+=float(w[visible&(a<=.05)].sum())
                partition_ink.append(np.maximum.reduce(list(r['coverage']['legacy'].values())).astype(np.float32)*meta['styles']['4'].get('ink_strength',.8))
            high=np.maximum(*partition_ink);low=high.reshape(v['camera']['height'],2,v['camera']['width'],2).mean((1,3));np.testing.assert_array_equal(low,f[arm+'_preS'])
            row=dict(view=view,arm=arm,**dict(totals),scope='Per-stroke own-raster support against fixed original proxy; not physical truth.');summaries.append(row);print('ATTRIBUTION',json.dumps(row),flush=True)
    js(out/'SUMMARY.json',summaries)

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
            a=arm.split('_')[0];im,alpha=compose(f['paper'],f[a+'_preS'],f['support'],arm.endswith('linked') and not arm.endswith('ungated'),scales[arm])
            actual[arm]+=float(np.abs(im-f['paper'])[target].sum(dtype=float))
    assert max(abs(x-budget)/budget for x in actual.values())<1e-5
    js(UNIT/'BUILD_MATCH.json',dict(records=records,natural_totals=totals,budget=budget,scales=scales,actual_matched=actual))
    js(UNIT/'BUILD_LOCK.json',dict(files={str(x.relative_to(UNIT)):sha(x) for x in [*out.iterdir(),UNIT/'BUILD_MATCH.json']}))
    print('MATCH',totals,scales,flush=True)
def matched(f,scales):
    for arm in ARMS:
        f[arm+'_matched'],f[arm+'_matched_alpha']=compose(f['paper'],f[arm.split('_')[0]+'_preS'],f['support'],arm.split('_')[1]=='linked',scales[arm])
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
        for link in ('linked','ungated'):result['delta'][link+'_'+mode]=edit_metrics(f['G0_'+link+'_'+mode],f['G1_'+link+'_'+mode],regions)
    for n,mask in [('target',target),('interior',inner)]:
        result['support'][n]=dict(pixels=int(mask.sum()),mean=float(f['support'][mask].mean()),above_005=float((f['support'][mask]>.05).mean()))
    for arm in ('G0','G1'):
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
            js(out/'EVALUATION.json',dict(camera=v['camera'],measurements=m,G0_exact=True,source_paper_support_fixed=True))
            for key in ('source','paper'):png(out/(key+'.png'),f[key])
            for arm in ('G0','G1'):
                png(out/(arm+'_preS_ink.png'),1-f[arm+'_preS'])
                for layer in (0,1):png(out/(arm+'_layer'+str(layer)+'_preS.png'),1-f[arm+'_layer'+str(layer)+'_preS'])
            panel(out/'SEPARATE_LAYERS.png',[1-f[arm+'_layer'+str(layer)+'_preS'] for layer in (0,1) for arm in ('G0','G1')],['Layer '+str(layer)+' | '+arm+' before S' for layer in (0,1) for arm in ('G0','G1')],columns=2)
            for arm in ARMS:
                for mode in ('natural','matched'):
                    key=arm+'_'+mode;png(out/(key+'.png'),f[key]);png(out/(key+'_ink.png'),1-f[key+'_alpha'])
            keys=['source','paper','G0_linked_matched','G1_linked_matched','G0_ungated_matched','G1_ungated_matched']
            titles=['Original GS','Fixed GS paper','G0 original seeds | linked matched','G1 surface placement | linked matched','G0 original seeds | ungated matched','G1 surface placement | ungated matched']
            panel(out/'COMPARISON.png',[f[k] for k in keys],[view+' | '+t for t in titles],columns=3)
            panel(out/'INK_LAYERS.png',[1-f[k] for k in ('G0_preS','G1_preS','G0_linked_matched_alpha','G1_linked_matched_alpha')],
                ['G0 before S | natural','G1 before S | natural','G0 after S | matched','G1 after S | matched'],columns=2)
            panel(out/'NATURAL.png',[f[k] for k in ('paper','G0_linked_natural','G1_linked_natural')],['Fixed GS paper','G0 natural linked','G1 natural linked'])
        row=dict(kind=kind,view=view,duplicate=duplicate,target_pixels=m['support']['target']['pixels'])
        for arm in ARMS:
            key=arm+'_matched';q=m['source_edit'][key]
            row[arm]=dict(ink_L1=m['ink_effect'][key]['target_full']['raw_L1_sum'],coverage=m['coverage'][key]['target']['fraction'],
                         interior_coverage=m['coverage'][key]['interior']['fraction'],far_other=q['far_other']['raw_L1_sum'],background=q['far_background']['raw_L1_sum'])
        summary.append(row);print('EVAL',json.dumps(row),flush=True)
    js(UNIT/'SUMMARY.json',summary)
    for label,filename,keys in [('ALL_DEV_MATCHED','matched',['source','paper','G0_linked_matched','G1_linked_matched']),
                               ('ALL_DEV_NATURAL','natural',['source','paper','G0_linked_natural','G1_linked_natural'])]:
        arrays=[];titles=[]
        for v in (v for v in p['views'] if v['kind']=='dev'):
            f=npz(UNIT/'dev'/v['camera']['view']/'FRAME.npz')
            for key in keys:arrays.append(f[key]);titles.append(v['camera']['view']+' | '+key)
        panel(UNIT/(label+'.png'),arrays,titles,columns=4)
    arrays=[];titles=[]
    for v in (v for v in p['views'] if v['kind']=='arc'):
        f=npz(UNIT/'arc'/v['camera']['view']/'FRAME.npz')
        for key in ('G0_linked_matched','G1_linked_matched'):arrays.append(f[key]);titles.append(v['camera']['view']+' | '+key)
    panel(UNIT/'REAR_CAMERA_SEQUENCE.png',arrays,titles,columns=2)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','derive','build','evaluate','attribution']);args=ap.parse_args();globals()[args.stage]()
