from pilotio import *
from core import run_backend, eligible_fragment
from PIL import Image,ImageDraw,ImageFont

RENDER_CODE=Path('/home/u00134/3dgs_line/gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01')

def save_result(folder,result):
    folder.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(folder/'geometry.npz',xyz=result['xyz'],tangent=result['tangent'],groups=result['groups'],membership=result['membership'])
    for key in ['hypotheses','intervals','links','stats','fragments']: js(folder/(key+'.json'),result[key])

def prepare_real(scene,roi,view):
    d=OUT/'real_budgeted'/scene; d.mkdir(parents=True,exist_ok=True)
    # Selection receipt is committed before any changed-result computation.
    js(d/'selection.json',dict(scene=scene,view=view,roi=roi,selection='whole original parents with at least one optimized control projecting inside fixed ROI; stable parent ID order, whole-parent cap',max_samples=CFG['max_samples'],basis='BUILD original source only',utc=now()))
    root=BASE/'arms/C/scenes'/scene/'full'; a=load_np(root/'gaussians.npz'); s=load_np(root/'SHARED_CONTROL_AND_SAMPLING.npz'); sample=load_np(OUT/'audit'/scene/'line_samples.npz'); parents=json.loads((root/'parents.json').read_text())
    reg=json.loads((BASE/'REGISTRY.json').read_text())['scenes'][scene]; c=next(c for c in reg['cameras'] if c['view']==view)
    ids=[]; selected_parents=[]; capped=0; nonroi=0; xmin,ymin,xmax,ymax=roi
    unique,starts,counts=np.unique(a['primitive_id'],return_index=True,return_counts=True); ranges={int(p):(int(st),int(n)) for p,st,n in zip(unique,starts,counts)}
    for i,p in enumerate(parents):
        uv,z=project(np.asarray(p['control']),c); inside=(z>.2)&(uv[:,0]>=xmin)&(uv[:,0]<xmax)&(uv[:,1]>=ymin)&(uv[:,1]<ymax)
        if not inside.any(): nonroi+=ranges[i][1]; continue
        st,n=ranges[i]
        if len(ids)+n>CFG['max_samples']: capped+=n; continue
        ids.extend(range(st,st+n)); selected_parents.append(i)
    ids=np.asarray(ids,np.int64); assert len(ids)>0,'NO_REAL_ROI_INPUT'
    audit=json.loads((OUT/'input_audit.json').read_text())[scene]; h=audit['h']; center=np.median(a['means'][ids],axis=0); x=(a['means'][ids]-center)/h
    fid=a['primitive_id'][ids]; eligible=np.zeros(len(ids),bool); protected=np.zeros(len(ids),bool)
    for p in selected_parents:
        ii=np.flatnonzero(fid==p); eligible[ii]=eligible_fragment(x[ii],1.) and not parents[p]['closed']; protected[ii[:2]]=True; protected[ii[-2:]]=True
    # Preserve exact duplicate support samples at crossings; original endpoints are
    # protected regardless of whether a physical junction has been established.
    _,inv,cnt=np.unique(np.round(x,6),axis=0,return_inverse=True,return_counts=True); protected|=cnt[inv]>1
    data=dict(xyz=x,tangent=sample['tangent'][ids],fragment_id=fid,confidence=np.ones(len(ids)),tangent_reliable=np.linalg.norm(sample['tangent'][ids],axis=1)>.9,eligible=eligible,protected=protected)
    np.savez_compressed(d/'input.npz',**data,line_gaussian_id=ids,sample_id=sample['sample_id'][ids],observation_end_ids=sample['observation_end_ids'][ids],control_index=sample['control_index'][ids],basis=sample['basis'][ids],source_gaussian_id=np.full(len(ids),-1,np.int64))
    js(d/'input_manifest.json',dict(h=h,center=center,selected_parents=selected_parents,input_hash=sha(d/'input.npz'),sample_count=len(ids),total_line_gaussians=len(a['means']),outside_ROI_samples=nonroi,over_cap_samples=capped,unselected_unchanged_samples=len(a['means'])-len(ids),eligible_samples=int(eligible.sum()),ineligible_preserved_samples=int((~eligible).sum()),confidence='UNKNOWN, neutral weight one',inverse='xyz_world=xyz_normalized*h+center',source_GS_ids='UNKNOWN'))
    return data,ids,a,s,reg,center,h

def image_array(a): return Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5))
def board(path,items,title,subtitle,roi=None):
    w,h=items[0][1].size; cols=3; rows=(len(items)+cols-1)//cols
    out=Image.new('RGB',(cols*w,rows*(h+28)+62),'white'); draw=ImageDraw.Draw(out)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
    small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',13)
    draw.text((8,4),title,fill='black',font=font); draw.text((8,30),subtitle,fill='black',font=small)
    for i,(label,im) in enumerate(items):
        im=im.copy()
        if roi: ImageDraw.Draw(im).rectangle(roi,outline=(255,100,0),width=2)
        xx=i%cols*w; yy=62+i//cols*(h+28); draw.text((xx+5,yy+4),label,fill='black',font=small); out.paste(im,(xx,yy+28))
    out.save(path)

def render_real(scene,ids,a,s,reg,center,h,results,roi,views):
    # Import only reviewed low-level helpers. Their modules perform no disk writes.
    sys.path.insert(0,str(RENDER_CODE))
    from format import read_ply,activate
    from renderer import render,join
    src=activate(read_ply(reg['model'])); line=activate(read_ply(BASE/'arms/C/scenes'/scene/'full/gaussians.ply'))
    if line['SH'].shape[-1]<src['SH'].shape[-1]: line['SH']=np.pad(line['SH'],((0,0),(0,0),(0,src['SH'].shape[-1]-line['SH'].shape[-1])))
    d=OUT/'real_budgeted'/scene; times=[]; bg=[1,1,1] if scene=='ficus' else [0,0,0]
    floor=np.r_[np.full(len(src['means']),.3 if scene=='ficus' else .12**2),np.full(len(line['means']),.12**2)]
    unchanged_mask=np.ones(len(line['means']),bool); unchanged_mask[ids]=False
    for view in views:
        guard(); c=next(c for c in reg['cameras'] if c['view']==view); items=[]; out=d/'figures'/view; out.mkdir(parents=True,exist_ok=True)
        for name,result in [('C8_original',None),*results.items()]:
            ln={k:v.copy() for k,v in line.items()}
            if result is not None:
                changed=np.linalg.norm(result['xyz']-(a['means'][ids]-center)/h,axis=1)>1e-10
                jj=ids[changed]; ln['means'][jj]=result['xyz'][changed]*h+center
                t=result['tangent'][changed]; p=s['pixel'][jj]
                ln['covariance'][jj]=(.38*p[:,None,None])**2*np.eye(3)+((.75*p)**2-(.38*p)**2)[:,None,None]*t[:,:,None]*t[:,None,:]
                for key in ['opacity','SH']: assert np.array_equal(ln[key],line[key])
                for key in ln: assert np.array_equal(ln[key][unchanged_mask],line[key][unchanged_mask])
                np.savez_compressed(d/name/'changed_line_geometry_world.npz',line_gaussian_id=jj,means=ln['means'][jj],covariance=ln['covariance'][jj]) if view==views[0] else None
            start=time.monotonic(); image=render(join(src,ln),c,bg,floor)['rgb']; elapsed=time.monotonic()-start
            im=image_array(image); im.save(out/(name+'_JOINT.png')); items.append((name+' | joint source occlusion',im)); times.append(dict(view=view,method=name,seconds=elapsed))
        board(out/'COMPARISON_FULL.jpg',items,f'{scene} / {view} | Fixed C8 input, finite-support refinement','Same source, camera, opacity and width. No new gaps confirmed or rendered.',roi if view==views[0] else None)
        if view==views[0]: board(out/'COMPARISON_ROI.png',[(lab,im.crop(tuple(roi))) for lab,im in items],f'{scene} | Fixed BUILD ROI','Actual joint render crops; no RGB-times-ink overlay.')
        # Group/candidate diagnostics stay visibly separate from final joint images.
        original=items[0][1]; hr=results['H1']; uv,z=project(a['means'][ids],c); diag=original.copy(); dr=ImageDraw.Draw(diag)
        palette=[(230,50,50),(0,190,230),(235,170,0),(190,70,240),(50,210,80)]
        for i,g in enumerate(hr['groups']):
            if g>=0 and z[i]>.2 and np.isfinite(uv[i]).all():
                xx,yy=uv[i]; dr.ellipse((xx-1,yy-1,xx+1,yy+1),fill=palette[g%len(palette)])
        neg=original.copy(); dn=ImageDraw.Draw(neg)
        for p in hr['links']:
            v,zz=project(np.asarray(p['endpoints'])*h+center,c)
            if (zz>.2).all(): dn.line([tuple(v[0]),tuple(v[1])],fill=(255,0,180),width=2)
        board(out/'GROUPS_AND_UNCONFIRMED.jpg',[("Original C8 | joint render",original),("H1 groups | X-RAY DIAGNOSTIC",diag),("Unconfirmed gaps | NOT rendered",neg)],f'{scene} / {view} | Groups and negative connection evidence','Colored projections can be hidden in 3D: diagnostics only. UNKNOWN evidence => no connection.')
        np.savez_compressed(out/'joint_difference.npz',H1_minus_original=np.asarray(items[-1][1],dtype=np.int16)-np.asarray(original,dtype=np.int16))
        js(d/'render_runtime.json',times); status('REAL_VIEW_RENDERED',scene=scene,view=view)

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--scene',default='scan24');args=p.parse_args();scene=args.scene
    if scene=='scan24': roi=CFG['scan24_roi'];view='0000';views=CFG['scan24_views']
    elif scene=='scan65': roi=[20,50,420,340];view='0000';views=['0000','0036']
    else: roi=[280,180,520,410];view='train_r_7';views=['train_r_7','test_r_14']
    guard(); status('REAL_RUNNING',scene=scene)
    data,ids,a,s,reg,center,h=prepare_real(scene,roi,view); results={}; rows=[]
    for method in CFG['methods']:
        guard(); result=run_backend(data,method,0);results[method]=result;rows.append(result['stats']);save_result(OUT/'real_budgeted'/scene/method,result);status('REAL_METHOD_DONE',scene=scene,**result['stats'])
    js(OUT/'real_budgeted'/scene/'metrics.json',rows)
    render_real(scene,ids,a,s,reg,center,h,results,roi,views)
    # Five paired seeds use exactly the same frozen real input. Deterministic methods
    # are rerun, not claimed to be independent realizations of scene evidence.
    for seed in CFG['seeds'][1:]:
        for method in CFG['methods']:
            guard(); result=run_backend(data,method,seed); save_result(OUT/'real_budgeted'/scene/'paired'/f'seed_{seed}'/method,result); rows.append(result['stats'])
        js(OUT/'real_budgeted'/scene/'metrics.json',rows);status('REAL_PAIRED_SEED_DONE',scene=scene,seed=seed)
    status('REAL_DONE',scene=scene)
if __name__=='__main__': main()
