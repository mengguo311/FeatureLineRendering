"""Finite-domain evidence is every original kernel center, never a clamped proxy."""
from runtime_io import *
from geometry_base import EPS,arc,sample,project,extended_s
from pair_model import model_group_guard,select_greedy,select_joint
from adapter import local_validator
from collections import defaultdict

def domain_summary(s,length,ids=None):
    left=np.maximum(0.,-s);right=np.maximum(0.,s-length);outside=(left>EPS)|(right>EPS)
    result=dict(left_p=float(left.max(initial=0)),right_p=float(right.max(initial=0)),outside_count=int(outside.sum()),sample_count=len(s))
    if ids is not None:
        result.update(worst_left_row=int(ids[left.argmax()]) if np.any(left>EPS) else None,worst_right_row=int(ids[right.argmax()]) if np.any(right>EPS) else None)
    return result

def model_compatibility(d,donor,q,guard=lambda:None):
    guard();leaf=d['leaves'][donor]
    if not leaf.valid:return False,'invalid_leaf',{}
    x=d['asset']['means'][leaf.rows]/d['p'];_,dist,tan,_,_=project(x,q)
    angle=np.degrees(np.arccos(np.clip(abs(np.sum(d['tangents'][leaf.rows]*tan,axis=1)),0,1)))
    met=dict(residual_max=float(dist.max(initial=0)),residual_q95=float(np.quantile(dist,.95)),tangent_max=float(angle.max(initial=0)))
    if not np.isfinite(list(met.values())).all():return False,'nonfinite',{}
    met['cost']=met['residual_max']+met['tangent_max']/30
    xx=sample(leaf.q);ss=project(xx,q)[0];old_ext=extended_s(xx,q)[0];center_ext=extended_s(x,q)[0];length=arc(q)[-1]
    # Support endpoints remain the original saved interval definition. Diagnose,
    # but do not change its mapping or mistake its clamping for new observations.
    ts=leaf.intervals.reshape(-1);ls=arc(leaf.q)
    support_points=np.stack([np.interp(ts,ls,leaf.q[:,k]) for k in range(3)],1)
    support_ext=extended_s(support_points,q)[0] if len(ts) else np.empty(0)
    clipped=np.clip(support_ext,0,length)
    dif=np.diff(ss);monotone=bool(np.all(dif>=-EPS) or np.all(dif<=EPS))
    common='residual' if met['residual_max']>1+EPS or met['residual_q95']>.5+EPS else ('tangent' if met['tangent_max']>30+EPS else None)
    old_reason=common or ('finite_domain' if old_ext.min()<-EPS or old_ext.max()>length+EPS else ('nonmonotone' if not monotone else 'ok'))
    new_reason=common or ('finite_domain_centers' if center_ext.min()<-EPS or center_ext.max()>length+EPS else ('nonmonotone' if not monotone else 'ok'))
    met['domain_audit']=dict(old_q=domain_summary(old_ext,length),centers=domain_summary(center_ext,length,leaf.rows),support_interval_endpoints=dict(**domain_summary(support_ext,length),absolute_clamping_p=float(abs(support_ext-clipped).sum()),unclamped_s=support_ext.tolist(),clamped_s=clipped.tolist()),old_compatible=old_reason=='ok',old_reason=old_reason,new_compatible=new_reason=='ok',new_reason=new_reason,monotone=monotone,domain_length_p=float(length),support_is_projected_proxy=True)
    if new_reason!='ok':return False,new_reason,met
    met['reverse']=bool(ss[-1]<ss[0]);return True,'ok',met

def build_extra_bank(d,ctx,models,guard=lambda:None):
    local=local_validator(d,d['p']);neighbors=defaultdict(set);bank=[];records=[]
    for e in d['overlaps']:
        neighbors[e['a']].add(e['b']);neighbors[e['b']].add(e['a'])
    for model in sorted(models,key=lambda x:tuple(x['model_key'])):
        if model['status']!='RECOVERED':continue
        q=np.array(model['q']);anchor=model['anchor'];partner=next(i for i in model['seed_pair'] if i!=anchor)
        if not local(d['leaves'][anchor])[0]:records.append(dict(model_key=model['model_key'],reason='anchor_local_invalid'));continue
        ok,why,hostmet=model_compatibility(d,anchor,q,guard)
        records.append(dict(model_key=model['model_key'],member=anchor,role='host',compatible=ok,reason=why,metrics=hostmet))
        if not ok:continue
        compatible=[]
        for donor in sorted(neighbors[anchor]):
            assert donor in ctx['carriers'],'COMPETITOR_OMITTED'
            if not local(d['leaves'][donor])[0]:ok,why,met=False,'donor_local_invalid',{}
            else:ok,why,met=model_compatibility(d,donor,q,guard)
            records.append(dict(model_key=model['model_key'],member=donor,compatible=ok,reason=why,metrics=met))
            if ok:compatible.append((met['cost'],donor,met))
        members=[anchor];costs=[];benefit=0.
        for cost,donor,met in sorted(compatible,key=lambda z:(z[0],z[1])):
            members.append(donor);costs.append(dict(carrier_id=donor,**met));benefit+=2-cost
            if partner not in members:continue
            ok,why,metrics=model_group_guard(d,q,members,guard)
            records.append(dict(model_key=model['model_key'],prefix_leaves=members.copy(),reason=why,benefit=float(benefit)))
            if ok and benefit>EPS:
                domain=project(d['leaves'][anchor].q[[0,-1]],q)[0];lo,hi=sorted(domain.tolist())
                outward=sum(max(0.,min(b,lo)-a)+max(0.,b-max(a,hi)) for a,b in metrics['supported_intervals'])
                metrics.update(anchor_outward_support_p=float(outward),model_outward_support_p=0.,outward_reference='old host endpoints projected to recovered model; not physical extension')
                bank.append(dict(hid=len(bank),anchor=anchor,model_key=model['model_key'],model_q=model['q'],model_kind=model['kind'],seed_pair=model['seed_pair'],leaves=sorted(members),prefix_order=members.copy(),benefit=float(benefit),costs=costs.copy(),host_metrics=hostmet,metrics=metrics))
    return bank,records
