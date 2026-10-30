"""Parent-owned plain scan24 merge runner. No subprocesses, no pooling."""
from common import *
import common
from core import Engine,arc,project,extended_s,union_intervals,EPS
from pipeline import load_state,restore,merge_then_export,checkpoint,verify_checkpoint
import argparse,traceback,signal


def load_inputs(c):
    verify(c['input_files']);verify(c['helper_files']);verify(c['source_files'])
    assert sha(c['decision_path'])==c['decision_sha256']
    a=dict(np.load(c['gaussians']));r=dict(np.load(c['representatives']));base=dict(np.load(c['baseline_membership']));prev=dict(np.load(c['previous_membership']))
    with np.load(c['controls']) as z:d=(z['control'][z['control_index']]*z['derivative_basis'][:,:,None]).sum(1)
    norm=np.linalg.norm(d,axis=1);t=d/np.maximum(norm[:,None],1e-15)
    assert len(a['means'])==c['kernel_count']==458490
    s=load_state(c['previous_state']);e=Engine(a,r,t,c['p']);restore(e,s);e.level=2
    arrays=dict(np.load(c['previous_carriers']));owner=np.full(len(a['means']),-1,np.int64)
    assert np.array_equal(arrays['carrier_id'],np.array(sorted(e.carriers)))
    for k,cid in enumerate(arrays['carrier_id']):
        cc=e.carriers[int(cid)];owner[cc.rows]=cc.cid
        assert cc.version==arrays['version'][k] and cc.valid==arrays['valid'][k] and cc.baseline==arrays['baseline'][k]
        np.testing.assert_array_equal(cc.reps,arrays['seedlets'][arrays['seed_offsets'][k]:arrays['seed_offsets'][k+1]])
        np.testing.assert_array_equal(cc.q*e.p,arrays['knots'][arrays['knot_offsets'][k]:arrays['knot_offsets'][k+1]])
        np.testing.assert_array_equal(e.rows_for(cc.reps),cc.rows)
        assert not cc.valid or (np.isfinite(t[cc.rows]).all() and np.all(norm[cc.rows]>0))
    np.testing.assert_array_equal(owner,prev['carrier_id']);np.testing.assert_array_equal(prev['line_kernel_id'],np.arange(len(owner)))
    assert sum(len(z.rows) for z in e.carriers.values())==np.count_nonzero(r['kernel_rep']>=0)
    for cc in e.carriers.values():
        primary=np.unique(prev['edge_id'][cc.rows]);assert len(primary)==1 and primary[0] in (-1,cc.cid)
    return a,r,base,prev,e


def carrier_arrays(e,path):
    cc=[e.carriers[k] for k in sorted(e.carriers)];ko=[0];ro=[0];so=[0];io=[0];oo=[0];q=[];rows=[];reps=[];intervals=[];origins=[]
    for n,c in enumerate(cc):
        if n%512==0:guard(20)
        q.extend(c.q*e.p);ko.append(len(q));rows.extend(c.rows);ro.append(len(rows));reps.extend(c.reps);so.append(len(reps));iv=e.support(c.reps,c.q)[0];intervals.extend(iv*e.p);io.append(len(intervals));origins.extend(c.origins);oo.append(len(origins))
    nz(path,carrier_id=np.array([c.cid for c in cc],np.int64),version=np.array([c.version for c in cc],np.int64),valid=np.array([c.valid for c in cc]),baseline=np.array([c.baseline for c in cc]),kind=np.array([c.kind for c in cc]),knot_offsets=np.array(ko),knots=np.array(q),row_offsets=np.array(ro),rows=np.array(rows,np.int64),seed_offsets=np.array(so),seedlets=np.array(reps,np.int32),interval_offsets=np.array(io),supported_intervals=np.array(intervals).reshape(-1,2),origin_offsets=np.array(oo),origins=np.array(origins,np.int64))


def export_membership(c,out,e,a,r,base,prev):
    ids,reason,aux,owner=e.primary(base['edge_id'])
    assert np.all(ids[prev['edge_id']>=0]>=0),'incumbent lost'
    assert np.all(ids[r['kernel_rep']<0]<0),'invalid activated'
    m=dict(line_kernel_id=np.arange(len(ids),dtype=np.int64),edge_id=ids,primitive_id=a['primitive_id'],previous_edge_id=prev['edge_id'],baseline_edge_id=base['edge_id'],carrier_id=owner,representative_id=r['kernel_rep'],reason_code=reason,baseline_reason_code=base['reason_code'],auxiliary_carrier_id=aux,provisional=np.ones(len(ids),bool))
    nz(out/'MEMBERSHIP.npz',**m);cold=dict(np.load(out/'MEMBERSHIP.npz'))
    for k in m:np.testing.assert_array_equal(cold[k],m[k])
    js(out/'REASON_SCHEMA.json',{'0':'assigned provisional','1':'insufficient seedlets/kernels/deduplicated support','2':'unresolved geometric alternatives','3':'source invalid / no valid representative','previous_reason_source':c['previous_membership'],'auxiliary_does_not_establish_topology':True})
    js(out/'LINEAGE.json',dict(predecessor=c['previous_lineage'],events=e.events));carrier_arrays(e,out/'CARRIERS.npz')
    return cold


def fresh_geometry(c,a):
    fresh=dict(np.load(c['gaussians']));assert set(fresh)==set(a);checks={}
    for k,v in a.items():
        if k=='colors':continue
        ok=fresh[k].dtype==v.dtype and fresh[k].shape==v.shape and fresh[k].tobytes()==v.tobytes();assert ok,k
        checks[k]=dict(dtype=str(v.dtype),shape=list(v.shape),sha256=hashlib.sha256(v.tobytes()).hexdigest(),bitexact=True)
    return fresh,dict(original_count=len(a['means']),row_order_bitexact=True,all_original_noncolor_fields=checks,geometry_source_sha256=sha(c['gaussians']),geometry_never_exported_or_refitted=True)


def render_whole(c,out,a,ids,render,cams,label):
    guard(5);cols=colors(ids).astype(np.float64);nz(out/'DISPLAY_COLORS.npz',colors=cols)
    js(out/'DISPLAY_SOURCE.json',dict(gaussians=c['gaussians'],sha256=c['input_files'][c['gaussians']],rows='all original rows, unchanged order',color_file='DISPLAY_COLORS.npz',floor=.0144,background=[1,1,1],label=label,camera_source=c['cameras'],camera_sha256=c['input_files'][c['cameras']]))
    cold=dict(np.load(out/'DISPLAY_COLORS.npz'));np.testing.assert_array_equal(cold['colors'],cols)
    asset={k:a[k] for k in ('means','covariance','opacity')};asset['colors']=cold['colors']
    for cam in cams:
        guard(5);save_image(out/f"{cam['view']}_FULL.png",render(asset,cam,(1,1,1),.0144)['rgb'])


def record_arrays(path,e):
    keys=sorted({k for r in e.records for k in r['metrics']});n=len(e.records)
    nz(path,a=np.array([r['a'] for r in e.records],np.int64),b=np.array([r['b'] for r in e.records],np.int64),operation=np.array([r['operation'] for r in e.records]),reason=np.array([r['reason'] for r in e.records]),cost=np.array([r['cost'] for r in e.records]),metric_names=np.array(keys),metrics=np.array([[r['metrics'].get(k,np.nan) for k in keys] for r in e.records]).reshape(n,len(keys)))


def tables(e,ids,pre,baseids):
    owner=np.full(len(ids),-1,np.int64)
    for cid,c in pre.items():owner[c.rows]=cid
    groups=[]
    for idx,cid in enumerate(np.unique(ids[ids>=0])):
        if idx%64==0:guard(10)
        c=e.carriers[int(cid)];iv,length,run,gap,total=e.support(c.reps,c.q);parents,counts=np.unique(e.a['primitive_id'][c.rows],return_counts=True)
        contributors=[]
        for pcid in np.unique(owner[c.rows]):
            pc=pre[int(pcid)];pi,pl,_,_,_=e.support(pc.reps,pc.q);mapped=e.support(pc.reps,c.q)[1]
            dom=project(pc.q,c.q)[0];lo,hi=float(dom.min()),float(dom.max());outside=float(sum(max(0,min(b,lo)-a)+max(0,b-max(a,hi)) for a,b in iv))
            contributors.append(dict(carrier_id=int(pcid),version=pc.version,kernels=len(pc.rows),seedlets=len(pc.reps),assigned_L1=bool(pc.baseline or (len(pc.reps)>=3 and len(pc.rows)>=6 and pl>=4-EPS)),baseline=pc.baseline,supported_length_p=pl,mapped_supported_length_p=mapped,mapped_finite_domain_p=[lo,hi],support_outside_domain_p=outside))
        contributors.sort(key=lambda z:(-z['supported_length_p'],z['carrier_id']));largest=contributors[0];gain=length-largest['supported_length_p'];substantial=[z for z in contributors if z['kernels']>=6 and z['supported_length_p']>=2]
        parent_contrib=[]
        for pid,n in zip(parents,counts):
            rr=c.reps[e.a['primitive_id'][e.r['mid'][c.reps]]==pid];pl=e.support(rr,c.q)[1] if len(rr) else 0
            parent_contrib.append(dict(parent=int(pid),kernels=int(n),supported_length_p=pl))
        original=[]
        for bid in np.unique(baseids[c.rows]):
            rr=c.reps[baseids[e.r['mid'][c.reps]]==bid];n=int(np.sum(baseids[c.rows]==bid));ln=e.support(rr,c.q)[1] if len(rr) else 0
            original.append(dict(v03_edge_id=int(bid),kernels=n,mapped_supported_length_p=ln))
        groups.append(dict(edge_id=int(cid),version=c.version,kernels=len(c.rows),seedlets=len(c.reps),model=c.kind,valid=c.valid,origins=list(c.origins),old_parent_count=len(parents),parent_contributions=parent_contrib,v03_contributions=original,L1_contributions=contributors,supported_length_p=length,longest_continuous_run_p=run,max_gap_p=gap,total_gap_p=total,carrier_length_p=float(arc(c.q)[-1]),extent_p=np.ptp(e.x[c.rows],axis=0).tolist(),bbox_min_p=e.x[c.rows].min(0).tolist(),bbox_max_p=e.x[c.rows].max(0).tolist(),gain_over_largest_L1_p=gain,outward_support_p=largest['support_outside_domain_p'],growth_gate=bool(gain>=max(4,.25*largest['supported_length_p']) and len(substantial)>=2 and largest['support_outside_domain_p']>EPS),provisional=True))
    return sorted(groups,key=lambda z:(-z['kernels'],z['edge_id']))


def geometry_margin(e,rec,pre):
    """Diagnostic only: measure exact pre-pass proposals, never change decisions."""
    a,b=pre[rec['a']],pre[rec['b']];reason=rec['reason'];met=rec['metrics']
    if reason=='accepted':return min(1-met.get('residual_max',0),(.5-met.get('residual_q95',0))/.5,(30-met.get('tangent_max',0))/30,(30-met.get('vertex_turn',0))/30,(60-met.get('window_turn',0))/60,(1.5-met.get('max_gap',0))/1.5)
    if reason=='parallel':
        if (arc(b.q)[-1],-b.cid)>(arc(a.q)[-1],-a.cid):a,b=b,a
        sb,db,tb=extended_s(b.q,a.q);return max(0,float(np.median(db))-.5)
    if reason=='endpoint_gap':return max(0,float(np.linalg.norm(a.q[[0,-1],None]-b.q[None,[0,-1]],axis=2).min())-1.5)
    if reason=='unsupported_gap':return max(0,met.get('max_gap',1.5)-1.5)
    if reason=='tangent':return max(0,met.get('tangent_max',30)-30)
    if reason=='endpoint_tangent':
        dist=np.linalg.norm(a.q[[0,-1],None]-b.q[None,[0,-1]],axis=2);ia,ib=np.unravel_index(dist.argmin(),dist.shape);qa=a.q if ia else a.q[::-1];qb=b.q if not ib else b.q[::-1];ta=qa[-1]-qa[-2];tb=qb[1]-qb[0];angle=np.degrees(np.arccos(np.clip(ta@tb/(np.linalg.norm(ta)*np.linalg.norm(tb)),-1,1)));return max(0,float(angle)-30)
    if reason=='turn':return max(met.get('vertex_turn',0)-30,met.get('window_turn',0)-60,0)
    if reason in ('branch','ambiguous'):return float(getattr(e,'diagnostic_margins',{}).get(reason,{}).get((rec['a'],rec['b']),float('inf')))
    return float(rec['cost'])


def diagnostics(c,out,e,a,ids,groups,pre,base,prev,render,cams):
    cross=[g for g in groups if g['old_parent_count']>1];length=sorted(cross,key=lambda g:(-g['supported_length_p'],g['edge_id']));selected={g['edge_id']:g for g in cross[:3]+length[:3]}
    for kind in ('line','polyline'):
        z=[g for g in length if g['model']==kind and g['outward_support_p']>EPS and len(g['L1_contributions'])>1]
        if z:selected[z[0]['edge_id']]=z[0]
    js(out/'VISUAL_SELECTION.json',dict(rule='top3 cross-parent count union top3 supported length plus largest straight/curved outward growth',edge_ids=list(selected),lineage_same_rows=True))
    def draw(rows,cols,name):
        asset={k:a[k][rows] for k in ('means','covariance','opacity')};asset['colors']=cols
        for cam in cams:
            guard(2);save_image(out/f"{name}_{cam['view']}.png",render(asset,cam,(1,1,1),.0144)['rgb'])
    for cid,g in selected.items():
        rows=e.carriers[cid].rows;nz(out/f'ROWS_{cid}.npz',rows=rows)
        for tag,labels in [('L0',base['edge_id']),('L1',prev['edge_id']),('M2',ids),('PARENTS',a['primitive_id'])]:draw(rows,colors(labels[rows]),f'GROUP_{cid}_{tag}')
        col=np.full((len(ids),3),.68);col[rows]=colors(ids[rows]);draw(np.arange(len(ids)),col,f'GROUP_{cid}_HIGHLIGHT')
    # Exact immutable L1 carrier versions are every proposal input in this single disjoint round.
    contexts=[]
    categories=[('parallel',('parallel',)),('branch',('branch',)),('crossing_tangent',('tangent','endpoint_tangent')),('gap',('endpoint_gap','unsupported_gap')),('ambiguity',('ambiguous',)),('accepted_worst_margin',('accepted',))]
    for name,reasons in categories:
        rr=[r for r in e.records if r['reason'] in reasons]
        if not rr:contexts.append(dict(category=name,status='NO_RECORDED_CASE'));continue
        chosen=min(rr,key=lambda r:(geometry_margin(e,r,pre),r['cost'],r['a'],r['b']))
        aa,bb=pre[chosen['a']],pre[chosen['b']];rows=np.r_[aa.rows,bb.rows];labels=np.r_[np.full(len(aa.rows),aa.cid),np.full(len(bb.rows),bb.cid)]
        nz(out/f'CONTEXT_{name}.npz',rows=rows,input_ids=np.array([aa.cid,bb.cid]),input_versions=np.array([aa.version,bb.version]),row_labels=labels)
        contexts.append(dict(category=name,status='SAVED',record=chosen,ranking_value=geometry_margin(e,chosen,pre),ranking_rule='minimum measured normalized guard margin; branch uses three-arm predicate margin; ambiguity uses 15-percent competition margin',input_versions=[[aa.cid,aa.version],[bb.cid,bb.version]],rows_file=f'CONTEXT_{name}.npz'))
        draw(rows,colors(labels),f'CONTEXT_{name}')
    js(out/'CONTEXT_SELECTION.json',contexts)


def run(c):
    common.configure(c);common.PHASE='input';unit=Path(c['unit']);run_dir=unit/'scenes/scan24';run_dir.mkdir(parents=True,exist_ok=True);start=time.time();stage='S0';facts=dict(status='error',completed=[],missing=['pooling','L3','L4','ficus','scan65'],science_claim='UNASSESSED',physical_identity_verified=False)
    try:
        guard(300);a,r,base,prev,e=load_inputs(c);pre=dict(e.carriers);guard(300)
        s0=run_dir/'S0';s0.mkdir(exist_ok=True)
        if (s0/'CHECKPOINT.json').exists():verify_checkpoint(s0,'S0_INPUTS')
        else:
            js(s0/'START.json',dict(utc=now(),pid=os.getpid(),stage='S0_INPUTS'))
            js(s0/'INPUT_REFERENCE.json',dict(files=c['input_files'],decision_sha256=c['decision_sha256'],source_files=c['source_files'],helper_files=c['helper_files'],baseline=c['baseline_membership'],predecessor=c['previous_membership']));checkpoint(s0,['INPUT_REFERENCE.json'],'S0_INPUTS')
        facts['completed'].append('S0_INPUTS');merge=run_dir/'stages/S2_MERGE';merge.mkdir(parents=True,exist_ok=True);stage='S1_S2';common.PHASE='topology'
        if (merge/'CHECKPOINT.json').exists():verify_checkpoint(merge,'S2_MERGE_COMPLETE');restore(e,load_state(merge/'STATE.pkl'))
        elif any(merge.iterdir()):raise RuntimeError('Incomplete topology artifacts preserved; cannot promote/resume incomplete competition')
        else:
            js(merge/'START.json',dict(utc=now(),pid=os.getpid(),stage='S1_S2'))
            merge_then_export(e,merge,lambda:None)
        verify_checkpoint(merge,'S2_MERGE_COMPLETE');state=load_state(merge/'STATE.pkl');assert len(state['events'])==len(e.events);restore(e,state);facts['completed'].append('S2_MERGE_COMPLETE');print('POST_MERGE_DURABLE',len(e.events),flush=True)
        common.PHASE='export';stage='S3';out=run_dir/'stages/M2_MERGE_ONLY'
        if out.exists() and not (out/'CHECKPOINT.json').exists():
            # Never overwrite interrupted export bytes; retry export only from verified complete S2.
            k=1
            while (run_dir/f'stages/M2_MERGE_ONLY_REEXPORT_{k}').exists():k+=1
            out=run_dir/f'stages/M2_MERGE_ONLY_REEXPORT_{k}'
        out.mkdir(parents=True,exist_ok=True);facts['output_stage']=str(out)
        cams=json.loads(Path(c['cameras']).read_text())['scan24'];assert [x['view'] for x in cams]==['0012','0036'];render=helpers(c)['render']
        if (out/'CHECKPOINT.json').exists():
            verify_checkpoint(out,'S3_NATIVE_DELIVERY');m=dict(np.load(out/'MEMBERSHIP.npz'));fresh,audit=fresh_geometry(c,a)
        else:
            js(out/'START.json',dict(utc=now(),pid=os.getpid(),stage='S3_NATIVE_DELIVERY'))
            m=export_membership(c,out,e,a,r,base,prev);fresh,audit=fresh_geometry(c,a);render_whole(c,out,fresh,m['edge_id'],render,cams,'M2_MERGE_ONLY')
            js(out/'GEOMETRY_AUDIT.json',audit);verify(c['input_files']);verify(c['helper_files']);verify(c['source_files'])
            checkpoint(out,['MEMBERSHIP.npz','CARRIERS.npz','LINEAGE.json','REASON_SCHEMA.json','DISPLAY_COLORS.npz','DISPLAY_SOURCE.json','GEOMETRY_AUDIT.json','0012_FULL.png','0036_FULL.png'],'S3_NATIVE_DELIVERY',all_rows=len(m['edge_id']),config_sha256=c['_config_sha256'])
        facts['completed'].append('S3_NATIVE_DELIVERY');facts['delivery_gate']=True;print('NATIVE_DELIVERY_COMPLETE',str(out),flush=True)
        stage='S4';common.PHASE='diagnostics';diag=out/'diagnostics';diag.mkdir(exist_ok=True)
        if any(diag.iterdir()):raise RuntimeError('Existing diagnostic prefix preserved; no overwrite')
        js(diag/'CANDIDATE_PROVENANCE.json',dict(predecessor_state=c['previous_state'],sha256=c['input_files'][c['previous_state']],versions='Every candidate refers to exact immutable L1 input carrier versions; single disjoint topology round',ordered_candidates=str(merge/'ORDERED_CANDIDATES.npz')))
        js(diag/'START.json',dict(utc=now(),pid=os.getpid(),stage='S4_DIAGNOSTICS'))
        record_arrays(diag/'CANDIDATE_STATUS.npz',e);groups=tables(e,m['edge_id'],pre,base['edge_id']);js(out/'GROUPS.json',dict(scene='scan24',stage='M2_MERGE_ONLY',p=e.p,groups=groups))
        comparison={}
        for tag,path,mp in [('L0',c['baseline_groups'],base),('L1',c['previous_groups'],prev)]:
            gg=json.loads(Path(path).read_text())['groups'];comparison[tag]=dict(assigned=int((mp['edge_id']>=0).sum()),coverage=float(np.mean(mp['edge_id']>=0)),UNKNOWN=int((mp['edge_id']<0).sum()),groups=len(gg),source=path,metrics=[{k:g[k] for k in ('edge_id','kernels','supported_length_p','longest_continuous_run_p','carrier_length_p','extent_p','max_gap_p','total_gap_p','parent_contributions') if k in g} for g in gg])
            ctrl=diag/tag;ctrl.mkdir();render_whole(c,ctrl,fresh,mp['edge_id'],render,cams,tag)
        gates=[g for g in groups if g['growth_gate']];metrics=dict(kernels=len(m['edge_id']),assigned=int((m['edge_id']>=0).sum()),coverage=float(np.mean(m['edge_id']>=0)),UNKNOWN=int((m['edge_id']<0).sum()),groups=len(groups),accepted_merges=len(e.events),fit_attempts=e.fit_count,reasons=dict(e.stats),changed_primary_rows=int((m['edge_id']!=prev['edge_id']).sum()),growth_gate_groups=[g['edge_id'] for g in gates],at_least_five_growth_groups=len(gates)>=5,straight_growth=any(g['model']=='line' for g in gates),curved_growth=any(g['model']=='polyline' for g in gates),visual_verdict='REQUIRES_SAME_SESSION_ANALYSIS',physical_identity_verified=False)
        js(out/'METRICS.json',metrics);js(diag/'COMPARISONS.json',comparison);diagnostics(c,diag,e,fresh,m['edge_id'],groups,pre,base,prev,render,cams)
        verify(c['input_files']);verify(c['helper_files']);verify(c['source_files']);fresh_geometry(c,a);js(diag/'HASHES_AFTER.json',dict(input_files=c['input_files'],source_files=c['source_files'],helper_files=c['helper_files']))
        checkpoint(diag,[str(f.relative_to(diag)) for f in sorted(diag.rglob('*')) if f.is_file()],'S4_DIAGNOSTICS');facts['completed'].append('S4_DIAGNOSTICS');facts.update(status='complete',science_claim='PENDING_VISUAL_ANALYSIS',metrics=metrics)
    except BaseException as exc:
        facts.update(status='partial' if facts['completed'] else 'error',failed_stage=stage,error=repr(exc),traceback=traceback.format_exc());raise
    finally:
        facts.update(utc=now(),elapsed_seconds=time.time()-start,parent_exit_authoritative=True,config_sha256=c['_config_sha256'])
        target=unit/'RUN_RESULT.json'
        if target.exists():target=unit/f'RUN_RESULT_REENTRY_{time.time_ns()}.json'
        js(target,facts)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);args=ap.parse_args();c=json.loads(Path(args.config).read_text());c['_config_sha256']=sha(args.config)
    def terminated(signum,frame):raise InterruptedError('parent signal '+str(signum))
    signal.signal(signal.SIGTERM,terminated);signal.signal(signal.SIGINT,terminated)
    run(c)
