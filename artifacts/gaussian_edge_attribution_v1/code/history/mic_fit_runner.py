"""Sealed F-only attribution, full-model native attribute projection, and reporting.

No dataset photographs, TEST/VAL, meshes, optimizer, or geometric curve fitting.
All writes are confined to the authorized experiment workspace.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, os, shutil, sys, time
sys.dont_write_bytecode=True
import numpy as np
from scipy import ndimage as ndi
from freeze import ROOT, ART, sha, atomic, utc
import core

OUT=ROOT/'out/gaussian_edge_attribution_v1'
CFG=json.loads((ART/'code/config.json').read_text())
INPUTS=json.loads((ART/'INPUTS_FROZEN.json').read_text())
CLASSES=('color','geometry','outline','union')

def status(state,**details):
    atomic(ART/'STATUS.json',dict(state=state,utc=utc(),requested_pose_count=98,**details))
    print(json.dumps(dict(state=state,**details),ensure_ascii=False),flush=True)

def guard_space(payload=2<<30):
    if shutil.disk_usage(ROOT).free <= (1<<30)+payload:raise RuntimeError('1GiB reserve plus estimated write payload unavailable')

def validate_protocol():
    for name,digest in json.loads((ART/'PROTOCOL_SEAL.json').read_text())['files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Frozen protocol/input hash changed: '+name)

def save_npz(path,**arrays):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.partial.npz')
    with tmp.open('wb') as f:np.savez_compressed(f,**arrays)
    os.replace(tmp,path)

def load_npz(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k] for k in z.files}

def seal(directory,context):
    directory=Path(directory)
    files={str(p.relative_to(directory)):sha(p) for p in sorted(directory.rglob('*')) if p.is_file() and p.name not in ('SEAL.json','ASSET_SEAL.json') and '.partial' not in p.name}
    value=dict(created_utc=utc(),context=context,files=files)
    atomic(directory/('ASSET_SEAL.json' if directory.name=='assets' else 'SEAL.json'),value)
    return value

def verify_seal(directory,asset=False):
    directory=Path(directory);path=directory/('ASSET_SEAL.json' if asset else 'SEAL.json')
    value=json.loads(path.read_text())
    for name,digest in value['files'].items():
        if sha(directory/name)!=digest:raise ValueError('Corrupt sealed artifact '+str(directory/name))
    return value

def source_context(scene):
    return dict(scene=scene,checkpoint_sha256=INPUTS['scenes'][scene]['checkpoint']['sha256'],
        protocol_seal_sha256=sha(ART/'PROTOCOL_SEAL.json'),core_source_sha256=sha(ART/'code/core.py'),
        runner_source_sha256=sha(__file__),config_sha256=sha(ART/'code/config.json'))

def read_raw(scene,spec,phase):
    if not spec['key'].startswith('F_'):
        verify_seal(OUT/scene/'assets',asset=True)
        if not (OUT/'mic/DISPLAY_SEAL.json').is_file():raise RuntimeError('C/arc forbidden before Mic F display seal')
    if sha(spec['raw_path'])!=spec['raw_sha256']:raise ValueError('Input raw hash changed')
    event=dict(utc=utc(),scene=scene,key=spec['key'],phase=phase,path=spec['raw_path'],sha256=spec['raw_sha256'])
    asset_seal=OUT/scene/'assets/ASSET_SEAL.json'
    if asset_seal.exists():event['asset_seal_sha256']=sha(asset_seal)
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'READ_EVENTS.jsonl').open('a') as f:f.write(json.dumps(event)+'\n')
    return load_npz(spec['raw_path'])

def shifted_evidence(evidence):
    dy,dx=CFG['null_shift_pixels'];result={}
    for name,value in evidence.items():
        a=np.asarray(value)
        if a.ndim>=2 and a.shape[:2]==(800,800):
            b=np.zeros_like(a);b[dy:,dx:]=a[:-dy,:-dx];result[name]=b
        else:result[name]=value
    return result

def serialize_stats(stats):
    arrays={};metadata={}
    for k,v in stats.items():
        if isinstance(v,np.ndarray):arrays[k]=v
        elif isinstance(v,(int,float,str,bool)) or v is None:metadata[k]=v
        elif isinstance(v,dict):
            for name,val in v.items():
                if isinstance(val,np.ndarray):arrays[k+'__'+name]=val
                else:metadata[k+'__'+name]=val
        else:arrays[k]=np.asarray(v)
    return arrays,metadata

def normalized_scene():
    path=OUT/'mic/NORMALIZATION.json'
    if path.exists():
        meta=json.loads(path.read_text())
        if meta['core_source_sha256']!=sha(ART/'code/core.py'):raise ValueError('Normalization implementation changed')
        return meta['normalization']
    fields=[]
    for spec in INPUTS['scenes']['mic']['frames'][:8]:
        status('MIC_F_NORMALIZATION',key=spec['key'])
        raw=read_raw('mic',spec,'F_NORMALIZATION')
        fields.append(core.evidence_fields(raw,CFG))
    norm=core.fit_normalization(fields,CFG)
    atomic(path,dict(normalization=norm,created_utc=utc(),core_source_sha256=sha(ART/'code/core.py'),
        source_F=[r['raw_sha256'] for r in INPUTS['scenes']['mic']['frames'][:8]],scope='Mic F only, inherited unchanged by Materials'))
    return norm

def fit_scene(scene):
    validate_protocol();guard_space(3<<30)
    destination=OUT/scene/'assets'
    if (destination/'ASSET_SEAL.json').exists():
        prior=verify_seal(destination,True)
        if prior['context']['core_source_sha256']!=sha(ART/'code/core.py'):raise ValueError('Cannot resume with changed core')
        status('F_ASSET_ALREADY_SEALED',scene=scene);return
    norm=normalized_scene()
    n=INPUTS['scenes'][scene]['checkpoint']['qualification']['gaussians']
    stats=[];null_stats=[]
    for spec in INPUTS['scenes'][scene]['frames'][:8]:
        key=spec['key'];status('F_ATTRIBUTION',scene=scene,key=key)
        raw=read_raw(scene,spec,'F_ATTRIBUTION');fields=core.evidence_fields(raw,CFG);evidence=core.compute_evidence(fields,norm,CFG)
        v=core.view_statistics(raw,evidence,n,CFG,with_side=True)
        v['split']='F';v['frame_id']=int(key[2:]);stats.append(v)
        null=core.view_statistics(raw,shifted_evidence(evidence),n,CFG,with_side=True)
        null['split']='F';null['frame_id']=int(key[2:]);null_stats.append(null)
        folder=OUT/scene/'F'/key;folder.mkdir(parents=True,exist_ok=True)
        save_npz(folder/'evidence.npz',**{k:v for k,v in evidence.items() if isinstance(v,np.ndarray)})
        a,m=serialize_stats(v);save_npz(folder/'statistics.npz',**a);atomic(folder/'statistics.json',m)
        a,m=serialize_stats(null);save_npz(folder/'null_statistics.npz',**a);atomic(folder/'null_statistics.json',m)
        seal(folder,dict(**source_context(scene),raw_sha256=spec['raw_sha256'],camera_hash=spec['camera_hash'],F_only=True))
    asset=core.aggregate_views(stats,CFG)
    single=core.aggregate_views(stats[:1],CFG,min_views=1)
    null=core.aggregate_views(null_stats,CFG)
    asset['original_ids']=np.arange(n,dtype=np.int32)
    asset['projection_baseline_union']=(asset['baseline_union']*asset['eligible']).astype(np.float32)
    asset['projection_enhanced_union']=(asset['enhanced_union']*asset['eligible']).astype(np.float32)
    asset['projection_single_union']=(single['enhanced_union']*single['eligible']).astype(np.float32)
    asset['projection_null_union']=(null['enhanced_union']*null['eligible']).astype(np.float32)
    for name in CLASSES:
        asset['projection_baseline_'+name]=(asset['baseline_'+name]*asset['eligible']).astype(np.float32)
        asset['projection_enhanced_'+name]=(asset['enhanced_'+name]*asset['eligible']).astype(np.float32)
    asset['single_eligible']=single['eligible'];asset['single_score']=single['enhanced_union']
    asset['null_score']=null['enhanced_union']
    selection={}
    for name in CLASSES:
        for arm in ('baseline','enhanced'):
            for pct,ids in core.rank_tiers(asset,CFG,score_key=arm+'_'+name).items():selection[f'{arm}_{name}_{int(pct):02d}']=np.asarray(ids,np.int32)
    for arm,a in [('single',single),('null',null)]:
        # Same support count as multi-F, when single F reliable population permits.
        order=np.lexsort((np.arange(n),-a['enhanced_union']))
        candidates=order[a['eligible'][order]]
        for pct in CFG['tiers_percent']:
            count=len(selection[f'enhanced_union_{pct:02d}'])
            selection[f'{arm}_union_{pct:02d}']=candidates[:count].astype(np.int32)
    for pct in CFG['tiers_percent']:
        ids=selection[f'enhanced_union_{pct:02d}']
        selection[f'random_union_{pct:02d}']=core.visibility_matched_random(asset,ids,CFG['random_seed']+pct,CFG).astype(np.int32)
    destination.mkdir(parents=True,exist_ok=True)
    save_npz(destination/'scores.npz',**{k:v for k,v in asset.items() if isinstance(v,np.ndarray)})
    save_npz(destination/'selection.npz',**selection)
    metadata=dict(**source_context(scene),created_utc=utc(),gaussian_count=n,
        estimator='TOP4-TRUNCATED',normalization_sha256=sha(OUT/'mic/NORMALIZATION.json'),
        independent_evidence='RGB/depth/alpha gradients; ID-independent main evidence',
        F_ids=CFG['fixed_frame_ids'],C_used_for_fit=False,
        never_seen_count=int(asset['unknown'].sum()),eligible_count=int(asset['eligible'].sum()),
        unreliable_seen_count=int((~asset['eligible']&~asset['unknown']).sum()),
        selection_counts={k:len(v) for k,v in selection.items()},
        projection_reliability='raw continuous estimates retained; primary P abstains ineligible IDs with zero field',
        class_semantics={'color':'RGB color-gradient support','geometry':'rendered depth support, no surface GT','outline':'view-dependent alpha outline'},
        identity_namespace=INPUTS['scenes'][scene]['checkpoint']['sha256'],
        single_count_control='same count as multiF tier where single-F eligible population permits; mismatch disclosed',
        array_fields={k:{'shape':list(v.shape),'dtype':str(v.dtype)} for k,v in asset.items() if isinstance(v,np.ndarray)})
    atomic(destination/'ASSET.json',metadata)
    # Source lineages are part of the asset seal, no later C writes allowed here.
    atomic(destination/'NORMALIZATION.json',dict(normalization=norm,source='Mic F'))
    seal(destination,source_context(scene))
    status('F_ASSET_SEALED_BEFORE_C',scene=scene,asset_sha256=sha(destination/'scores.npz'),asset_seal_sha256=sha(destination/'ASSET_SEAL.json'),eligible=metadata['eligible_count'],unknown=metadata['never_seen_count'])

def field_bank(asset,selection):
    n=len(asset['original_ids']);fields={
        'baseline_P':asset['projection_baseline_union'],'two_sided_P':asset['projection_enhanced_union'],
        'single_P':asset['projection_single_union'],'null_P':asset['projection_null_union']}
    for pct in CFG['tiers_percent']:
        for arm,label in [('enhanced','selected'),('baseline','baseline'),('random','random'),('single','single'),('null','null')]:
            arr=np.zeros(n,np.float32);arr[selection[f'{arm}_union_{pct:02d}']]=1
            fields[f'{label}_Q_{pct:02d}']=arr
    for name in CLASSES[:3]:
        arr=np.zeros(n,np.float32);arr[selection[f'enhanced_{name}_10']]=1
        fields[f'class_{name}_Q_10']=arr
        fields[f'class_{name}_P']=asset['projection_enhanced_'+name]
    return fields

def evaluate(p):
    alpha=p['alpha'];fg=alpha>=CFG['foreground_alpha'];e=p['evidence_union']
    edge=e>=CFG['positive_evidence_threshold']
    tol=ndi.binary_dilation(edge,iterations=CFG['evaluation_tolerance_pixels'])
    visible_reference=float((alpha*tol).sum(dtype=np.float64)/max(alpha.sum(dtype=np.float64),1e-30))
    rows={}
    for key,value in p.items():
        if (key.endswith('_P') or '_Q_' in key) and not key.startswith('top4_'):
            a=np.asarray(value);mass=float(a.sum(dtype=np.float64));concentration=float((a*tol).sum(dtype=np.float64)/max(mass,1e-30))
            rows[key]=dict(mass=mass,concentration=concentration,lift=concentration/max(visible_reference,1e-30),
                soft_alignment=float((a*e).sum(dtype=np.float64)/max(mass,1e-30)),
                area_full={str(t):float((a>t).mean()) for t in (.01,.1,.5)},
                area_foreground={str(t):float((a[fg]>t).mean()) if fg.any() else 0. for t in (.01,.1,.5)})
    comparisons={}
    for pct in CFG['tiers_percent']:
        tag=f'{pct:02d}';keys=[f'{arm}_Q_{tag}' for arm in ('selected','baseline','random','single','null')]
        target=min(rows[k]['mass'] for k in keys)
        comparisons[tag]={'target_mass':target,'display_mass_gains':{k:target/max(rows[k]['mass'],1e-30) for k in keys},
            'selected_vs_random_concentration_ratio':rows[keys[0]]['concentration']/max(rows[keys[2]]['concentration'],1e-30),
            'selected_vs_single_concentration_ratio':rows[keys[0]]['concentration']/max(rows[keys[3]]['concentration'],1e-30)}
    omitted=np.maximum(alpha-p['cached_mass'],0)
    return dict(visible_reference=visible_reference,foreground_pixels=int(fg.sum()),edge_pixels=int(edge.sum()),tolerance_pixels=int(tol.sum()),
        fields=rows,comparisons=comparisons,
        top4_audit=dict(alpha_mass=float(alpha.sum(dtype=np.float64)),cached_mass=float(p['cached_mass'].sum(dtype=np.float64)),
            omitted_mass=float(omitted.sum(dtype=np.float64)),coverage=float(p['cached_mass'].sum(dtype=np.float64)/max(alpha.sum(dtype=np.float64),1e-30)),
            foreground_mean_coverage=float(np.mean(p['cached_mass'][fg]/np.maximum(alpha[fg],1e-30))),
            selected_top10_full_mass=float(p['selected_Q_10'].sum(dtype=np.float64)),selected_top10_cached_mass=float(p['top4_selected_Q_10'].sum(dtype=np.float64)),
            selected_omitted_mass=float((p['selected_Q_10']-p['top4_selected_Q_10']).sum(dtype=np.float64))))

def project_scene(scene):
    validate_protocol();guard_space(6<<30)
    from native_attributes import NativeAttributeRenderer
    assets=OUT/scene/'assets';asset_seal=verify_seal(assets,True);asset=load_npz(assets/'scores.npz');selection=load_npz(assets/'selection.npz')
    bank=field_bank(asset,selection);names=list(bank);matrix=np.stack(list(bank.values()),axis=1)
    source=INPUTS['scenes'][scene];checkpoint=source['checkpoint'];norm=json.loads((OUT/'mic/NORMALIZATION.json').read_text())['normalization']
    renderer=NativeAttributeRenderer(checkpoint['path'],checkpoint['sha256'],OUT/scene/'native_logs')
    display_path=OUT/'mic/DISPLAY.json'
    display_values=[]
    for index,spec in enumerate(source['frames']):
        key=spec['key'];folder=OUT/scene/'frames'/key
        if (folder/'SEAL.json').exists():
            previous=verify_seal(folder)
            if previous['context']['asset_seal_sha256']!=sha(assets/'ASSET_SEAL.json'):raise ValueError('Projection asset identity changed')
            if scene=='mic' and index<8 and not display_path.exists():
                prior=load_npz(folder/'projection.npz');display_values.extend([prior[k][prior[k]>0] for k in ('baseline_P','two_sided_P')])
            continue
        if index>=8 and not display_path.exists():raise RuntimeError('Missing sealed F display parameters')
        status('FULL_MODEL_ATTRIBUTE_PROJECTION',scene=scene,key=key,completed=index,expected=49)
        # No current-view evidence enters the native call: fixed F field bank only.
        result=renderer.render_field_bank(spec['camera'],matrix)
        raw=read_raw(scene,spec,'ATTRIBUTE_EVALUATION_AFTER_F_ASSET_SEAL')
        calibration={k:float(np.max(np.abs(result[k]-raw[k]))) for k in ('alpha','depth','median_depth')}
        if calibration['alpha']>3e-6 or max(calibration[k] for k in ('depth','median_depth'))>1e-5:raise ValueError('Attribute traversal changed alpha/depth: '+str(calibration))
        p={name:result['attributes'][...,i] for i,name in enumerate(names)}
        if min(float(v.min()) for v in p.values()) < -1e-7:raise ValueError('Negative full contribution')
        if max(float(np.max(v-raw['alpha'])) for v in p.values())>3e-6:raise ValueError('Attribute exceeds original alpha')
        evidence=core.compute_evidence(core.evidence_fields(raw,CFG),norm,CFG)
        p.update(rgb=raw['rgb'],alpha=raw['alpha'],cached_mass=raw['topk_w'].sum(-1),**{'evidence_'+k:evidence[k] for k in CLASSES})
        for key_attr in ('baseline_P','two_sided_P','selected_Q_10'):
            p['top4_'+key_attr]=core.project(raw,scores=bank[key_attr])['attribute']
        p['baseline_conditional']=np.divide(p['baseline_P'],raw['alpha'],out=np.zeros_like(raw['alpha']),where=raw['alpha']>0)
        p['two_sided_conditional']=np.divide(p['two_sided_P'],raw['alpha'],out=np.zeros_like(raw['alpha']),where=raw['alpha']>0)
        save_npz(folder/'projection.npz',**p)
        atomic(folder/'METRICS.json',dict(key=key,scene=scene,projection_kind='full native original transmittance',calibration=calibration,**evaluate(p)))
        seal(folder,dict(scene=scene,key=key,camera_hash=spec['camera_hash'],raw_sha256=spec['raw_sha256'],
            asset_seal_sha256=sha(assets/'ASSET_SEAL.json'),renderer=renderer.metadata,
            projection_kind='full native original transmittance; all model Gaussian rows preserved'))
        if scene=='mic' and index<8:
            display_values.extend([p[k][p[k]>0] for k in ('baseline_P','two_sided_P')])
            if index==7:
                scale=float(np.percentile(np.concatenate(display_values),99)) if any(len(a) for a in display_values) else 1.
                atomic(display_path,dict(gain=1/max(scale,1e-12),positive_P99=scale,scope='Mic F only pooled baseline/two-sided full P',created_utc=utc()))
                atomic(OUT/'mic/DISPLAY_SEAL.json',dict(files={'DISPLAY.json':sha(display_path)},created_utc=utc()))
        del raw,p,result
    verify_seal(assets,True)
    atomic(OUT/scene/'PROJECTION_COMPLETE.json',dict(scene=scene,actual_poses=49,requested_poses=49,created_utc=utc(),asset_seal_sha256=sha(assets/'ASSET_SEAL.json')))
    status('ALL49_FULL_ATTRIBUTE_PROJECTIONS_SEALED',scene=scene)

def media_scene(scene):
    from media import write_panel,write_classes_tiers,build_scene_media,make_contact,mask_image,_save
    from PIL import Image,ImageDraw,ImageFont
    display=json.loads((OUT/'mic/DISPLAY.json').read_text());gain=display['gain'];specs=INPUTS['scenes'][scene]['frames']
    for spec in specs:
        key=spec['key'];status('NATIVE800_MEDIA',scene=scene,key=key)
        verify_seal(OUT/scene/'frames'/key);p=load_npz(OUT/scene/'frames'/key/'projection.npz')
        kwargs=dict(title=f'{scene} / {key} | native 800 | 固定 F 资产',display_gain=gain,projection_kind='全模型原始透射率完整遍历')
        write_panel(OUT/scene/'panels'/f'{key}.jpg',p['rgb'],p['evidence_union'],p['baseline_P'],p['two_sided_P'],p['selected_Q_10'],**kwargs)
        write_classes_tiers(OUT/scene/'classes_tiers'/f'{key}.jpg',p,**kwargs)
        # Equal-count groups are predefined; equal-mass display rescales all arms
        # to the minimum current projected mass, never changes IDs or projections.
        keys=['selected_Q_10','baseline_Q_10','random_Q_10','single_Q_10','null_Q_10']
        mass=[float(p[k].sum(dtype=np.float64)) for k in keys];target=min(mass)
        canvas=Image.new('RGB',(4000,872),'white');draw=ImageDraw.Draw(canvas)
        font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',22)
        for i,(k,m) in enumerate(zip(keys,mass)):
            draw.text((800*i+8,3),f'{key} {k} mass-gain={target/max(m,1e-30):.4f}',fill='black',font=font)
            canvas.paste(mask_image(p[k],target/max(m,1e-30)),(800*i,40))
        draw.text((10,840),'top10% 同数量组；显示质量对齐，不重新选择ID；灰色=贡献；null为一次固定平移证据',fill='black',font=font)
        _save(canvas,OUT/scene/'matched_controls'/f'{key}.jpg')
    result=build_scene_media(OUT/scene,[s['key'] for s in specs],[s['key'] for s in specs[16:]])
    for split,group in [('F',specs[:8]),('C',specs[8:16]),('arc',specs[16:])]:
        make_contact([OUT/scene/'panels'/f"{s['key']}.jpg" for s in group],OUT/scene/'media'/f'contact_{split}.jpg',tile_width=1600,columns=2)
    curate=ART/'media'/scene;curate.mkdir(parents=True,exist_ok=True)
    for path in (OUT/scene/'media').glob('*.jpg'):shutil.copyfile(path,curate/path.name)
    for name in ('arc33_telegram1600.mp4','MEDIA.json'):shutil.copyfile(OUT/scene/'media'/name,curate/name)
    for key in ('F_001','C_007','arc0_000','arc0_016','arc0_032'):
        shutil.copyfile(OUT/scene/'panels'/f'{key}.jpg',curate/f'{key}.jpg')
        # Native first/mid/last class and matched control images remain local;
        # small readable comparison contacts are tracked.
    make_contact([OUT/scene/'classes_tiers'/f'{key}.jpg' for key in ('F_001','C_007','arc0_000','arc0_016','arc0_032')],curate/'classes_tiers_representatives.jpg',tile_width=1600,columns=1)
    make_contact([OUT/scene/'matched_controls'/f'{key}.jpg' for key in ('F_001','C_007','arc0_000','arc0_016','arc0_032')],curate/'matched_controls_representatives.jpg',tile_width=1600,columns=1)
    status('MEDIA_COMPLETE49_ARC33',scene=scene)

def export_scene(scene):
    from plyfile import PlyData,PlyElement
    from scipy.spatial import cKDTree
    folder=OUT/scene/'assets';verify_seal(folder,True);scores=load_npz(folder/'scores.npz');selection=load_npz(folder/'selection.npz')
    checkpoint=INPUTS['scenes'][scene]['checkpoint'];ply=PlyData.read(checkpoint['path']);v=ply['vertex'].data
    dest=OUT/scene/'ply';dest.mkdir(parents=True,exist_ok=True);diagnostics={}
    xyz=np.stack([v[k] for k in ('x','y','z')],1);scales=np.exp(np.stack([v[f'scale_{i}'] for i in range(3)],1))
    for name in ('enhanced_union_01','enhanced_union_03','enhanced_union_10','enhanced_union_30','enhanced_color_10','enhanced_geometry_10','enhanced_outline_10'):
        ids=selection[name];path=dest/(name+'.ply')
        PlyData([PlyElement.describe(v[ids].copy(),'vertex')],text=False,byte_order=ply.byte_order).write(path)
        np.savetxt(dest/(name+'.original_ids.txt'),ids,fmt='%d')
        reread=PlyData.read(path)['vertex'].data
        if reread.dtype!=v.dtype or not np.array_equal(reread,v[ids]):raise ValueError('PLY original properties changed')
        diagnostics[name]=dict(count=len(ids),sha256=sha(path),original_ids_sha256=sha(dest/(name+'.original_ids.txt')),
            spatial_bbox_min=xyz[ids].min(0).tolist() if len(ids) else None,spatial_bbox_max=xyz[ids].max(0).tolist() if len(ids) else None,
            scale_quantiles=np.quantile(scales[ids],[.1,.5,.9],axis=0).tolist() if len(ids) else None,
            anisotropy_quantiles=np.quantile(scales[ids].max(1)/scales[ids].min(1),[.1,.5,.9]).tolist() if len(ids) else None,
            view_support_histogram=np.bincount(scores['support_view_count'][ids].astype(int),minlength=9).tolist(),
            foreground_visibility_mass=float(scores['raw_denominator'][ids].sum()))
        if len(ids)>1:
            distances=cKDTree(xyz[ids]).query(xyz[ids],k=2)[0][:,1]
            diagnostics[name]['nearest_selected_center_distance_quantiles']=np.quantile(distances,[.1,.5,.9]).tolist()
    atomic(dest/'PLY_EXPORT.json',dict(checkpoint_sha256=checkpoint['sha256'],all_vertex_properties_preserved=True,
        standalone_subset_warning='Subset-only rendering changes occlusion. Primary attribute images preserve the full model.',
        no_normal_from_covariance=True,no_curve_fit=True,exports=diagnostics))
    curate=ART/'assets'/scene;curate.mkdir(parents=True,exist_ok=True)
    for name in ('scores.npz','selection.npz','ASSET.json','NORMALIZATION.json','ASSET_SEAL.json'):shutil.copyfile(folder/name,curate/name)
    shutil.copyfile(dest/'PLY_EXPORT.json',curate/'PLY_EXPORT.json')
    summary={}
    for split,prefix in [('F','F_'),('C','C_'),('arc','arc0_')]:
        rows=[json.loads(p.read_text()) for p in sorted((OUT/scene/'frames').glob(prefix+'*/METRICS.json'))]
        if not rows:continue
        fields={}
        for name in rows[0]['fields']:
            f=[r['fields'][name] for r in rows]
            fields[name]={k:float(np.mean([a[k] for a in f])) for k in ('mass','concentration','lift','soft_alignment')}
            fields[name]['worst_lift']=min((dict(key=r['key'],lift=r['fields'][name]['lift']) for r in rows),key=lambda r:r['lift'])
        summary[split]=dict(count=len(rows),fields=fields,top4_mass_coverage=float(sum(r['top4_audit']['cached_mass'] for r in rows)/sum(r['top4_audit']['alpha_mass'] for r in rows)),
            selected_top10_captured_mass=float(sum(r['top4_audit']['selected_top10_cached_mass'] for r in rows)/sum(r['top4_audit']['selected_top10_full_mass'] for r in rows)),
            perview=[dict(key=r['key'],selected_lift=r['fields']['selected_Q_10']['lift'],random_lift=r['fields']['random_Q_10']['lift'],baseline_lift=r['fields']['baseline_Q_10']['lift'],single_lift=r['fields']['single_Q_10']['lift'],null_lift=r['fields']['null_Q_10']['lift']) for r in rows])
    atomic(ART/f'SUMMARY_{scene}.json',dict(scene=scene,asset=json.loads((folder/'ASSET.json').read_text()),splits=summary,ply_export=diagnostics))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['fit','project','media','export']);p.add_argument('scene',choices=['mic','materials']);a=p.parse_args()
    try:globals()[a.stage+'_scene'](a.scene)
    except Exception as exc:
        status('ENGINEERING_ERROR_REQUIRES_RECORDED_REPAIR',scene=a.scene,stage=a.stage,error=repr(exc));raise
