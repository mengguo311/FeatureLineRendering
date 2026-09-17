"""Offline TRAIN image relations and projection of frozen object-space paths.

All relations are 2D arrangements, including occlusion T's, NOT 3D junctions.
No mesh / labels / pretrained network / online image evidence is used here.
"""
import itertools
from collections import defaultdict
import cv2
import numpy as np
from scipy.sparse import csr_matrix
from . import common, visibility


def densify(paths):
    """Exact linear subdivision for raster visibility, not geometry optimization."""
    lengths = np.concatenate([np.linalg.norm(np.diff(p, axis=0), axis=1) for p in paths])
    step = max(float(np.median(lengths))*0.5, 1e-6)
    out = []
    for p in paths:
        pieces = []
        for a, b in zip(p[:-1], p[1:]):
            n = min(64, max(1, int(np.ceil(np.linalg.norm(b-a)/step))))
            pieces.append(a + np.arange(n)[:, None]/n*(b-a))
        out.append(np.vstack(pieces+[p[-1:]]))
    return out


def project_paths(paths, cam, depth):
    sizes = [len(p) for p in paths]
    vis, uv, _ = visibility.visible_mask(np.concatenate(paths), cam, depth)
    result = []; start = 0
    for size in sizes:
        v = vis[start:start+size]; p = uv[start:start+size]; start += size
        cuts = np.diff(np.r_[False, v, False].astype(int))
        runs = [p[a:b] for a, b in zip(np.where(cuts==1)[0], np.where(cuts==-1)[0]) if b-a>=2]
        result.append(runs)
    return result


def path_lengths(projected):
    return np.asarray([sum(np.linalg.norm(np.diff(p, axis=0), axis=1).sum() for p in runs) for runs in projected])


def draw_paths(projected, selected, shape, width=1):
    image = np.full((*shape, 3), 255, np.uint8)
    for i in np.flatnonzero(selected):
        for p in projected[i]:
            cv2.polylines(image, [np.round(p*16).astype(np.int32)], False, (0,0,0), width, cv2.LINE_AA, 4)
    return image


def pixel_matrix(projected, shape):
    rows, cols = [], []
    for i, runs in enumerate(projected):
        mask = np.zeros(shape, np.uint8)
        for p in runs:
            cv2.polylines(mask, [np.round(p*16).astype(np.int32)], False, 1, 1, cv2.LINE_8, 4)
        idx = np.flatnonzero(mask)
        rows.extend([i]*len(idx)); cols.extend(idx.tolist())
    return csr_matrix((np.ones(len(rows), np.float32), (rows, cols)), shape=(len(projected), int(np.prod(shape))))


def projected_metrics(projected, selected, shape):
    lens = path_lengths(projected)
    m = pixel_matrix(projected, shape)
    count = np.asarray(m[np.flatnonzero(selected)].sum(0)).ravel()
    ink = draw_paths(projected, selected, shape)
    fragments = [float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()) for i in np.flatnonzero(selected) for p in projected[i]]
    return {'visible_length_px':float(lens[selected].sum()),
        'visible_length_fraction':float(lens[selected].sum()/max(lens.sum(),1e-12)),
        'ink_area_antialiased_px':float((1-ink[:,:,0]/255.).sum()),
        'ink_pixels':int((count>0).sum()),
        'overlap_rate':float((count>1).sum()/max((count>0).sum(),1)),
        'short_fragment_fraction_lt12px':float(np.mean(np.asarray(fragments)<12)) if fragments else 0.,
        'fragments':len(fragments)}


def _segments(gray, sigma, cfg):
    blur = cv2.GaussianBlur(gray, (0,0), sigma)
    edges = cv2.Canny(blur, *cfg['canny'])
    found = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD).detect(edges)[0]
    if found is None:
        return np.empty((0,2,2)), edges
    lines = found[:,0].reshape(-1,2,2).astype(float)
    length = np.linalg.norm(lines[:,1]-lines[:,0], axis=1)
    lines = lines[length>=cfg['min_arm_px']]
    return lines, edges


def _arrangements(lines, cfg):
    result=[]; tol=cfg['junction_px']; minimum=cfg['min_arm_px']
    for i in range(len(lines)):
        a,b=lines[i]; u=(b-a)/np.linalg.norm(b-a)
        for j in range(i+1,len(lines)):
            c,d=lines[j]; v=(d-c)/np.linalg.norm(d-c)
            if abs(u@v)>np.cos(np.deg2rad(25)):
                continue
            # Intersection must lie close to BOTH finite segments. No distant
            # intersections of extended supporting lines receive evidence.
            try:
                t,s=np.linalg.solve(np.stack([u,-v],axis=1),c-a)
            except np.linalg.LinAlgError:
                continue
            if not (-tol<=t<=np.linalg.norm(b-a)+tol and -tol<=s<=np.linalg.norm(d-c)+tol):
                continue
            center=a+t*u
            arms=[]
            for end in (a,b,c,d):
                delta=end-center; length=np.linalg.norm(delta)
                if length>=minimum:
                    arms.append({'direction':(delta/length).tolist(),'length':float(length)})
            # L and T only. X crossings are excluded as texture-prone evidence.
            if len(arms) not in (2,3):
                continue
            result.append({'center':center.tolist(),'arms':arms,
                           'strength':float(sum(min(a['length'],32) for a in arms))})
    return result


def _repeat(a,b,cfg):
    if len(a['arms'])!=len(b['arms']) or np.linalg.norm(np.array(a['center'])-b['center'])>cfg['repeat_px']:
        return False
    ad=np.asarray([x['direction'] for x in a['arms']]); bd=np.asarray([x['direction'] for x in b['arms']])
    return any(np.all(np.sum(ad*bd[list(p)],axis=1)>=cfg['match_cos']) for p in itertools.permutations(range(len(bd))))


def detect_relations(gray,cfg):
    scales=[_segments(gray,s,cfg) for s in cfg['sigmas']]
    candidates=[_arrangements(lines,cfg) for lines,_ in scales]
    repeat=[e for e in candidates[0] if any(_repeat(e,f,cfg) for f in candidates[1])]
    kept=[]; cells=defaultdict(int)
    for e in sorted(repeat,key=lambda e:(-e['strength'],*e['center'])):
        cell=tuple((np.asarray(e['center'])//cfg['cell_px']).astype(int))
        if cells[cell]>=cfg['relations_per_cell'] or any(_repeat(e,f,cfg) for f in kept):
            continue
        kept.append(e); cells[cell]+=1
    long_mask=np.zeros(gray.shape,np.uint8)
    for lines,_ in scales:
        for line in lines:
            cv2.line(long_mask,tuple(np.round(line[0]).astype(int)),tuple(np.round(line[1]).astype(int)),1,1)
    dt=cv2.distanceTransform(1-long_mask,cv2.DIST_L2,5) if long_mask.any() else np.full(gray.shape,1e6,np.float32)
    return kept,dt,{'scale_segments':[len(x[0]) for x in scales],
                   'scale_relations':[len(x) for x in candidates],'repeat_before_cap':len(repeat),'relations':len(kept)}


def match_arm(e,arm,projected,cfg):
    center=np.asarray(e['center']); direction=np.asarray(arm['direction'])
    matches=[]
    for i,runs in enumerate(projected):
        best=0.
        for p in runs:
            delta=p-center; along=delta@direction
            distance=np.abs(delta[:,0]*direction[1]-delta[:,1]*direction[0])
            ok=(distance<=cfg['match_px'])&(along>=-cfg['junction_px'])&(along<=arm['length']+cfg['match_px'])
            if ok.sum()<2:
                continue
            # A continuous run must reach the junction and support a finite arm;
            # disconnected points near the line cannot invent a relation.
            cuts=np.diff(np.r_[False,ok,False].astype(int))
            for start,end in zip(np.where(cuts==1)[0],np.where(cuts==-1)[0]):
                q=p[start:end]; t=along[start:end]
                if len(q)<2 or t.min()>cfg['junction_px']+cfg['match_px']:
                    continue
                extent=float(t.max()-max(0,t.min()))
                deltaq=q[-1]-q[0]; norm=np.linalg.norm(deltaq)
                if norm<1e-8 or abs(deltaq@direction)/norm<cfg['match_cos']:
                    continue
                if extent<cfg['min_arm_px']*.6:
                    continue
                score=min(1.,extent/cfg['min_arm_px'])*float(np.exp(-distance[start:end].mean()/cfg['match_px']))
                best=max(best,score)
        if best>0:
            matches.append((i,best))
    return sorted(matches,key=lambda m:(-m[1],m[0]))[:cfg['max_matches_per_arm']]


def view_evidence(gray,projected,cfg,view):
    relations,dt,stats=detect_relations(gray,cfg)
    lengths=path_lengths(projected); denom=max(lengths.sum(),1e-12)
    unary=np.zeros(len(projected))
    for i,runs in enumerate(projected):
        for p in runs:
            midpoint=(p[1:]+p[:-1])/2; dl=np.linalg.norm(np.diff(p,axis=0),axis=1)
            xy=np.clip(np.round(midpoint).astype(int),[0,0],[gray.shape[1]-1,gray.shape[0]-1])
            unary[i]+=float((dl*np.exp(-dt[xy[:,1],xy[:,0]]/cfg['match_px'])).sum())*min(1.,dl.sum()/cfg['min_arm_px'])/denom
    output=[]
    for ei,e in enumerate(relations):
        matches=[match_arm(e,arm,projected,cfg) for arm in e['arms']]
        bundles={}
        for combo in itertools.product(*matches):
            ids=tuple(sorted({m[0] for m in combo}))
            if len(ids) not in (2,3):
                continue
            score=min(m[1] for m in combo)
            bundles[ids]=max(score,bundles.get(ids,0.))
        output.append(dict(e,view=view,evidence_id=ei,bundles=[{'ids':list(ids),'score':score} for ids,score in sorted(bundles.items())]))
    matrix=pixel_matrix(projected,gray.shape); pair=(matrix@matrix.T).tocoo()
    overlap=[(view,int(i),int(j),float(v/denom)) for i,j,v in zip(pair.row,pair.col,pair.data) if i<j]
    stats['explainable_relations']=sum(bool(e['bundles']) for e in output)
    stats['bundles']=sum(len(e['bundles']) for e in output)
    stats['candidate_visible_length_px']=float(lengths.sum())
    return unary,lengths,output,overlap,stats
