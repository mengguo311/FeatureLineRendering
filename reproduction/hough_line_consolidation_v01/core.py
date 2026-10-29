"""Independent sparse 3D line Hough adaptation, with shared downstream processing.

Reference: Dalitz et al., IPOL 2017, doi:10.5201/ipol.2017.208.
No author source is copied. Unlike the author implementation, samples are never
consumed by a peak. Confidence calibration and multiview confirmation are absent.
All coordinates supplied to run_backend are normalized by the input spacing h.
"""
from pilotio import *
from scipy.spatial import cKDTree

def fit_line(x,w,h=1.):
    x=np.asarray(x); base=np.asarray(w,dtype=float); ww=base.copy()
    for _ in range(CFG['irls_steps']):
        a=np.average(x,axis=0,weights=np.maximum(ww,1e-20)); y=x-a
        _,v=np.linalg.eigh((y*ww[:,None]).T@y); d=v[:,-1]
        r=np.linalg.norm(np.cross(y,d),axis=1)
        ww=base*np.minimum(1.,h/np.maximum(r,1e-20))
    return a,unit(d)

def eligible_fragment(x,h=1.):
    if len(x)<3: return False
    a,d=fit_line(x,np.ones(len(x)),h)
    if np.linalg.norm(np.cross(x-a,d),axis=1).max()>2*h: return False
    steps=np.diff(x,axis=0); valid=np.linalg.norm(steps,axis=1)>1e-12*h
    if not valid.any(): return False
    return bool(np.min(np.abs(unit(steps[valid])@d))>=np.cos(np.deg2rad(15)))

def support_intervals(s,h=1.):
    s=np.sort(np.asarray(s)); cuts=np.r_[0,np.flatnonzero(np.diff(s)>CFG['split_gap_h']*h)+1,len(s)]
    return [(float(s[a]),float(s[b-1])) for a,b in zip(cuts[:-1],cuts[1:]) if b>a]

def verify_gap(evidence):
    # Intentionally no real evidence adapter in M1. Never interpret an empty list as support.
    return dict(status='inferred',confirmed=False,render_gap=False,visibility='UNKNOWN',usable_interior_views=0,reason='M2_NOT_RUN_NO_INTERIOR_EVIDENCE',no_connect=True)

def associate_hypotheses(x,hypotheses,tolerance):
    return np.stack([np.linalg.norm(np.cross(x-a,d),axis=1)<=tolerance for a,d in hypotheses],1) if hypotheses else np.zeros((len(x),0),bool)

def occupied(x): return len(np.unique(np.floor(x).astype(np.int64),axis=0))
def canonical(d):
    d=unit(np.asarray(d))
    if d[2]<0 or (abs(d[2])<1e-14 and (d[1]<0 or (abs(d[1])<1e-14 and d[0]<0))): d=-d
    return d
def plane(d):
    e=np.eye(3)[int(np.argmin(abs(d)))]; u=unit(np.cross(d,e)); return np.stack([u,np.cross(d,u)],1)
def hemisphere(n):
    i=np.arange(n); z=(i+.5)/n; phi=i*np.pi*(3-np.sqrt(5))
    return np.c_[np.sqrt(1-z*z)*np.cos(phi),np.sqrt(1-z*z)*np.sin(phi),z]

def fragments(data):
    x=data['xyz']; result=[]
    for f in np.unique(data['fragment_id']):
        ids=np.flatnonzero(data['fragment_id']==f)
        a,d=fit_line(x[ids],data['confidence'][ids]); s=(x[ids]-a)@d
        # Eligibility uses observed positions AND the supplied ordered tangent estimate,
        # not evaluation identities. Raw noisy adjacent positions are not a tangent oracle.
        residual=np.linalg.norm(np.cross(x[ids]-a,d),axis=1)
        reliable=data['tangent_reliable'][ids]
        direction_ok=(not reliable.any()) or np.quantile(abs(data['tangent'][ids][reliable]@d),.1)>=np.cos(np.deg2rad(CFG['angle_degrees']))
        ok=bool(data['eligible'][ids].all() and residual.max()<=2 and direction_ok and occupied(x[ids])>=CFG['min_occupied'])
        result.append(dict(id=int(f),ids=ids,a=a,d=d,lo=float(s.min()),hi=float(s.max()),ends=np.array([a+s.min()*d,a+s.max()*d]),length=float(np.ptp(s)),eligible=ok))
    return result

def legal_pair(f,g):
    dot=abs(float(f['d']@g['d'])); angle=float(np.degrees(np.arccos(np.clip(dot,-1,1))))
    if angle>CFG['angle_degrees']: return None
    d=f['d']; a=f['a']; sf=(f['ends']-a)@d; sg=(g['ends']-a)@d
    if sf.max()<sg.min(): e1=f['ends'][sf.argmax()]; e2=g['ends'][sg.argmin()]; gap=float(sg.min()-sf.max())
    elif sg.max()<sf.min(): e1=g['ends'][sg.argmax()]; e2=f['ends'][sf.argmin()]; gap=float(sf.min()-sg.max())
    else: return None
    distance=float(np.linalg.norm(np.cross(e2-e1,d)))
    if gap>min(CFG['max_gap_h'],CFG['max_gap_fraction']*min(f['length'],g['length'])) or distance>CFG['distance_h']: return None
    return dict(pair=sorted([f['id'],g['id']]),gap_h=gap,perpendicular_h=distance,angle_degrees=angle,endpoints=np.array([e1,e2]),score=float(np.exp(-distance**2/4-angle**2/225-gap/20)))

def sparse_hough(data,ids,weighted=True,density=True,tangent_weight=True,confidence_weight=True):
    x=data['xyz'][ids]; t=data['tangent'][ids]; reliability=data['tangent_reliable'][ids]
    dirs=hemisphere(CFG['coarse_directions']); w=np.ones(len(x))
    if weighted and confidence_weight: w*=data['confidence'][ids]
    if weighted and density:
        _,inv,count=np.unique(np.floor(x).astype(np.int64),axis=0,return_inverse=True,return_counts=True); w/=count[inv]
    angular=np.ones((len(x),len(dirs)))
    if weighted and tangent_weight:
        angle=np.arccos(np.clip(abs(t@dirs.T),0,1)); angular=np.exp(-.5*(angle/np.deg2rad(15))**2)
        angular[~reliability]=1.
    angular/=np.maximum(angular.sum(1,keepdims=True),1e-30)
    mass=angular*w[:,None]; origin=np.median(x,axis=0); centered=x-origin
    angular_bound=1.5*np.sqrt(2*np.pi/len(dirs))
    coarse_width=max(CFG['coarse_offset_h'],2*np.linalg.norm(centered,axis=1).max()*np.sin(angular_bound))
    coarse=[]; evaluations=0
    for j,d in enumerate(dirs):
        U=plane(d); q=centered@U; keys=np.floor(q/coarse_width).astype(np.int64)
        cells,inv=np.unique(keys,axis=0,return_inverse=True); scores=np.bincount(inv,weights=mass[:,j]); evaluations+=len(x)
        for k in np.argsort(-scores,kind='stable')[:2]:
            keep=np.flatnonzero(inv==k)
            if len(keep)>=CFG['min_occupied']:
                a=origin+((cells[k]+.5)*coarse_width)@U.T
                coarse.append((float(scores[k]),a,d,keep))
    coarse.sort(key=lambda p:-p[0]); seeds=[]
    for item in coarse:
        _,a,d,keep=item
        if any(abs(d@dd)>.995 and np.linalg.norm(np.cross(a-aa,dd))<coarse_width*.5 for _,aa,dd,_ in seeds): continue
        seeds.append(item)
        if len(seeds)>=CFG['coarse_peak_limit']: break
    fine=[]
    for _,a,d,keep in seeds:
        # Continuous local orientation initialization followed by a genuine fine
        # offset/direction accumulator. The same 5-step final refiner is below.
        local=x[keep]; ca=np.average(local,axis=0,weights=np.maximum(w[keep],1e-20)); yy=local-ca
        _,vv=np.linalg.eigh((yy*w[keep,None]).T@yy); dd=canonical(vv[:,-1]); U0=plane(dd)
        fine_dirs=np.array([canonical(dd+np.tan(np.deg2rad(i))*U0[:,0]+np.tan(np.deg2rad(j))*U0[:,1]) for i in [-2,-1,0,1,2] for j in [-2,-1,0,1,2]])
        aw=np.ones((len(keep),25))
        if weighted and tangent_weight:
            an=np.arccos(np.clip(abs(t[keep]@fine_dirs.T),0,1)); aw=np.exp(-.5*(an/np.deg2rad(15))**2); aw[~reliability[keep]]=1
        aw/=np.maximum(aw.sum(1,keepdims=True),1e-30)
        # Each sample's aggregate fine vote across ALL coarse seeds is <=w_i.
        for j,fd in enumerate(fine_dirs):
            U=plane(fd); q=(local-ca)@U; keys=np.floor(q/CFG['fine_offset_h']).astype(np.int64)
            cells,inv=np.unique(keys,axis=0,return_inverse=True)
            weights=w[keep]*aw[:,j]/max(1,len(seeds)); scores=np.bincount(inv,weights=weights)
            k=int(np.argmax(scores)); aa=ca+((cells[k]+.5)*CFG['fine_offset_h'])@U.T
            fine.append((float(scores[k]),aa,fd)); evaluations+=len(keep)
    fine.sort(key=lambda p:-p[0])
    return fine,dict(coarse_directions=len(dirs),coarse_peaks=len(seeds),fine_votes=len(fine),coarse_width_h=coarse_width,coarse_angular_bound_degrees=float(np.degrees(angular_bound)),point_direction_evaluations=evaluations,coarse_sample_mass_max=float(mass.sum(1).max(initial=0)),fine_sample_mass_bound=float(w.max(initial=0)),density=density if weighted else False,tangent_weight=tangent_weight if weighted else False,confidence_weight=confidence_weight if weighted else False)

def run_backend(data,method,seed=0,density=True,tangent_weight=True,confidence_weight=True):
    start=time.monotonic(); x=data['xyz']; fs=fragments(data); fmap={f['id']:f for f in fs}; good=[f for f in fs if f['eligible']]
    ids=np.concatenate([f['ids'] for f in good]) if good else np.array([],int)
    stats=dict(method=method,seed=seed,input_samples=len(x),eligible_samples=len(ids),eligible_fragments=len(good),all_fragments=len(fs),refiner='shared weighted Huber orthogonal IRLS, 5 iterations',verifier='shared UNKNOWN, no confirmed gaps',confidence_calibration='UNKNOWN or synthetic neutral')
    raw=[]; baseline_pairs=[]; scored=0
    if method=='B0': raw=[(float(len(f['ids'])),f['a'],f['d']) for f in good]
    elif method=='B1':
        for i,f in enumerate(good):
            for g in good[i+1:]:
                scored+=1; pair=legal_pair(f,g)
                if pair is not None:
                    baseline_pairs.append(pair); jj=np.r_[f['ids'],g['ids']]
                    a=x[jj].mean(0); yy=x[jj]-a; _,vv=np.linalg.eigh(yy.T@yy); d=vv[:,-1]
                    raw.append((pair['score'],a,d))
        # Isolated fragments remain visible and can receive the shared local refiner.
        raw.extend((0.,f['a'],f['d']) for f in good)
    elif method=='B2' and len(ids)>=2:
        rng=np.random.default_rng(seed)
        for _ in range(CFG['ransac_trials']):
            i,j=rng.choice(ids,2,replace=False); d=x[j]-x[i]
            if np.linalg.norm(d)<1e-12: continue
            d=unit(d); residual=np.linalg.norm(np.cross(x[ids]-x[i],d),axis=1)
            match=(residual<=2)&((~data['tangent_reliable'][ids])|(abs(data['tangent'][ids]@d)>=np.cos(np.deg2rad(15))))
            raw.append((float(match.sum()),x[i],d)); scored+=len(ids)
    elif method in ('H0','H1') and len(ids):
        raw,hs=sparse_hough(data,ids,method=='H1',density,tangent_weight,confidence_weight); stats.update(hs)
    raw.sort(key=lambda p:-p[0]); hypotheses=[]; refined=0
    # Shared geometric NMS, support selection, IRLS, and non-destructive membership.
    for score,a,d in raw:
        if len(hypotheses)>=CFG['max_hypotheses'] or refined>=CFG['max_hypotheses']: break
        if method!='B0' and any(abs(d@q['direction'])>np.cos(np.deg2rad(3)) and np.linalg.norm(np.cross(a-q['anchor'],q['direction']))<1 for q in hypotheses): continue
        if method=='B0':
            f=min(good,key=lambda f:np.linalg.norm(f['a']-a)); match=f['ids']
        else:
            r=np.linalg.norm(np.cross(x[ids]-a,d),axis=1)
            match=ids[(r<=2)&((~data['tangent_reliable'][ids])|(abs(data['tangent'][ids]@d)>=np.cos(np.deg2rad(15))))]
        if len(match)<8 or occupied(x[match])<8: continue
        a,d=fit_line(x[match],data['confidence'][match]); refined+=1
        r=np.linalg.norm(np.cross(x[match]-a,d),axis=1); match=match[r<=2]
        if len(match)<8 or occupied(x[match])<8: continue
        # Retain whole qualified fragments only, never silently move just an arbitrary
        # subset of a curved path. Junction membership can exist in several hypotheses.
        members=[]
        for f in good:
            if method=='B0' and f['id']!=int(data['fragment_id'][match[0]]): continue
            rr=np.linalg.norm(np.cross(x[f['ids']]-a,d),axis=1)
            if rr.max()<=2 and abs(f['d']@d)>=np.cos(np.deg2rad(15)): members.append(f['id'])
        if not members: continue
        hypotheses.append(dict(id=len(hypotheses),anchor=a,direction=canonical(d),proposal_score=float(score),fragment_ids=members,sample_ids=np.concatenate([fmap[f]['ids'] for f in members])))
    intervals=[]; links={}; groups=np.full(len(x),-1,np.int32); projected=x.copy(); newt=data['tangent'].copy(); best=np.full(len(x),np.inf); membership=np.zeros(len(x),np.int32)
    for q in hypotheses:
        a=q['anchor']; d=q['direction']
        for f_id in q['fragment_ids']:
            f=fmap[f_id]; jj=f['ids']; s=(x[jj]-a)@d; membership[jj]+=1
            for lo,hi in support_intervals(s):
                take=jj[(s>=lo-1e-12)&(s<=hi+1e-12)]
                intervals.append(dict(hypothesis_id=q['id'],fragment_id=f_id,s_min=lo,s_max=hi,endpoints=np.array([a+lo*d,a+hi*d]),sample_ids=take,status='supported_within_original_fragment',source_gaussian_ids='UNKNOWN'))
            r=np.linalg.norm(np.cross(x[jj]-a,d),axis=1); take=jj[(r<best[jj])&(~data['protected'][jj])]
            projected[take]=a+((x[take]-a)@d)[:,None]*d; newt[take]=d; best[take]=np.linalg.norm(projected[take]-x[take],axis=1); groups[take]=q['id']
        if method!='B0':
            members=q['fragment_ids']
            for i,f in enumerate(members):
                for g in members[i+1:]:
                    p=legal_pair(fmap[f],fmap[g])
                    if p is not None:
                        p.update(hypothesis_id=q['id'],**verify_gap([])); key=tuple(p['pair'])
                        if key not in links or p['score']>links[key]['score']: links[key]=p
    # B1's exhaustive legal adjacency is its actual candidate set even when the
    # equal 32-hypothesis geometry budget does not select every proposed pair.
    if method=='B1':
        for p in baseline_pairs:
            p.update(hypothesis_id=None,**verify_gap([])); links[tuple(p['pair'])]=p
    unchanged=~np.isfinite(best)
    assert np.array_equal(projected[unchanged],x[unchanged])
    assert np.array_equal(projected[data['protected']],x[data['protected']])
    stats.update(seconds=time.monotonic()-start,raw_hypotheses=len(raw),final_hypotheses=len(hypotheses),refiner_calls=refined,refiner_iterations=refined*CFG['irls_steps'],baseline_point_or_pair_evaluations=scored,intervals=len(intervals),candidate_links=len(links),confirmed_links=0,rendered_new_gaps=0,assigned_samples=int((membership>0).sum()),unassigned_samples=int((membership==0).sum()),multiple_membership_samples=int((membership>1).sum()),changed_samples=int((np.linalg.norm(projected-x,axis=1)>1e-10).sum()),protected_samples=int(data['protected'].sum()),max_displacement_h=float(np.linalg.norm(projected-x,axis=1).max(initial=0)))
    return dict(hypotheses=hypotheses,intervals=intervals,links=list(links.values()),xyz=projected,tangent=newt,groups=groups,membership=membership,stats=stats,fragments=[{k:v for k,v in f.items() if k!='ids'} for f in fs])
