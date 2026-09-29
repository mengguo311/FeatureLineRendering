"""Native800 evaluation of sealed world geometry; no fitting or snapping."""
import numpy as np
import torch
import cv2
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from src.direct_curve import bezier,project,visibility


def evaluate_drawing(control,active,camera,maps,target,diagonal):
    p=torch.tensor(control,dtype=torch.float64);xyz=bezier(p,257)
    uv,z=project(xyz,torch.tensor(camera['native_K'],dtype=p.dtype),torch.tensor(camera['w2c'],dtype=p.dtype))
    _,_,state=visibility(uv,z,torch.tensor(maps.transpose(2,0,1)[None],dtype=p.dtype),diagonal)
    xy=uv.numpy();state=state.numpy();state[~active]=4
    deriv=np.gradient(xy,axis=1);weight=np.linalg.norm(deriv,axis=-1);weight[:,[0,-1]]*=.5
    tangent=deriv/np.maximum(np.linalg.norm(deriv,axis=-1,keepdims=True),1e-20)
    flat=xy.reshape(-1,2);t=tangent.reshape(-1,2);w=weight.ravel();s=state.ravel();ids=np.repeat(np.arange(len(p)),257)
    visible=(s==0)|(s==1);known=s==0;uv_valid=np.isfinite(flat).all(1)
    distance=np.full(len(flat),np.inf);near=np.full(len(flat),-1,int);angle=np.full(len(flat),90.)
    if len(target['xy']):
        distance[uv_valid],near[uv_valid]=cKDTree(target['xy']).query(flat[uv_valid])
        tt=target['tangent'][near[uv_valid]];dot=np.abs((tt*t[uv_valid]).sum(1));angle[uv_valid]=np.degrees(np.arccos(np.clip(dot,0,1)));angle[~np.isfinite(angle)]=90
    good=known&(distance<=2)&(angle<=20)
    covered=np.zeros(len(target['xy']),bool);assigned=np.full(len(target['xy']),-1,int)
    # Complete target allocation, re-evaluated from fixed current projection.
    ki=np.flatnonzero(known&uv_valid)
    if len(ki) and len(covered):
        neighborhoods=cKDTree(flat[ki]).query_ball_point(target['xy'],2.)
        for j,candidates in enumerate(neighborhoods):
            if not candidates or not np.isfinite(target['tangent'][j]).all():continue
            ii=ki[candidates];dot=np.abs(t[ii]@target['tangent'][j]);matches=ii[dot>=np.cos(np.radians(20))]
            if len(matches):covered[j]=True;assigned[j]=ids[matches[np.argmin(np.linalg.norm(flat[matches]-target['xy'][j],axis=1))]]
    ink=stroke_ink(xy,visible.reshape(state.shape),active)
    idmap=np.full((800,800),-1,'i2')
    for c in np.flatnonzero(active):
        for j in range(256):
            if visible[c*257+j] and visible[c*257+j+1]:
                aa,bb=np.rint(xy[c,j:j+2]).astype(int);cv2.line(idmap,tuple(aa),tuple(bb),int(c),2,cv2.LINE_8)
    image=np.repeat(np.round((1-ink)*255).astype('u1')[:,:,None],3,axis=2)
    roi=maps[:,:,0]>=.5;outline=(ndi.distance_transform_edt(roi)<=4)&roi | ((ndi.distance_transform_edt(~roi)<=4)&~roi)
    strata=np.where(outline,1,np.where(roi,2,0)).astype('u1')
    pixels=np.rint(flat).astype(int).clip(0,799);sample_strata=strata[pixels[:,1],pixels[:,0]]
    tx=np.rint(target['xy']).astype(int).clip(0,799);target_strata=strata[tx[:,1],tx[:,0]]
    def summary(sm,tm):
        vl=float(w[sm&visible].sum());kl=float(w[sm&known].sum());supported=float(w[sm&good].sum());nt=int(tm.sum())
        return dict(targets=nt,covered=int(covered[tm].sum()),coverage=float(covered[tm].mean()) if nt else None,visible_length=vl,evaluable_length=kl,supported_length=supported,unsupported_length=vl-supported,unsupported_fraction=(vl-supported)/vl if vl else None,precision=supported/kl if kl else None,beyond4_length=float(w[sm&visible&(distance>4)].sum()),beyond4_fraction=float(w[sm&visible&(distance>4)].sum()/vl) if vl else None,unknown_length=float(w[sm&(s==1)].sum()),occluded_length=float(w[sm&(s==2)].sum()),unknown_targets=int((tm&~np.isfinite(target['tangent']).all(1)).sum()))
    metrics=summary(np.ones(len(flat),bool),np.ones(len(covered),bool));metrics.update(actual_ink=float(ink.sum()),active_curves=int(np.sum(active)))
    metrics['strata']={name:summary(sample_strata==code,target_strata==code) for name,code in [('background',0),('outline',1),('interior',2)]}
    metrics['strata']['foreground']=summary(roi[pixels[:,1],pixels[:,0]],roi[tx[:,1],tx[:,0]])
    cells=[]
    sample_cell=(pixels[:,1]//100)*8+pixels[:,0]//100;target_cell=(tx[:,1]//100)*8+tx[:,0]//100
    for cell in range(64):
        row,col=divmod(cell,8);sl=np.s_[row*100:(row+1)*100,col*100:(col+1)*100]
        record=dict(cell=cell,row=row,column=col,active_curves=int(len(np.unique(ids[(sample_cell==cell)&visible]))),actual_ink=float(ink[sl].sum()),**summary(sample_cell==cell,target_cell==cell))
        record['strata']={name:summary((sample_cell==cell)&(sample_strata==code),(target_cell==cell)&(target_strata==code)) for name,code in [('background',0),('outline',1),('interior',2)]}
        record['strata']['foreground']=summary((sample_cell==cell)&roi[pixels[:,1],pixels[:,0]],(target_cell==cell)&roi[tx[:,1],tx[:,0]]);cells.append(record)
    nonempty=[c['coverage'] for c in cells if c['targets']];metrics['equal_cell_coverage']=float(np.mean(nonempty)) if nonempty else None
    per_id=np.array([w[(ids==i)&visible].sum() for i in range(len(p))])
    double_pairs=set();doubling=np.zeros(len(flat),bool);vi=np.flatnonzero(visible&uv_valid)
    if len(vi)>1:
        tree=cKDTree(flat[vi])
        for start in range(0,len(vi),64):
            indices=vi[start:start+64]
            neighborhoods=tree.query_ball_point(flat[indices],2.)
            for a,neighbors in zip(indices,neighborhoods):
                b=vi[neighbors]
                match=(ids[a]!=ids[b])&(abs(t[b]@t[a])>=np.cos(np.radians(20)))
                doubling[a]=bool(match.any())
                double_pairs.update(tuple(sorted((int(ids[a]),int(other)))) for other in np.unique(ids[b[match]]))
    metrics['doubling_length']=float(w[doubling].sum());metrics['doubling_pairs']=len(double_pairs);metrics['doubling_samples']=int(doubling.sum())
    detached=(visible&(distance>4)).reshape(state.shape);metrics['detachment_samples']=int(detached.sum());metrics['detachment_runs']=int(np.sum(np.diff(detached.astype(int),axis=1,prepend=0)==1))
    return dict(image=image,metrics=metrics,cells=cells,arrays=dict(xyz=xyz.numpy(),xy=xy,state=state,weights=weight,visible_ids=np.unique(ids[visible]),idmap=idmap,target_covered=covered,target_assignment=assigned,distance=distance,angle=angle,per_id_visible_length=per_id,ink=ink.astype('f4'),target_strata=target_strata))


def disagreement(a,b):
    a=np.asarray(a)>0.1;b=np.asarray(b)>0.1
    if not a.any() and not b.any():return 0.
    da=ndi.distance_transform_edt(~a) if a.any() else np.full(a.shape,np.inf)
    db=ndi.distance_transform_edt(~b) if b.any() else np.full(b.shape,np.inf)
    return float((np.sum(a&(db>2))+np.sum(b&(da>2)))/max(1,a.sum()+b.sum()))


def ambiguity_from_pairs(full_data,chosen,loo_data,common,pairs):
    from itertools import combinations
    best=min(full_data.values())
    equal=sorted(k for k,v in full_data.items() if v<=best+max(.01,.01*best))
    equal_loo=sorted(k for k,v in loo_data.items() if common is not None and abs(v-common)<=max(.01,.01*common))
    groups=[equal,sorted([chosen]+equal_loo)]
    differences={'|'.join(pair):pairs['|'.join(pair)] for group in groups for pair in combinations(group,2)}
    return dict(equally_good=equal,loo_equally_good=equal_loo,common_view_primary_data=common,reserved_disagreement=differences,failed=any(v>.2 for v in differences.values()),unique_geometry_claim=False)


def temporal(frames):
    rows=[]
    for n,(a,b) in enumerate(zip(frames[:-1],frames[1:])):
        x=a['per_id_visible_length'];y=b['per_id_visible_length'];change=abs(y-x)/np.maximum(np.maximum(x,y),1.)
        rows.append(dict(frame=n+1,popping_count=int(np.sum(change>.25)),max_relative_length_change=float(change.max(initial=0)),ink_length_change=float(abs(y.sum()-x.sum()))))
    return dict(popping_count=sum(r['popping_count'] for r in rows),transitions=rows,frame_count=len(frames))


def scene_gate(arms,ambiguity,visual,budget):
    d,i,l=[arms[k] for k in ['D','I','L']]
    def val(a,k,default=0.):return a[k] if a.get(k) is not None else default
    precision=(val(i,'precision')>=.9 and val(i,'beyond4_fraction',1.)<=.05 and val(i,'actual_ink')>0)
    retain=all(val(i,k)>=.9*val(d,k) for k in ['interior_coverage','outline_coverage'])
    extra=val(i,'interior_coverage')-val(d,'interior_coverage')>=.1-1e-12 and val(i,'unsupported_fraction',1.)<=val(d,'unsupported_fraction',1.) and val(i,'improved_cell_fraction')>=.5
    coupling=val(i,'coverage')>val(l,'coverage') and val(i,'unsupported_fraction',1.)<=val(l,'unsupported_fraction',1.)
    result=dict(precision=precision,retain_depth=retain,extra_rgb=extra,global_coupling=coupling,unambiguous=not ambiguity,visual=visual,budget=budget)
    result['continue']=all(result.values());return result


def motion_defects(previous,current,maps,previous_camera,current_camera):
    """Shared renderer-depth advection proxy for both persistent and 2D ink.

    This is not optical flow ground truth, and can be biased by GS depth error.
    """
    y,x=np.nonzero(previous>.1);z=maps[y,x,2];known=(maps[y,x,0]>=.5)&(z>0)
    uv=np.c_[x[known],y[known],np.ones(known.sum())];K=np.asarray(previous_camera['native_K']);pose=np.linalg.inv(previous_camera['w2c'])
    world=(uv@np.linalg.inv(K).T*z[known,None])@pose[:3,:3].T+pose[:3,3]
    w=np.asarray(current_camera['w2c']);q=world@w[:3,:3].T+w[:3,3];h=q@np.asarray(current_camera['native_K']).T
    pp=np.rint(h[:,:2]/np.maximum(h[:,2:],1e-6)).astype(int);inside=(q[:,2]>0)&(pp[:,0]>=0)&(pp[:,0]<800)&(pp[:,1]>=0)&(pp[:,1]<800)
    warped=np.zeros((800,800),bool);warped[pp[inside,1],pp[inside,0]]=True;now=current>.1
    dw=ndi.distance_transform_edt(~warped) if warped.any() else np.full(warped.shape,np.inf)
    dn=ndi.distance_transform_edt(~now) if now.any() else np.full(now.shape,np.inf)
    appearing=now&(dw>4);disappearing=warped&(dn>4);labels,n=ndi.label(appearing,np.ones((3,3)));sizes=np.bincount(labels.ravel())[1:]
    return dict(popping_components=int(np.sum(sizes>=4)),appearing_pixels=int(appearing.sum()),disappearing_pixels=int(disappearing.sum()),unknown_previous_pixels=int((~known).sum()),previous_ink=float(previous.sum()),current_ink=float(current.sum()),motion_disagreement=float((appearing.sum()+disappearing.sum())/max(1,now.sum()+warped.sum())))


def stroke_ink(xy,visible,active):
    """Fixed 1.5 native-pixel stroke, analytic distance-based antialiasing."""
    ink=np.zeros((800,800),'f4')
    for c in np.flatnonzero(active):
        for j in range(xy.shape[1]-1):
            if not (visible[c,j] and visible[c,j+1]):continue
            a,b=xy[c,j:j+2];low=np.maximum(np.floor(np.minimum(a,b)-1.25).astype(int),0);high=np.minimum(np.ceil(np.maximum(a,b)+1.25).astype(int),799)
            if np.any(high<low):continue
            yy,xx=np.mgrid[low[1]:high[1]+1,low[0]:high[0]+1];q=np.stack([xx,yy],-1)
            d=b-a;fraction=np.clip(np.sum((q-a)*d,axis=-1)/max(float(d@d),1e-20),0,1)
            distance=np.linalg.norm(q-(a+fraction[...,None]*d),axis=-1)
            coverage=np.clip(1.25-distance,0,1).astype('f4');region=ink[low[1]:high[1]+1,low[0]:high[0]+1]
            np.maximum(region,coverage,out=region)
    return ink
