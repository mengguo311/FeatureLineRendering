"""Read sealed M4 carriers and M5-on-M4 records; no fitting or candidate generation."""
from runtime_io import *
from port_paths import Leaf,Edge,endpoint_ports,DSU,complete_contexts
from geometry_base import project,arc,EPS
from dataclasses import dataclass
from collections import defaultdict,Counter
import pickle
@dataclass
class Carrier:
    cid:int
    reps:np.ndarray
    rows:np.ndarray
    q:np.ndarray
    kind:str
    valid:bool
    baseline:bool
    origins:tuple
    version:int=0
class Restricted(pickle.Unpickler):
    def find_class(self,module,name):
        if (module,name)==('core','Carrier'):return Carrier
        allowed={('collections','defaultdict'):defaultdict,('collections','Counter'):Counter,('builtins','list'):list,('numpy','ndarray'):np.ndarray,('numpy','dtype'):np.dtype}
        for prefix in ('numpy.core','numpy._core'):
            from numpy._core import multiarray,numeric
            allowed.update({(prefix+'.multiarray','_reconstruct'):multiarray._reconstruct,(prefix+'.multiarray','scalar'):multiarray.scalar,(prefix+'.numeric','_frombuffer'):numeric._frombuffer})
        if (module,name) not in allowed:raise pickle.UnpicklingError('FORBIDDEN '+module+'.'+name)
        return allowed[module,name]
def state_read(path):
    with open(path,'rb') as f:s=Restricted(f).load()
    assert {'carriers','aux','next_version'}<=s.keys()
    for cid,c in s['carriers'].items():
        assert type(c) is Carrier and c.cid==cid
        assert set(vars(c))=={'cid','reps','rows','q','kind','valid','baseline','origins','version'}
    return s

def load(c,guard):
    verify(c['input_files']);verify(c['helper_files']);verify(c['source_files']);guard('readiness')
    assert sha(c['decision_path'])==c['decision_sha256']
    pc=json.loads(Path(c['predecessor_checkpoint']).read_text());old=json.loads(Path(c['predecessor_config']).read_text())
    assert pc['complete'] and pc['stage']==c.get('predecessor_checkpoint_stage','M5_STATE') and pc['config_binding']==sha(c['predecessor_config']) and pc['decision_sha256']==old['decision_sha256']
    assert sha(old['decision_path'])==old['decision_sha256']
    cpdir=Path(c['predecessor_checkpoint']).parent
    verify({str(cpdir/k):h for k,h in pc['files'].items()})
    st=state_read(c['state']);arr=dict(np.load(c['carriers'],allow_pickle=False));m=dict(np.load(c['membership'],allow_pickle=False))
    a=dict(np.load(c['gaussians'],allow_pickle=False));r=dict(np.load(c['representatives'],allow_pickle=False))
    assert len(a['means'])==c['kernel_count']
    n=len(a['means']);owner=np.full(n,-1,np.int64);leaves={};p=c['p']
    np.testing.assert_array_equal(arr['carrier_id'],np.array(sorted(st['carriers'])))
    for j,cid0 in enumerate(arr['carrier_id']):
        if j%512==0:guard('readiness')
        cid=int(cid0);cc=st['carriers'][cid]
        assert not np.any(owner[cc.rows]>=0);owner[cc.rows]=cid
        for key in ('version','valid','baseline','kind'):assert getattr(cc,key)==arr[key][j]
        for field,key,off in [('rows','rows','row_offsets'),('reps','seedlets','seed_offsets'),('origins','origins','origin_offsets')]:np.testing.assert_array_equal(getattr(cc,field),arr[key][arr[off][j]:arr[off][j+1]])
        np.testing.assert_array_equal(cc.q*p,arr['knots'][arr['knot_offsets'][j]:arr['knot_offsets'][j+1]])
        rr=np.concatenate([r['member_rows'][r['member_offsets'][k]:r['member_offsets'][k+1]] for k in cc.reps])
        np.testing.assert_array_equal(cc.rows,rr)
        iv=arr['supported_intervals'][arr['interval_offsets'][j]:arr['interval_offsets'][j+1]]/p
        leaves[cid]=Leaf(cid,cc.version,cc.rows,cc.reps,cc.q,cc.valid,cc.baseline,iv)
        labels=np.unique(m['edge_id'][cc.rows]);assert len(labels)==1 and labels[0] in (-1,cid)
    np.testing.assert_array_equal(owner,m['carrier_id']);np.testing.assert_array_equal(m['line_kernel_id'],np.arange(n))
    assert np.all(m['edge_id'][r['kernel_rep']<0]<0)
    # Explicit source tangents are derived only in parent compute, once, without fitting.
    with np.load(c['controls'],allow_pickle=False) as control:der=(control['control'][control['control_index']]*control['derivative_basis'][:,:,None]).sum(axis=1)
    norm=np.linalg.norm(der,axis=1);t=der/np.maximum(norm[:,None],1e-15)
    for leaf in leaves.values():
        if leaf.valid:assert np.isfinite(t[leaf.rows]).all() and np.all(norm[leaf.rows]>0)
    assert len(leaves)==c['carrier_count'] and len(arr['knots'])==c['knot_count']
    assert int(st['next_version'])==c['next_version']
    assert np.isfinite(a['means']).all() and np.isfinite(a['covariance']).all() and np.isfinite(a['opacity']).all()
    state=dict(p=p,next_version=int(st['next_version']),leaves=leaves,asset=a,representatives=r,membership=m,owner=owner,arrays=arr,tangents=t,aux=st['aux'])
    return state

def local_validator(d,p):
    checked={}
    def validate(c):
        if c.cid not in checked:
            _,dist,tan,_,_=project(d['asset']['means'][c.rows]/p,c.q)
            angle=np.degrees(np.arccos(np.clip(abs(np.sum(d['tangents'][c.rows]*tan,axis=1)),0,1)))
            checked[c.cid]=(bool(dist.max(initial=0)<=1+EPS and np.quantile(dist,.95)<=.5+EPS and np.isfinite(angle).all() and angle.max(initial=0)<=30+EPS),'leaf_residual_tangent')
        return checked[c.cid]
    return validate
