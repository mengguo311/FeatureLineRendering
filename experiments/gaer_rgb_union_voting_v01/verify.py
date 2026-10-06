"""Independent saved-result audit; does not call assignment or rerank fitting."""
import json,time
import numpy as np
from PIL import Image
from runtime import *
from freeze import check_protected

def audit():
    start=time.perf_counter();frozen=json.loads((ART/'PRODUCTION_FREEZE.json').read_text());checks=0;scenes={}
    def require(b,msg):
        nonlocal checks
        checks+=1
        if not b:raise AssertionError(msg)
    for seal in sorted((ART/'seals').glob('*.json')):
        for rel,h in json.loads(seal.read_text())['files'].items():require(sha(ROOT/rel)==h,'seal '+rel)
    for scene,record in frozen['scenes'].items():
        vote=np.load(ART/'downloads'/(scene+'_votes_all_original.npz'));allcounts=[];marked=received=unassignable=0
        require(vote['original_ids'].tolist()==list(range(record['count'])),'original-N IDs')
        for v in record['vote_views']:
            src=np.load(ART/'downloads'/scene/v['key']/'source_fields.npz');a=np.load(ART/'downloads'/scene/v['key']/'assignment.npz')
            buf=np.load(OUT/'units'/scene/v['key']/'K8_buffer.npz');line=src['line_binary'];winner=a['winner_map'];valid=line&(winner>=0)
            require(winner.dtype==np.int32 and winner.shape==(800,800),'winner map native format')
            require(np.array_equal(line,src['ink']>.2),'unchanged marked mask')
            require(array_sha(line)==v['line_binary_sha256'],'source line mask hash')
            require(array_sha(src['RGB'])==v['RGB_float32_sha256'],'source RGB hash')
            centerids=buf['original_ids'][line];cw=buf['alphaT_weights'][line];wm=winner[line]
            exists=((centerids==wm[:,None])&(cw>0)).any(1)&(wm>=0)
            real=((centerids>=0)&(cw>0)).any(1)
            require(np.array_equal(exists,real),'EVERY real marked contributor assigned exactly once')
            require(np.all(winner[~line]==-1),'unmarked receives no vote')
            require(np.all(a['fallback_map'][line&~valid]==5),'background explicitly unassignable')
            counts=np.bincount(winner[valid],minlength=record['count']);require(np.array_equal(counts,a['counts']),'per-view raw bincount')
            require(int(counts.sum())==int(valid.sum()),'one primary vote per receiving pixel')
            # Independently evaluate 128 evenly spaced marked pixels with dicts,
            # original-ID unions, and ordinary scalar bilinear arithmetic.
            yy,xx=np.nonzero(line);ix=np.linspace(0,len(yy)-1,min(128,len(yy)),dtype=int)
            ids=buf['original_ids'];weights=buf['alphaT_weights'];alpha=buf['full_accepted_alpha']
            def sample(y,x):
                y0,x0=int(np.floor(y)),int(np.floor(x));fy,fx=y-y0,x-x0;d={};full=0.
                for Y,X,b in ((y0,x0,(1-fy)*(1-fx)),(y0,x0+1,(1-fy)*fx),(y0+1,x0,fy*(1-fx)),(y0+1,x0+1,fy*fx)):
                    if b<=0 or not(0<=Y<800 and 0<=X<800):continue
                    full+=b*float(alpha[Y,X])
                    for i,w in zip(ids[Y,X],weights[Y,X]):
                        if i>=0 and w>0:d[int(i)]=d.get(int(i),0.)+b*float(w)
                return d,max(0.,full-sum(d.values()))
            for j in ix:
                y,x=int(yy[j]),int(xx[j]);c={int(i):float(w) for i,w in zip(ids[y,x],weights[y,x]) if i>=0 and w>0}
                if not c:require(winner[y,x]==-1,'scalar oracle background');continue
                n=src['normal_xy'][y,x].astype(float);norm=np.linalg.norm(n);n=np.nan_to_num(n)/max(float(np.nan_to_num(norm)),1e-8)
                am,ra=sample(y-2*n[1],x-2*n[0]);ap,rp=sample(y+2*n[1],x+2*n[0]);ds={i:abs(am.get(i,0)-ap.get(i,0)) for i in c}
                did=min(c,key=lambda i:(-ds[i],i));cid=min(c,key=lambda i:(-c[i],i))
                reason=int(a['fallback_map'][y,x]);expected=did if reason==0 else cid
                require(winner[y,x]==expected,'independent scalar winner '+scene+' '+v['key'])
                require(abs(float(a['unknown_bound'][j])-(ra+rp))<2e-6,'independent unknown bound')
            allcounts.append(counts);marked+=int(line.sum());received+=int(valid.sum());unassignable+=int((line&~valid).sum())
        C=np.stack(allcounts);require(np.array_equal(C,vote['per_view_counts']),'8 source counts persisted')
        require(np.array_equal(C.sum(0),vote['raw_frequency']),'raw frequency sum')
        require(np.array_equal((C>0).sum(0),vote['view_count']),'distinct views once per Gaussian')
        eligible=np.flatnonzero(C.sum(0)>0);order=eligible[np.lexsort((eligible,-(C>0).sum(0)[eligible],-C.sum(0)[eligible]))]
        require(np.array_equal(order,vote['ranked_original_ids']),'raw rank deterministic')
        for k in (100,500,2000):require(np.array_equal(order[:k],vote['top'+str(k)+'_ids']),'fixed TOP'+str(k))
        for k in (2,4,6):require(np.array_equal(np.flatnonzero((C>0).sum(0)>=k),vote['views_ge'+str(k)+'_ids']),'V threshold '+str(k))
        vote_w2c={array_sha(np.asarray(v['camera']['w2c'],np.float64)) for v in record['vote_views']}
        evaluation_w2c={array_sha(np.asarray(v['camera']['w2c'],np.float64)) for v in record['evaluation_views']}
        require(len(vote_w2c)==8 and len(evaluation_w2c)==2 and not(vote_w2c&evaluation_w2c),'distinct 8+2 frozen cameras')
        for v in record['evaluation_views']:
            rec=json.loads((ART/'results'/(scene+'_eval_'+v['key']+'.json')).read_text());src=np.load(ROOT/rec['source_archive'])
            for name,expected in rec['metrics'].items():
                a=np.load(OUT/'display_maps'/scene/'eval'/v['key']/(name+'_fullT.npz'))['contribution'];line=src['line_binary'];alpha=src['alpha']
                require(np.all(a>=0) and np.all(a<=alpha+3e-6),'actual fullT support bounds')
                line_mass=float(a[line].sum(dtype=np.float64));den=float(alpha[line].sum(dtype=np.float64))
                require(abs(line_mass/max(den,1e-20)-expected['line']['mass_recall'])<1e-10,'saved fullT heldout recall')
                require(abs(float(a[~line].sum(dtype=np.float64))/max(float(a.sum(dtype=np.float64)),1e-20)-expected['leakage_non_line_mass_fraction'])<1e-10,'saved leakage')
        for image in (ART/'media'/scene).rglob('*'):
            if image.suffix in ('.png','.jpg'):
                with Image.open(image) as im:im.load();require(im.width>0 and im.height>0,'decode '+str(image))
        scenes[scene]=dict(marked_pixels=marked,received_pixels=received,unassignable_pixels=unassignable,
            eligible_vote_IDs=len(order),source_views=8,evaluation_views=2,scalar_oracle_pixels_per_view=128)
    protected=check_protected(frozen);require(protected['passed'],'protected bytes before/after')
    rec=dict(passed=True,checks=checks,scenes=scenes,protected_files=protected['checked_files'],seconds=time.perf_counter()-start,
        independence='separate scalar dictionary sampler and saved-buffer counting; primary agent audit, not independent human semantic review')
    atomic_json(ART/'tests/INDEPENDENT_AUDIT.json',rec);print(json.dumps(rec,ensure_ascii=False),flush=True);return rec

if __name__=='__main__':audit()
