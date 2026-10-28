"""Object-space association; distances use genuine mesh-edge portal routes.

The portal metric is an upper bound on intrinsic distance, not exact geodesics.
Same-face segment distance and resulting clipping intervals are analytic.
"""
import runtime
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from base_walk import adjacency
from line_field import transport

def crossings(paths,guide):
    out=[]
    for gi,face in enumerate(guide['face']):
        g=guide['bary'][gi,:,:2];gd=g[1]-g[0]
        for pi in np.flatnonzero(paths['face']==face):
            p=paths['bary'][pi,:,:2];pd=p[1]-p[0]
            matrix=np.column_stack((pd,-gd))
            if abs(np.linalg.det(matrix))<1e-13:continue
            t,s=np.linalg.solve(matrix,g[0]-p[0])
            if 1e-9<t<1-1e-9 and -1e-9<=s<=1+1e-9:
                out.append(dict(path_row=int(pi),guide_row=int(gi),face=int(face),parent_id=int(paths['stroke_id'][pi]),
                    path_t=float(t),guide_t=float(s),point=((1-t)*paths['points'][pi,0]+t*paths['points'][pi,1]).tolist()))
    return out

def segment_dist(points,segments):
    points=np.asarray(points).reshape(-1,3)
    if not len(segments):return np.full(len(points),np.inf)
    a=segments[:,0];v=segments[:,1]-a;vv=np.sum(v*v,axis=1)
    t=np.clip(np.einsum('nsi,si->ns',points[:,None]-a,v)/np.maximum(vv,1e-30),0,1)
    return np.linalg.norm(points[:,None]-a-t[:,:,None]*v,axis=2).min(1)

class SurfaceGuide:
    """Finite guide plus 5 portals per manifold shared edge; no XYZ neighbors."""
    def __init__(self,mesh,guide,allowed):
        self.mesh=mesh;self.guide=guide;self.allowed=np.asarray(allowed,bool)
        self.local={int(f):guide['points'][guide['face']==f] for f in np.unique(guide['face']) if self.allowed[f]}
        self.face_nodes=[[] for _ in mesh['faces']];self.neighbors=[[] for _ in mesh['faces']]
        nodes=[]
        for edge,faces in sorted(adjacency(mesh).items()):
            if len(faces)!=2 or not self.allowed[faces].all():continue
            i,j=faces;self.neighbors[i].append((j,edge));self.neighbors[j].append((i,edge))
            for t in (0.,.25,.5,.75,1.):
                node=len(nodes);nodes.append((1-t)*mesh['vertices'][edge[0]]+t*mesh['vertices'][edge[1]])
                self.face_nodes[i].append(node);self.face_nodes[j].append(node)
        self.nodes=np.asarray(nodes,float).reshape(-1,3);n=len(nodes);rows=[];cols=[];values=[]
        for ns in self.face_nodes:
            for i in ns:
                for j in ns:
                    if i!=j:rows.append(i);cols.append(j);values.append(float(np.linalg.norm(self.nodes[i]-self.nodes[j])))
        initial=np.full(n,np.inf)
        for face,segments in self.local.items():
            ids=self.face_nodes[face]
            if ids:initial[ids]=np.minimum(initial[ids],segment_dist(self.nodes[ids],segments))
        for i in np.flatnonzero(np.isfinite(initial)):
            rows.append(n);cols.append(int(i));values.append(float(initial[i]))
        graph=coo_matrix((values,(rows,cols)),shape=(n+1,n+1)).tocsr()
        self.portal_distance=dijkstra(graph,directed=True,indices=n)[:n]

    def distance(self,face,points):
        points=np.asarray(points).reshape(-1,3)
        if not self.allowed[face]:return np.full(len(points),np.inf)
        d=segment_dist(points,self.local.get(int(face),np.empty((0,2,3))))
        ids=self.face_nodes[face]
        if ids:d=np.minimum(d,(np.linalg.norm(points[:,None]-self.nodes[ids],axis=2)+self.portal_distance[ids]).min(1))
        return d

def quadratic_interval(a,v,r,lo=0.,hi=1.):
    A=float(v@v);B=2*float(a@v);C=float(a@a)-r*r
    if A<1e-28:return [(lo,hi)] if C<0 else []
    disc=B*B-4*A*C
    if disc<=0:return []
    roots=((-B-np.sqrt(disc))/(2*A),(-B+np.sqrt(disc))/(2*A))
    l=max(lo,roots[0]);h=min(hi,roots[1])
    return [(l,h)] if h-l>1e-12 else []

def capsule_intervals(p,segment,r):
    x=p[0];v=p[1]-x;a,b=segment;d=b-a;dd=float(d@d)
    if dd<1e-25:return quadratic_interval(x-a,v,r)
    u0=float((x-a)@d/dd);ud=float(v@d/dd)
    cuts=[0.,1.]
    if abs(ud)>1e-14:
        cuts.extend(t for t in ((0-u0)/ud,(1-u0)/ud) if 0<t<1)
    cuts=sorted(cuts);out=[]
    for l,h in zip(cuts[:-1],cuts[1:]):
        u=u0+ud*(l+h)/2
        if u<0:offset=x-a;direction=v
        elif u>1:offset=x-b;direction=v
        else:offset=x-a-u0*d;direction=v-ud*d
        out.extend(quadratic_interval(offset,direction,r,l,h))
    return out

def merge_intervals(values):
    out=[]
    for l,h in sorted(values):
        if out and l<=out[-1][1]+1e-11:out[-1][1]=max(h,out[-1][1])
        else:out.append([float(l),float(h)])
    return out

def excluded_intervals(metric,face,p,width):
    if not metric.allowed[face]:return []
    values=[]
    for s in metric.local.get(int(face),[]):values.extend(capsule_intervals(p,s,width))
    for node in metric.face_nodes[face]:
        radius=width-metric.portal_distance[node]
        if radius>0:values.extend(quadratic_interval(p[0]-metric.nodes[node],p[1]-p[0],radius))
    return merge_intervals(values)

def retain_intervals(mesh,paths,removed):
    result={k:[] for k in paths};rows=[];ts=[];records=[]
    for i,(p,b,f) in enumerate(zip(paths['points'],paths['bary'],paths['face'])):
        intervals=merge_intervals(removed.get(i,[]));start=0.;keep=[]
        for l,h in intervals:
            if l-start>1e-11:keep.append([start,l])
            start=h
        if 1-start>1e-11:keep.append([start,1.])
        for l,h in keep:
            bb=np.stack([(1-l)*b[0]+l*b[1],(1-h)*b[0]+h*b[1]])
            for key,values in paths.items():
                value=bb if key=='bary' else (bb@mesh['tri'][f] if key=='points' else values[i])
                result[key].append(value)
            rows.append(i);ts.append([l,h])
        if intervals:records.append(dict(parent_id=int(paths['stroke_id'][i]),parent_segment=i,face=int(f),removed_t=intervals,retained_t=keep,
            removed_length=float(np.linalg.norm(p[1]-p[0])*sum(h-l for l,h in intervals))))
    out={k:np.asarray(v,dtype=paths[k].dtype).reshape((-1,)+paths[k].shape[1:]) for k,v in result.items()}
    out['input_segment_row']=np.asarray(rows,np.int64);out['input_interval']=np.asarray(ts,float).reshape(-1,2)
    before=float(np.linalg.norm(paths['points'][:,1]-paths['points'][:,0],axis=1).sum())
    after=float(np.linalg.norm(out['points'][:,1]-out['points'][:,0],axis=1).sum())
    return out,dict(raw_length=before,retained_length=after,trimmed_length=before-after,intervals=records,
        parent_ids_preserved=True,metric='Exact same-face finite capsules plus actual shared-edge 5-portal route upper-bound balls; no spatial KNN')

def trim_paths(mesh,paths,metric,width):
    removed={i:excluded_intervals(metric,int(f),p,width) for i,(p,f) in enumerate(zip(paths['points'],paths['face']))}
    return retain_intervals(mesh,paths,removed)

def guided_field(mesh,raw,metric,radius,max_degrees):
    import heapq
    n=len(mesh['faces']);cost=np.full(n,np.inf);tangent=np.zeros((n,3));queue=[];centers=mesh['tri'].mean(1)
    for face,segments in metric.local.items():
        t=(segments[:,1]-segments[:,0]).sum(0);norm=np.linalg.norm(t)
        if norm<1e-12:continue
        cost[face]=0.;tangent[face]=t/norm;heapq.heappush(queue,(0.,face))
    while queue:
        d,i=heapq.heappop(queue)
        if d!=cost[i]:continue
        for j,edge in metric.neighbors[i]:
            mid=mesh['vertices'][list(edge)].mean(0)
            nd=d+np.linalg.norm(centers[i]-mid)+np.linalg.norm(centers[j]-mid)
            if nd<cost[j]:
                cost[j]=nd;t=transport(mesh,j,i,edge)@tangent[i];tangent[j]=t/np.linalg.norm(t);heapq.heappush(queue,(nd,j))
    out=raw.copy();changes=np.zeros(n);dist=np.full(n,np.inf)
    for face in np.flatnonzero(metric.allowed & np.isfinite(cost)):
        d=metric.distance(int(face),centers[face:face+1])[0];dist[face]=d
        if d>=radius:continue
        r=raw[face];g=tangent[face]
        if r@g<0:g=-g
        theta=np.arccos(np.clip(r@g,-1,1));delta=min(theta,np.deg2rad(max_degrees))*(1-d/radius)
        if theta<1e-12:continue
        perpendicular=g-(r@g)*r;pn=np.linalg.norm(perpendicular)
        if pn<1e-12:continue
        out[face]=np.cos(delta)*r+np.sin(delta)*perpendicular/pn;changes[face]=np.rad2deg(delta)
    return out,dict(maximum_change_degrees=float(changes.max()),changed_faces=int((changes>0).sum()),
        change_quantiles=np.quantile(changes[metric.allowed],[0,.5,.9,.95,1]).tolist(),
        tangent_rule='Nearest guide-face centroid/edge route tree; tangent parallel transport through manifold edges; raw orientation modulo sign; linear intrinsic influence; 30 degree cap',
        per_face_change=changes,per_face_distance=dist)
