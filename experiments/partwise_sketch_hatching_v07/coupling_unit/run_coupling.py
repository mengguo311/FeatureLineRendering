"""Unit007: preserve H primary paths and restore F0 cross-layer relation."""
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
from coupling import restore_crossing,replace_second_layer
from line_field import transport

OLD=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_010')
PREV=ROOT/'units/unit_001'
PACKAGE=ROOT/'replay_package/data/lego'
BASE=ROOT/'units/unit_006'
PATH_ARMS=('F0','H','J')
ARMS=tuple(a+'_'+link for a in PATH_ARMS for link in ('linked','ungated'))

def freeze():
    assert not (UNIT/'PROTOCOL.json').exists()
    decision=json.loads((UNIT/'DECISION.json').read_text());assert decision['action']=='continue'
    boot=json.loads((PREV/'BOOTSTRAP_STATUS.json').read_text());assert all(x['returncode']==0 for x in boot['stages'])
    js(UNIT/'CAMERAS.json',json.loads((BASE/'CAMERAS.json').read_text()))
    views=json.loads((UNIT/'CAMERAS.json').read_text())['views']
    inputs=[UNIT/'DECISION.json',PREV/'BOOTSTRAP_STATUS.json',PREV/'cold_hybrid/RELOAD_RECEIPT.json',PREV/'asset/SEEDS_AND_STOPS.json',BASE/'CAMERAS.json',BASE/'asset/FIELDS.npz',BASE/'ASSET_LOCK.json',BASE/'BUILD_MATCH.json']
    for part in ('old','added'):
        inputs.append(PREV/'asset'/('A_'+part+'.npz'))
        for arm in ('F0','H'):
            inputs.extend([BASE/'asset'/(arm+'_'+part+'.npz'),BASE/'asset'/(arm+'_'+part+'_SEEDS.json')])
    inputs.extend(PACKAGE/name for name in ('asset.json','SOURCE_LINK.npz','SOURCE_BINDING.npz','unit_008_asset/TARGET.npz'))
    for v in views:
        inputs.append(Path(v['cache']));inputs.append(BASE/'build'/(v['camera']['view']+'.npz') if v['kind']=='build' else BASE/v['kind']/v['camera']['view']/'FRAME.npz')
    for unit in range(1,7):inputs.append(ROOT/'units'/('unit_%03d'%unit)/'REPORT_ZH.md')
    meta=json.loads((PACKAGE/'asset.json').read_text());inputs.append(Path(meta['original']['original_ply']))
    js(UNIT/'INPUT_LOCK.json',dict(files={str(p):sha(p) for p in sorted(set(inputs))}))
    source=fresh(UNIT/'source_snapshot');files={};snapshots={}
    for origin in (HERE,VENDOR):
        for p in origin.iterdir():
            if not p.is_file() or p.suffix not in ('.py','.cpp','.json','.md'):continue
            relative=Path('own' if origin==HERE else 'vendor')/p.name;dest=source/relative;dest.parent.mkdir(exist_ok=True);shutil.copyfile(p,dest)
            files[str(p)]=sha(p);snapshots[str(relative)]=sha(dest)
    js(UNIT/'SOURCE_LOCK.json',dict(files=files,snapshots=snapshots))
    p=dict(unit='unit_007',frozen_utc=now(),decision_sha256=sha(UNIT/'DECISION.json'),
        question='Does the visible benefit survive restoration of baseline per-face crossing relation with exactly frozen H primary paths?',
        changed_variable=decision['changed_variable'],falsification=decision['falsification'],
        construction='J0=H0; J1=(F00 dot F01)*H0 + (n dot (F00 cross F01))*(n cross H0). No new angle/anchor/field solve. H/J differ in secondary crossing relation AND spatial coherence.',
        walker='Byte-exact inherited unit003 walker; original unit001 layer1 midpoint seeds and requested lengths. Never derive seeds or requested lengths from shortened H.',
        identities='F0/H copied byte-exact from unit006. J layer0 retains H geometry/IDs/records; J layer1 original parent+1100000000000, explicit face/bary. No Gaussian ownership implication.',
        controls='Original carrier16543/29999; GS310475 rows/fullSH/opacity; paper41058,ink21006 and exact weights; M1/UNKNOWN195279,target2121,old2030/added91 partitions; width1px,AA2,depth tolerance.004,band2.',
        matching='One frozen scalar per F0/H/J linked/ungated arm from four BUILD absolute hybrid-paper RGB L1; common minimum natural budget. Retain natural strengths; no DEV fitting.',
        cache_policy='Verified original-GS source/paper/S reused; actual ink rasterization. No repeated bootstrap or H solver.',
        view_policy='Four BUILD, four DEV and231/241/251 rear arc; all EXPOSED, repeated241 not independent; three frames not temporal certification.',
        scope='CPU original-GS paper and optional original-ID regional S, proxy paths only. No native line-GS, semantic/physical truth or per-path original-ID certification.',
        resources=dict(CPU_affinity=2,numeric_threads=1,GPU=False,serial=True),
        frozen={name:sha(UNIT/name) for name in ('INPUT_LOCK.json','SOURCE_LOCK.json','CAMERAS.json')})
    js(UNIT/'PROTOCOL.json',p);js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json')))
    js(UNIT/'STATUS.json',dict(execution_state='partial',stage='frozen_before_real_generation_and_eval',scientific_verdict='pending',gaussian_link_progress='Verified original-GS layers reused; coupling comparison pending',scientific_seal=False))
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
    p=protocol();out=fresh(UNIT/'asset');oldmesh,mesh,original,meta=load_assets()
    s=npz(BASE/'asset/FIELDS.npz');partitions=s['partitions'];selected=partitions>0
    j=restore_crossing(mesh['normals'],s['F0'],s['H'],selected)
    np.testing.assert_array_equal(j[:,0],s['H'][:,0]);s['J']=j
    s['change_degrees']=np.rad2deg(np.arccos(np.clip(np.abs(np.sum(j*s['H'],axis=2)),0,1)))
    save(out/'FIELDS.npz',**s);stats={};seeds={}
    for part,old,label in zip(('old','added'),original,(1,2)):
        save(out/('A_'+part+'.npz'),**old)
        for arm in ('F0','H'):
            for suffix in ('.npz','_SEEDS.json'):
                name=arm+'_'+part+suffix;shutil.copyfile(BASE/'asset'/name,out/name)
        h=npz(out/('H_'+part+'.npz'));hr=json.loads((out/('H_'+part+'_SEEDS.json')).read_text())
        jp,jr=replace_second_layer(mesh,old,h,hr,partitions==label,j,1_100_000_000_000)
        save(out/('J_'+part+'.npz'),**jp);js(out/('J_'+part+'_SEEDS.json'),jr)
        for arm in PATH_ARMS:
            paths=npz(out/(arm+'_'+part+'.npz'));records=json.loads((out/(arm+'_'+part+'_SEEDS.json')).read_text())
            stats[arm+'_'+part]=path_stats(paths)
            seeds[arm+'_'+part]=dict(seeds=len(records),stops=dict(collections.Counter(r[k] for r in records for k in ('minus_stop','plus_stop'))),requested_length=sum(r['requested_length'] for r in records),actual_length=sum(r['actual_length'] for r in records))
    cross={};energies={};area=.5*np.linalg.norm(np.cross(mesh['tri'][:,1]-mesh['tri'][:,0],mesh['tri'][:,2]-mesh['tri'][:,0]),axis=1)
    for arm in PATH_ARMS:
        f=s[arm];angles=np.rad2deg(np.arccos(np.clip(np.abs(np.sum(f[selected,0]*f[selected,1],axis=1)),0,1)))
        cross[arm]=dict(area_weighted_mean_degrees=float(np.average(angles,weights=area[selected])),area_fraction_below15=float(area[selected][angles<15].sum()/area[selected].sum()),quantiles=np.quantile(angles,[.1,.5,.9]).tolist())
        energies[arm]={}
        for name in ('graph_pairs','excluded_pairs'):
            vals=[];weights=[]
            for i,k in s[name]:
                edge=tuple(sorted(set(mesh['faces'][i])&set(mesh['faces'][k])));T=transport(mesh,int(i),int(k),edge)
                dot=np.sum(f[i]*(f[k]@T.T),axis=1);vals.append(1-np.clip(dot*dot,0,1));weights.append((area[i]+area[k])/2)
            energies[arm][name]=np.average(vals,axis=0,weights=weights).tolist()
    result=dict(paths=stats,seeds=seeds,cross_layer=cross,normalized_field_energy=energies,primary_field_exact=True,
        graph_pairs=len(s['graph_pairs']),excluded_pairs=len(s['excluded_pairs']),original_carrier_unchanged=True,
        scope='H/J changes second-layer relation and coherence together; F0/J retains per-face cross-angle. No all-carrier-noise attribution.')
    js(out/'ASSET.json',result);js(out/'PROVENANCE.json',dict(F0_H_source=str(BASE/'asset'),original_seed_source=str(PREV/'asset'),new_layer1_offset=1_100_000_000_000,preserved_primary='All H layer0 path arrays and identities retained exactly',decision_sha256=p['decision_sha256']))
    js(UNIT/'ASSET_LOCK.json',dict(files={str(x.relative_to(UNIT)):sha(x) for x in out.iterdir()}));print('ASSET',json.dumps(result),flush=True)

def check_assets():
    for path,h in json.loads((UNIT/'ASSET_LOCK.json').read_text())['files'].items():assert sha(UNIT/path)==h,path

def render_pair(meshes,paths,meta,camera):
    ink=[];rasters=[]
    for m,path in zip(meshes,paths):
        r=_coverage(m,{4:path},meta['styles'],camera,2)
        ink.append(np.maximum.reduce(list(r['coverage'][4].values())).astype(np.float32)*meta['styles']['4'].get('ink_strength',.8));rasters.append(r)
    high=np.maximum(*ink);low=high.reshape(camera['height'],2,camera['width'],2).mean((1,3))
    return low,rasters

def compute(v):
    ref=npz(v['cache']);oldmesh,mesh,_,meta=load_assets();fields_saved=npz(UNIT/'asset/FIELDS.npz')
    f={k:ref[k].copy() for k in ('source','paper','support','regions','old_regions')}
    for arm in PATH_ARMS:
        paths=[npz(UNIT/'asset'/(arm+'_'+part+'.npz')) for part in ('old','added')]
        ink,rasters=render_pair((oldmesh,mesh),paths,meta,v['camera']);f[arm+'_preS']=ink
        for layer in (0,1):
            high=np.maximum(*[r['coverage'][4][layer].astype(np.float32)*meta['styles']['4'].get('ink_strength',.8) for r in rasters])
            f[arm+'_layer'+str(layer)+'_preS']=high.reshape(v['camera']['height'],2,v['camera']['width'],2).mean((1,3))
        np.testing.assert_array_equal(rasters[0]['regions'],ref['old_regions']);np.testing.assert_array_equal(rasters[1]['regions'],ref['regions'])
        f[arm+'_fragment_diagnostics']=np.asarray([[r['diagnostics']['4'][key] for key in ('covered_fragments','accepted_fragments','region_rejected','depth_rejected')] for r in rasters],np.int64)
        if arm=='F0':np.testing.assert_array_equal(ink,ref['local_ink'])
        for link in ('linked','ungated'):
            key=arm+'_'+link;f[key+'_natural'],f[key+'_natural_alpha']=compose(f['paper'],ink,f['support'],link=='linked')
        if arm=='F0':np.testing.assert_array_equal(f['F0_linked_natural'],ref['local_raw'])
    np.testing.assert_array_equal(f['J_layer0_preS'],f['H_layer0_preS'])
    baseline=npz(BASE/'build'/(v['camera']['view']+'.npz')) if v['kind']=='build' else npz(BASE/v['kind']/v['camera']['view']/'FRAME.npz')
    for arm in ('F0','H'):
        for suffix in ('_preS','_layer0_preS','_layer1_preS','_linked_natural','_ungated_natural'):
            np.testing.assert_array_equal(f[arm+suffix],baseline[arm+suffix])
    ids=rasters[1]['first_hit_face'];change=fields_saved['change_degrees'].max(1)
    f['visible_field_change_degrees']=np.where(ids>=0,change[np.maximum(ids,0)],0.)
    return f

def attribution():
    p=protocol();scales=json.loads((UNIT/'BUILD_MATCH.json').read_text())['scales'];oldmesh,mesh,_,meta=load_assets();out=fresh(UNIT/'attribution');summaries=[]
    for v in (v for v in p['views'] if v['kind']=='dev' and v['camera']['view'] in ('orbit_61_24_5.3','orbit_241_24_5.3')):
        view=v['camera']['view'];folder=fresh(out/view);f=npz(UNIT/'dev'/view/'FRAME.npz')
        for arm in PATH_ARMS:
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
        for link in ('linked','ungated'):
            for a,b in (('F0','H'),('F0','J'),('H','J')):
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
            js(out/'EVALUATION.json',dict(camera=v['camera'],measurements=m,F0_exact=True,source_paper_support_fixed=True))
            for key in ('source','paper'):png(out/(key+'.png'),f[key])
            for arm in PATH_ARMS:
                png(out/(arm+'_preS_ink.png'),1-f[arm+'_preS'])
                for layer in (0,1):png(out/(arm+'_layer'+str(layer)+'_preS.png'),1-f[arm+'_layer'+str(layer)+'_preS'])
            for arm in ARMS:
                for mode in ('natural','matched'):
                    key=arm+'_'+mode;png(out/(key+'.png'),f[key]);png(out/(key+'_ink.png'),1-f[key+'_alpha'])
            keys=['source','paper','F0_linked_matched','H_linked_matched','J_linked_matched','F0_ungated_matched','H_ungated_matched','J_ungated_matched']
            panel(out/'COMPARISON.png',[f[k] for k in keys],[view+' | '+k for k in keys],columns=4)
            keys=[a+'_preS' for a in PATH_ARMS]+[a+'_linked_matched_alpha' for a in PATH_ARMS]
            panel(out/'INK_LAYERS.png',[1-f[k] for k in keys],keys,columns=3)
            keys=['paper']+[a+'_linked_natural' for a in PATH_ARMS]
            panel(out/'NATURAL.png',[f[k] for k in keys],keys,columns=4)
        row=dict(kind=kind,view=view,duplicate=duplicate,target_pixels=m['support']['target']['pixels'])
        for arm in ARMS:
            key=arm+'_matched';q=m['source_edit'][key]
            row[arm]=dict(ink_L1=m['ink_effect'][key]['target_full']['raw_L1_sum'],coverage=m['coverage'][key]['target']['fraction'],
                         interior_coverage=m['coverage'][key]['interior']['fraction'],far_other=q['far_other']['raw_L1_sum'],background=q['far_background']['raw_L1_sum'])
        summary.append(row);print('EVAL',json.dumps(row),flush=True)
    js(UNIT/'SUMMARY.json',summary)
    for label,filename,keys in [('ALL_DEV_MATCHED','matched',['source','paper','F0_linked_matched','H_linked_matched','J_linked_matched']),
                               ('ALL_DEV_NATURAL','natural',['source','paper','F0_linked_natural','H_linked_natural','J_linked_natural'])]:
        arrays=[];titles=[]
        for v in (v for v in p['views'] if v['kind']=='dev'):
            f=npz(UNIT/'dev'/v['camera']['view']/'FRAME.npz')
            for key in keys:arrays.append(f[key]);titles.append(v['camera']['view']+' | '+key)
        panel(UNIT/(label+'.png'),arrays,titles,columns=5)
    arrays=[];titles=[]
    for v in (v for v in p['views'] if v['kind']=='arc'):
        f=npz(UNIT/'arc'/v['camera']['view']/'FRAME.npz')
        for key in ('F0_linked_matched','H_linked_matched','J_linked_matched'):arrays.append(f[key]);titles.append(v['camera']['view']+' | '+key)
    panel(UNIT/'REAR_CAMERA_SEQUENCE.png',arrays,titles,columns=3)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','derive','build','evaluate','attribution']);args=ap.parse_args();globals()[args.stage]()
