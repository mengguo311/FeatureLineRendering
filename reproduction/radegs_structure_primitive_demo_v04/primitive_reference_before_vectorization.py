"""Bounded ordered short-curve hypotheses. No per-pixel voting or transitive union."""
from common import np,core,CFG
from scipy.spatial import cKDTree

def ordered_paths(mask):
    y,x=np.nonzero(mask);nodes=set(zip(x.tolist(),y.tolist()));adj={}
    for a in sorted(nodes):
        xx,yy=a;neighbors=[]
        for dx,dy in [(0,1),(1,0),(0,-1),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]:
            b=(xx+dx,yy+dy)
            if b not in nodes:continue
            if dx and dy and ((xx+dx,yy) in nodes or (xx,yy+dy) in nodes):continue
            neighbors.append(b)
        adj[a]=sorted(neighbors)
    used=set();paths=[]
    def edge(a,b):return tuple(sorted((a,b)))
    def walk(a,b):
        p=[a,b];used.add(edge(a,b));prev,cur=a,b
        while len(adj[cur])==2:
            nxt=adj[cur][0] if adj[cur][0]!=prev else adj[cur][1]
            if edge(cur,nxt) in used:break
            used.add(edge(cur,nxt));p.append(nxt);prev,cur=cur,nxt
        return np.array(p,int)
    for a in sorted(nodes):
        if len(adj[a])==0:paths.append(np.array([a]))
        elif len(adj[a])!=2:
            for b in adj[a]:
                if edge(a,b) not in used:paths.append(walk(a,b))
    for a in sorted(nodes):
        for b in adj[a]:
            if edge(a,b) not in used:paths.append(walk(a,b))
    return paths

def split_path(uv,z,pixel,max_arc=16):
    uv=np.asarray(uv);z=np.asarray(z);n=len(uv)
    if n<=2:return [uv]
    jumps=np.flatnonzero(abs(np.diff(z))>4*pixel)+1
    chunks=[]
    for ids in np.split(np.arange(n),jumps):
        if len(ids)<3:chunks.append(uv[ids]);continue
        q=uv[ids];corners=[]
        # Nonmaximum selection keeps the real corner rather than a train of cuts.
        scores=np.zeros(len(q))
        for i in range(1,len(q)-1):
            a=q[i]-q[max(0,i-3)];b=q[min(len(q)-1,i+3)]-q[i]
            scores[i]=np.degrees(np.arccos(np.clip(a@b/max(1e-20,np.linalg.norm(a)*np.linalg.norm(b)),-1,1)))
        for i in np.argsort(-scores,kind='stable'):
            if scores[i]>35 and all(abs(i-j)>3 for j in corners):corners.append(int(i))
        breaks=sorted(set([0,len(q)-1]+corners))
        for a,b in zip(breaks[:-1],breaks[1:]):
            arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q[a:b+1],axis=0),axis=1))];start=0
            for j in range(1,len(arc)):
                if arc[j]-arc[start]>=max_arc:
                    chunks.append(q[a+start:a+j+1]);start=j
            if start<len(arc)-1:chunks.append(q[a+start:b+1])
    return [q for q in chunks if len(q)]

def basis(t,kind,derivative=False):
    t=np.asarray(t);b=np.zeros((len(t),4))
    if kind=='point':
        if not derivative:b[:,0]=1
    elif kind=='line':
        if derivative:b[:,0]=-1;b[:,3]=1
        else:b[:,0]=1-t;b[:,3]=t
    else:
        if derivative:b=np.stack([-3*(1-t)**2,3*(1-t)**2-6*t*(1-t),6*t*(1-t)-3*t*t,3*t*t],1)
        else:b=np.stack([(1-t)**3,3*t*(1-t)**2,3*t*t*(1-t),t**3],1)
    return b
def curve_eval(control,kind,t):return basis(t,kind)@np.asarray(control)

def fit_segment(points,pixel):
    p=np.asarray(points,float)
    if len(p)==0 or not np.isfinite(p).all() or not np.isfinite(pixel) or pixel<=0:raise ValueError('invalid geometry')
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    if arc[-1]<pixel*.05:
        return {'type':'point','control':np.repeat(p[:1],4,axis=0),'pixel':float(pixel),'points':p,'fit_error_pixel':0.,'opacity':.6,'width':.45}
    t=arc/arc[-1];A=np.stack([1-t,t],1);ends=np.linalg.lstsq(A,p,rcond=None)[0];ctrl=np.linspace(ends[0],ends[1],4)
    err=float(np.max(np.linalg.norm(A@ends-p,axis=1)));kind='line'
    if err>.6*pixel and len(p)>=6:
        bb=basis(t,'bezier');cc=np.empty((4,3));cc[0]=p[0];cc[3]=p[-1];cc[1:3]=np.linalg.lstsq(bb[:,1:3],p-bb[:,0,None]*p[0]-bb[:,3,None]*p[-1],rcond=None)[0]
        ce=float(np.max(np.linalg.norm(bb@cc-p,axis=1)))
        if ce<=pixel and ce<=.7*err and (cc>=p.min(0)-2*pixel).all() and (cc<=p.max(0)+2*pixel).all():ctrl=cc;err=ce;kind='bezier'
    return {'type':kind,'control':ctrl,'pixel':float(pixel),'points':p,'fit_error_pixel':err/pixel,'opacity':.6,'width':.45}

def visibility_evidence(z,depth,alpha,marked):
    if not(np.isfinite(z) and z>0 and np.isfinite(depth) and depth>0 and np.isfinite(alpha) and alpha>=.5):return 'unknown'
    tol=.005*depth
    if z>depth+tol:return 'hidden'
    if z<depth-tol:return 'front_conflict'
    return 'visible_line' if marked else 'visible_offline'

def compatible(a,b):
    if a['type']=='point' or b['type']=='point':
        d=np.linalg.norm(a['control'][0]-b['control'][0])/min(a['pixel'],b['pixel'])
        return (d<.1 and a['type']==b['type']),d
    qa=curve_eval(a['control'],a['type'],np.linspace(0,1,17));qb=curve_eval(b['control'],b['type'],np.linspace(0,1,17));p=min(a['pixel'],b['pixel'])
    ta=core.normalize(qa[-1]-qa[0]);tb=core.normalize(qb[-1]-qb[0])
    if abs(ta@tb)<np.cos(np.radians(25)):return False,1e9
    if ta@tb<0:qb=qb[::-1]
    d=np.linalg.norm(qa[:,None]-qb[None],axis=2);ia=d.argmin(1);ib=d.argmin(0);da=d[np.arange(17),ia]/p;db=d[ib,np.arange(17)]/p
    cutoff=.1 if ('silhouette' in (a.get('kind'),b.get('kind'))) else 1.
    ma=da<=cutoff;mb=db<=cutoff
    if min(ma.mean(),mb.mean())<.6:return False,1e9
    if np.any(np.diff(ia[ma])<0) or np.any(np.diff(ib[mb])<0):return False,1e9
    # At least five actual ordered locations, also checked in both source cameras.
    for s,pa,pb,m in [(a,qa,qb[ia],ma),(b,qb,qa[ib],mb)]:
        if s.get('camera') is not None:
            u,z=core.project(pa[m],s['camera']);v,zz=core.project(pb[m],s['camera']);e=np.linalg.norm(u-v,axis=1)
            if np.median(e)>1 or np.quantile(e,.9)>2 or np.any(z<=0) or np.any(zz<=0):return False,1e9
    return True,float((np.mean(da[ma])+np.mean(db[mb]))/2)

def associate(segments):
    if not segments:return [],[]
    centers=np.array([s['control'].mean(0) for s in segments]);radii=np.array([np.linalg.norm(s['control']-centers[i],axis=1).max()+s['pixel'] for i,s in enumerate(segments)])
    tree=cKDTree(centers);assigned=np.full(len(segments),-1,int);groups=[];ambiguities=[]
    # Duplicate acquisition of the exact same source observation is an alias,
    # not another constraint or primitive. Provenance remains in members.
    aliases={};first={}
    for i,s in enumerate(segments):
        key=(s['view'],s['type'],np.ascontiguousarray(s['control']).tobytes(),np.ascontiguousarray(s.get('uv',[])).tobytes())
        if key in first:aliases.setdefault(first[key],[]).append(i)
        else:first[key]=i
    alias_ids={j for js in aliases.values() for j in js}
    for i,a in enumerate(segments):
        if assigned[i]>=0 or i in alias_ids:continue
        candidates=[]
        for j in tree.query_ball_point(centers[i],radii[i]+radii.max()):
            if j<=i or assigned[j]>=0 or j in alias_ids or segments[j]['view']==a['view']:continue
            if np.linalg.norm(centers[i]-centers[j])>radii[i]+radii[j]:continue
            ok,cost=compatible(a,segments[j])
            if ok:candidates.append((cost,j))
        candidates.sort();g=[i];seen={a['view']}
        for cost,j in candidates:
            b=segments[j]
            if b['view'] in seen:continue
            alternatives=[(cc,k) for cc,k in candidates if segments[k]['view']==b['view'] and k!=j and abs(cc-cost)<max(.02,.2*cost)]
            if alternatives:ambiguities.append({'segment':i,'candidates':[j]+[k for _,k in alternatives]});continue
            if all(compatible(segments[k],b)[0] for k in g):g.append(j);seen.add(b['view'])
        # Identical observations are idempotent. Fitting uses a bounded common arc
        # scaffold; no concatenation/transitive joining of disjoint intervals.
        ref=a['control'];kind=a['type'];tt=np.linspace(0,1,17);refpts=curve_eval(ref,kind,tt);aligned=[]
        for j in g:
            q=curve_eval(segments[j]['control'],segments[j]['type'],tt)
            if np.linalg.norm(q[0]-refpts[0])>np.linalg.norm(q[-1]-refpts[0]):q=q[::-1]
            aligned.append(q)
        if len(g)==1 or all(np.max(abs(q-refpts))<1e-13 for q in aligned):q=refpts
        else:
            # Align by a common bounded WORLD interval, not each observation's
            # normalized 0..1 parameter (which would shrink partial overlaps).
            axis=core.normalize(refpts[-1]-refpts[0]);coords=[q@axis for q in aligned]
            locations=np.linspace(min(s.min() for s in coords),max(s.max() for s in coords),max(17,int(np.ceil((max(s.max() for s in coords)-min(s.min() for s in coords))/a['pixel']))+1))
            observations=[]
            for q,s in zip(aligned,coords):
                order=np.argsort(s,kind='stable');s=s[order];q=q[order]
                row=np.stack([np.interp(locations,s,q[:,d]) for d in range(3)],1);row[(locations<s.min()-1e-12)|(locations>s.max()+1e-12)]=np.nan;observations.append(row)
            q=np.nanmedian(observations,axis=0)
        f=fit_segment(q,float(np.median([segments[j]['pixel'] for j in g])))
        f.update(members=g,views=sorted(seen),kind=a.get('kind','surface'),opacity=float(np.median([segments[j].get('opacity',.6) for j in g])),width=.45,normal=a.get('normal',np.array([0.,0.,1.])))
        f['anchor_control']=f['control'].copy();aa=[j for k in g for j in aliases.get(k,[])];f['alias_members']=aa;f['members']=g+aa
        assigned[g+aa]=len(groups);groups.append(f)
    return groups,ambiguities

def sampling_layout(graph):
    pids=[];ts=[];bs=[];ds=[];steps=[]
    for i,g in enumerate(graph):
        q=curve_eval(g['control'],g['type'],np.linspace(0,1,65));arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))]
        n=1 if g['type']=='point' else max(1,int(np.ceil(arc[-1]/g['pixel'])))
        t=np.full(1,.5) if n==1 else np.interp((np.arange(n)+.5)*arc[-1]/n,arc,np.linspace(0,1,65))
        pids.extend([i]*n);ts.extend(t);bs.extend(basis(t,g['type']));ds.extend(basis(t,g['type'],True));steps.extend([max(.2*g['pixel'],arc[-1]/n)]*n)
    return np.asarray(pids,int),np.asarray(ts),np.asarray(bs),np.asarray(ds),np.asarray(steps)

def sample_graph(graph,layout=None):
    if layout is None:layout=sampling_layout(graph)
    pids,t,B,D,step=layout;ctrl=np.array([g['control'] for g in graph]);means=np.einsum('ni,nij->nj',B,ctrl[pids]);tan=core.normalize(np.einsum('ni,nij->nj',D,ctrl[pids]));pixel=np.array([g['pixel'] for g in graph])[pids]
    normals=np.array([g.get('normal',[0,0,1]) for g in graph])[pids];side=core.normalize(np.cross(normals,tan));bad=np.linalg.norm(side,axis=1)<.1
    if bad.any():side[bad]=core.normalize(np.cross(np.eye(3)[np.argmin(abs(tan[bad]),axis=1)],tan[bad]))
    other=core.normalize(np.cross(tan,side));F=np.stack([tan,side,other],-1)
    scales=np.stack([.65*step,np.array([g.get('width',.45) for g in graph])[pids]*pixel,.25*pixel],1)
    cov=(F*scales[:,None,:]**2)@F.transpose(0,2,1);point=np.array([g['type']=='point' for g in graph])[pids];cov[point]=np.eye(3)*(.45*pixel[point,None,None])**2
    return {'means':means,'covariance':cov,'opacity':np.array([g.get('opacity',.6) for g in graph])[pids], 'colors':np.zeros((len(pids),3)), 'primitive_id':pids,'arc_t':t,'view_votes':np.array([len(g.get('views',[0])) for g in graph],np.uint8)[pids],'source_count':np.array([len(g.get('members',[0])) for g in graph],np.uint16)[pids],'source_anchor':pids.astype(np.int32)}
