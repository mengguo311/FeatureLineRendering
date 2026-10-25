"""Saved layout x carrier crossover; original first-hit reference stays fixed."""
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
from crossover import cross_layouts
BASE=ROOT/'units/unit_002'
PACKAGE=ROOT/'replay_package/data/lego'
PATH_ARMS=('OO','OC','CO','CC')
PAIRS=(('OO','OC'),('CO','CC'),('OO','CO'),('OC','CC'),('OO','CC'),('OC','CO'))
ARMS=tuple(a+'_'+link for a in PATH_ARMS for link in ('linked','ungated'))

def prior_frame(v):
    return BASE/'build'/(v['camera']['view']+'.npz') if v['kind']=='build' else BASE/v['kind']/v['camera']['view']/'FRAME.npz'

def freeze():
    assert not (UNIT/'PROTOCOL.json').exists()
    decision=json.loads((UNIT/'DECISION.json').read_text());assert decision['action']=='continue'
    js(UNIT/'CAMERAS.json',json.loads((BASE/'CAMERAS.json').read_text()))
    views=json.loads((UNIT/'CAMERAS.json').read_text())['views']
    inputs=[UNIT/'DECISION.json',BASE/'CAMERAS.json',BASE/'ASSET_LOCK.json',BASE/'ARTIFACT_MANIFEST.json',BASE/'REPORT_ZH.md',
        ROOT/'units/unit_009/REPORT_ZH.md',ROOT/'units/unit_009/MATERIAL_VISIBILITY.json',
        ROOT/'units/unit_001/BOOTSTRAP_STATUS.json',ROOT/'units/unit_001/cold_hybrid/RELOAD_RECEIPT.json']
    assetlock=json.loads((BASE/'ASSET_LOCK.json').read_text())['files']
    for name,h in assetlock.items():assert sha(BASE/name)==h,name;inputs.append(BASE/name)
    manifest=json.loads((BASE/'ARTIFACT_MANIFEST.json').read_text())['files']
    for v in views:
        q=prior_frame(v);assert sha(q)==manifest[str(q.relative_to(BASE))],q
        inputs.extend([q,Path(v['cache'])])
    inputs.extend(PACKAGE/name for name in ('asset.json','SOURCE_LINK.npz','SOURCE_BINDING.npz','unit_008_asset/TARGET.npz'))
    meta=json.loads((PACKAGE/'asset.json').read_text());inputs.append(Path(meta['original']['original_ply']))
    js(UNIT/'INPUT_LOCK.json',dict(files={str(p):sha(p) for p in sorted(set(inputs))}))
    source=fresh(UNIT/'source_snapshot');files={};snapshots={}
    for origin in (HERE,VENDOR):
        for q in origin.iterdir():
            if not q.is_file() or q.suffix not in ('.py','.cpp','.json','.md'):continue
            relative=Path('own' if origin==HERE else 'vendor')/q.name;dest=source/relative;dest.parent.mkdir(exist_ok=True);shutil.copyfile(q,dest)
            files[str(q)]=sha(q);snapshots[str(relative)]=sha(dest)
    js(UNIT/'SOURCE_LOCK.json',dict(files=files,snapshots=snapshots))
    p=dict(unit='unit_010',frozen_utc=now(),decision_sha256=sha(UNIT/'DECISION.json'),
        question='Saved slicer material layout versus embedding; does carrier-induced layout help when returned to original geometry?',
        changed_variable=decision['changed_variable'],falsification=decision['falsification'],
        arms={'OO':'unit002 A paths on original O','OC':'same P_O face/bary on saved C','CO':'unit002 C material paths pulled back to O','CC':'unit002 C paths on C'},
        construction='No new denoising/field/generation. Same ordered topology and labels. Exact saved diagonals; two new cross embeddings.',
        identities='OC 5e12, CO 6e12 plus partition 1e6 plus source-rank; immediate saved layout ID. No cross-family correspondence.',
        controls='Original310475 GS rows/fullSH/opacity/PLY, paper41058/ink21006, M1/UNKNOWN195279,target2121 old2030/added91,style and width1px/AA2/band2 fixed.',
        visibility='Carrier-specific owner planes; every arm raycasts original O; .004 tolerance unchanged.',
        matching='One global factor per 8 linked/ungated arm, 4 BUILD target RGB L1 hybrid-paper, common minimum natural total. Natural outputs retained.',
        material_sampling='Within OO->OC and CO->CC ONLY; use O-embedded saved centerline samples and fixed O projected-length weights. No correspondence across layout families.',
        views='Four exposed BUILD; four exposed DEV plus231/241/251 arc;241 duplicate; six distinct eval cameras, no temporal claim.',
        cache_policy='Hash-verified original GS layers and unit002 OO/CC natural frames reused. Both cross arms actually rasterized; replay rerasterizes all four. unit001 bootstrap not repeated.',
        scope='Diagnostic response of same slicing generator and embedding; not a full algorithm factorial, true surface, native Gaussian ink or per-path original-ID certification.',
        resources=dict(cpu_affinity=2,numeric_threads=1,GPU=False,serial=True),
        frozen={name:sha(UNIT/name) for name in ('INPUT_LOCK.json','SOURCE_LOCK.json','CAMERAS.json')})
    js(UNIT/'PROTOCOL.json',p);js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json')))
    js(UNIT/'STATUS.json',dict(execution_state='partial',stage='frozen_before_real_scene',scientific_verdict='pending',gaussian_link_progress='Frozen original rows/weights; crossover pending',scientific_seal=False))
    print('FROZEN',len(set(inputs)),flush=True)

def protocol():
    p=json.loads((UNIT/'PROTOCOL.json').read_text());assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    assert sha(UNIT/'DECISION.json')==p['decision_sha256']
    for name,h in p['frozen'].items():assert sha(UNIT/name)==h,name
    for path,h in json.loads((UNIT/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(path)==h,path
    p['views']=json.loads((UNIT/'CAMERAS.json').read_text())['views'];return p

def load_assets():
    t=npz(PACKAGE/'unit_008_asset/TARGET.npz');c=npz(BASE/'asset/CARRIER.npz')
    np.testing.assert_array_equal(c['faces'],t['faces'])
    refs=[mesh_data(t['vertices'],t['faces'],t[k]) for k in ('old_face_regions','face_regions')]
    targets=[mesh_data(c['vertices'],c['faces'],c[k]) for k in ('old_face_regions','face_regions')]
    for a,b in zip(refs,targets):np.testing.assert_array_equal(a['regions'],b['regions'])
    return refs,targets,t,json.loads((PACKAGE/'asset.json').read_text())

def derive():
    p=protocol();out=fresh(UNIT/'asset');refs,targets,t,meta=load_assets();stats={};migrations={}
    shutil.copyfile(BASE/'asset/CARRIER.npz',out/'CARRIER.npz')
    for part,ref,target,offset in zip(('old','added'),refs,targets,(0,1_000_000)):
        a=npz(BASE/'asset'/('A_'+part+'.npz'));c=npz(BASE/'asset'/('C_'+part+'.npz'))
        paths,records=cross_layouts(a,c,ref,target,5_000_000_000_000+offset,6_000_000_000_000+offset)
        for arm in PATH_ARMS:
            if arm in ('OO','CC'):shutil.copyfile(BASE/'asset'/(('A' if arm=='OO' else 'C')+'_'+part+'.npz'),out/(arm+'_'+part+'.npz'))
            else:save(out/(arm+'_'+part+'.npz'),**paths[arm]);js(out/(arm+'_'+part+'_MIGRATION.json'),records[arm])
            stats[arm+'_'+part]=path_stats(paths[arm])
        migrations[part]={arm:dict(paths=len(rows),moved_paths=sum(r['moved'] for r in rows),max_endpoint_displacement=max(r['max_endpoint_displacement'] for r in rows)) for arm,rows in records.items()}
    link=npz(PACKAGE/'SOURCE_LINK.npz');binding=npz(PACKAGE/'SOURCE_BINDING.npz')
    np.testing.assert_array_equal(link['source_index'],np.arange(310475));assert binding['unknown'].sum()==195279
    assert (link['paper_strength']>0).sum()==41058 and (link['ink_strength']>0).sum()==21006
    result=dict(paths=stats,migration=migrations,source_rows=310475,paper_rows=41058,ink_rows=21006,UNKNOWN=195279,
        scope='Two saved slicer layouts; no H regeneration or repair. All historical negative results and guard failures preserved.')
    js(out/'ASSET.json',result);js(out/'PROVENANCE.json',dict(source=str(BASE/'asset'),decision_sha256=p['decision_sha256'],scope=p['scope']))
    js(UNIT/'ASSET_LOCK.json',dict(files={str(x.relative_to(UNIT)):sha(x) for x in out.iterdir()}));print('ASSET',json.dumps(result),flush=True)

def check_assets():
    for path,h in json.loads((UNIT/'ASSET_LOCK.json').read_text())['files'].items():assert sha(UNIT/path)==h,path

def compute(v,rerender_all=False):
    cached=npz(v['cache']);prior=npz(prior_frame(v));refs,targets,t,meta=load_assets()
    f={k:cached[k].copy() for k in ('source','paper','support','regions','old_regions')}
    for key in f:np.testing.assert_array_equal(f[key],prior[key])
    for arm in PATH_ARMS:
        diagonal={'OO':'A','CC':'C'}.get(arm)
        if diagonal and not rerender_all:
            for suffix in ('_preS','_fragment_diagnostics'):f[arm+suffix]=prior[diagonal+suffix].copy()
        else:
            rasters=[];carriers=refs if arm[1]=='O' else targets
            for part,m,ref in zip(('old','added'),carriers,refs):
                path=npz(UNIT/'asset'/(arm+'_'+part+'.npz'));rasters.append(_coverage(m,{4:path},meta['styles'],v['camera'],2,occluder=ref))
            strength=meta['styles']['4'].get('ink_strength',.8)
            high=np.maximum(*[np.maximum.reduce(list(r['coverage'][4].values())).astype(np.float32)*strength for r in rasters])
            f[arm+'_preS']=high.reshape(v['camera']['height'],2,v['camera']['width'],2).mean((1,3))
            for key,r in zip(('old_regions','regions'),rasters):np.testing.assert_array_equal(r['regions'],cached[key])
            f[arm+'_fragment_diagnostics']=np.asarray([[r['diagnostics']['4'][k] for k in ('covered_fragments','accepted_fragments','region_rejected','depth_rejected')] for r in rasters],np.int64)
        for link in ('linked','ungated'):
            f[arm+'_'+link+'_natural'],f[arm+'_'+link+'_natural_alpha']=compose(f['paper'],f[arm+'_preS'],f['support'],link=='linked')
        if diagonal:
            for suffix in ('_preS','_fragment_diagnostics','_linked_natural','_ungated_natural','_linked_natural_alpha','_ungated_natural_alpha'):np.testing.assert_array_equal(f[arm+suffix],prior[diagonal+suffix])
    return f

def attribution():
    p=protocol();check_assets();scales=json.loads((UNIT/'BUILD_MATCH.json').read_text())['scales'];refs,targets,_,meta=load_assets();out=fresh(UNIT/'attribution');summaries=[]
    for v in (v for v in p['views'] if v['kind']=='dev' and v['camera']['view'] in ('orbit_61_24_5.3','orbit_241_24_5.3')):
        view=v['camera']['view'];folder=fresh(out/view);f=npz(UNIT/'dev'/view/'FRAME.npz')
        for arm in PATH_ARMS:
            carriers=refs if arm[1]=='O' else targets;totals=collections.Counter();inks=[]
            for part,m,ref in zip(('old','added'),carriers,refs):
                paths=npz(UNIT/'asset'/(arm+'_'+part+'.npz'));r=compare_visibility(m,paths,meta['styles'],v['camera'],occluder=ref);s=r['samples'];support=sample_support(s,f['support'])
                save(folder/(arm+'_'+part+'_SAMPLES.npz'),**s,original_ID_S=support)
                visible=s['status']==0;w=s['length_weight'];alpha=s['legacy_alpha']
                totals['projected_length']+=float(w.sum());totals['proxy_visible_length']+=float(w[visible].sum())
                for code in (1,2,3,4):totals['rejected_status_'+str(code)]+=float(w[s['status']==code].sum())
                for mode,a in [('preS',alpha),('linked_natural',alpha*support),('linked_matched',alpha*support*scales[arm+'_linked'])]:totals[mode+'_own_visible_missing_length']+=float(w[visible&(a<=.05)].sum())
                inks.append(np.maximum.reduce(list(r['coverage']['legacy'].values())).astype(np.float32)*meta['styles']['4'].get('ink_strength',.8))
            low=np.maximum(*inks).reshape(v['camera']['height'],2,v['camera']['width'],2).mean((1,3));np.testing.assert_array_equal(low,f[arm+'_preS'])
            row=dict(view=view,arm=arm,**dict(totals),scope='Own-stroke raster support; fixed original first-hit reference. No cross-family path matching.');summaries.append(row);print('ATTRIBUTION',json.dumps(row),flush=True)
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
            for a,b in PAIRS:
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
            js(out/'EVALUATION.json',dict(camera=v['camera'],measurements=m,saved_diagonals_exact=True,source_paper_support_fixed=True))
            for key in ('source','paper'):png(out/(key+'.png'),f[key])
            for arm in PATH_ARMS:
                png(out/(arm+'_preS_ink.png'),1-f[arm+'_preS'])
            for arm in ARMS:
                for mode in ('natural','matched'):
                    key=arm+'_'+mode;png(out/(key+'.png'),f[key]);png(out/(key+'_ink.png'),1-f[key+'_alpha'])
            keys=['source','paper']+[a+'_linked_matched' for a in PATH_ARMS]+[a+'_ungated_matched' for a in PATH_ARMS]
            panel(out/'COMPARISON.png',[f[k] for k in keys],[view+' | '+k for k in keys],columns=4)
            keys=[a+'_preS' for a in PATH_ARMS]+[a+'_linked_matched_alpha' for a in PATH_ARMS]
            panel(out/'INK_LAYERS.png',[1-f[k] for k in keys],keys,columns=4)
            keys=['source','paper']+[a+'_linked_natural' for a in PATH_ARMS]+[a+'_ungated_natural' for a in PATH_ARMS]
            panel(out/'NATURAL.png',[f[k] for k in keys],keys,columns=4)
        row=dict(kind=kind,view=view,duplicate=duplicate,target_pixels=m['support']['target']['pixels'])
        for arm in ARMS:
            key=arm+'_matched';q=m['source_edit'][key]
            row[arm]=dict(ink_L1=m['ink_effect'][key]['target_full']['raw_L1_sum'],coverage=m['coverage'][key]['target']['fraction'],
                         interior_coverage=m['coverage'][key]['interior']['fraction'],far_other=q['far_other']['raw_L1_sum'],background=q['far_background']['raw_L1_sum'])
        summary.append(row);print('EVAL',json.dumps(row),flush=True)
    js(UNIT/'SUMMARY.json',summary)
    for label,filename,keys in [('ALL_DEV_MATCHED','matched',['source','paper']+[a+'_linked_matched' for a in PATH_ARMS]),
                               ('ALL_DEV_NATURAL','natural',['source','paper']+[a+'_linked_natural' for a in PATH_ARMS])]:
        arrays=[];titles=[]
        for v in (v for v in p['views'] if v['kind']=='dev'):
            f=npz(UNIT/'dev'/v['camera']['view']/'FRAME.npz')
            for key in keys:arrays.append(f[key]);titles.append(v['camera']['view']+' | '+key)
        panel(UNIT/(label+'.png'),arrays,titles,columns=6)
    arrays=[];titles=[]
    for v in (v for v in p['views'] if v['kind']=='arc'):
        f=npz(UNIT/'arc'/v['camera']['view']/'FRAME.npz')
        for key in (a+'_linked_matched' for a in PATH_ARMS):arrays.append(f[key]);titles.append(v['camera']['view']+' | '+key)
    panel(UNIT/'REAR_CAMERA_SEQUENCE.png',arrays,titles,columns=4)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','derive','build','evaluate','attribution']);args=ap.parse_args();globals()[args.stage]()
