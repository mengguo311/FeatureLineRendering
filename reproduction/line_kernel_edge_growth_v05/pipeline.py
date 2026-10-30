"""Durable topology pass. Observers never change candidate/fit/commit decisions."""
from common import *
from core import Carrier,EPS,RAD
from collections import defaultdict,Counter
import io

class RestrictedState(pickle.Unpickler):
    def find_class(self,module,name):
        if module=='core' and name=='Carrier':return Carrier
        allowed={('collections','defaultdict'):defaultdict,('collections','Counter'):Counter,('builtins','list'):list,('numpy','ndarray'):np.ndarray,('numpy','dtype'):np.dtype,('numpy.core.multiarray','_reconstruct'):np.core.multiarray._reconstruct,('numpy.core.numeric','_frombuffer'):np.core.numeric._frombuffer,('numpy._core.multiarray','_reconstruct'):np.core.multiarray._reconstruct,('numpy._core.numeric','_frombuffer'):np.core.numeric._frombuffer,('numpy.core.multiarray','scalar'):np.core.multiarray.scalar}
        if (module,name) not in allowed:raise pickle.UnpicklingError('Forbidden global '+module+'.'+name)
        return allowed[(module,name)]
def load_state(path):
    with open(path,'rb') as f:s=RestrictedState(f).load()
    assert isinstance(s,dict) and {'carriers','aux','next_version'}<=set(s)
    for k,c in s['carriers'].items():
        assert type(c) is Carrier and k==c.cid
        assert set(vars(c))=={'cid','reps','rows','q','kind','valid','baseline','origins','version'}
    return s

def state_of(e):return dict(carriers=e.carriers,aux=e.aux,next_version=e.next_version,events=e.events,records=e.records,stats=e.stats,fit_count=e.fit_count,level=e.level,diagnostic_margins=getattr(e,'diagnostic_margins',{}))
def restore(e,s):
    for k,v in s.items():setattr(e,k,v)

def checkpoint(out,names,stage,**extra):
    import common
    if common.CFG:extra.update(decision_sha256=common.CFG['decision_sha256'],config_binding=common.CFG['_config_sha256'])
    js(out/'CHECKPOINT.json',dict(complete=True,stage=stage,utc=now(),files={n:sha(out/n) for n in names},**extra))
def verify_checkpoint(out,stage):
    c=json.loads((out/'CHECKPOINT.json').read_text());assert c['complete'] and c['stage']==stage
    verify({str(out/k):h for k,h in c['files'].items()})
    import common
    if common.CFG:assert c.get('decision_sha256')==common.CFG['decision_sha256'] and c.get('config_binding')==common.CFG['_config_sha256']
    return c

class Journal:
    def __init__(self,out):self.out=Path(out);self.batch=[];self.batch_index=0;self.competition=False;self.current=None;self.branch_margins={};self.ambiguity_margins={}
    def flush(self,e,cursor):
        if not self.batch:return
        self.batch_index+=1;name=f'DELTA_{self.batch_index:04d}.pkl'
        pk(self.out/'journal'/name,dict(competition_complete=True,cursor=cursor,commits=self.batch,next_version=e.next_version))
        js(self.out/'journal'/f'{name}.seal.json',dict(complete=True,file=name,sha256=sha(self.out/'journal'/name),commit_count=len(self.batch),cursor=cursor));self.batch=[]
    def __call__(self,what,e,data):
        if what=='evaluation_begin':self.current=tuple(data)
        elif what=='branch_reject':
            margin=branch_margin(e,data['reps'],data['q']);self.branch_margins[self.current]=margin
        elif what=='ambiguity_detected':
            margin=min(.15-(data['valid'][k][0]-data['best'])/max(data['valid'][k][0],1e-15) for k in data['near'])
            for k in data['ks']:
                z=data['valid'][k];pair=(z[1],z[2]);self.ambiguity_margins[pair]=min(margin,self.ambiguity_margins.get(pair,float('inf')))
        elif what=='candidates':
            z=np.asarray(data,float).reshape(-1,3);nz(self.out/'ORDERED_CANDIDATES.npz',cost=z[:,0],a=z[:,1].astype(np.int64),b=z[:,2].astype(np.int64))
        elif what=='competition_complete':
            self.competition=True
            e.diagnostic_margins=dict(branch=self.branch_margins,ambiguous=self.ambiguity_margins)
            pk(self.out/'DIAGNOSTIC_MARGINS.pkl',e.diagnostic_margins)
            pk(self.out/'COMPETITION_AUX.pkl',dict(aux=e.aux));js(self.out/'COMPETITION_COMPLETE.json',dict(utc=now(),complete=True,fit_count=e.fit_count,valid_count=data['valid_count'],ambiguous_count=data['ambiguous_count']))
        elif what=='commit':
            assert self.competition
            self.batch.append(data)
            if len(self.batch)==256:self.flush(e,data['cursor']);guard()
        elif what=='pass_complete':
            self.flush(e,data['valid_count']);save_merge(e,self.out)

def save_merge(e,out):
    pk(out/'STATE.pkl',state_of(e));checkpoint(out,['STATE.pkl','ORDERED_CANDIDATES.npz','COMPETITION_COMPLETE.json','COMPETITION_AUX.pkl','DIAGNOSTIC_MARGINS.pkl'],'S2_MERGE_COMPLETE',accepted=len(e.events),fit_count=e.fit_count)

def merge_then_export(engine,out,expensive):
    engine.observer=Journal(out);engine.pass_once(False)
    # S2 is fully durable, independently of failures in any later stage.
    expensive()


def branch_margin(e,reps,q):
    """Margin of the original three-arm predicate, diagnostic only."""
    from itertools import combinations
    xx=e.rx[reps];tt=e.rt[reps];margins=[]
    for center in q:
        dx=xx-center;rr=np.linalg.norm(dx,axis=1);sel=np.flatnonzero((rr>EPS)&(rr<=4.))
        if len(sel)<9:continue
        dirs=tt[sel]*np.where(np.sum(tt[sel]*dx[sel],1)>=0,1.,-1.)[:,None];clusters=[]
        for z,d in zip(sel,dirs):
            for axis,members in clusters:
                if np.dot(axis,d)>=np.cos(20*RAD):members.append(z);break
            else:clusters.append((d,[z]))
        arms=[(axis,zz) for axis,zz in clusters if len(zz)>=3 and np.ptp(rr[zz])>=2.-EPS]
        for triple in combinations(arms,3):
            span=min(float(np.ptp(rr[zz]))-2 for _,zz in triple)/2
            angle=min(float(np.degrees(np.arccos(np.clip(a@b,-1,1))))-20 for (a,_),(b,_) in combinations(triple,2))/20
            margins.append(min(span,angle))
    return max(margins,default=0.)
