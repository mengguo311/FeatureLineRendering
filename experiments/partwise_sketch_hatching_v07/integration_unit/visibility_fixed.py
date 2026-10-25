"""Fixed-path comparison: owner-plane fragments versus visible centerline cells.

The candidate keeps the owner-plane depth ONLY as a one-sided foreground guard.
It never expands the .004 tolerance, changes paths, fills region holes, or joins
distinct strokes. Exact subpixel proxy rays are an implementation reference, not
independent physical surface truth. Both arms use the same 2x sample grid.
"""
import runtime
import numpy as np
from geometry import project,ray_surface
from hatching import layer_ids,visibility_masks

TOLERANCE=.004
STEP_PIXELS=.25


def cast_points(mesh,camera,uv):
    import open3d as o3d
    E=np.asarray(camera['extrinsic']);inv=np.linalg.inv(E[:3,:3])
    local=np.column_stack(((uv[:,0]-camera['cx'])/camera['fx'],
                          (uv[:,1]-camera['cy'])/camera['fy'],np.ones(len(uv))))
    direction=local@inv.T;origin=-inv@E[:3,3]
    rays=np.column_stack((np.broadcast_to(origin,direction.shape),direction)).astype(np.float32)
    scene=o3d.t.geometry.RaycastingScene(nthreads=1)
    scene.add_triangles(o3d.core.Tensor(mesh['vertices'].astype(np.float32)),
                        o3d.core.Tensor(mesh['faces'].astype(np.uint32)))
    hit=scene.cast_rays(o3d.core.Tensor(rays),nthreads=1)
    depth=hit['t_hit'].numpy();face=hit['primitive_ids'].numpy().astype(np.int64)
    face[~np.isfinite(depth)]=-1
    regions=np.zeros(len(face),np.int32);good=face>=0;regions[good]=mesh['regions'][face[good]]
    return depth,face,regions


def endpoint_records(mesh,paths):
    """Classify stored endpoints; internal-face ends are intentional length cuts.

    This interpretation applies to the frozen generate_region asset; exact
    missing gap geometry is not inferred. Shared-edge ambiguity remains explicit.
    """
    edges={}
    for i,f in enumerate(mesh['faces']):
        for j,k in ((0,1),(1,2),(2,0)):edges.setdefault(tuple(sorted((int(f[j]),int(f[k])))),[]).append(i)
    result=[]
    for sid in np.unique(paths['stroke_id']):
        ix=np.flatnonzero(paths['stroke_id']==sid);labels=[]
        for idx,end in ((ix[0],0),(ix[-1],1)):
            if 'bary' not in paths:labels.append('fixture_endpoint');continue
            b=paths['bary'][idx,end];f=int(paths['face'][idx]);zero=np.flatnonzero(np.abs(b)<1e-7)
            if len(zero)==0:labels.append('planned_length_cut_in_face');continue
            if len(zero)!=1:labels.append('vertex_or_ambiguous');continue
            v=mesh['faces'][f][np.arange(3)!=zero[0]];adj=edges[tuple(sorted(map(int,v)))]
            if len(adj)==1:labels.append('mesh_boundary');continue
            if len(adj)!=2:labels.append('nonmanifold_edge');continue
            other=adj[0] if adj[1]==f else adj[1]
            labels.append('authored_region_boundary' if mesh['regions'][other]!=4 else 'shared_edge_unclassified')
        result.append(dict(stroke_id=int(sid),layer=int(layer_ids(paths)[ix[0]]),segments=len(ix),
            world_length=float(np.linalg.norm(paths['points'][ix,1]-paths['points'][ix,0],axis=1).sum()),
            stored_internal_discontinuities=int((np.linalg.norm(paths['points'][ix[:-1],1]-paths['points'][ix[1:],0],axis=1)>1e-8).sum()),
            start_class=labels[0],end_class=labels[1]))
    return result


def compare_visibility(mesh,paths,styles,camera,supersample=2,occluder=None):
    depth,face_image,regions,c=ray_surface(mesh if occluder is None else occluder,camera,supersample)
    size=c['width'];scale=supersample;strength=styles['4'].get('ink_strength',.8)
    layers=layer_ids(paths);supports=visibility_masks(paths,4)
    E=np.asarray(c['extrinsic']);R=E[:3,:3]
    nc=mesh['normals']@np.linalg.inv(R);pc=mesh['tri'][:,0]@R.T+E[:3,3]
    plane=np.einsum('ij,ij->i',nc,pc)
    bit_image=np.left_shift(np.uint64(1),regions.astype(np.uint64))
    projected=[];uvs=[];zs=[];indices=[];weights=[];offsets=[0]
    for i,points in enumerate(paths['points']):
        uv,z=project(points,camera);length=float(np.linalg.norm(uv[1]-uv[0]))
        n=max(1,int(np.ceil(length/STEP_PIXELS))) if (z>.2).all() else 1
        t=(np.arange(n)+.5)/n
        uvs.append(uv[0]+t[:,None]*(uv[1]-uv[0]));zs.append(1/((1-t)/z[0]+t/z[1]))
        indices.append(np.full(n,i,np.int32));weights.append(np.full(n,length/n))
        projected.append((uv,z,n));offsets.append(offsets[-1]+n)
    uv=np.concatenate(uvs);zz_center=np.concatenate(zs);seg=np.concatenate(indices);w=np.concatenate(weights)
    hit_z,hit_face,hit_region=cast_points(mesh if occluder is None else occluder,camera,uv)
    in_frame=(uv[:,0]>=0)&(uv[:,1]>=0)&(uv[:,0]<camera['width'])&(uv[:,1]<camera['height'])
    status=np.zeros(len(uv),np.uint8)
    status[~in_frame|~np.isfinite(hit_z)]=1
    rg=np.left_shift(np.uint64(1),hit_region.astype(np.uint64))
    status[(status==0)&((rg&supports[seg])==0)]=2
    status[(status==0)&(np.abs(zz_center-hit_z)>TOLERANCE)]=3
    status[zz_center<=.2]=4
    cov={a:{int(l):np.zeros((size,size),bool) for l in np.unique(layers)} for a in ('legacy','interval')}
    tiles={};counts={a:0 for a in cov};covered_count=region_count=foreground_count=0
    for sid in np.unique(paths['stroke_id']):
        ix=np.flatnonzero(paths['stroke_id']==sid)
        alluv=np.concatenate([projected[i][0] for i in ix]);rad=styles['4']['width']/2+1
        lo=np.maximum(0,np.floor(alluv.min(0)-rad)).astype(int)
        hi=np.minimum(camera['width']-1,np.ceil(alluv.max(0)+rad)).astype(int)
        if (hi>=lo).all():tiles[int(sid)]=(lo*scale,hi*scale+scale-1,{a:np.zeros(((hi[1]-lo[1]+1)*scale,(hi[0]-lo[0]+1)*scale),bool) for a in cov})
    for i,(points,face,layer,support) in enumerate(zip(paths['points'],paths['face'],layers,supports)):
        if layer==1 and not styles['4'].get('cross_enabled',False):continue
        up,z=project(points,c)
        if (z<=.2).any():continue
        d=up[1]-up[0];length2=float(d@d)
        if length2<1e-14:continue
        radius=styles['4']['width']*scale/2
        lo=np.maximum(0,np.ceil(up.min(0)-radius)).astype(int)
        hi=np.minimum(size-1,np.floor(up.max(0)+radius)).astype(int)
        if (hi<lo).any():continue
        yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        rawt=((xx-up[0,0])*d[0]+(yy-up[0,1])*d[1])/length2;t=np.clip(rawt,0,1)
        covered=(xx-up[0,0]-t*d[0])**2+(yy-up[0,1]-t*d[1])**2<=radius**2
        normal=nc[face];den=normal[0]*(xx-c['cx'])/c['fx']+normal[1]*(yy-c['cy'])/c['fy']+normal[2]
        zz=np.divide(plane[face],den,out=np.full_like(den,np.inf),where=np.abs(den)>1e-12)
        dd=depth[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        valid=np.isfinite(dd)&((bit_image[lo[1]:hi[1]+1,lo[0]:hi[0]+1]&support)!=0)
        diff=np.full_like(dd,np.inf);np.subtract(zz,dd,out=diff,where=np.isfinite(zz)&np.isfinite(dd))
        old=covered&valid&(np.abs(diff)<=TOLERANCE)
        good=status[offsets[i]:offsets[i+1]]==0;n=len(good)
        boundaries=np.diff(np.r_[False,good,False].astype(np.int8))
        starts=np.flatnonzero(boundaries==1)/n;ends=np.flatnonzero(boundaries==-1)/n
        candidate=np.zeros_like(covered)
        for start,end in zip(starts,ends):
            tt=np.clip(rawt,start,end)
            candidate|=(xx-up[0,0]-tt*d[0])**2+(yy-up[0,1]-tt*d[1])**2<=radius**2
        # Preserve true nearer surfaces, including same-region disconnected ones.
        new=candidate&valid&np.isfinite(zz)&(zz>.2)&(diff<=TOLERANCE)
        covered_count+=int(covered.sum());region_count+=int((covered&~valid).sum())
        foreground_count+=int((candidate&valid&(diff>TOLERANCE)).sum())
        for arm,mask in (('legacy',old),('interval',new)):
            cov[arm][int(layer)][lo[1]:hi[1]+1,lo[0]:hi[0]+1]|=mask;counts[arm]+=int(mask.sum())
            origin,_,tile=tiles[int(paths['stroke_id'][i])]
            tile[arm][lo[1]-origin[1]:hi[1]-origin[1]+1,lo[0]-origin[0]:hi[0]-origin[0]+1]|=mask
    low=lambda x:x.reshape(camera['height'],scale,camera['width'],scale).mean((1,3))
    ink={a:low(np.maximum.reduce(list(cov[a].values())).astype(np.float32)*strength) for a in cov}
    sample_alpha={a:np.zeros(len(uv),np.float32) for a in cov}
    xy=np.rint(uv).astype(int)
    for sid,(origin,_,tile) in tiles.items():
        select=np.flatnonzero(paths['stroke_id'][seg]==sid);relative=xy[select]-origin//scale
        for arm,mask in tile.items():
            h,w0=mask.shape;small=mask.astype(np.float32).reshape(h//scale,scale,w0//scale,scale).mean((1,3))*strength
            inside=(relative[:,0]>=0)&(relative[:,1]>=0)&(relative[:,0]<small.shape[1])&(relative[:,1]<small.shape[0])
            sample_alpha[arm][select[inside]]=small[relative[inside,1],relative[inside,0]]
    samples=dict(uv=uv,segment_index=seg,stroke_id=paths['stroke_id'][seg],layer_id=layers[seg],
        length_weight=w,status=status,center_depth=zz_center,hit_depth=hit_z,hit_face=hit_face,
        legacy_alpha=sample_alpha['legacy'],interval_alpha=sample_alpha['interval'])
    return dict(coverage=cov,ink=ink,samples=samples,
        regions=regions[scale//2::scale,scale//2::scale].copy(),depth=depth[scale//2::scale,scale//2::scale].copy(),
        diagnostics=dict(covered_fragments=covered_count,region_or_no_surface_rejected_fragments=region_count,
            accepted_fragments=counts,interval_foreground_rejected_fragments=foreground_count,
            center_samples=len(uv),status_definition={'0':'visible','1':'outside_or_no_surface','2':'region_rejected','3':'depth_rejected','4':'near_plane'}))


def sample_support(samples,support):
    xy=np.rint(samples['uv']).astype(int);valid=(xy[:,0]>=0)&(xy[:,1]>=0)&(xy[:,0]<support.shape[1])&(xy[:,1]<support.shape[0])
    out=np.zeros(len(xy),np.float32);out[valid]=support[xy[valid,1],xy[valid,0]]
    return out


def stroke_readback(samples,support,scales):
    s=sample_support(samples,support);visible=samples['status']==0;w=samples['length_weight'];rows=[]
    for sid in np.unique(samples['stroke_id']):
        ix=np.flatnonzero(samples['stroke_id']==sid);row=dict(stroke_id=int(sid),layer=int(samples['layer_id'][ix[0]]),
            projected_length=float(w[ix].sum()),proxy_visible_length=float(w[ix][visible[ix]].sum()),
            rejected_length={str(k):float(w[ix][samples['status'][ix]==k].sum()) for k in (1,2,3,4)})
        for arm in ('legacy','interval'):
            raw=samples[arm+'_alpha'][ix];q=visible[ix];ww=w[ix]
            for mode,alpha in (('before_S',raw),('raw',raw*s[ix]),('matched',raw*s[ix]*scales[arm])):
                hit=alpha>.05;missing=q&~hit
                # Counts are image-sampling diagnostics; starts after actual
                # proxy visibility breaks are not classified as unplanned gaps.
                enclosed=(~hit[1:-1])&q[1:-1]&q[:-2]&q[2:]
                row[arm+'_'+mode]=dict(visible_supported_length=float(ww[q&hit].sum()),
                    visible_missing_length=float(ww[missing].sum()),
                    occluded_supported_length=float(ww[(~q)&hit].sum()),
                    missing_runs=int(np.count_nonzero(np.diff(np.r_[False,missing,False].astype(np.int8))==1)),
                    interior_missing_samples=int(enclosed.sum()))
        rows.append(row)
    return rows
