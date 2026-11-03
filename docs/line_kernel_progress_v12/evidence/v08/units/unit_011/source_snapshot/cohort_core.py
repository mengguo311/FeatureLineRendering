"""Frozen metadata cohort and additive seed registration; no numerical-policy changes."""
import copy,math
import switch_core as sc

def select_cohort(events,groups,versions,used,per_kind=16):
    endpoints={(int(e['output'][0]),int(e['output'][1])) for e in events if e['operation']=='endpoint'}
    records=[];seen=set()
    for g in sorted(groups,key=lambda z:(z['edge_id'],z['version'])):
        cid=int(g['edge_id']);version=int(g['version']);key=(cid,version)
        assert key not in seen,'DUPLICATE_GROUP_VERSION'
        seen.add(key);support=float(g['supported_length_p']);assert math.isfinite(support) and support>=0
        count=sum(int(x['kernels'])>=12 and float(x['mapped_supported_length_p'])>=2 for x in g['M4_contributions'])
        row=dict(carrier_id=cid,version=version,model=g['model'],supported_length_p=support,substantial_M4_contributions=count,selected=False)
        why=('no_endpoint_event' if key not in endpoints else 'inactive_or_version_mismatch' if versions.get(cid)!=version else 'saved_invalid' if not g['valid'] else 'starting_used_leaf' if cid in used else 'insufficient_M4_contributions' if count<2 else 'unsupported_model_kind' if g['model'] not in ('line','polyline') else 'eligible')
        row['reason']=why;records.append(row)
    selected=[]
    for kind in ('line','polyline'):
        queue=sorted((r for r in records if r['reason']=='eligible' and r['model']==kind),key=lambda r:(-r['supported_length_p'],r['carrier_id']))
        for rank,r in enumerate(queue):
            r['rank_within_kind']=rank;r['selected']=rank<per_kind;r['reason']='selected' if r['selected'] else 'unselected_cohort_cap'
            if r['selected']:selected.append(copy.deepcopy(r))
    missing=[dict(carrier_id=i,version=v,reason='endpoint_output_absent_from_saved_groups') for i,v in sorted(endpoints-seen)]
    return sorted(selected,key=lambda r:r['carrier_id']),dict(records=records,endpoint_outputs_without_group=missing,per_kind_cap=per_kind,selection_uses_continuation_results=False)

def augment(saved,d,selected,oracle):
    state=sc.reopen(saved);receipts=[]
    for item in sorted(selected,key=lambda z:z['carrier_id']):
        sid=item['carrier_id'];leaf=d['leaves'][sid]
        assert sid not in state['used'] and leaf.version==item['version']
        chain=[(sid,False)];ok,why,met=oracle(chain)
        state['chains'][sid]=chain;state['versions'][sid]=leaf.version
        state['curves'][sid]=leaf.q.tolist();state['ports'][sid]=[copy.deepcopy(d['ports'][(sid,p)]) for p in (0,1)]
        state['metrics'][sid]=dict(seed_status='valid' if ok else why,**met)
        state['accepted'][sid]=0;state['used'].add(sid)
        if not ok:state['stopped'].update({(sid,0),(sid,1)})
        receipts.append(dict(carrier_id=sid,version=leaf.version,status='ready' if ok else 'NOT_RUN',reason=why,port_known=[p['known'] for p in state['ports'][sid]],replacement_selected=False))
    assert state['next_version']==saved['next_version'] and state['events']==saved['events']
    return state,receipts

def frontier_signature(state,sid):
    return dict(version=int(state['versions'][sid]),used=sorted(state['used']))

def replay_visits(paths,d,state,index,endpoints,guard):
    from pathlib import Path
    import json
    from runtime_io import sha
    receipts=[];contexts={sid:set(i for i,_ in chain) for sid,chain in state['chains'].items()}
    for path in paths:
        old=json.loads(Path(path).read_text());sid=old['seed'];side=old['side'];guard()
        assert old['version']==state['versions'][sid]
        lib=sc.candidates(d,state,sid,side,index,endpoints,guard,256,3)
        for k,v in lib.items():assert json.loads(json.dumps(v,allow_nan=False))==old[k],'COHORT_PRIOR_REPLAY '+k
        choice=sc.choices(lib['records']);assert choice==old['shadow'] and choice['BASE'] is None and choice['HISTORY'] is None
        for q in lib['queries']:contexts[sid].update(z[0] for z in q['neighbors'])
        receipts.append(dict(seed=sid,side=side,path=str(path),sha256=sha(path),matched=True))
    return dict(status='MATCHED',visits=receipts,performed_before_new_seed_protection=True),contexts
