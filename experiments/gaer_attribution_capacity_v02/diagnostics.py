"""Sparse full-record diagnostics and frozen ROI score groups, original IDs only."""
import numpy as np
import torch
from scipy.sparse import csr_matrix,coo_matrix
from runtime import *
from operators import raw_forward

def normal_points(a,points):
 p=np.asarray(points,float);n=a['normal_xy'][p[:,0].astype(int),p[:,1].astype(int)].astype(float);norm=np.linalg.norm(n,axis=1);conf=a['confidence'][p[:,0].astype(int),p[:,1].astype(int)]
 ok=np.isfinite(norm)&(norm>1e-8)&(conf>=.22);n=np.nan_to_num(n)/np.maximum(np.nan_to_num(norm),1e-8)[:,None];n[norm<=1e-8]=[1,0]
 return n[:,::-1],ok

def neighbours(points):
 p=np.asarray(points);base=np.floor(p).astype(int);f=p-base;coords=[];rows=[];values=[]
 for dy,dx,b in ((0,0,(1-f[:,0])*(1-f[:,1])),(0,1,(1-f[:,0])*f[:,1]),(1,0,f[:,0]*(1-f[:,1])),(1,1,f[:,0]*f[:,1])):
  good=b>0;coords.extend((base[good]+[dy,dx]).tolist());rows.extend(np.flatnonzero(good).tolist());values.extend(b[good].tolist())
 return np.asarray(coords,np.int32),np.asarray(rows),np.asarray(values)
def row_sample(query_pixels,points):
 coords,rows,values=neighbours(points);lookup={tuple(p):i for i,p in enumerate(query_pixels)};cols=np.array([lookup[tuple(p)] for p in coords]);return coo_matrix((values,(rows,cols)),shape=(len(points),len(query_pixels))).tocsr()
def maxrows(c):
 ids=np.full(c.shape[0],-1,np.int32);vals=np.zeros(c.shape[0]);second=np.zeros(c.shape[0])
 for j in range(c.shape[0]):
  lo,hi=c.indptr[j:j+2]
  if lo<hi:
   v=c.data[lo:hi];i=c.indices[lo:hi];order=np.lexsort((i,-v));ids[j]=i[order[0]];vals[j]=v[order[0]];second[j]=v[order[1]] if len(order)>1 else 0
 return ids,vals,vals-second

def analyze_view(scene,key,module,s,model,a,rois,query,config):
 points=np.array([p for r in rois for p in r['sample_points_yx']],np.int32);n,ok=normal_points(a,points);minus=points-2*n;plus=points+2*n
 profiles=[]
 for r in rois:
  center=np.array([r['center_yx']]);cn,_=normal_points(a,center);profiles.append(center+np.arange(-12,13)[:,None]*cn)
 allpoints=np.concatenate([points,minus,plus,*profiles]);pixels=np.unique(neighbours(allpoints)[0],axis=0)
 native=raw_forward(module,s,model);R,rgb,radii,geom,binning,img=native
 offsets,ids,weights,T=[t.cpu().numpy() for t in query.query(geom,binning,img,len(model['means3D']),R,800,800,torch.tensor(pixels,device='cuda',dtype=torch.int32))]
 xy,cov,conic,colors=[t.cpu().numpy() for t in query.geometry(geom,len(model['means3D']))];colors[radii.cpu().numpy()==0]=0
 full=csr_matrix((weights,ids,offsets),shape=(len(pixels),len(model['means3D'])));full.sum_duplicates();full.sort_indices()
 y,x=pixels.T;sumw=np.asarray(full.sum(1)).ravel();alphaerr=float(np.abs(sumw-a['alpha'][y,x]).max());recon=full@colors+T[:,None];rgberr=float(np.abs(recon-a['RGB'][y,x]).max())
 if alphaerr>config['full_replay_alpha_tolerance'] or rgberr>config['full_replay_RGB_tolerance']:raise RuntimeError(f'full replay invalid alpha={alphaerr} RGB={rgberr}')
 C=row_sample(pixels,points);M=row_sample(pixels,minus);P=row_sample(pixels,plus);results={};archives={};groups=[];nGauss=len(model['means3D'])
 for K in (8,16,32,'full'):
  if K=='full':records=full
  else:
   rr=[];cc=[];dd=[]
   for j in range(len(pixels)):
    lo,hi=offsets[j:j+2];order=np.argsort(-weights[lo:hi],kind='stable')[:K];rr.extend([j]*len(order));cc.extend(ids[lo:hi][order]);dd.extend(weights[lo:hi][order])
   records=coo_matrix((dd,(rr,cc)),shape=full.shape).tocsr()
  center=C@records;m=M@records;p=P@records;difference=(m-p).tocsr();difference.eliminate_zeros();visible=center.copy();visible.data[:]=1;D=abs(difference).multiply(visible).tocsr()
  cid,cmax,_=maxrows(center);did,dmax,margin=maxrows(D);residual=np.maximum(0,np.asarray((M+P)@sumw).ravel()-np.asarray((m+p).sum(1)).ravel());reason=np.zeros(len(points),np.uint8);reason[residual>dmax+2e-6]=3;reason[dmax<=2e-6]=2;reason[~ok]=1;reason[cid<0]=5;winner=np.where(reason==0,did,cid)
  results[str(K)]=dict(reason_counts={str(v):int((reason==v).sum()) for v in (0,1,2,3,5)},samples=len(points),winner_certified_margin_pixels=int(((margin>4e-6)&(reason==0)).sum()),mean_D_sum=float(np.asarray(D.sum(1)).mean()),residual_quantiles=np.quantile(residual,[0,.5,.9,1]).tolist(),D_sum_quantiles=np.quantile(np.asarray(D.sum(1)).ravel(),[0,.5,.9,1]).tolist())
  archives[f'K{K}_winner']=winner;archives[f'K{K}_reason']=reason;archives[f'K{K}_margin']=margin;archives[f'K{K}_D_sum']=np.asarray(D.sum(1)).ravel();archives[f'K{K}_residual']=residual
  if K=='full':fc=center;fd=difference;fD=D;fullwinner=winner;fullreason=reason
 for K in (8,16,32):
  results[str(K)].update(winner_change_to_full=int((archives[f'K{K}_winner']!=fullwinner).sum()),fallback_to_valid_full=int(((archives[f'K{K}_reason']!=0)&(fullreason==0)).sum()))
 delta_rgb=(M-P)@a['RGB'][y,x];delta_T=np.asarray((M-P)@T).ravel();fg=fd@colors;reconstructed=fg+delta_T[:,None];err=np.abs(delta_rgb-reconstructed)
 if float(err.max())>config['decomposition_tolerance']:raise RuntimeError('RGB signed decomposition invalid')
 # Per-ID signed RGB terms relative to white; equivalent to foreground+BG.
 rr,cc=fd.nonzero();vals=np.asarray(fd[rr,cc]).ravel();terms=(colors[cc]-1)*vals[:,None];delta_norm=np.linalg.norm(delta_rgb,axis=1);unit=delta_rgb/np.maximum(delta_norm[:,None],1e-12);aligned=np.sum(terms*unit[rr],1);color=coo_matrix((np.maximum(aligned,0),(rr,cc)),shape=fd.shape).tocsr().multiply((fc>0).astype(float)).tocsr()
 abs_color=np.zeros(len(points));np.add.at(abs_color,rr,np.linalg.norm(terms,axis=1));cancellation=1-delta_norm/np.maximum(abs_color,1e-20)
 for j,r in enumerate(rois):
  sl=slice(j*25,(j+1)*25);cs=np.asarray(fc[sl].sum(0)).ravel();ds=np.asarray(fD[sl].sum(0)).ravel();color_score=np.asarray(color[sl].sum(0)).ravel();one=np.bincount(fullwinner[sl][fullwinner[sl]>=0],minlength=nGauss).astype(float)
  scores={'center':cs,'oneD':one,'multiD':ds,'color_signed':color_score};group=dict(roi=j,category=r['category'],fragment=r['fragment'],center_yx=r['center_yx'],profiles_yx=profiles[j],normal_ok=int(ok[sl].sum()),scores=scores,selected={method:np.lexsort((np.arange(nGauss),-score))[:8].astype(np.int32) for method,score in scores.items()})
  groups.append(group)
  results.setdefault('roi',[]).append(dict(roi=j,category=r['category'],fragment=r['fragment'],marked_samples=int(a['line_binary'][points[sl,0],points[sl,1]].sum()),normal_ok=int(ok[sl].sum()),center_vs_fullD_different=int((archives['Kfull_winner'][sl]!=archives['K8_winner'][sl]).sum()),fullD_vs_center_different=int((fullwinner[sl]!=maxrows(fc[sl])[0]).sum()),rgb_delta_norm_mean=float(delta_norm[sl].mean()),sum_abs_contribution_D_mean=float(np.asarray(fD[sl].sum(1)).mean()),color_cancellation_mean=float(cancellation[sl].mean()),decomposition_max_abs=float(err[sl].max())))
 score_arrays={f'score_{method}':np.stack([g['scores'][method] for g in groups]) for method in ('center','oneD','multiD','color_signed')}
 dst=ART/'downloads'/scene/f'{key}_ROI_full_CSR.npz';npz(dst,**score_arrays,query_pixels_yx=pixels,accepted_offsets=offsets,accepted_original_ids=ids,accepted_weights=weights,final_T=T,sample_points_yx=points,normal_yx=n,normal_ok=ok,minus_yx=minus,plus_yx=plus,effective_SH3_colors=colors,projected_means_xy=xy,projected_conic_opacity=conic,original_cov3D=cov,delta_RGB=delta_rgb,foreground_color_delta=fg,background_delta_T=delta_T,cancellation=cancellation,**archives)
 results['groups']=[dict(roi=g['roi'],category=g['category'],fragment=g['fragment'],center_yx=g['center_yx'],profiles_yx=g['profiles_yx'].tolist(),normal_ok=g['normal_ok'],selected={k:v.tolist() for k,v in g['selected'].items()},multiD_top16=np.lexsort((np.arange(nGauss),-g['scores']['multiD']))[:16].tolist()) for g in groups]
 results.update(full_replay_alpha_max_abs=alphaerr,full_replay_RGB_max_abs=rgberr,decomposition_max_abs=float(err.max()),accepted_nnz=len(ids),query_pixels=len(pixels),H1='D is normal contribution variation, not causal RGB edge responsibility',files=[rel(dst)])
 return results,groups,(xy,conic,colors,cov)

def sample_image(image,points):
 # Image HWC or HW; all frozen profile points inside bounds.
 p=np.asarray(points);base=np.floor(p).astype(int);f=p-base;result=np.zeros((len(p),)+image.shape[2:])
 for dy,dx,b in ((0,0,(1-f[:,0])*(1-f[:,1])),(0,1,(1-f[:,0])*f[:,1]),(1,0,f[:,0]*(1-f[:,1])),(1,1,f[:,0]*f[:,1])):
  yy=base[:,0]+dy;xx=base[:,1]+dx;result+=image[yy,xx]*b.reshape((-1,)+(1,)*(image.ndim-2))
 return result
