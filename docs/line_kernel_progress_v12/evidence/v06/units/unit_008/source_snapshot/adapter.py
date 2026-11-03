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

def validate_candidates(leaves,z,ordered,ambiguous):
    pairs=list(zip(z['a'].tolist(),z['b'].tolist()));op=list(zip(ordered['a'].tolist(),ordered['b'].tolist()))
    assert len(set(pairs))==len(pairs) and set(pairs)==set(op),'CANDIDATE_PAIR_COVERAGE'
    names=z['metric_names'].tolist();mi={k:i for i,k in enumerate(names)}
    assert {'residual_max','residual_q95','tangent_max'}<=mi.keys()
    edges=[];all_endpoint=[];valid_reasons={'accepted','round_conflict','ambiguous'}
    for k,(a,b) in enumerate(pairs):
        assert a in leaves and b in leaves and a<b
        if z['operation'][k]!='endpoint' or z['reason'][k] not in valid_reasons:continue
        assert leaves[a].valid and leaves[b].valid
        met=z['metrics'][k];cost=float(z['cost'][k]);expected=float(met[mi['residual_max']]+met[mi['tangent_max']]/30)
        assert np.isfinite(met).all() and abs(cost-expected)<=1e-12,'SUCCESSFUL_COST_SEMANTICS'
        assert met[mi['residual_max']]<=1+EPS and met[mi['residual_q95']]<=.5+EPS and met[mi['tangent_max']]<=30+EPS
        pa,pb=endpoint_ports(leaves[a],leaves[b]);e=Edge(k,a,pa,b,pb,cost);all_endpoint.append(e)
        if (a,b) not in ambiguous:edges.append(e)
    return edges,all_endpoint,pairs

def load(c,guard):
    verify(c['input_files']);verify(c['helper_files']);verify(c['source_files']);guard('readiness')
    assert sha(c['decision_path'])==c['decision_sha256']
    pc=json.loads(Path(c['predecessor_checkpoint']).read_text());old=json.loads(Path(c['predecessor_config']).read_text())
    assert pc['complete'] and pc['stage']=='M4_STATE' and pc['config_binding']==sha(c['predecessor_config']) and pc['decision_sha256']==old['decision_sha256']
    assert sha(old['decision_path'])==old['decision_sha256']
    cpdir=Path(c['predecessor_checkpoint']).parent
    verify({str(cpdir/k):h for k,h in pc['files'].items()})
    st=state_read(c['state']);arr=dict(np.load(c['carriers'],allow_pickle=False));m=dict(np.load(c['membership'],allow_pickle=False))
    a=dict(np.load(c['gaussians'],allow_pickle=False));r=dict(np.load(c['representatives'],allow_pickle=False))
    assert len(a['means'])==c['kernel_count']==458490
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
    z=dict(np.load(c['candidate_status'],allow_pickle=False));ordered=dict(np.load(c['ordered_candidates'],allow_pickle=False))
    amb={tuple(map(int,pair)) for pair in np.load(c['ambiguity'],allow_pickle=False)['pairs']}
    edges,all_endpoint,pairs=validate_candidates(leaves,z,ordered,amb)
    # Explicit source tangents are derived only in parent compute, once, without fitting.
    with np.load(c['controls'],allow_pickle=False) as control:der=(control['control'][control['control_index']]*control['derivative_basis'][:,:,None]).sum(axis=1)
    norm=np.linalg.norm(der,axis=1);t=der/np.maximum(norm[:,None],1e-15)
    for leaf in leaves.values():
        if leaf.valid:assert np.isfinite(t[leaf.rows]).all() and np.all(norm[leaf.rows]>0)
    state=dict(p=p,next_version=int(st['next_version']),leaves=leaves,asset=a,representatives=r,membership=m,owner=owner,arrays=arr,candidates=z,ordered=ordered,edges=edges,all_endpoint=all_endpoint,pairs=pairs,ambiguous=amb,tangents=t,aux=st['aux'])
    return state

def select(c,d):
    reference=np.load(c['reference_membership'],allow_pickle=False)['edge_id'];owner=d['owner']
    seeds=[('reference_group_'+str(gid),sorted(set(owner[reference==gid].tolist())-{-1})) for gid in c['seed_groups']]
    seeds += [('negative_'+str(a)+'_'+str(b),[a,b]) for a,b in c['negative_pairs']]
    priorities=set(x for _,ids in seeds[:len(c['seed_groups'])] for x in ids)
    uf=DSU()
    for e in d['edges']:uf.union(e.a,e.b)
    groups=defaultdict(list)
    for cid in uf.p:groups[uf.find(cid)].append(cid)
    incident=defaultdict(list)
    for k,(a,b) in enumerate(d['pairs']):incident[a].append(k);incident[b].append(k)
    contexts=[];covered=[]
    for ids in sorted((sorted(v) for v in groups.values()),key=lambda v:(not bool(set(v)&priorities),v[0])):
        core=set(ids);ee=[e.eid for e in d['edges'] if e.a in core]
        assert all((e.a in core)==(e.b in core) for e in d['edges']),'ELIGIBLE_BOUNDARY'
        records=sorted({k for cid in ids for k in incident[cid]});halo=set(ids)
        for k in records:halo.update(d['pairs'][k])
        covered.extend(ee)
        contexts.append(dict(context_id=len(contexts),labels=[tag for tag,ss in seeds if core.intersection(ss)],carriers=ids,evidence_carriers=sorted(halo),incident_record_ids=records,eligible_edge_ids=ee,all_successful_endpoint_edges=sum(e.a in core and e.b in core for e in d['all_endpoint']),incident_record_count=len(records),status='READY' if len(ids)<=c.get('decision_carrier_cap',128) else 'NOT_RUN_OVERSIZE',visual_truth='UNKNOWN_NOT_LABELED',proposal_scope='Complete eligible decision component; one-hop full incident-record evidence; saved capped v05 proposals only'))
    assert sorted(covered)==sorted(e.eid for e in d['edges']),'ELIGIBLE_COVERAGE'
    assert len(covered)==len(set(covered)),'DUPLICATE_DECISION_EDGE'
    return seeds,contexts

def local_validator(d,p):
    checked={}
    def validate(c):
        if c.cid not in checked:
            _,dist,tan,_,_=project(d['asset']['means'][c.rows]/p,c.q)
            angle=np.degrees(np.arccos(np.clip(abs(np.sum(d['tangents'][c.rows]*tan,axis=1)),0,1)))
            checked[c.cid]=(bool(dist.max(initial=0)<=1+EPS and np.quantile(dist,.95)<=.5+EPS and np.isfinite(angle).all() and angle.max(initial=0)<=30+EPS),'leaf_residual_tangent')
        return checked[c.cid]
    return validate
