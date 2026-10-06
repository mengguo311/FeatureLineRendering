"""Sparse original-ID comparison. Zero-fill is an observed truncated estimate only."""
import numpy as np
from scipy.ndimage import distance_transform_edt,binary_erosion

def silhouette(alpha,threshold):
    fg=alpha>threshold
    sdf=distance_transform_edt(fg)-distance_transform_edt(~fg)
    # Border value 1 avoids inventing an image-frame silhouette.
    edge=fg & ~binary_erosion(fg,border_value=1)
    gy,gx=np.gradient(sdf); norm=np.hypot(gy,gx)
    valid=edge & (norm>1e-8)
    p=np.column_stack(np.nonzero(valid)).astype(np.float64)
    n=np.column_stack((gy[valid],gx[valid]))/norm[valid,None]
    return valid,p,n,sdf

def sparse_sample(ids,weights,points,full_alpha):
    h,w,k=ids.shape; maps=[]; residual=[]
    for y,x in points:
        y0,x0=int(np.floor(y)),int(np.floor(x)); fy,fx=y-y0,x-x0
        out={}; full=0.
        for yy,xx,b in ((y0,x0,(1-fy)*(1-fx)),(y0,x0+1,(1-fy)*fx),
                         (y0+1,x0,fy*(1-fx)),(y0+1,x0+1,fy*fx)):
            if b==0 or not(0<=yy<h and 0<=xx<w): continue
            full+=b*float(full_alpha[yy,xx])
            for i,v in zip(ids[yy,xx],weights[yy,xx]):
                if i>=0 and v>0: out[int(i)]=out.get(int(i),0.)+b*float(v)
        maps.append(out); residual.append(max(0.,full-sum(out.values())))
    return maps,np.array(residual,dtype=np.float64)

def compare_sides(ids,weights,full_alpha,minus,plus,count,E=None,batch=512):
    raw=np.zeros(count,np.float64); participation=np.zeros(count,np.float64)
    l1=np.zeros(len(minus)); bound=np.zeros(len(minus))
    if E is None: E=np.ones(len(minus))
    for start in range(0,len(minus),batch):
        end=min(start+batch,len(minus))
        a,ra=sparse_sample(ids,weights,minus[start:end],full_alpha)
        b,rb=sparse_sample(ids,weights,plus[start:end],full_alpha)
        bound[start:end]=ra+rb
        for j,(am,bm) in enumerate(zip(a,b),start):
            for i in am.keys()|bm.keys():
                av,bv=am.get(i,0.),bm.get(i,0.)
                d=abs(av-bv);raw[i]+=E[j]*d;participation[i]+=E[j]*(av+bv)/2
                l1[j]+=d
    return l1,raw,participation,bound

def normalize_scores(raw,mass,min_mass,epsilon):
    score=np.asarray(raw)/(np.asarray(mass)+epsilon)
    return np.where(np.asarray(mass)>=min_mass,score,0.)

def select_ids(score,raw,mass,ratio_floor,raw_floor,min_mass):
    return np.flatnonzero((score>=ratio_floor)&(raw>=raw_floor)&(mass>=min_mass)).astype(np.int32)

def top_ids(score,eligible,count):
    ids=np.flatnonzero(eligible & (score>0))
    return ids[np.lexsort((ids,-score[ids]))[:count]].astype(np.int32)

def matched_random(selected,mass,seed,logwidth=.1):
    rng=np.random.default_rng(seed); bins=np.floor(np.log(np.maximum(mass,1e-12))/logwidth).astype(np.int32)
    pools={}; chosen=[]; used=set()
    for i in selected:
        b=bins[i]
        if b not in pools: pools[b]=rng.permutation(np.flatnonzero(bins==b)).tolist()
        while pools[b] and pools[b][-1] in used: pools[b].pop()
        if not pools[b]: raise RuntimeError('mass matching bin exhausted')
        j=pools[b].pop(); chosen.append(j);used.add(j)
    return np.array(chosen,np.int32)

def jaccard(a,b):
    a,b=set(map(int,a)),set(map(int,b));return len(a&b)/len(a|b) if a|b else 1.
