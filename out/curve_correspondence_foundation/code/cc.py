"""Preregistered correspondence foundation; no scene-specific parameters."""
import hashlib
import itertools
import numpy as np
import cv2
from scipy.ndimage import map_coordinates
from src.foundation import project_jacobian
from src.multiscene_probe import edge_field


def axial_angle(a,b):
    a=np.asarray(a,float);b=np.asarray(b,float)
    den=np.linalg.norm(a,axis=-1)*np.linalg.norm(b,axis=-1)
    value=np.degrees(np.arccos(np.clip(abs(np.sum(a*b,axis=-1))/np.maximum(den,1e-30),0,1)))
    return np.where(den>1e-12,value,np.nan)


def arclength(p):
    return np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]


def interpolate(p,s):
    arc=arclength(p)
    return np.stack([np.interp(s,arc,np.asarray(p)[:,k]) for k in range(np.shape(p)[1])],axis=-1)


def resample(p,step):
    p=np.asarray(p,float);length=arclength(p)[-1]
    if length<=0:return p[:1],np.zeros(1)
    s=np.linspace(0,length,int(np.ceil(length/step))+1)
    return interpolate(p,s),s


def trace_edges(edge):
    pixels=set(map(tuple,np.argwhere(edge)[:,::-1]));adj={}
    for x,y in sorted(pixels):
        ns=[]
        for dx,dy in itertools.product([-1,0,1],repeat=2):
            if (dx,dy)==(0,0) or (x+dx,y+dy) not in pixels:continue
            if dx and dy and ((x+dx,y) in pixels or (x,y+dy) in pixels):continue
            ns.append((x+dx,y+dy))
        adj[x,y]=sorted(ns)
    used=set();paths=[]
    def key(a,b):return tuple(sorted((a,b)))
    def walk(a,b):
        path=[a,b];used.add(key(a,b))
        while len(adj[b])==2:
            choices=[c for c in adj[b] if key(b,c) not in used]
            if not choices:break
            c=choices[0];used.add(key(b,c));path.append(c);a,b=b,c
            if b==path[0]:break
        return [list(p) for p in path]
    for a in sorted(adj):
        if len(adj[a])==0:paths.append([list(a)])
        if len(adj[a])!=2:
            for b in adj[a]:
                if key(a,b) not in used:paths.append(walk(a,b))
    for a in sorted(adj):
        for b in adj[a]:
            if key(a,b) not in used:paths.append(walk(a,b))
    return dict(paths=paths,junctions=[list(p) for p in sorted(adj) if len(adj[p])>2],
                endpoints=[list(p) for p in sorted(adj) if len(adj[p])<2])


def split_path(p,min_length,max_length,corner_window,corner_degrees,corner_suppression):
    p=np.asarray(p,float);s=arclength(p)
    if len(p)<2:return [dict(pixels=p,length=0.,eligible=False,start=0.,end=0.)]
    candidates=[]
    for i in range(1,len(p)-1):
        if min(s[i],s[-1]-s[i])<corner_window:continue
        a=p[i]-interpolate(p,s[i]-corner_window);b=interpolate(p,s[i]+corner_window)-p[i]
        den=np.linalg.norm(a)*np.linalg.norm(b)
        angle=np.degrees(np.arccos(np.clip(np.dot(a,b)/max(den,1e-30),-1,1)))
        if angle>corner_degrees:candidates.append((-angle,i))
    cuts=[0.,float(s[-1])];selected=[]
    for _,i in sorted(candidates):
        if all(abs(s[i]-s[j])>=corner_suppression for j in selected):selected.append(i);cuts.append(float(s[i]))
    cuts=sorted(cuts);expanded=[cuts[0]]
    for a,b in zip(cuts[:-1],cuts[1:]):expanded.extend(np.linspace(a,b,max(1,int(np.ceil((b-a)/max_length)))+1)[1:].tolist())
    result=[]
    for a,b in zip(expanded[:-1],expanded[1:]):
        points=np.vstack([interpolate(p,a),p[(s>a)&(s<b)],interpolate(p,b)])
        result.append(dict(pixels=points,length=b-a,eligible=b-a>=min_length,start=a,end=b))
    return result


def tangents(p):
    p=np.asarray(p,float);t=np.gradient(p,axis=0)
    return t/np.maximum(np.linalg.norm(t,axis=1,keepdims=True),1e-30)


def describe(rgb,points,sigma,offsets):
    rgb=cv2.GaussianBlur(np.asarray(rgb,float),(0,0),sigma)
    t=tangents(points);n=np.c_[-t[:,1],t[:,0]];sides=[]
    for sign in [-1,1]:
        values=[]
        for offset in offsets:
            q=points+sign*offset*n
            values.append(np.stack([map_coordinates(rgb[:,:,c],[q[:,1],q[:,0]],order=1,mode='nearest') for c in range(3)],axis=1))
        sides.append(np.mean(values,axis=0))
    return np.stack(sides,axis=1)


def extract(rgb,view,cfg):
    field=edge_field(rgb,cfg);graph=trace_edges(field['edge']);curves=[];rejected=[]
    args={k:v for k,v in cfg['extraction'].items() if k!='sample_step'}
    for parent,path in enumerate(graph['paths']):
        for piece,part in enumerate(split_path(path,**args)):
            record=dict(view=int(view),parent=parent,piece=piece,**part)
            if not part['eligible']:rejected.append(record);continue
            points,arc=resample(part['pixels'],cfg['extraction']['sample_step'])
            digest=hashlib.sha256(f'{view}:{parent}:{piece}:'.encode()+np.asarray(part['pixels'],'<f8').tobytes()).hexdigest()[:20]
            record.update(id=f'{view}:{digest}',points=points,arc=arc,tangent=tangents(points),
                          descriptor=describe(rgb,points,cfg['matching']['descriptor_sigma'],cfg['matching']['normal_offsets']))
            curves.append(record)
    return dict(edge=field['edge'],graph=graph,curves=curves,rejected=rejected,field=field)


def fundamental(ca,cb):
    wa=np.asarray(ca['w2c']);wb=np.asarray(cb['w2c']);rel=wb@np.linalg.inv(wa)
    x,y,z=rel[:3,3];cross=np.array([[0,-z,y],[z,0,-x],[-y,x,0.]])
    F=np.linalg.inv(cb['K']).T@cross@rel[:3,:3]@np.linalg.inv(ca['K'])
    return F/max(np.linalg.norm(F),1e-30)


def intersections(lines,curve,m):
    p=np.asarray(curve['points']);arc=np.asarray(curve['arc']);d=np.diff(p,axis=0)
    norms=np.linalg.norm(lines[:,:2],axis=1);lines=lines/np.maximum(norms[:,None],1e-30)
    signed=lines[:,:2]@p.T+lines[:,2:3]
    denominator=lines[:,:2]@d.T
    crossing=abs(denominator)/np.maximum(np.linalg.norm(d,axis=1),1e-30)
    with np.errstate(divide='ignore',invalid='ignore'):fraction=-signed[:,:-1]/denominator
    good=(fraction>=0)&(fraction<=1)&(crossing>=np.sin(np.radians(m['min_crossing_angle'])))
    result=np.full(len(lines),np.nan);why=dict(missing=0,multiple=0,tangent=0)
    for i in range(len(lines)):
        js=np.flatnonzero(good[i]);values=(arc[js]+fraction[i,js]*np.diff(arc)[js]).tolist()
        for k,j in [(0,0),(-1,-1)]:
            if abs(signed[i,k])<=m['endpoint_epipolar_tolerance'] and crossing[i,j]>=np.sin(np.radians(m['min_crossing_angle'])):values.append(float(arc[k]))
        if not values:
            why['missing']+=1
            if np.any(abs(signed[i])<=m['endpoint_epipolar_tolerance']):why['tangent']+=1
            continue
        groups=[]
        for v in sorted(values):
            if not groups or v-groups[-1][-1]>m['intersection_merge_arc']:groups.append([v])
            else:groups[-1].append(v)
        if len(groups)>1:why['multiple']+=1;continue
        # Exact crossings take precedence over tolerated endpoint proximity.
        exact=arc[js]+fraction[i,js]*np.diff(arc)[js]
        result[i]=float(np.mean(exact)) if len(exact) else float(np.mean(groups[0]))
    return result,why


def align_arcs(sa,tb,la,lb,m,enforce_order=True):
    sa=np.asarray(sa);tb=np.asarray(tb);valid=np.isfinite(tb);best=None
    for sign in ([1,-1] if enforce_order else [1]):
        runs=[];run=[]
        for i in range(len(sa)):
            if not valid[i]:
                if run:runs.append(run);run=[]
                continue
            okay=True
            if run:
                j=run[-1];da=sa[i]-sa[j];db=sign*(tb[i]-tb[j])
                okay=da<=m['source_gap']+1e-9
                if enforce_order:okay &= db>1e-6 and db<=m['target_gap']+1e-9 and m['slope_min']<=db/da<=m['slope_max']
            if not okay:runs.append(run);run=[]
            run.append(i)
        if run:runs.append(run)
        for run in runs:
            a=sa[run];b=tb[run];spana=float(a[-1]-a[0]);spanb=float(np.ptp(b));coverage=min(spana/max(la,1e-12),spanb/max(lb,1e-12))
            item=dict(indices=run,sa=a,tb=b,reverse=bool(sign<0),coverage=coverage,span_a=spana,span_b=spanb,
                      passed=bool(len(run)>=m['min_samples'] and min(spana,spanb)>=m['min_arc']-1e-8 and coverage>=m['min_coverage']-1e-8))
            quality=(min(spana,spanb),len(run),-run[0],sign)
            if best is None or quality>best[0]:best=(quality,item)
    return best[1] if best else dict(indices=[],sa=np.array([]),tb=np.array([]),reverse=False,coverage=0.,span_a=0.,span_b=0.,passed=False)


def transfer(edge,source,arc):
    x=np.asarray(edge['sa']);y=np.asarray(edge['tb'])
    if source!=edge['a']:x,y=y,x
    order=np.argsort(x,kind='stable');x=x[order];y=y[order]
    return np.interp(arc,x,y,left=np.nan,right=np.nan)


def pair_candidate(a,b,ca,cb,m,enforce_order=True):
    F=fundamental(ca,cb);ha=np.c_[a['points'],np.ones(len(a['points']))];hb=np.c_[b['points'],np.ones(len(b['points']))]
    tb,why_b=intersections(ha@F.T,b,m);sa,why_a=intersections(hb@F,a,m)
    forward=align_arcs(a['arc'],tb,a['length'],b['length'],m,enforce_order)
    backward=align_arcs(b['arc'],sa,b['length'],a['length'],m,enforce_order)
    record=dict(a=a['id'],b=b['id'],views=[int(a['view']),int(b['view'])],sa=forward['sa'],tb=forward['tb'],reverse=forward['reverse'],
                coverage=min(forward['coverage'],backward['coverage']),score=None,reasons=[],intersections_a=why_a,intersections_b=why_b,
                forward_span=[forward['span_a'],forward['span_b']],backward_span=[backward['span_a'],backward['span_b']],order_enforced=enforce_order)
    if not forward['passed'] or not backward['passed']:
        record['reasons'].append('order_or_insufficient_common_arc' if enforce_order else 'insufficient_common_arc');return record
    reverse_edge=dict(a=b['id'],b=a['id'],sa=backward['sa'],tb=backward['tb'])
    restored=transfer(reverse_edge,b['id'],forward['tb']);finite=np.isfinite(restored)
    closure=float(np.quantile(abs(restored[finite]-forward['sa'][finite]),.9)) if finite.any() else np.inf
    record['mutual_arc_p90']=closure
    if finite.sum()<m['min_samples'] or closure>m['mutual_arc_p90_max']:record['reasons'].append('nonreciprocal_alignment')
    da=np.asarray(a['descriptor'])[forward['indices']]
    db=np.stack([np.interp(forward['tb'],b['arc'],np.asarray(b['descriptor'])[:,i,j]) for i in range(2) for j in range(3)],axis=1).reshape(-1,2,3)
    scores=[float(np.mean(np.sqrt(np.mean((da-x)**2,axis=(1,2))))) for x in [db,db[:,::-1]]]
    record['descriptor_costs']=scores;record['descriptor_side_reversed']=bool(scores[1]<scores[0]);record['score']=min(scores)+m['coverage_cost']*(1-record['coverage'])
    if min(scores)>m['descriptor_rms_max']:record['reasons'].append('appearance')
    return record


def select_mutual(rows,m):
    groups={}
    for i,r in enumerate(rows):
        r['selected']=False
        if r['reasons']:continue
        # Competitors are only within the same view pair; IDs contain view prefix.
        va=str(r['a']).split(':')[0];vb=str(r['b']).split(':')[0]
        pair=tuple(r.get('views',[va,vb]))
        for side in ['a','b']:groups.setdefault((pair,side,r[side]),[]).append(i)
    winners={}
    for key,indices in groups.items():
        ordered=sorted(indices,key=lambda i:(rows[i]['score'],i));i=ordered[0]
        s=rows[i]['score'];second=rows[ordered[1]]['score'] if len(ordered)>1 else np.inf
        margin=second-s;ratio=s/second if second>0 else 1.
        winners[key]=(i,margin,ratio,margin>=m['margin_min'] and ratio<=m['ratio_max'])
    for i,r in enumerate(rows):
        if r['reasons']:continue
        va=str(r['a']).split(':')[0];vb=str(r['b']).split(':')[0];pair=tuple(r.get('views',[va,vb]));okay=True
        for side in ['a','b']:
            winner,margin,ratio,passed=winners[pair,side,r[side]]
            r['margin_'+side]=margin;r['ratio_'+side]=ratio
            okay &= winner==i and passed
        r['selected']=bool(okay)
        if not okay:r['reasons'].append('ambiguous_or_nonmutual_identity')
    return rows


def cycle_certificate(edges,m,enforce_order=True):
    nodes=sorted(set(x for e in edges for x in [e['a'],e['b']]));lookup={frozenset([e['a'],e['b']]):e for e in edges}
    if len(nodes)!=3 or len(lookup)!=3:return dict(passed=False,reasons=['not_triangle'])
    if enforce_order and sum(e['reverse'] for e in edges)%2:return dict(passed=False,reasons=['reversal_cycle'])
    residuals=[];coverage=[]
    for a,b,c in itertools.permutations(nodes):
        e=lookup[frozenset([a,b])];s=np.asarray(e['sa'] if e['a']==a else e['tb']);s=np.sort(s)
        t=transfer(e,a,s);u=transfer(lookup[frozenset([b,c])],b,t);back=transfer(lookup[frozenset([a,c])],c,u)
        direct=transfer(lookup[frozenset([a,c])],a,s)
        finite=np.isfinite(back)&np.isfinite(direct)&np.isfinite(u)
        span=float(np.ptp(s[finite])) if finite.any() else 0.
        coverage.append(dict(source=a,via=b,count=int(finite.sum()),arc=span))
        if finite.sum()<m['min_samples'] or span<m['min_arc']-1e-8:return dict(passed=False,reasons=['cycle_common_support'],coverage=coverage)
        residuals.extend(abs(back[finite]-s[finite]));residuals.extend(abs(u[finite]-direct[finite]))
    p90=float(np.quantile(residuals,.9));return dict(passed=p90<=m['cycle_arc_p90_max'],p90=p90,coverage=coverage,reasons=[] if p90<=m['cycle_arc_p90_max'] else ['arc_cycle'])


def build_tracks(curves,edges,m,enforce_order=True):
    edges=[e for e in edges if e.get('selected')];lookup={frozenset([e['a'],e['b']]):e for e in edges};adj={n:set() for n in curves}
    for e in edges:adj[e['a']].add(e['b']);adj[e['b']].add(e['a'])
    triangles=[];rejected=[]
    for a in sorted(adj):
        for b in sorted(n for n in adj[a] if n>a):
            for c in sorted(n for n in adj[a]&adj[b] if n>b):
                es=[lookup[frozenset(x)] for x in [(a,b),(a,c),(b,c)]];cert=cycle_certificate(es,m,enforce_order)
                if cert['passed']:triangles.append(dict(nodes={a,b,c},cert=cert))
                else:rejected.append(dict(nodes=[a,b,c],stage='cycle',**cert))
    groups=[]
    for tri in triangles:
        hits=[i for i,g in enumerate(groups) if any(len(tri['nodes']&x['nodes'])>=2 for x in g)]
        merged=[tri]
        for i in reversed(hits):merged+=groups.pop(i)
        groups.append(merged)
    candidates=[]
    for group in groups:
        nodes=sorted(set.union(*(t['nodes'] for t in group)));views=[curves[n]['view'] for n in nodes]
        if len(set(views))!=len(views):rejected.append(dict(nodes=nodes,stage='track',reasons=['many_to_one_view']));continue
        root=nodes[0];s=np.asarray(curves[root]['arc']);maps={root:s.copy()};pending=[root]
        while pending:
            a=pending.pop(0)
            for b in sorted(adj[a]&set(nodes)):
                if b not in maps:maps[b]=transfer(lookup[frozenset([a,b])],a,maps[a]);pending.append(b)
        valid=np.logical_and.reduce([np.isfinite(maps[n]) for n in nodes]);indices=np.flatnonzero(valid)
        if len(indices)<m['min_samples'] or np.ptp(s[valid])<m['min_arc']-1e-8:
            rejected.append(dict(nodes=nodes,stage='track',reasons=['track_common_support']));continue
        errors=[]
        for a,b in itertools.combinations(nodes,2):
            if frozenset([a,b]) not in lookup:continue
            prediction=transfer(lookup[frozenset([a,b])],a,maps[a][valid]);errors.extend(abs(prediction-maps[b][valid]))
        p90=float(np.quantile(errors,.9)) if np.isfinite(errors).all() else np.inf
        if p90>m['cycle_arc_p90_max']:
            rejected.append(dict(nodes=nodes,stage='track',reasons=['inconsistent_alternative_transfer'],p90=p90));continue
        # Keep contiguous root support only; no gap can be filled by fitting.
        runs=np.split(indices,np.flatnonzero(np.diff(indices)>1)+1)
        for run in runs:
            if len(run)<m['min_samples'] or np.ptp(s[run])<m['min_arc']-1e-8:continue
            candidates.append(dict(nodes=nodes,root=root,root_arc=s[run],maps={n:maps[n][run] for n in nodes},cycle_p90=p90,triangles=len(group),identity_frozen_before_fit=True))
    conflicts=set()
    for i,a in enumerate(candidates):
        for j,b in enumerate(candidates[:i]):
            if a['nodes']!=b['nodes'] and set(a['nodes'])&set(b['nodes']):conflicts.update([i,j])
    tracks=[]
    for i,t in enumerate(candidates):
        if i in conflicts:rejected.append(dict(nodes=t['nodes'],stage='track',reasons=['competing_track_identity']))
        else:tracks.append(t)
    return tracks,rejected


def camera_center(camera):
    return np.linalg.inv(camera['w2c'])[:3,3]


def baseline_angles(X,cameras):
    rays=np.array([np.asarray(X)-camera_center(c) for c in cameras]);rays/=np.maximum(np.linalg.norm(rays,axis=1,keepdims=True),1e-30)
    return sorted([float(np.degrees(np.arccos(np.clip(np.dot(a,b),-1,1)))) for a,b in itertools.combinations(rays,2)],reverse=True)


def dlt(uv,cameras):
    rows=[]
    for p,c in zip(uv,cameras):
        P=np.asarray(c['K'])@np.asarray(c['w2c'])[:3]
        for i in range(2):
            r=p[i]*P[2]-P[i];rows.append(r/max(np.linalg.norm(r[:3]),1e-30))
    _,_,v=np.linalg.svd(rows);h=v[-1]
    return h[:3]/h[3] if abs(h[3])>1e-12 else np.full(3,np.nan)


def triangulate(uv,cameras,f,min_views=None):
    from scipy.optimize import least_squares
    uv=np.asarray(uv);required=f['min_views'] if min_views is None else min_views;hypotheses=[]
    def residual(x):
        values=[]
        for c,p in zip(cameras,uv):
            pred,z,_=project_jacobian(x[None],c['K'],c['w2c']);values.extend(np.nan_to_num(pred[0]-p,nan=1e6))
        return np.array(values)
    for ij in itertools.combinations(range(len(cameras)),2):
        x=dlt(uv[list(ij)],[cameras[i] for i in ij])
        if not np.isfinite(x).all():continue
        error=np.linalg.norm(residual(x).reshape(-1,2),axis=1)
        hypotheses.append((int(np.sum(error<=f['inlier_px'])),-float(np.minimum(error,f['inlier_px'])@np.minimum(error,f['inlier_px'])),ij,x))
    if not hypotheses:return dict(xyz=np.full(3,np.nan),passed=False,reasons=['singular_triangulation'],inliers=0,baseline=[])
    best=max(hypotheses,key=lambda x:x[:3]);opt=least_squares(residual,best[-1],loss='huber',f_scale=f['huber'],max_nfev=f['max_nfev'])
    X=opt.x;errors=np.linalg.norm(residual(X).reshape(-1,2),axis=1);angles=baseline_angles(X,cameras)
    reasons=[];inliers=int(np.sum(errors<=f['inlier_px']))
    if inliers<required:reasons.append('triangulation_inliers')
    if any((np.asarray(c['w2c'])[:3,:3]@X+np.asarray(c['w2c'])[:3,3])[2]<=0 for c in cameras):reasons.append('negative_depth')
    if not angles or angles[0]<f['baseline_max_min'] or (required>=3 and (len(angles)<2 or angles[1]<f['baseline_second_min'])):reasons.append('baseline')
    return dict(xyz=X,passed=not reasons,reasons=reasons,inliers=inliers,baseline=angles,errors=errors,optimizer_success=bool(opt.success))


def closest_local(points,curve,arc,window):
    curve=np.asarray(curve);s=arclength(curve);closest=[];chosen=[]
    for p,u in zip(points,arc):
        lo=max(0.,u-window);hi=min(s[-1],u+window)
        knots=np.r_[lo,s[(s>lo)&(s<hi)],hi];local=interpolate(curve,knots)
        a=local[:-1];d=np.diff(local,axis=0);den=np.sum(d*d,axis=1)
        t=np.clip(np.sum((p-a)*d,axis=1)/np.maximum(den,1e-30),0,1);q=a+t[:,None]*d
        j=int(np.argmin(np.sum((q-p)**2,axis=1)));closest.append(q[j]);chosen.append(knots[j]+t[j]*(knots[j+1]-knots[j]))
    return np.array(closest),np.array(chosen)


def bundle_adjust(initial,cameras,observed_curves,arcs,delta,f):
    from scipy.optimize import least_squares
    initial=np.asarray(initial,float);anchors=[interpolate(p,s) for p,s in zip(observed_curves,arcs)]
    def data(x):
        rows=[]
        for c,p,s in zip(cameras,observed_curves,arcs):
            uv,_,_=project_jacobian(x,c['K'],c['w2c']);near,_=closest_local(uv,p,s,f['local_arc_window']);rows.append(uv-near)
        return np.array(rows)
    def residual(flat):
        x=flat.reshape(initial.shape);r=[data(x).ravel()]
        for c,anchor in zip(cameras,anchors):
            uv,_,_=project_jacobian(x,c['K'],c['w2c']);r.append((f['anchor_weight']*(uv-anchor)).ravel())
        r.append((f['second_difference_weight']*np.diff(x,n=2,axis=0)/delta).ravel())
        return np.nan_to_num(np.concatenate(r),nan=1e6)
    before=float(np.sqrt(np.mean(np.sum(data(initial)**2,axis=-1))))
    bounds=f['bound_delta']*delta
    opt=least_squares(residual,initial.ravel(),bounds=(initial.ravel()-bounds,initial.ravel()+bounds),loss='huber',f_scale=f['huber'],max_nfev=f['max_nfev'])
    x=opt.x.reshape(initial.shape);after=float(np.sqrt(np.mean(np.sum(data(x)**2,axis=-1))))
    return dict(xyz=x,rms_before=before,rms_after=after,success=bool(opt.success),nfev=int(opt.nfev),cost=float(opt.cost))


def contiguous_runs(mask):
    indices=np.flatnonzero(mask)
    return [] if not len(indices) else np.split(indices,np.flatnonzero(np.diff(indices)>1)+1)


def fit_track(track,curves,cameras,box,delta,f,min_views=None,enforce_order=True):
    nodes=track['nodes'];cams=[cameras[curves[n]['view']] for n in nodes]
    start,end=track['root_arc'][0],track['root_arc'][-1]
    s=np.linspace(start,end,int(np.ceil((end-start)/f['knot_step']))+1)
    maps=[np.interp(s,track['root_arc'],track['maps'][n]) for n in nodes]
    obs=[np.asarray(curves[n]['points']) for n in nodes];uv=np.array([interpolate(p,a) for p,a in zip(obs,maps)])
    fits=[triangulate(uv[:,i],cams,f,min_views) for i in range(len(s))]
    xyz=np.array([t['xyz'] for t in fits]);valid=np.array([t['passed'] for t in fits])
    inside=np.all((xyz>=np.asarray(box)[0])&(xyz<=np.asarray(box)[1]),axis=1);valid &= inside
    rejected=[dict(v,stage='triangulation',nodes=nodes,root_arc=float(s[i]),reasons=v['reasons']+([] if inside[i] else ['outside_box'])) for i,v in enumerate(fits) if not valid[i]]
    accepted=[]
    for run in contiguous_runs(valid):
        if len(run)<f['min_knots'] or np.ptp(s[run])<f['min_arc']-1e-8:
            rejected.append(dict(stage='fit',nodes=nodes,reasons=['short_supported_run'],root_arc=s[run]));continue
        selected_maps=[a[run] for a in maps];refined=bundle_adjust(xyz[run],cams,obs,selected_maps,delta,f);x=refined['xyz'];angles=[];order_ok=True;positive=True
        for c,p,a in zip(cams,obs,selected_maps):
            projected,z,_=project_jacobian(x,c['K'],c['w2c']);positive &= bool(np.all(z>0))
            nearest,arc=closest_local(projected,p,a,f['local_arc_window']);t=tangents(p);ps=arclength(p)
            ot=np.stack([np.interp(arc,ps,t[:,j]) for j in range(2)],axis=1);angles.extend(axial_angle(tangents(projected),ot))
            if enforce_order:order_ok &= bool(np.all(np.diff(arc)>0) or np.all(np.diff(arc)<0))
        median=float(np.nanmedian(angles));reasons=[]
        if refined['rms_after']>f['rms_max']:reasons.append('fit_residual')
        if not np.isfinite(median) or median>f['tangent_median_max']:reasons.append('fit_tangent')
        if not order_ok:reasons.append('refined_order_crossing')
        if not positive:reasons.append('negative_depth')
        if not np.all((x>=np.asarray(box)[0])&(x<=np.asarray(box)[1])):reasons.append('outside_box')
        if any(baseline_angles(p,cams)[0]<f['baseline_max_min'] for p in x):reasons.append('refined_baseline')
        identity='|'.join(nodes)+f':{s[run[0]]:.9f}:{s[run[-1]]:.9f}'
        record=dict(id=hashlib.sha256(identity.encode()).hexdigest()[:24],nodes=nodes,views=[int(curves[n]['view']) for n in nodes],xyz=x,root_arc=s[run],maps={n:a for n,a in zip(nodes,selected_maps)},cycle_p90=track.get('cycle_p90'),identity_frozen_before_fit=True,fit_rms=refined['rms_after'],fit_tangent_median=median,triangulation=fits,BA=refined,baseline_min=float(min(baseline_angles(p,cams)[0] for p in x)),reasons=reasons)
        if reasons:rejected.append(dict(stage='BA',**record))
        else:accepted.append(record)
    return accepted,rejected


def classify_support(front,supported,inside):
    result=[]
    for t,s,i in zip(front,supported,inside):
        result.append('out_of_frame' if not i else 'hidden' if t<=.1 else 'uncertain' if t<.8 else 'visible_supported' if s else 'visible_unsupported')
    return result


def support_spans(record,flags,f,min_views=None):
    need=f['min_views'] if min_views is None else min_views
    mask=np.asarray(flags).sum(axis=1)>=need
    if not len(mask) or np.mean(mask)<f['gs_knot_fraction']:return []
    result=[]
    for run in contiguous_runs(mask):
        arc=np.asarray(record['root_arc'])[run]
        if len(run)<f['min_knots'] or np.ptp(arc)<f['min_arc']-1e-8:continue
        r=dict(record,xyz=np.asarray(record['xyz'])[run],root_arc=arc,id=record['id']+f':gs:{int(run[0])}:{int(run[-1])}')
        if 'maps' in record:r['maps']={n:np.asarray(a)[run] for n,a in record['maps'].items()}
        result.append(r)
    return result


def shift_curves(curves,views,controls):
    result={};d=controls['shift_pixels']
    for key,c in curves.items():
        j=views.index(c['view']);offset=np.array([d*((j%3)-1),d*(((j+1)%3)-1)])
        result[key]=dict(c,points=np.asarray(c['points'])+offset,pixels=np.asarray(c['pixels'])+offset,shift=offset)
    return result


def random_graph(edges,curves,seed):
    import copy
    rng=np.random.default_rng(seed);groups={};result=copy.deepcopy(edges)
    for i,e in enumerate(result):
        pair=(curves[e['a']]['view'],curves[e['b']]['view']);groups.setdefault(pair,[]).append(i)
    for pair,indices in sorted(groups.items()):
        targets=sorted(k for k,v in curves.items() if v['view']==pair[1]);permutation=rng.permutation(len(targets));mapping={n:targets[j] for n,j in zip(targets,permutation)}
        for i in indices:result[i]['b']=mapping[result[i]['b']];result[i]['randomized']=True
    return result


def pair_tracks(edges):
    result=[]
    for e in edges:
        if not e.get('selected'):continue
        s=np.asarray(e['sa']);t=np.asarray(e['tb'])
        result.append(dict(nodes=[e['a'],e['b']],root=e['a'],root_arc=s,maps={e['a']:s,e['b']:t},cycle_p90=None,triangles=0,identity_frozen_before_fit=True))
    return result


def sample_geometry(records,delta):
    points=[];tangent=[];weights=[];identity=[]
    for i,r in enumerate(records):
        p,s=resample(r['xyz'],delta*.5)
        if len(p)<2:continue
        ds=np.diff(s);w=np.r_[ds[0]/2,(ds[:-1]+ds[1:])/2,ds[-1]/2]
        points.extend(p);tangent.extend(tangents(p));weights.extend(w);identity.extend([i]*len(p))
    return np.array(points).reshape(-1,3),np.array(tangent).reshape(-1,3),np.array(weights),np.array(identity,int)


def weighted_quantile(values,weights,q):
    v=np.asarray(values);w=np.asarray(weights)
    if not len(v) or np.sum(w)<=0:return None
    order=np.argsort(v);c=np.cumsum(w[order]);return float(v[order][min(len(v)-1,int(np.searchsorted(c,q*c[-1])))])


def match_geometry(base,other,delta,g):
    from scipy.spatial import cKDTree
    a,ta,wa,ia=sample_geometry(base,delta);b,tb,wb,ib=sample_geometry(other,delta)
    def direction(x,tx,wx,ix,y,ty,iy):
        if not len(x) or not len(y):return dict(coverage=0.,samples=len(x),matched=0,length=float(wx.sum()),matched_length=0.,distance=[],angle=[],weights=[])
        distances=[];neighbors=[]
        for group in np.unique(iy):
            js=np.flatnonzero(iy==group);dist,j=cKDTree(y[js]).query(x);distances.append(dist);neighbors.append(js[j])
        distances=np.array(distances).T;neighbors=np.array(neighbors).T;order=np.argsort(distances,axis=1);rows=np.arange(len(x));j=neighbors[rows,order[:,0]];d=distances[rows,order[:,0]]
        margin=distances[rows,order[:,1]]-d if distances.shape[1]>1 else np.full(len(x),np.inf)
        angle=axial_angle(tx,ty[j]);backdist,back=cKDTree(x).query(y[j]);mutual=np.linalg.norm(x[back]-x,axis=1)<=g['match_max_delta']*delta
        good=(d<=g['match_max_delta']*delta)&(angle<=g['match_angle'])&(margin>=g['match_margin_delta']*delta)&mutual
        return dict(coverage=float(wx[good].sum()/wx.sum()),samples=len(x),matched=int(good.sum()),length=float(wx.sum()),matched_length=float(wx[good].sum()),distance=(d[good]/delta).tolist(),angle=angle[good].tolist(),weights=wx[good].tolist(),ambiguous=int(np.sum(margin<g['match_margin_delta']*delta)))
    forward=direction(a,ta,wa,ia,b,tb,ib);backward=direction(b,tb,wb,ib,a,ta,ia)
    d=forward['distance']+backward['distance'];ang=forward['angle']+backward['angle'];w=forward['weights']+backward['weights']
    metrics=dict(base_count=len(base),other_count=len(other),forward=forward['coverage'],backward=backward['coverage'],base_length=float(wa.sum()),other_length=float(wb.sum()),
        length_change=abs(float(wb.sum()-wa.sum()))/float(wa.sum()) if wa.sum()>0 else None,
        distance_median_delta=weighted_quantile(d,w,.5),distance_p90_delta=weighted_quantile(d,w,.9),angle_median=weighted_quantile(ang,w,.5),angle_p90=weighted_quantile(ang,w,.9),forward_detail=forward,backward_detail=backward)
    metrics['passed']=bool(d and wa.sum()>0 and min(metrics['forward'],metrics['backward'])>=g['repeat_coverage'] and metrics['length_change']<=g['repeat_length_change'] and metrics['distance_median_delta']<=g['repeat_median_delta'] and metrics['distance_p90_delta']<=g['repeat_p90_delta'] and metrics['angle_median']<=g['repeat_median_angle'] and metrics['angle_p90']<=g['repeat_p90_angle'])
    return metrics


def predict(records,cameras,fields,delta,g):
    x,t,w,ids=sample_geometry(records,delta);rows=[];per_view={};distances=[];angles=[];quantile_weights=[];joint_lengths=[];total_lengths=[];track_support={str(i):[] for i in range(len(records))}
    for view,c in cameras.items():
        field=fields[view];h,width=field['edge'].shape;uv,z,J=project_jacobian(x,c['K'],c['w2c']);finite=np.isfinite(uv).all(1)
        pix=np.rint(np.nan_to_num(uv,nan=-1e6)).astype(int);inside=finite&(z>0)&(pix[:,0]>=0)&(pix[:,0]<width)&(pix[:,1]>=0)&(pix[:,1]<h)
        projected=np.einsum('nij,nj->ni',J,t);speed=np.linalg.norm(projected,axis=1);length_weights=np.nan_to_num(speed*w);length_weights[~inside]=0
        dt=np.full(len(x),np.inf);angle=np.full(len(x),90.)
        good=np.flatnonzero(inside)
        if len(good):
            q=pix[good];dt[good]=field['dt'][q[:,1],q[:,0]];angle[good]=axial_angle(projected[good],field['nearest_tangent'][q[:,1],q[:,0]])
        direction=inside&np.isfinite(angle)&(speed*delta>=.25)
        joint=direction&(dt<=g['joint_px'])&(angle<=g['joint_angle']);den=float(length_weights.sum());num=float(length_weights[joint].sum())
        for i in range(len(records)):
            mask=(ids==i)&inside;length=float(length_weights[mask].sum());supported=length>0 and float(length_weights[mask&joint].sum())/length>=g['joint_fraction']
            if supported:track_support[str(i)].append(int(view))
        per_view[str(view)]=dict(samples=len(x),in_frame=int(inside.sum()),out_of_frame=int((~inside).sum()),direction_evaluable=int(direction.sum()),direction_unknown=int((inside&~direction).sum()),projected_length=den,supported_length=num,unsupported_length=den-num,joint_fraction=num/den if den else 0.)
        if den:
            distances.extend(dt[inside]);angles.extend(np.where(direction[inside],angle[inside],90.));quantile_weights.extend(length_weights[inside]/den)
        joint_lengths.append(num);total_lengths.append(den)
        rows.append(dict(view=int(view),uv=uv,inside=inside,distance=dt,angle=angle,joint=joint,projected_weights=length_weights,track_index=ids))
    # Equal weight per view, including empty views as zero support.
    fraction=float(np.mean([v['joint_fraction'] for v in per_view.values()])) if per_view else 0.
    md=weighted_quantile(distances,quantile_weights,.5);pd=weighted_quantile(distances,quantile_weights,.9);ma=weighted_quantile(angles,quantile_weights,.5);pa=weighted_quantile(angles,quantile_weights,.9)
    coverage=sum(len(v)>=g['min_prediction_views'] for v in track_support.values())/len(records) if records else 0.
    return dict(track_count=len(records),per_view=per_view,track_support=track_support,track_coverage=coverage,joint_fraction=fraction,distance_median=md,distance_p90=pd,angle_median=ma,angle_p90=pa,supported_length=float(np.mean(joint_lengths)) if joint_lengths else 0.,unsupported_length=float(np.mean(np.subtract(total_lengths,joint_lengths))) if total_lengths else 0.,passed=bool(records and md is not None and md<=g['prediction_median_px'] and pd<=g['prediction_p90_px'] and ma<=g['prediction_median_angle'] and pa<=g['prediction_p90_angle'] and fraction>=g['joint_fraction']),samples=rows)


def yield_metrics(records,cameras,delta,g):
    packed=[];cells={v:set() for v in cameras};lengths={v:0. for v in cameras}
    for r in sorted(records,key=lambda r:r['id']):
        center=np.asarray(r['xyz']).mean(0)
        if all(np.linalg.norm(center-p)>=g['centroid_separation_delta']*delta for p in packed):packed.append(center)
        for v in r['views']:
            if v not in cameras:continue
            c=cameras[v];uv,z,_=project_jacobian(np.asarray(r['xyz']),c['K'],c['w2c']);valid=np.isfinite(uv).all(1)&(z>0)
            if valid.all():
                lengths[v]+=float(arclength(uv)[-1]);cells[v].update(map(tuple,np.floor(uv/g['spatial_cell_px']).astype(int)))
    mean_length=float(np.mean(list(lengths.values()))) if lengths else 0.;four=sum(len(r['views'])>=4 for r in records)/len(records) if records else 0.
    spatial=sum(len(x)>=g['min_spatial_cells'] for x in cells.values());fit=bool(records and all(r['fit_rms']<=g['fit_rms_max'] and r['fit_tangent_median']<=g['fit_tangent_median_max'] for r in records))
    return dict(track_count=len(records),separated_tracks=len(packed),F_projected_length=mean_length,per_view_length={str(k):v for k,v in lengths.items()},per_view_cells={str(k):len(v) for k,v in cells.items()},spatial_views=spatial,four_view_fraction=four,fit_passed=fit,passed=bool(len(packed)>=g['min_tracks'] and mean_length>=g['projected_length_F_min'] and spatial>=g['min_spatial_views'] and four>=g['four_view_fraction_min'] and all(len(r['views'])>=3 for r in records)))


def null_gate(primary,controls,g):
    length=primary['supported_length'];precision=primary['joint_fraction']
    if length<=0:return False
    if any(controls[n]['supported_length']>length*g['null_length_ratio'] for n in ['shifted','random_graph']):return False
    return not any(controls[n]['supported_length']>=length*g['ablation_length_ratio'] and controls[n]['joint_fraction']>=precision-g['ablation_joint_slack'] for n in ['pairwise','no_order'])


def gs_benefit(image,gs,g):
    good=image['supported_length'];bad=image['unsupported_length'];sg=gs['supported_length'];sb=gs['unsupported_length']
    reduction=bad>0 and sb<=(1-g['gs_error_reduction'])*bad and sg>=(1-g['gs_supported_loss'])*good
    gain=good>0 and sg>=(1+g['gs_supported_gain'])*good and gs['joint_fraction']>=image['joint_fraction']-g['gs_precision_loss']
    return dict(passed=bool(good>0 and (reduction or gain)),reduction=bool(reduction),gain=bool(gain),image_supported=good,image_unsupported=bad,gs_supported=sg,gs_unsupported=sb)


def decision(valid,image_pass,gs_pass,benefit):
    if not valid:return 'ENGINEERING_NOT_READY'
    if image_pass and (not gs_pass or not benefit):return 'PIVOT_IMAGE_ONLY'
    if gs_pass and benefit:return 'CURVE_CORRESPONDENCE_GO_MANUAL_PENDING'
    return 'STOP_CORRESPONDENCE'


def match_all(curves,cameras,box,m,enforce_order=True):
    from collections import Counter
    center=np.mean(box,axis=0);rows=[];stats=Counter();per_pair=[]
    for va,vb in itertools.combinations(sorted(cameras),2):
        ra=camera_center(cameras[va])-center;rb=camera_center(cameras[vb])-center
        angle=float(np.degrees(np.arccos(np.clip(np.dot(ra,rb)/(np.linalg.norm(ra)*np.linalg.norm(rb)),-1,1))))
        aa=[c for c in curves.values() if c['view']==va];bb=[c for c in curves.values() if c['view']==vb]
        stats['curve_pairs']+=len(aa)*len(bb)
        if not m['pair_angle_min']<=angle<=m['pair_angle_max']:
            stats['camera_baseline_excluded']+=len(aa)*len(bb);per_pair.append(dict(views=[va,vb],angle=angle,allowed=False,curve_pairs=len(aa)*len(bb)));continue
        F=fundamental(cameras[va],cameras[vb]);count_before=len(rows)
        for a in aa:
            lines=np.c_[a['points'],np.ones(len(a['points']))]@F.T
            lines/=np.maximum(np.linalg.norm(lines[:,:2],axis=1,keepdims=True),1e-30)
            for b in bb:
                # Exact necessary range test: each epipolar line must meet the
                # target curve coordinate range, expanded only for endpoint tolerance.
                signed=lines[:,:2]@np.asarray(b['points']).T+lines[:,2:3]
                possible=(signed.min(1)<=m['endpoint_epipolar_tolerance'])&(signed.max(1)>=-m['endpoint_epipolar_tolerance'])
                if possible.sum()<m['min_samples'] or np.ptp(np.asarray(a['arc'])[possible])<m['min_arc']-1e-8:
                    stats['epipolar_range_excluded']+=1;continue
                rows.append(pair_candidate(a,b,cameras[va],cameras[vb],m,enforce_order));stats['proposed']+=1
        per_pair.append(dict(views=[va,vb],angle=angle,allowed=True,curve_pairs=len(aa)*len(bb),proposed=len(rows)-count_before))
    select_mutual(rows,m);stats['selected']=sum(r['selected'] for r in rows)
    return rows,dict(stats,per_pair=per_pair,rejection_reasons=dict(Counter(x for r in rows for x in r['reasons'])))


def reconstruct(curves,cameras,edges,box,delta,cfg,pairwise=False,enforce_order=True):
    from collections import Counter
    tracks,rejected=(pair_tracks(edges),[]) if pairwise else build_tracks(curves,edges,cfg['matching'],enforce_order)
    accepted=[];fit_rejected=[]
    for t in tracks:
        a,r=fit_track(t,curves,cameras,box,delta,cfg['fit'],cfg['controls']['pairwise_min_views'] if pairwise else None,enforce_order)
        accepted.extend(a);fit_rejected.extend(r)
    return dict(accepted=accepted,identity_hypotheses=len(tracks),identity_tracks=tracks,rejected=rejected+fit_rejected,rejection_reasons=dict(Counter(x for r in rejected+fit_rejected for x in r['reasons'])),pairwise=pairwise,order_enforced=enforce_order)


def apply_gs(records,cameras,layers,delta,f,min_views=None):
    from collections import Counter
    result=[];detail=Counter();certificates=[]
    for r in records:
        x=np.asarray(r['xyz']);flags=[];classifications={}
        for v in r['views']:
            if v not in cameras or v not in layers:continue
            c=cameras[v];uv,z,_=project_jacobian(x,c['K'],c['w2c']);inside=np.isfinite(uv).all(1)&(z>0)&np.all((uv>=-.5)&(uv<399.5),axis=1)
            front,support=layers[v].query(uv,z,delta);cl=classify_support(front,support,inside);detail.update(cl);classifications[str(v)]=cl
            flags.append([s=='visible_supported' for s in cl])
        flags=np.array(flags).T if flags else np.zeros((len(x),0),bool)
        out=support_spans(r,flags,f,min_views);result.extend(out)
        certificates.append(dict(id=r['id'],classifications=classifications,accepted_spans=[x['id'] for x in out],passing_knots=int(np.sum(flags.sum(1)>=(min_views or f['min_views']))),knots=len(x)))
    return result,dict(detail,input_tracks=len(records),output_tracks=len(result),certificates=certificates)
