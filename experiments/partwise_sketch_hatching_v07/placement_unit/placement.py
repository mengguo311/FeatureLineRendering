"""One deterministic length-preserving seed-placement pass on a fixed field.

Distances use manifold-edge midpoint portals and straight in-triangle links.
This is an intrinsic polyhedral route upper bound, NOT exact geodesic distance.
Whole paths enter the objective; different direction layers never repel.
"""
import runtime
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from base_walk import adjacency
from line_field import regenerate,walk_field

DEFAULTS=dict(candidates_per_stroke=12,random_seed=20261025,sample_step=.01,
              layer_clearance_caps=[.06,.075],passes=1,length_tolerance=1e-9)

def point_segments(points,segments):
    if not len(segments):return np.full(len(points),np.inf)
    a=segments[:,0];d=segments[:,1]-a;l2=np.sum(d*d,axis=1)
    t=np.clip(np.einsum('psi,si->ps',points[:,None,:]-a[None,:,:],d)/np.maximum(l2,1e-30),0,1)
    return np.linalg.norm(points[:,None,:]-a[None,:,:]-t[:,:,None]*d[None,:,:],axis=2).min(1)

class PortalMetric:
    def __init__(self,mesh,allowed,sample_step=.01):
        self.mesh=mesh;self.allowed=np.asarray(allowed,bool);self.sample_step=sample_step
        self.face_nodes=[[] for _ in mesh['faces']];self.portal_faces=[];points=[];neighbors=[[] for _ in mesh['faces']]
        for edge,fs in sorted(adjacency(mesh).items()):
            if len(fs)!=2 or not self.allowed[fs].all():continue
            index=len(points);points.append(mesh['vertices'][list(edge)].mean(0));self.portal_faces.append((edge,np.array(fs,int)))
            i,j=fs;self.face_nodes[i].append(index);self.face_nodes[j].append(index);neighbors[i].append(j);neighbors[j].append(i)
        self.points=np.asarray(points,float).reshape(-1,3);self.n=len(points);rr=[];cc=[];ww=[]
        for ns in self.face_nodes:
            for i in ns:
                for j in ns:
                    if i!=j:rr.append(i);cc.append(j);ww.append(float(np.linalg.norm(self.points[i]-self.points[j])))
        self.rows=np.asarray(rr,int);self.cols=np.asarray(cc,int);self.weights=np.asarray(ww,float)
        self.components=np.full(len(mesh['faces']),-1,int);label=0
        for face in np.flatnonzero(self.allowed):
            if self.components[face]>=0:continue
            self.components[face]=label;stack=[int(face)]
            while stack:
                for nxt in neighbors[stack.pop()]:
                    if self.components[nxt]<0:self.components[nxt]=label;stack.append(nxt)
            label+=1
        self.component_count=label

    def distance_field(self,paths):
        initial=np.full(self.n,np.inf)
        for face in np.unique(paths['face']):
            ns=self.face_nodes[face]
            if ns:
                d=point_segments(self.points[ns],paths['points'][paths['face']==face]);initial[ns]=np.minimum(initial[ns],d)
        valid=np.flatnonzero(np.isfinite(initial))
        if not len(valid):return initial
        rows=np.r_[self.rows,np.full(len(valid),self.n)];cols=np.r_[self.cols,valid];weights=np.r_[self.weights,initial[valid]]
        graph=coo_matrix((weights,(rows,cols)),shape=(self.n+1,self.n+1)).tocsr()
        return dijkstra(graph,directed=True,indices=self.n)[:self.n]

    def clearance(self,paths,distance,others):
        distances=[];weights=[]
        for segment,face in zip(paths['points'],paths['face']):
            length=float(np.linalg.norm(segment[1]-segment[0]));n=max(2,int(np.ceil(length/self.sample_step)))
            t=np.linspace(0,1,n+1);points=(1-t[:,None])*segment[0]+t[:,None]*segment[1]
            d=point_segments(points,others['points'][others['face']==face]);ns=self.face_nodes[face]
            if ns:d=np.minimum(d,(np.linalg.norm(points[:,None,:]-self.points[ns][None,:,:],axis=2)+distance[ns][None,:]).min(1))
            w=np.full(n+1,length/n);w[[0,-1]]*=.5;distances.extend(d);weights.extend(w)
        return np.asarray(distances),np.asarray(weights)

def concatenate(paths):
    return {key:np.concatenate([p[key] for p in paths]) for key in paths[0]}

def score(metric,path,distance,others,cap):
    d,w=metric.clearance(path,distance,others);d=np.minimum(d,cap)
    return float(d.min()),float(np.average(d,weights=w))

def candidate(mesh,record,face,bary,field,allowed,edges,id_offset):
    layer=record['layer_id'];initial=field[face,layer].copy();length=record['requested_length']
    if np.linalg.norm(initial)<1e-12:return None,'field_degeneracy'
    minus=walk_field(mesh,face,bary,-initial,length/2,allowed,field[:,layer],edges)
    plus=walk_field(mesh,face,bary,initial,length/2,allowed,field[:,layer],edges)
    if minus['reason']!='requested_length' or plus['reason']!='requested_length':return None,minus['reason']+'|'+plus['reason']
    p={k:np.concatenate([minus[k][::-1,::-1] if k in ('points','bary') else minus[k][::-1],plus[k]]) for k in ('points','bary','face')}
    actual=minus['length']+plus['length']
    if abs(actual-length)>DEFAULTS['length_tolerance']:return None,'length_mismatch'
    count=len(p['face']);sid=record['parent_stroke_id']
    for key,value,dtype in [('stroke_id',sid+id_offset,np.int64),('layer_id',layer,np.uint8),('visibility_mask',record['visibility_mask'],np.uint64),('parent_stroke_id',sid,np.int64)]:p[key]=np.full(count,value,dtype)
    r=dict(record,stroke_id=sid+id_offset,seed_face=int(face),seed_bary=bary.tolist(),seed_point=(bary@mesh['tri'][face]).tolist(),
           initial_tangent=initial.tolist(),actual_length=actual,minus_stop=minus['reason'],plus_stop=plus['reason'],segments=count,
           obtuse_edge_transitions=minus['obtuse_edge_transitions']+plus['obtuse_edge_transitions'])
    return (p,r),None

def distribution(metric,paths,records,caps):
    all_d=[];all_w=[];per_stroke=[]
    for i,(path,r) in enumerate(zip(paths,records)):
        group=[p for j,(p,s) in enumerate(zip(paths,records)) if j!=i and s['component']==r['component'] and s['layer_id']==r['layer_id']]
        if not group:continue
        others=concatenate(group);d,w=metric.clearance(path,metric.distance_field(others),others);cap=caps[r['layer_id']]
        d=np.minimum(d,cap);all_d.extend(d);all_w.extend(w)
        per_stroke.append(dict(parent_stroke_id=r['parent_stroke_id'],minimum_capped_distance=float(d.min()),weighted_mean_capped_distance=float(np.average(d,weights=w))))
    if not all_d:return dict(strokes_with_neighbors=0,weighted_mean_capped_distance=0.,sample_quantiles=[],per_stroke=[])
    return dict(strokes_with_neighbors=len(per_stroke),weighted_mean_capped_distance=float(np.average(all_d,weights=all_w)),
                sample_quantiles=np.quantile(all_d,[0,.1,.5,.9,1]).tolist(),per_stroke=per_stroke)

def place(mesh,old,allowed,field,id_offset,config=None):
    cfg=dict(DEFAULTS if config is None else config)
    if cfg['passes']!=1:raise ValueError('Only the frozen single pass is supported')
    control,records=regenerate(mesh,old,allowed,field,id_offset);metric=PortalMetric(mesh,allowed,cfg['sample_step']);edges=adjacency(mesh)
    areas=.5*np.linalg.norm(np.cross(mesh['tri'][:,1]-mesh['tri'][:,0],mesh['tri'][:,2]-mesh['tri'][:,0]),axis=1)
    paths=[]
    for r in records:
        ix=control['stroke_id']==r['stroke_id'];p={k:v[ix].copy() for k,v in control.items()};paths.append(p)
        r['component']=int(metric.components[r['seed_face']]);r['visibility_mask']=int(p['visibility_mask'][0]);r['original_seed_point']=r['seed_point']
        r['initial_change_degrees']=0.;r['chosen_candidate']=0
    before=distribution(metric,paths,records,cfg['layer_clearance_caps']);reasons={};attempted=0;feasible=0
    for i,r in enumerate(records):
        group=[p for j,(p,s) in enumerate(zip(paths,records)) if j!=i and s['component']==r['component'] and s['layer_id']==r['layer_id']]
        others=concatenate(group) if group else {k:v[:0] for k,v in paths[i].items()}
        distance=metric.distance_field(others);cap=cfg['layer_clearance_caps'][r['layer_id']]
        original_score=score(metric,paths[i],distance,others,cap);best=original_score;best_path=paths[i];best_record=dict(r)
        faces=np.flatnonzero((metric.components==r['component'])&(areas>1e-20));prob=areas[faces]/areas[faces].sum()
        rng=np.random.Generator(np.random.PCG64(cfg['random_seed']+r['parent_stroke_id']))
        choices=rng.choice(faces,size=cfg['candidates_per_stroke'],p=prob);uv=rng.random((len(choices),2));u=np.sqrt(uv[:,0])
        barys=np.column_stack([1-u,u*(1-uv[:,1]),u*uv[:,1]])
        local_feasible=0
        for number,(face,bary) in enumerate(zip(choices,barys),1):
            attempted+=1;result,reason=candidate(mesh,r,int(face),bary,field,allowed,edges,id_offset)
            if result is None:reasons[reason]=reasons.get(reason,0)+1;continue
            feasible+=1;local_feasible+=1;p,rr=result;s=score(metric,p,distance,others,cap)
            if s[0]>best[0]+1e-10 or (abs(s[0]-best[0])<=1e-10 and s[1]>best[1]+1e-10):
                best=s;best_path=p;best_record=dict(rr,chosen_candidate=number)
        best_record.update(original_score=list(original_score),chosen_score=list(best),feasible_alternatives=local_feasible,
            seed_displacement=float(np.linalg.norm(np.asarray(best_record['seed_point'])-r['original_seed_point'])))
        old_tangent=np.asarray(r['initial_tangent']);new_tangent=np.asarray(best_record['initial_tangent'])
        best_record['initial_change_degrees']=float(np.rad2deg(np.arccos(np.clip(abs(old_tangent@new_tangent),0,1))))
        paths[i]=best_path;records[i]=best_record
    after=distribution(metric,paths,records,cfg['layer_clearance_caps']);new=concatenate(paths)
    diagnostics=dict(config=cfg,components=metric.component_count,portal_count=metric.n,strokes=len(records),
        moved_strokes=sum(r['seed_displacement']>1e-10 for r in records),attempted_candidates=attempted,feasible_candidates=feasible,
        rejected_reasons=reasons,before=before,after=after,
        metric_scope='Sampled whole-stroke clearance using shared-edge midpoint portal routes plus exact same-face point-to-segment distances; intrinsic upper bound, not exact geodesic or collision certification. Distances capped at inherited layer spacing; same-layer only.',
        selection='Ascending parent stroke ID; coordinate replacement against every other current stroke in same component/layer; lexicographic max(min capped clearance, arclength-weighted mean); original first and ties retained; one pass; 12 area-uniform alternatives per stroke.')
    return new,records,diagnostics
