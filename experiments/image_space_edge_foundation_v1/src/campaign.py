"""Small resumable native-image campaign. Development precedes fixed evaluation."""
import copy,json,os,time
from pathlib import Path
import cv2,numpy as np
from scipy.ndimage import distance_transform_edt
from skimage.morphology import skeletonize
from runtime import *
from boundary import *
from presentation import *
from fixtures import fixtures,moving_sequence

def native_spec(entry):
    c=copy.deepcopy(entry['camera']);c['width']=c.get('native_width',800);c['height']=c.get('native_height',800)
    fx=c['width']/(2*np.tan(c['FoVx']/2));fy=c['height']/(2*np.tan(c['FoVy']/2))
    c['K']=[[float(fx),0,(c['width']-1)/2],[0,float(fy),(c['height']-1)/2],[0,0,1]]
    return c
def inputs():
    d=json.loads(DATA_PATH.read_text());local={};public={}
    for scene,s in d['scenes'].items():
        groups={'dev':s['roles']['dev'],'fixed':[v for v in s['roles']['edit-holdout'] if v['index'] in [0,8,18,30]],'arc':s['arc']}
        local[scene]=dict(model=s['model'],model_sha256=s['model_sha256'],groups=groups)
        public[scene]=dict(model_sha256=s['model_sha256'],gaussian_count=s['ply']['count'],SH_degree=3,groups={})
        for role,views in groups.items():
            public[scene]['groups'][role]=[dict(key=v['key'],native_camera=native_spec(v),native_camera_sha256=digest(native_spec(v)),
                source_camera_sha256=v['camera_hash'],GS_TRAIN_seen=v.get('GS_TRAIN_seen'),previous_research_seen=True,
                scope='exploratory, historical TRAIN/research seen; not fresh blind',reference_sha256=v.get('expected_photo_sha256'),
                reference='original TRAIN RGBA composited on white; comparison only' if v.get('original_path') else None) for v in views]
        assert len(groups['fixed'])==4 and len(groups['arc'])==33
    return local,public
def allfiles(*directories):return [str(p.relative_to(ROOT)) for d in directories for p in sorted(d.rglob('*')) if p.is_file() and not p.name.endswith('.tmp')]
def npz(path,**arrays):
    p=scoped(path);tmp=p.with_name(p.name+'.tmp')
    with tmp.open('wb') as f:np.savez_compressed(f,**arrays)
    os.replace(tmp,p)
def reference(entry,size):
    im=np.asarray(Image.open(entry['original_path']).convert('RGBA'),np.float32)/255
    rgb=im[...,:3]*im[...,3,None]+1-im[...,3,None]
    assert rgb.shape[:2]==(size,size)
    return rgb
def render_group(scene,role,local):
    from native import load_model,render,stock_camera_check
    import torch
    s=local[scene];guard(scene+'/load_'+role,True)
    assert sha(s['model'])==s['model_sha256'];m=load_model(s['model']);records=[]
    for i,e in enumerate(s['groups'][role]):
        guard(f'{scene}/native/{role}/{e["key"]}',True);c=native_spec(e);p=OUT/'raw'/scene/role/e['key']
        im,a=render(m,c);npz(p/'native.npz',rgb=im,alpha=a)
        save_image(p/'native.png',im)
        rec=dict(key=e['key'],camera_sha256=digest(c),native_png_sha256=sha(p/'native.png'),
                 float_rgb_sha256=hashlib.sha256(im.tobytes()).hexdigest(),width=c['width'],height=c['height'],fullSH3=True,
                 native_min=float(im.min()),native_max=float(im.max()),alpha_min=float(a.min()),alpha_max=float(a.max()))
        if role=='dev' and i==0:rec['stock_Camera_max_abs']=stock_camera_check(m,c);assert rec['stock_Camera_max_abs']<5e-4
        records.append(rec)
    del m;torch.cuda.empty_cache()
    return dict(scene=scene,role=role,native_frames=len(records),unique_float_rgb=len({r['float_rgb_sha256'] for r in records}),records=records,
                files=allfiles(OUT/'raw'/scene/role))

def metrics(soft):
    darkness=1-ink(soft)[...,0]
    return dict(ink_area=float(darkness.sum()),visible_area=int((darkness>.2).sum()),
                ridge_length=int(skeletonize(darkness>.2).sum()))
def save_fields(directory,result):
    names=['raw','magnitude','normal','coherence','agreement','support','confidence','detail','structural','union','unknown','classmap','profile_confidence','width_map']
    npz(directory/'fields.npz',**{k:result[k] for k in names})
    npz(directory/'profiles.npz',**result['profiles'])
    paths=chains(result['union'],result['normal'])
    atomic_json(directory/'chains.json',dict(coordinates='native image xy pixels; no lifting',chains=paths,
                length_weighted_coherence=float(sum(p['coherence']*p['arc_length'] for p in paths)/max(sum(p['arc_length'] for p in paths),1)),
                total_arc_length=float(sum(p['arc_length'] for p in paths))))
    return paths
def dev_spatial(scene,local,cfg):
    panels=[];records=[];directory=OUT/'dev_fields'/scene
    for e in local[scene]['groups']['dev']:
        guard(scene+'/dev_spatial/'+e['key']);z=np.load(OUT/'raw'/scene/'dev'/e['key']/'native.npz');im=z['rgb']
        r=analyze(im,cfg);base,raw=classic_response(im,cfg);p=directory/e['key'];save_fields(p,r)
        npz(p/'baselines.npz',classic=base,classic_raw=raw,canny=canny_response(im))
        panels.extend([(e['key']+' native fullSH3',im),(e['key']+' structural RGB',ink(r['structural'])),(e['key']+' detail union RGB',ink(r['union'])),(e['key']+' classic luminance',ink(base))])
        records.append(dict(key=e['key'],profiles=len(r['profiles']['xy']),valid=int(r['profiles']['valid'].sum()),
                            structural=metrics(r['structural']),union=metrics(r['union']),classic=metrics(base),
                            profile_union_delta=float(abs(r['union']-r['detail']).sum())))
    imagepath=panel_sheet(panels,ART/'dev'/f'{scene}_fourview.jpg',columns=4,size=400,title=f'{scene} DEV native rendered cameras / exploratory')
    return dict(scene=scene,records=records,files=allfiles(directory)+[imagepath])
def calibrate(local,cfg):
    # Only DEV is inspected. Baseline intensity thresholds and presentation gains
    # are fitted to aggregate visible ink area + skeleton length, never top-k.
    dev=[]
    for scene,s in local.items():
        for e in s['groups']['dev']:
            z=np.load(OUT/'raw'/scene/'dev'/e['key']/'native.npz');f=np.load(OUT/'dev_fields'/scene/e['key']/'fields.npz');b=np.load(OUT/'dev_fields'/scene/e['key']/'baselines.npz')
            dev.append((scene,e['key'],z['rgb'],f['union'],b['classic']))
    target={k:sum(metrics(v[3])[k] for v in dev) for k in ['ink_area','ridge_length']}
    def score(area,length):return float(np.log((area+1)/(target['ink_area']+1))**2+np.log((length+1)/(target['ridge_length']+1))**2)
    trials=[]
    for gain in [.65,.8,1.,1.2,1.5,2.,2.5,3.]:
        ms=[metrics(np.clip(v[4]*gain,0,1)) for v in dev];a=sum(m['ink_area'] for m in ms);l=sum(m['ridge_length'] for m in ms)
        trials.append(dict(arm='classic',gain=gain,area=a,length=l,objective=score(a,l)))
    for threshold in [4,7,10,15,20,30,45,60,90]:
        for gain in [.6,.8,1.]:
            ms=[metrics(canny_response(v[2],threshold)*gain) for v in dev];a=sum(m['ink_area'] for m in ms);l=sum(m['ridge_length'] for m in ms)
            trials.append(dict(arm='canny',threshold=threshold,gain=gain,area=a,length=l,objective=score(a,l)))
    selected={arm:min([t for t in trials if t['arm']==arm],key=lambda t:t['objective']) for arm in ['classic','canny']}
    return dict(target=target,selected=selected,trials=trials,
                rule='single shared parameters for both scenes, selected on 8 DEV images before fixed/arc render',
                exact_match=False,qualification='aggregate closest match; residual area/length mismatch explicitly retained',
                residuals={k:dict(area_ratio=v['area']/target['ink_area'],length_ratio=v['length']/target['ridge_length']) for k,v in selected.items()})

def fixed_spatial(scene,local,cfg,matching):
    line_panels={};overlay_panels=[];control_panels=[];records=[];sheet_panels=[]
    roi=[240,260,560,580] if scene=='lego' else [240,330,560,650]
    for e in local[scene]['groups']['fixed']:
        key=e['key'];guard(scene+'/fixed_spatial/'+key)
        z=np.load(OUT/'raw'/scene/'fixed'/key/'native.npz');im=z['rgb'];alpha=z['alpha'];r=analyze(im,cfg)
        classic,classic_raw=classic_response(im,cfg);canny_raw=canny_response(im)
        canny=canny_response(im,matching['canny']['threshold'])*matching['canny']['gain']
        classic_matched=np.clip(classic*matching['classic']['gain'],0,1);outline=alpha_outline(alpha)
        auxiliary=np.maximum(r['union'],outline)
        output=OUT/'fixed_fields'/scene/key;paths=save_fields(output,r)
        npz(output/'baselines.npz',canny_raw=canny_raw,canny_matched=canny,classic_raw=classic_raw,classic_ridge=classic,classic_matched=classic_matched,alpha_outline=outline)
        # Restrict RGB controls to reliable full foreground; silhouette is an aux.
        control_result=copy.copy(r);p=copy.copy(r['profiles']);control_result['profiles']=p
        interior=cv2.erode((alpha>.995).astype(np.uint8),np.ones((23,23),np.uint8)).astype(bool)
        xy=p['xy'].astype(int);p['valid']=p['valid']&interior[xy[:,1],xy[:,0]]
        sharp,gs=control_width(im,control_result,.65,cfg);soft,gb=control_width(im,control_result,1.5,cfg)
        npz(output/'rgb_controls.npz',original=im,sharpen=sharp,soften=soft,alpha=alpha,sharpen_band=gs['band'],soften_band=gb['band'])
        media=ART/'media'/scene/'fixed'/key
        ref=reference(e,im.shape[0]);save_image(media/'reference.png',ref);save_image(media/'native.png',im)
        responses={'canny':canny,'classic':classic_matched,'structural':r['structural'],'detail_union':r['union'],'alpha_aux':outline,'union_plus_alpha_aux':auxiliary}
        for name,field in responses.items():
            save_image(media/(name+'_ink.png'),ink(field));save_image(media/(name+'_overlay.png'),overlay(im,field))
            line_panels.setdefault(name,[]).append((key+' / '+name,ink(field)))
        save_image(media/'sharpen.png',sharp);save_image(media/'soften.png',soft)
        evidence=[('normal direction (unoriented)',map_rgb((np.arctan2(r['normal'][...,1],r['normal'][...,0])+np.pi/2)/np.pi,'hsv')),
                  ('raw broad response',map_rgb(r['raw'])),('tensor confidence',map_rgb(r['confidence'])),('profile confidence',map_rgb(r['profile_confidence'])),
                  ('detail / unknown',map_rgb(r['unknown'])),('classes: fit=green detail=orange',np.stack([r['classmap']==2,r['classmap']==1,np.zeros_like(alpha)],-1).astype(np.float32))]
        for name,a in [('confidence',map_rgb(r['confidence'])),('unknown',map_rgb(r['unknown'])),('width',map_rgb(r['width_map']/11.))]:save_image(media/(name+'.png'),a)
        panel_sheet(evidence,media/'evidence.jpg',columns=3,size=400,title='RGB evidence; no semantic edge truth')
        profile_plot(r['profiles'],media/'normal_profiles.png')
        panel_sheet([('reference comparison only',ref),('native fullSH3',im),('Canny matched DEV',ink(canny)),('classic matched DEV',ink(classic_matched)),('RGB structural',ink(r['structural'])),('RGB generous union',ink(r['union'])),('RGB union overlay',overlay(im,r['union'])),('union + alpha auxiliary',ink(auxiliary))],media/'full_object.jpg',columns=4,size=800,title=f'{scene} {key} fixed exploratory same camera')
        crop_panels=[]
        for name,a in [('native RGB',im),('Canny',ink(canny)),('classic',ink(classic_matched)),('structural',ink(r['structural'])),('union ink',ink(r['union'])),('union overlay',overlay(im,r['union']))]:
            crop=a[roi[1]:roi[3],roi[0]:roi[2]];save_image(media/(name.replace(' ','_')+'_crop.png'),crop);crop_panels.append((name,array_image(crop)))
        panel_sheet(crop_panels,media/'native_resolution_crops.png',columns=3,size=320,title='Fixed ROI / original pixels; no resampling of crop')
        panel_sheet([(n,a.resize((640,640),Image.Resampling.NEAREST)) for n,a in crop_panels],media/'crops_2x.png',columns=3,size=640,title='Same ROI / nearest 2x zoom')
        # Compact native float16 raw fields are committed; full float32 + profiles
        # and every arc frame remain in ignored out with hashes and exact seals.
        npz(media/'raw_fields.npz',**{k:r[k].astype(np.float16) if r[k].dtype.kind=='f' else r[k] for k in ['raw','normal','confidence','structural','detail','union','unknown','classmap']})
        npz(media/'normal_profiles.npz',**r['profiles'])
        overlay_panels.extend([(key+' native',im),(key+' Canny',overlay(im,canny)),(key+' RGB union',overlay(im,r['union'])),(key+' RGB + alpha aux',overlay(im,auxiliary))])
        control_panels.extend([(key+' native',im),(key+' width x0.65',sharp),(key+' width x1.50',soft),(key+' 8x bounded RGB delta',np.clip(.5+(sharp-im)*8,0,1))])
        rawpanels=[('Canny raw default 45',ink(canny_raw)),('classic raw ridge',ink(classic)),('RGB union raw',ink(r['union'])),('broad field unmatched',map_rgb(r['raw']))]
        panel_sheet(rawpanels,media/'unmatched_raw.jpg',size=400)
        records.append(dict(key=key,camera_sha256=digest(native_spec(e)),roi=roi,roi_source='fixed native screen rectangle before fixed render, not human boundary annotation',
            profiles=len(p['xy']),valid_profiles=int(r['profiles']['valid'].sum()),rejections={str(i):int((r['profiles']['rejection']==i).sum()) for i in range(7)},
            chain_count=len(paths),chain_arc_length=float(sum(c['arc_length'] for c in paths)),
            metrics={k:metrics(v) for k,v in responses.items()},raw_metrics={'canny45':metrics(canny_raw),'classic_unmatched':metrics(classic)},
            profile_union_change_pixels=int((r['union']>r['detail']+1e-6).sum()),profile_union_delta=float((r['union']-r['detail']).sum()),
            control={k:{n:v for n,v in g.items() if n!='band'} for k,g in [('sharpen',gs),('soften',gb)]},
            spatial_semantics='fit color transition or detail/unknown, no material/geometry certification'))
    dest=ART/'media'/scene
    lp=[]
    for name in ['canny','classic','structural','detail_union','alpha_aux','union_plus_alpha_aux']:lp.extend(line_panels[name])
    panel_sheet(lp,dest/'fourview_line_only.png',columns=4,size=800,title=f'{scene} four fixed exploratory cameras / full objects / no kernels')
    panel_sheet(overlay_panels,dest/'fourview_overlays.jpg',columns=4,size=800,title=f'{scene} same native RGB / baseline and boundary field overlays')
    panel_sheet(control_panels,dest/'fourview_RGB_width_control.jpg',columns=4,size=800,title='Screen-space local stylization / no photorealistic repair claim')
    return dict(scene=scene,fixed_views=4,records=records,files=allfiles(OUT/'fixed_fields'/scene,ART/'media'/scene))

def arc_spatial(scene,local,cfg,matching):
    records=[];directory=OUT/'arc_fields'/scene
    for e in local[scene]['groups']['arc']:
        guard(scene+'/arc_spatial/'+e['key']);z=np.load(OUT/'raw'/scene/'arc'/e['key']/'native.npz');im=z['rgb'];r=analyze(im,cfg)
        p=directory/e['key'];save_fields(p,r)
        base=canny_response(im,matching['canny']['threshold'])*matching['canny']['gain'];classic,_=classic_response(im,cfg)
        npz(p/'baselines.npz',canny=base,classic=np.clip(classic*matching['classic']['gain'],0,1))
        records.append(dict(key=e['key'],profiles=len(r['profiles']['xy']),valid_profiles=int(r['profiles']['valid'].sum()),spatial=metrics(r['union']),structural=metrics(r['structural'])))
    return dict(scene=scene,arc_frames=33,records=records,files=allfiles(directory))

def temporal_arc(scene,local,cfg):
    directory=OUT/'temporal'/scene;records=[];previm=prevs=prevt=None
    for i,e in enumerate(local[scene]['groups']['arc']):
        guard(scene+'/temporal/'+e['key']);z=np.load(OUT/'raw'/scene/'arc'/e['key']/'native.npz');im=z['rgb'];spatial=np.load(OUT/'arc_fields'/scene/e['key']/'fields.npz')['union']
        if i==0:temporal=spatial.copy();rec=dict(index=i,key=e['key'],reset='first frame',failures=[])
        else:
            f=flow_pair(previm,im,cfg);temporal,warpt=blend_temporal(prevt,spatial,f,cfg);warps=remap(prevs,f['mx'],f['my'])
            valid=f['valid']&((spatial>.075)|(warps>.075));n=max(int(valid.sum()),1)
            a=spatial>.2;b=warps>.2;t=temporal>.2;tw=warpt>.2
            edge_domain=(spatial>.075)|(warps>.075)
            edge_valid=float(f['valid'][edge_domain].mean()) if edge_domain.any() else 0.
            ghosts=int(((temporal>.12)&(spatial<.02)).sum())
            error_s=float(abs(spatial-warps)[valid].sum()/n);error_t=float(abs(temporal-warpt)[valid].sum()/n)
            failures=[]
            if edge_valid<.5:failures.append('low_flow_confidence')
            if ghosts:failures.append('unsupported_ghost')
            if error_s>.2:failures.append('large_motion_corrected_spatial_error')
            rec=dict(index=i,key=e['key'],edge_valid_fraction=edge_valid,flow_valid_fraction=float(f['valid'].mean()),
                     motion_corrected_spatial_MAE=error_s,motion_corrected_temporal_MAE=error_t,
                     spatial_churn=float(np.logical_xor(a,b)[valid].sum()/n),temporal_churn=float(np.logical_xor(t,tw)[valid].sum()/n),
                     unsupported_ghost_pixels=ghosts,zero_evidence_nonzero_pixels=int(((spatial==0)&(temporal!=0)).sum()),
                     max_temporal_delta=float(abs(temporal-spatial).max()),failures=failures,
                     qualification='flow correspondence diagnostic; repeated texture cannot certify 3D reprojection')
            npz(directory/(e['key']+'_flow.npz'),backward=f['backward'],forward=f['forward'],confidence=f['confidence'],valid=f['valid'],fb=f['fb'],photo=f['photo'])
        npz(directory/(e['key']+'.npz'),spatial=spatial,temporal=temporal)
        records.append(rec);previm,prevs,prevt=im,spatial,temporal
    vals=records[1:]
    return dict(scene=scene,frames=33,records=records,failure_frames=[r['index'] for r in records if r['failures']],
                aggregate={k:float(np.mean([r[k] for r in vals])) for k in ['motion_corrected_spatial_MAE','motion_corrected_temporal_MAE','spatial_churn','temporal_churn','edge_valid_fraction']},
                unsupported_ghost_pixels=sum(r.get('unsupported_ghost_pixels',0) for r in records),files=allfiles(directory))

def arc_media(scene,local,cfg):
    media=ART/'media'/scene/'arc';panels_all=[];native_hashes=[];frame_dirs={name:OUT/'video_frames'/scene/name for name in ['lines','overlays']}
    snapshots=[]
    for i,e in enumerate(local[scene]['groups']['arc']):
        guard(scene+'/video_frame/'+e['key']);z=np.load(OUT/'raw'/scene/'arc'/e['key']/'native.npz');im=z['rgb'];a=np.load(OUT/'arc_fields'/scene/e['key']/'baselines.npz')['canny'];t=np.load(OUT/'temporal'/scene/(e['key']+'.npz'))
        native_hashes.append(hashlib.sha256(im.tobytes()).hexdigest())
        rows={'lines':[(f'{i:02d} native fullSH3',im),('Canny DEV matched',ink(a)),('spatial RGB union / OFF',ink(t['spatial'])),('same spatial + flow / ON',ink(t['temporal']))],
              'overlays':[(f'{i:02d} native fullSH3',im),('Canny overlay',overlay(im,a)),('spatial RGB overlay / OFF',overlay(im,t['spatial'])),('temporal RGB overlay / ON',overlay(im,t['temporal']))]}
        for name,panels in rows.items():
            path=frame_dirs[name]/f'{i:03d}.png';panel_sheet(panels,path,size=800)
            if i in [0,16,32]:
                dst=scoped(media/f'{name}_{i:03d}.png');shutil.copyfile(path,dst);snapshots.append(str(dst.relative_to(ROOT)))
        if i in [0,16,32]:save_image(media/f'native_{i:03d}.png',im)
        panels_all.extend([(f'{i:02d} actual native RGB',im),(f'{i:02d} spatial OFF',ink(t['spatial'])),(f'{i:02d} temporal ON',ink(t['temporal']))])
    assert len(set(native_hashes))==33
    panel_sheet(panels_all,media/'all33_actual_strip.jpg',columns=9,size=240,title=f'{scene}: every frame in order; RGB / spatial OFF / temporal ON')
    panel_sheet([p for j,p in enumerate(panels_all) if j%3==0],media/'native_all33_contactsheet.jpg',columns=11,size=200,title='33 actual independently rendered contiguous prior camera arc')
    videos=[encode_video(frame_dirs[name],media/(name+'_33.mp4'),3200,844) for name in ['lines','overlays']]
    return dict(scene=scene,videos=videos,actual_native_frames=33,distinct_native_frames=len(set(native_hashes)),native_float_sha256=native_hashes,
                snapshots=snapshots,files=allfiles(media,*frame_dirs.values()))

def diagnostic_pr(soft,truth):
    pred=soft>.2;target=truth>0
    if not target.any():return dict(precision=None,recall=None,false_positive_pixels=int(pred.sum()))
    dt=distance_transform_edt(~target);dp=distance_transform_edt(~pred)
    return dict(precision=float((dt[pred]<=2).mean()) if pred.any() else 0.,recall=float((dp[target]<=2).mean()),
                tolerance_pixels=2,qualification='diagnostic analytic screen-space edge truth, not semantic certification')
def measure_width(im,minus,plus,center):
    row=im[im.shape[0]//2];d=plus-minus;t=(row-minus)@d/(d@d+1e-12)
    x=np.arange(len(t));return float(np.interp(.9,t,x)-np.interp(.1,t,x))
def synthetic(cfg,matching):
    records=[];directory=ART/'synthetic';outdir=OUT/'synthetic'
    for name,(im,t) in fixtures().items():
        r=analyze(im,cfg);classic,_=classic_response(im,cfg);canny=canny_response(im,matching['canny']['threshold'])*matching['canny']['gain']
        npz(outdir/(name+'.npz'),rgb=im,truth=t['truth'],union=r['union'],structural=r['structural'],detail=r['detail'],classmap=r['classmap'])
        save_image(directory/(name+'_truth.png'),np.repeat(t['truth'][...,None],3,axis=2))
        panel_sheet([('analytic input',im),('Canny DEV matched',ink(canny)),('classic luminance',ink(classic)),('structural fit',ink(r['structural'])),('generous union',ink(r['union'])),('unknown evidence',map_rgb(r['unknown']))],directory/(name+'.png'),columns=3,size=256,title=name)
        rec=dict(name=name,valid_profiles=int(r['profiles']['valid'].sum()),candidates=len(r['profiles']['xy']),
                 diagnostics={k:diagnostic_pr(v,t['truth']) for k,v in [('canny',canny),('classic',classic),('union',r['union']),('structural',r['structural'])]})
        if name in ['width','color_step']:
            sharp,gs=control_width(im,r,.65,cfg);soft,gb=control_width(im,r,1.5,cfg)
            m,p=im[64,0],im[64,-1]
            rec['control']=dict(known_width=t['width'],measured_original=measure_width(im,m,p,t['center']),measured_sharpen=measure_width(sharp,m,p,t['center']),measured_soften=measure_width(soft,m,p,t['center']),
                               guards={k:{n:v for n,v in g.items() if n!='band'} for k,g in [('sharpen',gs),('soften',gb)]})
            panel_sheet([('known width original',im),('width x.65 conservative',sharp),('width x1.5 conservative',soft)],directory/(name+'_width_control.png'),size=256)
            npz(outdir/(name+'_control.npz'),original=im,sharpen=sharp,soften=soft,band=gs['band'])
        records.append(rec)
    seq=moving_sequence();previm=prev=None;moving=[];panels=[]
    for i,im in enumerate(seq):
        r=analyze(im,cfg);sp=r['union']
        if i==0:temp=sp.copy();meta={}
        else:temp,meta=temporal_pair(previm,im,prev,sp,cfg)
        # Truth from exact constructed pixel discontinuities, not our score.
        jump=np.zeros(im.shape[:2],bool);jump[:,1:]|=np.max(abs(np.diff(im,axis=1)),2)>.02;jump[1:]|=np.max(abs(np.diff(im,axis=0)),2)>.02
        domain=distance_transform_edt(~jump)<=3 if jump.any() else np.zeros(jump.shape,bool)
        ghost=float(temp[~domain].sum()/max(float(temp.sum()),1.))
        sx=float((sp*np.arange(im.shape[1])[None]).sum()/max(float(sp.sum()),1.));tx=float((temp*np.arange(im.shape[1])[None]).sum()/max(float(temp.sum()),1.))
        moving.append(dict(frame=i,ghost_mass_outside_truth_3px=ghost,temporal_minus_spatial_centroid=tx-sx,max_delta=float(abs(temp-sp).max()),zero_evidence_ghosts=int(((sp==0)&(temp!=0)).sum())))
        panels.extend([(f'{i} constructed RGB',im),(f'{i} spatial OFF',ink(sp)),(f'{i} temporal ON',ink(temp))]);previm,prev=im,temp
        npz(outdir/f'moving_{i}.npz',rgb=im,spatial=sp,temporal=temp,truth_jump=jump)
    panel_sheet(panels,directory/'moving_disocclusion_all_frames.png',columns=3,size=256,title='Moving edge / independent occluder / final disappearance: all frames')
    return dict(fixtures=records,moving_disocclusion=moving,files=allfiles(directory,outdir))

def production_freeze(local,public,cfg,match):
    p=ART/'PRODUCTION_FREEZE.json';obj=dict(schema='screen-space-boundary-foundation-v1',base='f76fd00f03dc96a099a5ea1ff7935cb8ddb04f0e',
         start_head='51da04473768828266c36b1137663a4fab649a90',source_hashes=source_hashes(),data_freeze_sha256=sha(DATA_PATH),prior_input_sha256=sha(PRIOR_PATH),
         config=cfg,baseline_matching=match,scenes=public,core_API_inputs=['RGB only'],auxiliary=['native alpha contour only'],
         representation='per-view 2D normal profiles, soft response and screen-space stroke chains',
         temporal='Farneback forward/backward, evidence-clamped soft response only; no path/UID persistence',
         control='optional bounded local RGB transition stylization; alpha unchanged; no geometry/photorealistic repair claim',
         ROI={'lego':[240,260,560,580],'chair':[240,330,560,650]},
         resource_guards={'root_reserve_GiB':4,'Git_reserve_GiB':1.5,'stage_cap_GiB':8,'GPU':0,'CPU_threads':2},
         frozen_before_fixed_and_arc=True,fresh_blind=False,human_review='pending',novelty='independent prototype; no published-method reproduction or novelty claim')
    if p.exists():
        old=json.loads(p.read_text())
        if old!=obj:raise RuntimeError('production freeze immutable; changed code/config cannot resume')
    else:atomic_json(p,obj)
    atomic_json(OUT/'LOCAL_INPUTS.json',local)
    return sha(p)

def run(mode):
    import fcntl
    lock=(OUT/'runner.lock').open('w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    local,public=inputs();cfg=dict(DEFAULT)
    if not (OUT/'BASELINE_BEFORE.json').exists():atomic_json(OUT/'BASELINE_BEFORE.json',baseline_snapshot())
    if mode=='dev':
        devfreeze=digest(dict(config=cfg,cameras={s:v['groups']['dev'] for s,v in public.items()},sources=source_hashes()))
        atomic_json(ART/'DEV_FREEZE.json',dict(digest=devfreeze,config=cfg,sources=source_hashes(),role='8 historically seen exploratory DEV cameras'))
        for scene in local:
            r=unit(scene+'_native_dev',devfreeze,lambda scene=scene:render_group(scene,'dev',local),True)
            if r.get('status')!='FAILED':unit(scene+'_dev_spatial',devfreeze,lambda scene=scene:dev_spatial(scene,local,cfg))
        match=calibrate(local,cfg);atomic_json(ART/'DEV_MATCHING.json',match)
        event('DEV','COMPLETE',matching=match['residuals']);return
    match=json.loads((ART/'DEV_MATCHING.json').read_text());freeze=production_freeze(local,public,cfg,match)
    matching=match['selected']
    unit('synthetic',freeze,lambda:synthetic(cfg,matching))
    # Errors in one scene never prevent the other scene from being attempted.
    for scene in local:
        for role in ['fixed','arc']:
            native=unit(scene+'_native_'+role,freeze,lambda scene=scene,role=role:render_group(scene,role,local),True)
            if native.get('status')=='FAILED':continue
            if role=='fixed':unit(scene+'_fixed_spatial',freeze,lambda scene=scene:fixed_spatial(scene,local,cfg,matching))
            else:
                a=unit(scene+'_arc_spatial',freeze,lambda scene=scene:arc_spatial(scene,local,cfg,matching))
                if a.get('status')=='FAILED':continue
                t=unit(scene+'_temporal',freeze,lambda scene=scene:temporal_arc(scene,local,cfg))
                if t.get('status')!='FAILED':unit(scene+'_arc_media',freeze,lambda scene=scene:arc_media(scene,local,cfg))
    event('PRODUCTION','FINISHED_ATTEMPTS')
    atomic_json(OUT/'RUNNER_COMPLETE.json',dict(freeze=freeze,finished=True,utc=time.time(),results=[p.name for p in (ART/'results').glob('*.json')]))
