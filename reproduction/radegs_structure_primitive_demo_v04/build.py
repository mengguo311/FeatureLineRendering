from common import *
from primitive import *
from skimage.morphology import skeletonize
from scipy.ndimage import distance_transform_edt,maximum_filter,minimum_filter

def prepare_scene(scene,dst,roi=False):
    dst.mkdir(parents=True,exist_ok=True);cs=demo.cameras(scene);aa={};ff={};segments=[];records=[];node_tokens={};summary={};offset=0
    replay=None
    if scene=='scan24' and not roi and (T/'geometry_replay/segments.pkl').exists():
        import pickle
        cp=T/'geometry_replay/segments.pkl';meta=json.loads((cp.parent/'CACHE_SEAL.json').read_text());assert sha(cp)==meta['sha256'];assert meta['source_freeze_sha256']==sha(T/'SOURCE_FREEZE.json');replay=pickle.loads(cp.read_bytes());assert len(replay)==76935
    for vi,v in enumerate(BUILD):
        a=demo.read(scene,v);f=demo.detect(a);aa[v]=a;ff[v]=f;c=cs[v];h,w=a['z'].shape
        y,x=np.nonzero(f['marked']);u=np.stack([x,y],1);n=len(x);z=a['z'][y,x];valid=np.isfinite(z)&(z>0)
        rr={'uv':u,'depth':z,'darkness':f['dark'][y,x],'confidence':f['confidence'][y,x],'alpha':a['alpha'][y,x],'source_view':np.full(n,vi,np.int8),'segment_id':np.full(n,-1,np.int32),'primitive_id':np.full(n,-1,np.int32),'arc':np.zeros(n,np.float32),'reason':np.where(valid,3,1).astype(np.int8)}
        domain=np.ones((h,w),bool)
        if roi:
            box=CFG['roi'] if v=='0000' else CFG['roi_windows'][v];domain[:]=False;domain[box[1]:box[3],box[0]:box[2]]=True
            rr['reason'][~domain[y,x]]=2
        mask=f['marked']&np.isfinite(a['z'])&(a['z']>0)&domain;sk=skeletonize(mask);paths=ordered_paths(sk)
        lookup=np.full((h,w),-1,np.int32);lookup[y,x]=np.arange(n)+offset
        smap=np.full((h,w),-1,np.int32);span=maximum_filter(a['z'],3)-minimum_filter(a['z'],3)
        def add(q):
            zz=a['z'][q[:,1],q[:,0]];p=float(np.median(zz)/np.sqrt(c['fx']*c['fy']));world=core.backproject(q,zz,c);s=fit_segment(world,p)
            if s['fit_error_pixel']>1 and len(q)>2:
                mid=len(q)//2;add(q[:mid+1]);add(q[mid:]);return
            sid=len(segments);s.update(view=vi,camera=c,uv=q,source_ids=lookup[q[:,1],q[:,0]].tolist(),normal=np.asarray(c['extrinsic'])[2,:3].copy(),opacity=float(np.clip(np.median(f['dark'][q[:,1],q[:,0]]),.02,.95)))
            suspect=(span[q[:,1],q[:,0]]>4*p)|(~np.isfinite(a['alpha'][q[:,1],q[:,0]]))|(a['alpha'][q[:,1],q[:,0]]<.5)
            s['kind']='silhouette' if suspect.any() else 'surface';s['layer_id']=sid;s['chain_id']=chain_id
            segments.append(s);smap[q[:,1],q[:,0]]=sid
            for end,qq in [(0,q[0]),(3,q[-1])]:node_tokens.setdefault((vi,int(qq[0]),int(qq[1])),[]).append((sid,end))
        if replay is None:
            for chain_id,path in enumerate(paths):
                zq=a['z'][path[:,1],path[:,0]];p=float(np.median(zq)/np.sqrt(c['fx']*c['fy']))
                for q in split_path(path,zq,p,CFG['max_chain_arc_px']):add(q)
        else:
            for s in replay:
                if s['view']!=vi:continue
                q=s['uv'];np.testing.assert_array_equal(lookup[q[:,1],q[:,0]],s['source_ids']);sid=len(segments);segments.append(s);smap[q[:,1],q[:,0]]=sid
                for end,qq in [(0,q[0]),(3,q[-1])]:node_tokens.setdefault((vi,int(qq[0]),int(qq[1])),[]).append((sid,end))
        dist,near=distance_transform_edt(~sk,return_indices=True)
        ny,nx=near[:,y,x];sid=smap[ny,nx];same_depth=abs(z-a['z'][ny,nx])<=4*np.maximum(z/np.sqrt(c['fx']*c['fy']),1e-15)
        assigned=valid&domain[y,x]&(dist[y,x]<=3)&(sid>=0)&same_depth
        rr['segment_id'][assigned]=sid[assigned];rr['reason'][assigned]=0
        rr['reason'][valid&domain[y,x]&(dist[y,x]<=3)&~same_depth]=4
        for sid0 in np.unique(sid[assigned]):
            idx=np.flatnonzero(assigned&(sid==sid0));q=segments[sid0]['uv'];t=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))];t=t/max(t[-1],1e-12)
            _,nearest=cKDTree(q).query(u[idx]);rr['arc'][idx]=t[nearest]
        records.append(rr);offset+=n
        np.savez_compressed(dst/f'{v}_maps.npz',darkness=f['dark'],marked=f['marked'],skeleton=sk,domain=domain,invalid_depth=f['marked']&~(np.isfinite(a['z'])&(a['z']>0)))
        summary[v]={'all_marked':n,'domain_marked':int((f['marked']&domain).sum()),'skeleton':int(sk.sum()),'invalid_depth':int((~valid).sum()),'paths':len(paths),'chain_segments_cumulative':len(segments)}
        print('chains',scene,v,summary[v],flush=True)
    graph,amb=associate(segments);mapping=np.full(len(segments),-1,np.int32)
    for i,g in enumerate(graph):mapping[g['members']]=i
    ledger={k:np.concatenate([r[k] for r in records]) for k in records[0]};ok=ledger['segment_id']>=0;ledger['primitive_id'][ok]=mapping[ledger['segment_id'][ok]]
    # Store the actual ordered raw chain nodes and source identities, not nearest
    # pixels presented as cross-view correspondences.
    ptr=np.r_[0,np.cumsum([len(s['source_ids']) for s in segments])]
    np.savez_compressed(dst/'ordered_segments.npz',source_ids=np.concatenate([s['source_ids'] for s in segments]),indptr=ptr,view=np.array([s['view'] for s in segments]),chain=np.array([s['chain_id'] for s in segments]),layer=np.array([s['layer_id'] for s in segments]),segment_to_primitive=mapping)
    np.savez_compressed(dst/'observations.npz',**ledger)
    js(dst/'ambiguities.json',amb)
    # Explicit endpoint graph: share only the SAME observed junction/end token
    # from one source view, close in world geometry. No unseen gap connection.
    ctrl=np.array([g['control'] for g in graph]);parent=np.arange(len(graph)*4)
    def root(i):
        while parent[i]!=i:i=parent[i]
        return i
    junctions=[]
    for token,links in node_tokens.items():
        linked=[]
        for sid,end in links:
            gid=int(mapping[sid]);q=segments[sid]['control'][end]
            k=0 if np.linalg.norm(ctrl[gid,0]-q)<=np.linalg.norm(ctrl[gid,3]-q) else 3
            if np.linalg.norm(ctrl[gid,k]-q)<=.6*graph[gid]['pixel']:linked.append((gid,k))
        linked=sorted(set(linked))
        if len(linked)<2:continue
        accepted=[linked[0]]
        for a in linked[1:]:
            if all(np.linalg.norm(ctrl[a]-ctrl[b])<=.4*min(graph[a[0]]['pixel'],graph[b[0]]['pixel']) for b in accepted):accepted.append(a)
        if len(accepted)>=2:
            for a in accepted[1:]:parent[root(a[0]*4+a[1])]=root(accepted[0][0]*4+accepted[0][1])
            junctions.append({'source_token':list(token),'control_refs':[list(a) for a in accepted]})
    roots=np.array([root(i) for i in range(len(parent))]);unique,inverse=np.unique(roots,return_inverse=True);points=np.zeros((len(unique),3));bounds=np.full(len(unique),np.inf)
    for i in range(len(unique)):
        ids=np.flatnonzero(inverse==i);points[i]=ctrl.reshape(-1,3)[ids].mean(0);bounds[i]=min(graph[j//4]['pixel'] for j in ids)*.75
    node_index=inverse.reshape(-1,4)
    for i,g in enumerate(graph):g['control']=points[node_index[i]].copy();g['anchor_control']=g['control'].copy()
    js(dst/'topology.json',{'junctions':junctions,'merge_policy':'only same observed endpoint token; pairwise world bound .4 pixel; no gap closure','ambiguity_count':len(amb)})
    summary.update(primitives=len(graph),segments=len(segments),merged_segments=len(segments)-len(graph),type_counts={k:sum(g['type']==k for g in graph) for k in ('point','line','bezier')},kind_counts={k:sum(g['kind']==k for g in graph) for k in ('surface','silhouette')},all_observations=len(ledger['depth']),assigned_observations=int(ok.sum()),reason_counts={str(k):int((ledger['reason']==k).sum()) for k in np.unique(ledger['reason'])},shared_junctions=len(junctions),ambiguous_seed_groups=len(amb))
    return graph,{'points':points,'node_index':node_index,'bounds':bounds},aa,ff,cs,summary

def save_graph(dst,graph,nodes,layout,label):
    graph_np={'control':np.array([g['control'] for g in graph]),'type':np.array([g['type'] for g in graph]),'pixel':np.array([g['pixel'] for g in graph]),'normal':np.array([g['normal'] for g in graph]),'opacity':np.array([g['opacity'] for g in graph]),'width':np.array([g['width'] for g in graph]),'kind':np.array([g['kind'] for g in graph]),**nodes}
    np.savez_compressed(dst/f'{label}_primitives.npz',**graph_np)
    js(dst/f'{label}_graph.json',{'primitive_count':len(graph),'units':'COLMAP scene units, not meters','build_views':BUILD,'parameter_file':f'{label}_primitives.npz','primitives':[{'id':i,'type':g['type'],'kind':g['kind'],'control_node_indices':nodes['node_index'][i].tolist(),'control_points':g['control'].tolist(),'source_segments':g['members'],'source_views':[BUILD[v] for v in g['views']],'fit_error_pixel':g['fit_error_pixel'],'pixel_scale':g['pixel'],'width_pixel':g['width'],'opacity':g['opacity']} for i,g in enumerate(graph)]})
    a=sample_graph(graph,layout);np.savez_compressed(dst/f'{label}_gaussians.npz',**a);demo.save_ply(dst/f'{label}_gaussians.ply',a)
    return a
