"""Unit002 A/C: same slicer; bounded carrier geometry; original occluder frozen."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT as ROOT,HERE,VENDOR,sha,js,now,output_guard
from pathlib import Path
import argparse,json,shutil,collections
import numpy as np
from scipy import ndimage
from PIL import Image,ImageDraw
from geometry import mesh_data
from hybrid import compose,edit_metrics
from carrier import denoise,DEFAULTS
from fixed_render import _coverage
from visibility_fixed import endpoint_records,compare_visibility,sample_support
from v06_local_frame import regenerate_partitions
OLD=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_010')
PREV=ROOT/'units/unit_001'
PACKAGE=ROOT/'replay_package/data/lego'
ARMS=('A_linked','C_linked','A_ungated','C_ungated')

def freeze():
    assert not (UNIT/'PROTOCOL.json').exists()
    decision=json.loads((UNIT/'DECISION.json').read_text());assert decision['action']=='continue'
    boot=json.loads((PREV/'BOOTSTRAP_STATUS.json').read_text());assert all(x['returncode']==0 for x in boot['stages'])
    views=json.loads((PREV/'CAMERAS.json').read_text())
    js(UNIT/'CAMERAS.json',views)
    inputs=[UNIT/'DECISION.json',OLD/'asset/FRAME.json',OLD/'source_snapshot/local_frame.py']
    inputs += [p for p in PREV.rglob('*') if p.is_file()]
    inputs += [p for p in PACKAGE.rglob('*') if p.is_file()]
    inputs += [Path(x['cache']) for x in views['views']]
    meta=json.loads((PACKAGE/'asset.json').read_text());inputs.append(Path(meta['original']['original_ply']))
    js(UNIT/'INPUT_LOCK.json',dict(files={str(p):sha(p) for p in sorted(set(inputs))}))
    source=fresh(UNIT/'source_snapshot');files={};snapshots={}
    for origin in [HERE,VENDOR]:
        for p in origin.iterdir():
            if not p.is_file() or p.suffix not in ('.py','.cpp','.json','.md'):continue
            relative=Path('own' if origin==HERE else 'vendor')/p.name
            dest=source/relative;dest.parent.mkdir(exist_ok=True);shutil.copyfile(p,dest)
            files[str(p)]=sha(p);snapshots[str(relative)]=sha(dest)
    js(UNIT/'SOURCE_LOCK.json',dict(files=files,snapshots=snapshots))
    p=dict(unit='unit_002',frozen_utc=now(),decision_sha256=sha(UNIT/'DECISION.json'),
        question='Does bounded carrier denoising improve the SAME slicing generator with original occlusion fixed?',
        changed_variable=decision['changed_variable'],falsification=decision['falsification'],
        denoise=DEFAULTS,normal_filter='One edge-adjacent bilateral normal pass; area and Gaussian centroid/unsigned-angle weights; align normal sign to center face.',
        vertex_rule='Three simultaneous area-weighted plane-residual steps using fixed filtered normals; total displacement capped by min(0.1 initial local median edge length,0.002 world).',
        protected='Non-target vertices; mesh/nonmanifold boundaries; old/added/other partition interfaces; initial unsigned dihedral >=60 degrees; degenerate faces. Reject inversion vertices. No hole filling or neighbor rewiring.',
        A='Exact unit001 A / unit010 LOCAL partitions; reproduce from original carrier and saved FRAME basis before C.',
        C='Same generator, fixed basis/phase/style, denoised copy; new stroke ID namespace +200000000000, fresh face/bary anchors; no parent stroke ownership claim.',
        visibility='Same .004 absolute owner-plane versus first-hit depth rule, AA2 and 1px. Carrier face planes vary; original full mesh ray depth/region bits stay fixed. No new occlusion mode.',
        matching='One scalar per A/C linked/ungated arm from four BUILD target abs(hybrid-paper); common budget is minimum natural total; retain natural outputs; no DEV fitting.',
        cache_policy='Reuse fixed GS source/paper/S; actual ink rasterization per distinct camera; bootstrap already completed once in unit001.',
        controls='Original310475 rows, paper41058, ink21006, UNKNOWN195279, M1, authored2121 faces, old2030/added91 stops, source geometry/fullSH/opacity, masks band2 all fixed.',
        scope='CPU original-GS paper plus region-S-linked proxy strokes; diagnostic smooth carrier is not measured true surface; no native Gaussian hatch or per-path original-ID certification.',
        resources=dict(CPU_affinity=2,numeric_threads=1,GPU=False,serial=True),
        frozen={name:sha(UNIT/name) for name in ('INPUT_LOCK.json','SOURCE_LOCK.json','CAMERAS.json')})
    js(UNIT/'PROTOCOL.json',p);js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json')))
    js(UNIT/'STATUS.json',dict(execution_state='partial',stage='frozen_before_generation_and_eval',scientific_verdict='pending',gaussian_link_progress='Original-GS replay reused; A/C pending',scientific_seal=False))
    print('FROZEN',len(set(inputs)),'inputs',flush=True)

def protocol():
    p=json.loads((UNIT/'PROTOCOL.json').read_text())
    assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    assert sha(UNIT/'DECISION.json')==p['decision_sha256']
    for name,h in p['frozen'].items():assert sha(UNIT/name)==h,name
    for path,h in json.loads((UNIT/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(path)==h,path
    p['views']=json.loads((UNIT/'CAMERAS.json').read_text())['views'];return p

def load_assets():
    t=npz(PACKAGE/'unit_008_asset/TARGET.npz')
    oldmesh=mesh_data(t['vertices'],t['faces'],t['old_face_regions']);mesh=mesh_data(t['vertices'],t['faces'],t['face_regions'])
    a=[npz(PREV/'asset'/('A_'+part+'.npz')) for part in ('old','added')]
    meta=json.loads((PACKAGE/'asset.json').read_text());return oldmesh,mesh,a,meta

def derive():
    p=protocol();out=fresh(UNIT/'asset');oldmesh,mesh,a,meta=load_assets()
    basis=json.loads((OLD/'asset/FRAME.json').read_text())['basis']
    recovered=regenerate_partitions(oldmesh,mesh,*a,meta['styles']['4'],basis,revision=True)
    for original,again in zip(a,recovered):
        assert set(original)==set(again)
        for k in original:np.testing.assert_array_equal(original[k],again[k],err_msg=k)
    partitions=np.where(oldmesh['regions']==4,1,np.where(mesh['regions']==4,2,0)).astype(np.int32)
    c,d=denoise(mesh,partitions,p['denoise']);cold=mesh_data(c['vertices'],c['faces'],oldmesh['regions'])
    generated=regenerate_partitions(cold,c,*a,meta['styles']['4'],basis,revision=True)
    save(out/'CARRIER.npz',vertices=c['vertices'],faces=c['faces'],face_regions=c['regions'],old_face_regions=cold['regions'],partitions=partitions)
    save(out/'DENOISE.npz',**d)
    stats={};endpoint={}
    for part,aa,cc in zip(('old','added'),a,generated):
        cc['stroke_id']=cc['stroke_id']+200_000_000_000
        assert not np.isin(cc['stroke_id'],aa['stroke_id']).any()
        np.testing.assert_allclose(cc['points'],np.einsum('nij,njk->nik',cc['bary'],c['tri'][cc['face']]),atol=1e-10,rtol=0)
        allowed=partitions==(1 if part=='old' else 2);assert allowed[cc['face']].all()
        assert (cc['bary']>=-1e-10).all()
        save(out/('A_'+part+'.npz'),**aa);save(out/('C_'+part+'.npz'),**cc)
        stats[part]=dict(A=path_stats(aa),C=path_stats(cc))
        labeled=dict(c,regions=np.where(allowed,4,1));endpoint[part]=endpoint_records(labeled,cc)
    links=npz(PACKAGE/'SOURCE_LINK.npz');binding=npz(PACKAGE/'SOURCE_BINDING.npz')
    np.testing.assert_array_equal(links['source_index'],np.arange(310475))
    assert int(binding['unknown'].sum())==195279 and int((links['paper_strength']>0).sum())==41058 and int((links['ink_strength']>0).sum())==21006
    selected=d['selected'];moved=d['displacement']>1e-12
    normal_change=np.rad2deg(np.arccos(np.clip(np.abs((mesh['normals']*c['normals']).sum(1)),0,1)))
    changed_faces=np.any(moved[c['faces']],axis=1)
    edges={}
    for i,face in enumerate(c['faces']):
        for j,k in ((0,1),(1,2),(2,0)):edges.setdefault(tuple(sorted((int(face[j]),int(face[k])))),[]).append(i)
    pairs=np.asarray([fs for fs in edges.values() if len(fs)==2 and partitions[fs[0]]>0 and partitions[fs[0]]==partitions[fs[1]]])
    roughness={}
    for name,m in [('A',mesh),('C',c)]:
        ang=np.rad2deg(np.arccos(np.clip(np.abs((m['normals'][pairs[:,0]]*m['normals'][pairs[:,1]]).sum(1)),0,1)))
        roughness[name]=np.quantile(ang,[.5,.9,.95,1]).tolist()
    summary=dict(config=p['denoise'],partitions=stats,selected_vertices=int(selected.sum()),movable_vertices=int((~d['protected']).sum()),
        moved_vertices=int(moved.sum()),selected_boundary_vertices=int((selected&d['boundary']).sum()),selected_sharp_vertices=int((selected&d['sharp']).sum()),
        inversion_rejected_vertices=int(d['rejected_inversion'].sum()),changed_target_faces=int((changed_faces&(partitions>0)).sum()),
        displacement_quantiles=np.quantile(d['displacement'][selected],[.5,.9,.95,1]).tolist(),
        moved_displacement_quantiles=np.quantile(d['displacement'][moved],[.5,.9,.95,1]).tolist() if moved.any() else [],
        target_normal_change_degrees=np.quantile(normal_change[partitions>0],[.5,.9,.95,1]).tolist(),
        target_adjacent_unsigned_angles=roughness,original_slicer_reproduced_exactly=True,source_rows=310475,paper_rows=41058,ink_rows=21006,UNKNOWN=195279,
        warning='Unsigned dihedrals mix true shape and noise. Protected edges are geometric heuristics, not semantic truth. A/C path counts may differ as a consequence of geometry.')
    save(out/'FACE_CHANGES.npz',changed_faces=changed_faces,normal_change_degrees=normal_change)
    js(out/'ASSET.json',summary);js(out/'C_ENDPOINTS.json',endpoint)
    js(out/'PROVENANCE.json',dict(carrier='CARRIER.npz',path_generation='Frozen original plane-slice generator on changed vertices, then fresh face/bary anchors',basis=basis,
       new_id_offset=200_000_000_000,old_paths=str(PREV/'asset'),source_id_scope='Source IDs remain original PLY rows. New stroke/face IDs are not Gaussian ownership.'))
    js(UNIT/'ASSET_LOCK.json',dict(files={str(x.relative_to(UNIT)):sha(x) for x in out.iterdir()}))
    print('ASSET',json.dumps(summary),flush=True)

def check_assets():
    for path,h in json.loads((UNIT/'ASSET_LOCK.json').read_text())['files'].items():assert sha(UNIT/path)==h,path

def render_pair_fixed(carriers,references,paths,meta,camera):
    ink=[];diagnostics={};rasters=[]
    for part,m,ref,path in zip(('old','added'),carriers,references,paths):
        r=_coverage(m,{4:path},meta['styles'],camera,2,occluder=ref)
        high=np.maximum.reduce(list(r['coverage'][4].values())).astype(np.float32)*meta['styles']['4'].get('ink_strength',.8)
        ink.append(high);rasters.append(r);diagnostics[part]=r['diagnostics']['4']
    high=np.maximum(*ink);low=high.reshape(camera['height'],2,camera['width'],2).mean((1,3))
    return low,dict(regions=rasters[1]['regions'],old_regions=rasters[0]['regions'],diagnostics=diagnostics,first_hit_face=rasters[1]['first_hit_face'])

def compute(v):
    ref=npz(v['cache']);oldmesh,mesh,_,meta=load_assets();ca=npz(UNIT/'asset/CARRIER.npz')
    cm=mesh_data(ca['vertices'],ca['faces'],ca['face_regions']);co=mesh_data(ca['vertices'],ca['faces'],ca['old_face_regions'])
    f={k:ref[k].copy() for k in ('source','paper','support','regions','old_regions')}
    for arm,carriers in [('A',(oldmesh,mesh)),('C',(co,cm))]:
        paths=[npz(UNIT/'asset'/(arm+'_'+part+'.npz')) for part in ('old','added')]
        ink,r=render_pair_fixed(carriers,(oldmesh,mesh),paths,meta,v['camera'])
        for key in ('regions','old_regions'):np.testing.assert_array_equal(r[key],ref[key])
        f[arm+'_preS']=ink
        if arm=='C':
            ids=r['first_hit_face'];changed=npz(UNIT/'asset/FACE_CHANGES.npz')['changed_faces']
            f['changed_carrier_visible_mask']=(ids>=0)&changed[np.maximum(ids,0)]
        f[arm+'_fragment_diagnostics']=np.asarray([[r['diagnostics'][part][key] for key in ('covered_fragments','accepted_fragments','region_rejected','depth_rejected')] for part in ('old','added')],np.int64)
        if arm=='A':np.testing.assert_array_equal(ink,ref['local_ink'])
        for link in ('linked','ungated'):
            key=arm+'_'+link;f[key+'_natural'],f[key+'_natural_alpha']=compose(f['paper'],ink,f['support'],link=='linked')
        if arm=='A':np.testing.assert_array_equal(f['A_linked_natural'],ref['local_raw'])
    return f

def attribution():
    p=protocol();scales=json.loads((UNIT/'BUILD_MATCH.json').read_text())['scales'];oldmesh,mesh,_,meta=load_assets();out=fresh(UNIT/'attribution')
    ca=npz(UNIT/'asset/CARRIER.npz');cm=mesh_data(ca['vertices'],ca['faces'],ca['face_regions']);co=mesh_data(ca['vertices'],ca['faces'],ca['old_face_regions'])
    selected=[v for v in p['views'] if v['kind']=='dev' and v['camera']['view'] in ('orbit_61_24_5.3','orbit_241_24_5.3')]
    summaries=[]
    for v in selected:
        view=v['camera']['view'];folder=fresh(out/view);f=npz(UNIT/'dev'/view/'FRAME.npz')
        for arm,carriers in [('A',(oldmesh,mesh)),('C',(co,cm))]:
            totals=collections.Counter();partition_ink=[]
            for part,m,ref in zip(('old','added'),carriers,(oldmesh,mesh)):
                paths=npz(UNIT/'asset'/(arm+'_'+part+'.npz'))
                r=compare_visibility(m,paths,meta['styles'],v['camera'],occluder=ref);s=r['samples'];support=sample_support(s,f['support'])
                save(folder/(arm+'_'+part+'_SAMPLES.npz'),**s,original_ID_S=support)
                visible=s['status']==0;w=s['length_weight'];alpha=s['legacy_alpha']
                totals['projected_length']+=float(w.sum());totals['proxy_visible_length']+=float(w[visible].sum())
                for code in (1,2,3,4):totals['rejected_status_'+str(code)]+=float(w[s['status']==code].sum())
                for mode,a in [('preS',alpha),('linked_natural',alpha*support),('linked_matched',alpha*support*scales[arm+'_linked'])]:
                    totals[mode+'_own_visible_missing_length']+=float(w[visible&(a<=.05)].sum())
                partition_ink.append(np.maximum.reduce(list(r['coverage']['legacy'].values())).astype(np.float32)*meta['styles']['4'].get('ink_strength',.8))
            high=np.maximum(*partition_ink);low=high.reshape(v['camera']['height'],2,v['camera']['width'],2).mean((1,3))
            np.testing.assert_array_equal(low,f[arm+'_preS'])
            row=dict(view=view,arm=arm,**dict(totals),scope='Per-stroke own-raster support; fixed original proxy first-hit reference, changed carrier centerline/planes. No physical truth or interval-backend replacement.')
            summaries.append(row);print('ATTRIBUTION',json.dumps(row),flush=True)
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
        for link in ('linked','ungated'):result['delta'][link+'_'+mode]=edit_metrics(f['A_'+link+'_'+mode],f['C_'+link+'_'+mode],regions)
    for n,mask in [('target',target),('interior',inner)]:
        result['support'][n]=dict(pixels=int(mask.sum()),mean=float(f['support'][mask].mean()),above_005=float((f['support'][mask]>.05).mean()))
    for arm in ('A','C'):
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
            for arm in ('A','C'):png(out/(arm+'_preS_ink.png'),1-f[arm+'_preS'])
            for arm in ARMS:
                for mode in ('natural','matched'):
                    key=arm+'_'+mode;png(out/(key+'.png'),f[key]);png(out/(key+'_ink.png'),1-f[key+'_alpha'])
            keys=['source','paper','A_linked_matched','C_linked_matched','A_ungated_matched','C_ungated_matched']
            titles=['Original GS','Fixed GS paper','A slice | linked matched','C carrier | linked matched','A slice | ungated matched','C carrier | ungated matched']
            panel(out/'COMPARISON.png',[f[k] for k in keys],[view+' | '+t for t in titles],columns=3)
            panel(out/'INK_LAYERS.png',[1-f[k] for k in ('A_preS','C_preS','A_linked_matched_alpha','C_linked_matched_alpha')],
                ['A before S | natural','C before S | natural','A after S | matched','C after S | matched'],columns=2)
            panel(out/'NATURAL.png',[f[k] for k in ('paper','A_linked_natural','C_linked_natural')],['Fixed GS paper','A natural linked','C natural linked'])
        row=dict(kind=kind,view=view,duplicate=duplicate,target_pixels=m['support']['target']['pixels'])
        for arm in ARMS:
            key=arm+'_matched';q=m['source_edit'][key]
            row[arm]=dict(ink_L1=m['ink_effect'][key]['target_full']['raw_L1_sum'],coverage=m['coverage'][key]['target']['fraction'],
                         interior_coverage=m['coverage'][key]['interior']['fraction'],far_other=q['far_other']['raw_L1_sum'],background=q['far_background']['raw_L1_sum'])
        summary.append(row);print('EVAL',json.dumps(row),flush=True)
    js(UNIT/'SUMMARY.json',summary)
    for label,filename,keys in [('ALL_DEV_MATCHED','matched',['source','paper','A_linked_matched','C_linked_matched']),
                               ('ALL_DEV_NATURAL','natural',['source','paper','A_linked_natural','C_linked_natural'])]:
        arrays=[];titles=[]
        for v in (v for v in p['views'] if v['kind']=='dev'):
            f=npz(UNIT/'dev'/v['camera']['view']/'FRAME.npz')
            for key in keys:arrays.append(f[key]);titles.append(v['camera']['view']+' | '+key)
        panel(UNIT/(label+'.png'),arrays,titles,columns=4)
    arrays=[];titles=[]
    for v in (v for v in p['views'] if v['kind']=='arc'):
        f=npz(UNIT/'arc'/v['camera']['view']/'FRAME.npz')
        for key in ('A_linked_matched','C_linked_matched'):arrays.append(f[key]);titles.append(v['camera']['view']+' | '+key)
    panel(UNIT/'REAR_CAMERA_SEQUENCE.png',arrays,titles,columns=2)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','derive','build','evaluate','attribution']);args=ap.parse_args();globals()[args.stage]()
