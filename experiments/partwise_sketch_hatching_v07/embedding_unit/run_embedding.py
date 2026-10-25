"""Unit009: frozen H material paths on original versus saved denoised carrier."""
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
from embedding import migrate
BASE=ROOT/'units/unit_008'
CARRIER=ROOT/'units/unit_002/asset/CARRIER.npz'
PACKAGE=ROOT/'replay_package/data/lego'
PATH_ARMS=('A','T')
ARMS=tuple(a+'_'+link for a in PATH_ARMS for link in ('linked','ungated'))

def freeze():
    assert not (UNIT/'PROTOCOL.json').exists()
    decision=json.loads((UNIT/'DECISION.json').read_text());assert decision['action']=='continue'
    js(UNIT/'CAMERAS.json',json.loads((BASE/'CAMERAS.json').read_text()))
    views=json.loads((UNIT/'CAMERAS.json').read_text())['views']
    inputs=[UNIT/'DECISION.json',BASE/'CAMERAS.json',BASE/'ASSET_LOCK.json',BASE/'REPORT_ZH.md',BASE/'BOUNDARY_READBACK.json',
        CARRIER,ROOT/'units/unit_002/asset/DENOISE.npz',ROOT/'units/unit_002/ASSET_LOCK.json',ROOT/'units/unit_002/asset/ASSET.json',
        ROOT/'units/unit_001/BOOTSTRAP_STATUS.json',ROOT/'units/unit_001/cold_hybrid/RELOAD_RECEIPT.json']
    for part in ('old','added'):inputs.extend(BASE/'asset'/name for name in ('A_'+part+'.npz','A_'+part+'_SEEDS.json'))
    inputs.extend(PACKAGE/name for name in ('asset.json','SOURCE_LINK.npz','SOURCE_BINDING.npz','unit_008_asset/TARGET.npz'))
    for v in views:
        inputs.append(Path(v['cache']));inputs.append(BASE/'build'/(v['camera']['view']+'.npz') if v['kind']=='build' else BASE/v['kind']/v['camera']['view']/'FRAME.npz')
    meta=json.loads((PACKAGE/'asset.json').read_text());inputs.append(Path(meta['original']['original_ply']))
    # Existing hashes are checked before importing saved carrier and H paths.
    for root,names in [(BASE,{'asset/A_old.npz','asset/A_added.npz','asset/A_old_SEEDS.json','asset/A_added_SEEDS.json'}),(ROOT/'units/unit_002',{'asset/CARRIER.npz','asset/DENOISE.npz','asset/ASSET.json'})]:
        prior=json.loads((root/'ASSET_LOCK.json').read_text())['files']
        for name in names:assert sha(root/name)==prior[name],name
    js(UNIT/'INPUT_LOCK.json',dict(files={str(p):sha(p) for p in sorted(set(inputs))}))
    source=fresh(UNIT/'source_snapshot');files={};snapshots={}
    for origin in (HERE,VENDOR):
        for p in origin.iterdir():
            if not p.is_file() or p.suffix not in ('.py','.cpp','.json','.md'):continue
            relative=Path('own' if origin==HERE else 'vendor')/p.name;dest=source/relative;dest.parent.mkdir(exist_ok=True);shutil.copyfile(p,dest)
            files[str(p)]=sha(p);snapshots[str(relative)]=sha(dest)
    js(UNIT/'SOURCE_LOCK.json',dict(files=files,snapshots=snapshots))
    protocol=dict(unit='unit_009',frozen_utc=now(),decision_sha256=sha(UNIT/'DECISION.json'),
        question='Does already saved bounded carrier denoising help the exact frozen H paths without regeneration?',
        changed_variable=decision['changed_variable'],falsification=decision['falsification'],
        construction='A byte-exact unit008 A=H; T points=bary@unit002 CARRIER triangles, all other fields except new stroke IDs unchanged. No denoising, walking, cuts, repairs or field estimation.',
        identities='T IDs 4e12+partition_offset+rank of immediate H parent; original parent field retained; immediate H lineage stored separately.',
        visibility='Owner face plane from each carrier; first-hit and region masks always original carrier, tolerance .004, width1px,AA2,band2.',
        controls='GS310475 rows/fullSH/opacity, paper41058/ink21006, M1/UNKNOWN195279,target2121 old2030/added91,380 saved H paths and inherited guard failure.',
        matching='One global scalar per A/T linked/ungated arm from four BUILD hybrid-paper absolute RGB L1; common minimum natural total; natural outputs retained.',
        views='Four BUILD, four DEV,231/241/251 arc; all EXPOSED,241 duplicated. No temporal claim.',
        cache_policy='Verified original-GS source/paper/S reused; actual ink rasterization; unit001 cold bootstrap not repeated.',
        scope='Fixed-path embedding perturbation, not full carrier-generator factorial, physical truth or per-path original-ID certification.',
        resources=dict(cpu_affinity=2,numeric_threads=1,GPU=False,serial=True),
        frozen={name:sha(UNIT/name) for name in ('INPUT_LOCK.json','SOURCE_LOCK.json','CAMERAS.json')})
    js(UNIT/'PROTOCOL.json',protocol);js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json')))
    js(UNIT/'STATUS.json',dict(execution_state='partial',stage='frozen_before_real_scene',scientific_verdict='pending',gaussian_link_progress='Original rows and GS layers fixed; migration pending',scientific_seal=False))
    print('FROZEN',len(set(inputs)),flush=True)

def protocol():
    p=json.loads((UNIT/'PROTOCOL.json').read_text());assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    assert sha(UNIT/'DECISION.json')==p['decision_sha256']
    for name,h in p['frozen'].items():assert sha(UNIT/name)==h,name
    for path,h in json.loads((UNIT/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(path)==h,path
    p['views']=json.loads((UNIT/'CAMERAS.json').read_text())['views'];return p

def load_assets():
    t=npz(PACKAGE/'unit_008_asset/TARGET.npz');c=npz(CARRIER)
    np.testing.assert_array_equal(c['faces'],t['faces'])
    refs=[mesh_data(t['vertices'],t['faces'],t[k]) for k in ('old_face_regions','face_regions')]
    targets=[mesh_data(c['vertices'],c['faces'],c[k]) for k in ('old_face_regions','face_regions')]
    for a,b in zip(refs,targets):np.testing.assert_array_equal(a['regions'],b['regions'])
    return refs,targets,t,json.loads((PACKAGE/'asset.json').read_text())

def derive():
    p=protocol();out=fresh(UNIT/'asset');refs,targets,t,meta=load_assets();stats={};migrations={}
    shutil.copyfile(CARRIER,out/'CARRIER.npz')
    for part,ref,target,offset in zip(('old','added'),refs,targets,(0,1_000_000)):
        shutil.copyfile(BASE/'asset'/('A_'+part+'.npz'),out/('A_'+part+'.npz'))
        shutil.copyfile(BASE/'asset'/('A_'+part+'_SEEDS.json'),out/('A_'+part+'_INHERITED_STOPS.json'))
        a=npz(out/('A_'+part+'.npz'));q,records=migrate(a,ref,target,4_000_000_000_000+offset)
        save(out/('T_'+part+'.npz'),**q);js(out/(part+'_MIGRATION.json'),records)
        for arm,paths in [('A',a),('T',q)]:stats[arm+'_'+part]=path_stats(paths)
        migrations[part]=dict(paths=len(records),moved_paths=sum(r['moved'] for r in records),max_endpoint_displacement=max(r['max_endpoint_displacement'] for r in records),
            changed_segments=int((np.linalg.norm(q['points']-a['points'],axis=2)>1e-12).any(1).sum()))
    link=npz(PACKAGE/'SOURCE_LINK.npz');binding=npz(PACKAGE/'SOURCE_BINDING.npz')
    np.testing.assert_array_equal(link['source_index'],np.arange(310475));assert binding['unknown'].sum()==195279
    assert (link['paper_strength']>0).sum()==41058 and (link['ink_strength']>0).sum()==21006
    result=dict(paths=stats,migration=migrations,source_rows=310475,paper_rows=41058,ink_rows=21006,UNKNOWN=195279,
        inherited_failure='All H stop records preserved; migration is not a new integration and does not repair zero_step_cycle.')
    js(out/'ASSET.json',result);js(out/'PROVENANCE.json',dict(A_source=str(BASE/'asset'),T_carrier=str(CARRIER),decision_sha256=p['decision_sha256'],scope=p['scope']))
    js(UNIT/'ASSET_LOCK.json',dict(files={str(x.relative_to(UNIT)):sha(x) for x in out.iterdir()}));print('ASSET',json.dumps(result),flush=True)

def check_assets():
    for path,h in json.loads((UNIT/'ASSET_LOCK.json').read_text())['files'].items():assert sha(UNIT/path)==h,path

def compute(v):
    cached=npz(v['cache']);refs,targets,t,meta=load_assets()
    f={k:cached[k].copy() for k in ('source','paper','support','regions','old_regions')}
    for arm,carriers in [('A',refs),('T',targets)]:
        rasters=[]
        for part,m,ref in zip(('old','added'),carriers,refs):
            path=npz(UNIT/'asset'/(arm+'_'+part+'.npz'));rasters.append(_coverage(m,{4:path},meta['styles'],v['camera'],2,occluder=ref))
        strength=meta['styles']['4'].get('ink_strength',.8)
        high=np.maximum(*[np.maximum.reduce(list(r['coverage'][4].values())).astype(np.float32)*strength for r in rasters])
        f[arm+'_preS']=high.reshape(v['camera']['height'],2,v['camera']['width'],2).mean((1,3))
        for layer in (0,1):
            h=np.maximum(*[r['coverage'][4][layer].astype(np.float32)*strength for r in rasters]);f[arm+'_layer'+str(layer)+'_preS']=h.reshape(v['camera']['height'],2,v['camera']['width'],2).mean((1,3))
        np.testing.assert_array_equal(rasters[0]['regions'],cached['old_regions']);np.testing.assert_array_equal(rasters[1]['regions'],cached['regions'])
        f[arm+'_fragment_diagnostics']=np.asarray([[r['diagnostics']['4'][k] for k in ('covered_fragments','accepted_fragments','region_rejected','depth_rejected')] for r in rasters],np.int64)
        for link in ('linked','ungated'):f[arm+'_'+link+'_natural'],f[arm+'_'+link+'_natural_alpha']=compose(f['paper'],f[arm+'_preS'],f['support'],link=='linked')
    prior=BASE/'build'/(v['camera']['view']+'.npz') if v['kind']=='build' else BASE/v['kind']/v['camera']['view']/'FRAME.npz'
    baseline=npz(prior)
    for suffix in ('_preS','_layer0_preS','_layer1_preS','_linked_natural','_ungated_natural'):np.testing.assert_array_equal(f['A'+suffix],baseline['A'+suffix])
    return f

def attribution():
    p=protocol();check_assets();scales=json.loads((UNIT/'BUILD_MATCH.json').read_text())['scales'];refs,targets,_,meta=load_assets();out=fresh(UNIT/'attribution');summaries=[]
    for v in (v for v in p['views'] if v['kind']=='dev' and v['camera']['view'] in ('orbit_61_24_5.3','orbit_241_24_5.3')):
        view=v['camera']['view'];folder=fresh(out/view);f=npz(UNIT/'dev'/view/'FRAME.npz')
        for arm,carriers in [('A',refs),('T',targets)]:
            totals=collections.Counter();inks=[]
            for part,m,ref in zip(('old','added'),carriers,refs):
                paths=npz(UNIT/'asset'/(arm+'_'+part+'.npz'));r=compare_visibility(m,paths,meta['styles'],v['camera'],occluder=ref);s=r['samples'];support=sample_support(s,f['support'])
                original=npz(UNIT/'asset'/('A_'+part+'.npz'));moved=np.linalg.norm(npz(UNIT/'asset'/('T_'+part+'.npz'))['points']-original['points'],axis=2).max(1)>1e-12
                affected=moved[s['segment_index']];save(folder/(arm+'_'+part+'_SAMPLES.npz'),**s,original_ID_S=support,affected_segment=affected)
                visible=s['status']==0;w=s['length_weight'];alpha=s['legacy_alpha']
                totals['projected_length']+=float(w.sum());totals['proxy_visible_length']+=float(w[visible].sum());totals['affected_proxy_visible_length']+=float(w[visible&affected].sum())
                totals['affected_visible_strokes']+=len(np.unique(s['stroke_id'][visible&affected]))
                for code in (1,2,3,4):totals['rejected_status_'+str(code)]+=float(w[s['status']==code].sum())
                for mode,a in [('preS',alpha),('linked_natural',alpha*support),('linked_matched',alpha*support*scales[arm+'_linked'])]:totals[mode+'_own_visible_missing_length']+=float(w[visible&(a<=.05)].sum())
                inks.append(np.maximum.reduce(list(r['coverage']['legacy'].values())).astype(np.float32)*meta['styles']['4'].get('ink_strength',.8))
            low=np.maximum(*inks).reshape(v['camera']['height'],2,v['camera']['width'],2).mean((1,3));np.testing.assert_array_equal(low,f[arm+'_preS'])
            row=dict(view=view,arm=arm,**dict(totals),scope='Own-stroke raster support against fixed original occluder; projection/sampling changes are not physical truth.');summaries.append(row);print('ATTRIBUTION',json.dumps(row),flush=True)
    js(UNIT/'attribution/SUMMARY.json',summaries)

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
        for link in ('linked','ungated'):
            for a,b in (('A','T'),):
                result['delta'][a+'_vs_'+b+'_'+link+'_'+mode]=edit_metrics(f[a+'_'+link+'_'+mode],f[b+'_'+link+'_'+mode],regions)
    for n,mask in [('target',target),('interior',inner)]:
        result['support'][n]=dict(pixels=int(mask.sum()),mean=float(f['support'][mask].mean()),above_005=float((f['support'][mask]>.05).mean()))
    for arm in PATH_ARMS:
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
            for arm in PATH_ARMS:
                png(out/(arm+'_preS_ink.png'),1-f[arm+'_preS'])
                for layer in (0,1):png(out/(arm+'_layer'+str(layer)+'_preS.png'),1-f[arm+'_layer'+str(layer)+'_preS'])
            for arm in ARMS:
                for mode in ('natural','matched'):
                    key=arm+'_'+mode;png(out/(key+'.png'),f[key]);png(out/(key+'_ink.png'),1-f[key+'_alpha'])
            keys=['source','paper','A_linked_matched','T_linked_matched','A_ungated_matched','T_ungated_matched']
            panel(out/'COMPARISON.png',[f[k] for k in keys],[view+' | '+k for k in keys],columns=4)
            keys=[a+'_preS' for a in PATH_ARMS]+[a+'_linked_matched_alpha' for a in PATH_ARMS]
            panel(out/'INK_LAYERS.png',[1-f[k] for k in keys],keys,columns=2)
            keys=['paper']+[a+'_linked_natural' for a in PATH_ARMS]
            panel(out/'NATURAL.png',[f[k] for k in keys],keys,columns=4)
        row=dict(kind=kind,view=view,duplicate=duplicate,target_pixels=m['support']['target']['pixels'])
        for arm in ARMS:
            key=arm+'_matched';q=m['source_edit'][key]
            row[arm]=dict(ink_L1=m['ink_effect'][key]['target_full']['raw_L1_sum'],coverage=m['coverage'][key]['target']['fraction'],
                         interior_coverage=m['coverage'][key]['interior']['fraction'],far_other=q['far_other']['raw_L1_sum'],background=q['far_background']['raw_L1_sum'])
        summary.append(row);print('EVAL',json.dumps(row),flush=True)
    js(UNIT/'SUMMARY.json',summary)
    for label,filename,keys in [('ALL_DEV_MATCHED','matched',['source','paper','A_linked_matched','T_linked_matched']),
                               ('ALL_DEV_NATURAL','natural',['source','paper','A_linked_natural','T_linked_natural'])]:
        arrays=[];titles=[]
        for v in (v for v in p['views'] if v['kind']=='dev'):
            f=npz(UNIT/'dev'/v['camera']['view']/'FRAME.npz')
            for key in keys:arrays.append(f[key]);titles.append(v['camera']['view']+' | '+key)
        panel(UNIT/(label+'.png'),arrays,titles,columns=4)
    arrays=[];titles=[]
    for v in (v for v in p['views'] if v['kind']=='arc'):
        f=npz(UNIT/'arc'/v['camera']['view']/'FRAME.npz')
        for key in ('A_linked_matched','T_linked_matched'):arrays.append(f[key]);titles.append(v['camera']['view']+' | '+key)
    panel(UNIT/'REAR_CAMERA_SEQUENCE.png',arrays,titles,columns=2)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','derive','build','evaluate','attribution']);args=ap.parse_args();globals()[args.stage]()
