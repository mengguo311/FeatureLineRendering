"""Fixed original-kernel-anchored edge occupancy. This is neither SDF nor surface GT."""
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes
def rotations(q):
 q=np.asarray(q,dtype=np.float64);q=q/np.linalg.norm(q,axis=1,keepdims=True);w,x,y,z=q.T
 return np.stack([1-2*(y*y+z*z),2*(x*y-w*z),2*(x*z+w*y),2*(x*y+w*z),1-2*(x*x+z*z),2*(y*z-w*x),2*(x*z-w*y),2*(y*z+w*x),1-2*(x*x+y*y)],1).reshape(-1,3,3)
def project(x,c):
 m=np.asarray(c['w2c']);p=x@m[:3,:3].T+m[:3,3];f=np.array([c['width']/(2*np.tan(c['FoVx']/2)),c['height']/(2*np.tan(c['FoVy']/2))]);uv=p[:,:2]/p[:,2:3]*f+[(c['width']-1)/2,(c['height']-1)/2];return uv,p[:,2]
def build_region(model,ids,stats,width,cameras,evidences,grid_resolution=224):
 ids=np.asarray(ids,dtype=np.int64);xyz=np.asarray(model['xyz']);pts=xyz[ids];score=stats['score'][ids]
 good=score>.100001;ids=ids[good];pts=pts[good];score=score[good]
 if not len(ids):raise ValueError('no anchored occupancy support')
 lo=pts.min(0);hi=pts.max(0);diag=float(np.linalg.norm(hi-lo));spacing=diag/grid_resolution
 margin=max(.04*diag,4*spacing);origin=lo-margin;shape=np.ceil((hi-lo+2*margin)/spacing).astype(int)+1
 field=np.zeros(tuple(shape),np.float32);owner=np.full(tuple(shape),-1,np.int32);overlap_pairs=[]
 rot=rotations(model['rotations'][ids]);native_scales=np.asarray(model['scales'])[ids]
 # Full covariance orientation kept as support, not inferred edge tangent. Fixed world floor.
 sigma=np.sqrt((1.25*native_scales)**2+(width*spacing)**2)
 qlimit=2*np.log(score/.1);extent_sigma=np.sqrt(qlimit)
 max_axis=.025*diag;axes=np.minimum(sigma*extent_sigma[:,None],max_axis)
 axes=np.maximum(axes,.55*spacing);inv=np.einsum('nij,nj,nkj->nik',rot,1/axes**2,rot)
 bounds=np.sqrt(np.einsum('nij,nj,nij->ni',rot,axes**2,rot))
 for j,(p,b) in enumerate(zip(pts,bounds)):
  low=np.maximum(np.floor((p-b-origin)/spacing).astype(int),0);high=np.minimum(np.ceil((p+b-origin)/spacing).astype(int)+1,shape)
  if np.any(high<=low):continue
  sl=tuple(slice(int(a),int(b)) for a,b in zip(low,high));g=np.stack(np.meshgrid(*[np.arange(a,b) for a,b in zip(low,high)],indexing='ij'),-1)
  delta=origin+g*spacing-p;q=np.einsum('...i,ij,...j->...',delta,inv[j],delta)
  # Scaled level field has identical q=1 boundary; score retained in ownership tie-break.
  val=np.where(q<=1,1+score[j]*(1-q),0).astype(np.float32);f=field[sl]
  witnesses=np.unique(owner[sl][(val>0)&(owner[sl]>=0)])
  if len(witnesses):overlap_pairs.append(np.column_stack([np.full(len(witnesses),ids[j]),witnesses]))
  take=val>f;f[take]=val[take];owner[sl][take]=ids[j]
 raw=field>0
 closed=ndi.binary_closing(raw,structure=ndi.generate_binary_structure(3,1))|raw
 additions=np.argwhere(closed&~raw);reject=np.zeros(closed.shape,bool)
 witness_offsets=[0];witness_ids=[];fill_pairs=[]
 for a in additions:
  sl=tuple(slice(max(0,int(t)-1),min(int(n),int(t)+2)) for t,n in zip(a,shape));w=np.unique(owner[sl]);w=w[w>=0];witness_ids.extend(w.tolist());witness_offsets.append(len(witness_ids))
  if len(w)>1:fill_pairs.extend((int(w[0]),int(v)) for v in w[1:])
 active=np.argwhere(closed);points=origin+active*spacing
 rejected_view=np.full(len(active),-1,np.int16)
 for k,(c,e) in enumerate(zip(cameras,evidences)):
  uv,z=project(points,c);u=np.rint(uv[:,0]).astype(int);v=np.rint(uv[:,1]).astype(int);inside=(z>.2)&(u>=0)&(u<c['width'])&(v>=0)&(v<c['height'])
  valid=ndi.binary_dilation(e['foreground'],iterations=2);bad=np.zeros(len(active),bool);bad[inside]=~valid[v[inside],u[inside]]
  # Outside image / unseen direction is unknown, not a veto.
  rejected_view[(rejected_view<0)&bad]=k
 reject[tuple(active[rejected_view>=0].T)]=True;occupancy=closed&~reject
 labs,ncomp=ndi.label(occupancy,ndi.generate_binary_structure(3,1));sizes=np.bincount(labs.ravel())[1:]
 vertices,faces,_,_=marching_cubes(occupancy.astype(np.float32),.5,spacing=(spacing,)*3,allow_degenerate=False)
 vertices+=origin;tree=cKDTree(pts);nearest_distance,nearest=tree.query(vertices,workers=2)
 raw_retained=occupancy&(owner>=0);raw_positions=np.argwhere(raw_retained);raw_owner=owner[raw_retained]
 if not len(raw_positions):raise ValueError('no raw support survived construction constraints')
 _,witness=cKDTree(raw_positions).query((vertices-origin)/spacing,workers=2);anchor_ids=raw_owner[witness];anchor_local=np.searchsorted(ids,anchor_ids)
 distance=np.linalg.norm(vertices-xyz[anchor_ids],axis=1)
 addpoints=origin+additions*spacing
 if len(addpoints):
  dd,nn=tree.query(addpoints,k=min(2,len(ids)),workers=2);nn=np.asarray(nn).reshape(len(addpoints),-1);dd=np.asarray(dd).reshape(len(addpoints),-1)
  fill_ids=ids[nn];fill_direction=pts[nn[:,-1]]-pts[nn[:,0]]
 else:dd=np.empty((0,2));fill_ids=np.empty((0,2),np.int64);fill_direction=np.empty((0,3))
 # Adjacency is overlap of occupied support cells, not a tangent-consistency assertion.
 allpairs=overlap_pairs+[np.asarray(fill_pairs,dtype=np.int64).reshape(-1,2)]
 for axis in range(3):
  sa=[slice(None)]*3;sb=sa.copy();sa[axis]=slice(None,-1);sb[axis]=slice(1,None);a=owner[tuple(sa)];b=owner[tuple(sb)]
  both=occupancy[tuple(sa)]&occupancy[tuple(sb)]&(a>=0)&(b>=0)&(a!=b)
  pair=np.stack([a[both],b[both]],1);pair.sort(1);allpairs.append(pair)
 pairs=np.concatenate(allpairs);pairs.sort(1);pairs=np.unique(pairs,axis=0)
 local_delta=np.einsum('ni,nij->nj',vertices-pts[anchor_local],rot[anchor_local]);mahal=np.linalg.norm(local_delta/np.maximum(native_scales[anchor_local],1e-12),axis=1)
 return dict(vertices=vertices.astype(np.float32),faces=faces.astype(np.int32),vertex_anchor_ids=anchor_ids,vertex_nearest_center_ids=ids[nearest],vertex_displacement=distance.astype(np.float32),vertex_original_mahalanobis=mahal.astype(np.float32),support_ids=ids,retained_owner_ids=np.unique(raw_owner),support_axes=axes.astype(np.float32),native_scales=native_scales,grid_origin=origin,spacing=np.asarray(spacing),grid_shape=shape,component_count=int(ncomp),component_sizes=sizes,occupied_voxels=np.asarray(int(occupancy.sum())),raw_voxels=np.asarray(int(raw.sum())),fill_grid_indices=additions.astype(np.int32),fill_anchor_ids=fill_ids,fill_witness_offsets=np.asarray(witness_offsets,np.int64),fill_witness_ids=np.asarray(witness_ids,np.int64),fill_distances=dd.astype(np.float32),fill_direction=fill_direction.astype(np.float32),fill_rejected=reject[tuple(additions.T)] if len(additions) else np.empty(0,bool),rejected_grid_indices=active[rejected_view>=0].astype(np.int32),rejected_first_view=rejected_view[rejected_view>=0],merge_ids=pairs,merge_distance=np.linalg.norm(xyz[pairs[:,1]]-xyz[pairs[:,0]],axis=1).astype(np.float32),merge_direction=(xyz[pairs[:,1]]-xyz[pairs[:,0]]).astype(np.float32),width_world_floor=np.asarray(width*spacing),representation=np.asarray('fixed original Gaussian anchored edge occupancy; not SDF'))
