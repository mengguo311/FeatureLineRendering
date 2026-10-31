"""Plain ficus scene transfer and saved-scan24 control replay. Parent owns compute."""
from common import *
import common
from core import Engine
from pipeline import Journal,load_state,state_of,checkpoint,verify_checkpoint
from transfer_behavior import scene_contract,select_groups,resume_state,crop_family
from runner import carrier_arrays,fresh_geometry,render_whole,record_arrays,tables,geometry_margin
from collections import Counter
import argparse,signal,traceback

class TransferEngine(Engine):
    def fit(self,*args,**kwargs):
        self.guard_calls=getattr(self,'guard_calls',0)+1
        if self.guard_calls%64==0:guard(20)
        return super().fit(*args,**kwargs)

class StageJournal(Journal):
    def __init__(self,out,stage,pooling):super().__init__(out);self.stage=stage;self.pooling=pooling
    def __call__(self,what,e,data):
        # Pool revalidations have changing versions. No misleading pre-pass margin labels.
        if self.pooling and what in ('branch_reject','ambiguity_detected'):return
        if what=='pass_complete':
            self.flush(e,data['valid_count']);save_state(e,self.out,self.stage,extra=['ORDERED_CANDIDATES.npz','COMPETITION_COMPLETE.json','COMPETITION_AUX.pkl','DIAGNOSTIC_MARGINS.pkl'])
        else:super().__call__(what,e,data)

def save_state(e,out,stage,extra=()):
    pk(out/'STATE.pkl',state_of(e));checkpoint(out,['STATE.pkl']+list(extra),stage,fit_count=e.fit_count,accepted_events=len(e.events),next_version=e.next_version)

def reset_level(e,level):
    e.level=level;e.fit_count=0;e.events=[];e.records=[];e.stats=Counter();e.diagnostic_margins={}
    if hasattr(e,'observer'):del e.observer

def complete_pass(e,path,stage,pooling):
    path.mkdir(parents=True,exist_ok=True)
    if (path/'CHECKPOINT.json').exists():
        verify_checkpoint(path,stage);resume_state(e,load_state(path/'STATE.pkl'));return
    if any(path.iterdir()):raise RuntimeError('INCOMPLETE_PASS_PRESERVED '+str(path))
    js(path/'START.json',dict(utc=now(),pid=os.getpid(),stage=stage,pooling=pooling,fit_count_before=e.fit_count,next_version=e.next_version))
    e.observer=StageJournal(path,stage,pooling);e.pass_once(pooling)
    verify_checkpoint(path,stage);resume_state(e,load_state(path/'STATE.pkl'))
    print('PASS_DURABLE',stage,'fits',e.fit_count,'events',len(e.events),flush=True)

def render_rows(a,rows,labels,render,cam,path):
    asset={k:a[k][rows] for k in ('means','covariance','opacity')};asset['colors']=colors(labels)
    guard(2);save_image(path,render(asset,cam,(1,1,1),.0144)['rgb'])

def group_figures(out,a,rowsets,labels,render,cams,ids,highlight=True):
    crops=[]
    for cid,rows in rowsets.items():
        nz(out/f'ROWS_{cid}.npz',rows=rows)
        for cam in cams:
            family=[]
            for tag,all_ids in labels.items():
                p=out/f"GROUP_{cid}_{tag}_{cam['view']}.png";render_rows(a,rows,all_ids[rows],render,cam,p);family.append(p)
            crops.append(crop_family(family,out/f"CROP_{cid}_{cam['view']}"))
            if highlight:
                col=np.full((len(ids),3),.68);col[rows]=colors(ids[rows]);asset={k:a[k] for k in ('means','covariance','opacity')};asset['colors']=col
                guard(2);save_image(out/f"GROUP_{cid}_HIGHLIGHT_{cam['view']}.png",render(asset,cam,(1,1,1),.0144)['rgb'])
    js(out/'CROPS.json',crops)

def control_replay(c):
    out=Path(c['unit'])/'controls/scan24';stage='SCAN24_SAVED_CONTROL'
    if (out/'CHECKPOINT.json').exists():verify_checkpoint(out,stage);return
    out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):raise RuntimeError('INCOMPLETE_CONTROL_PRESERVED')
    cc=c['control'];a=dict(np.load(cc['gaussians']));ids=dict(np.load(cc['M2_membership']))['edge_id'];base=dict(np.load(cc['L0_membership']))['edge_id'];prev=dict(np.load(cc['L1_membership']))['edge_id'];arrays=dict(np.load(cc['M2_carriers']))
    rowsets={}
    for cid in cc['group_ids']:
        k=int(np.flatnonzero(arrays['carrier_id']==cid)[0]);rows=arrays['rows'][arrays['row_offsets'][k]:arrays['row_offsets'][k+1]];np.testing.assert_array_equal(np.sort(rows),np.flatnonzero(ids==cid));rowsets[cid]=rows
    cams=json.loads(Path(c['cameras']).read_text())['scan24'];assert [z['view'] for z in cams]==['0012','0036']
    js(out/'START.json',dict(utc=now(),pid=os.getpid(),mode='SAVED_MEMBERSHIP_REPLAY_NO_FITTING'))
    group_figures(out,a,rowsets,dict(L0=base,L1=prev,M2=ids,PARENTS=a['primitive_id']),helpers(c)['render'],cams,ids)
    source=dict(gaussians=cc['gaussians'],sha256=c['input_files'][cc['gaussians']],membership_files={k:v for k,v in cc.items() if k.endswith('membership')},group_ids=cc['group_ids'],geometry_changed=False,fit_calls=0)
    js(out/'DISPLAY_SOURCE.json',source);verify(c['input_files']);checkpoint(out,[str(p.relative_to(out)) for p in sorted(out.rglob('*')) if p.is_file()],stage)

def load_ficus(c):
    a=dict(np.load(c['gaussians']));r=dict(np.load(c['representatives']));base=dict(np.load(c['baseline_membership']));chains=dict(np.load(c['chains']));cams=json.loads(Path(c['cameras']).read_text())[c['scene']];scene_contract(c,a,cams)
    with np.load(c['controls']) as z:d=(z['control'][z['control_index']]*z['derivative_basis'][:,:,None]).sum(1)
    n=np.linalg.norm(d,axis=1);t=d/np.maximum(n[:,None],1e-15)
    return a,r,base,chains,cams,TransferEngine(a,r,t,c['p'])

def export_stage(c,out,e,a,r,base,prev,pre,render,cams,label,predecessor):
    stage=label+'_NATIVE'
    if (out/'CHECKPOINT.json').exists():
        verify_checkpoint(out,stage);return dict(np.load(out/'MEMBERSHIP.npz')),read_groups(out)
    out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):raise RuntimeError('INCOMPLETE_EXPORT_PRESERVED '+str(out))
    js(out/'START.json',dict(utc=now(),pid=os.getpid(),stage=stage))
    ids,reason,aux,owner=e.primary(base['edge_id'])
    if label=='L0':np.testing.assert_array_equal(ids,base['edge_id']);reason=base['reason_code'].copy()
    assert np.all(ids[prev['edge_id']>=0]>=0);assert np.all(ids[r['kernel_rep']<0]<0)
    m=dict(line_kernel_id=np.arange(len(ids),dtype=np.int64),edge_id=ids,primitive_id=a['primitive_id'],previous_edge_id=prev['edge_id'],baseline_edge_id=base['edge_id'],carrier_id=owner,representative_id=r['kernel_rep'],reason_code=reason,baseline_reason_code=base['reason_code'],auxiliary_carrier_id=aux,provisional=np.ones(len(ids),bool))
    nz(out/'MEMBERSHIP.npz',**m);cold=dict(np.load(out/'MEMBERSHIP.npz'))
    for k in m:np.testing.assert_array_equal(cold[k],m[k])
    js(out/'REASON_SCHEMA.json',dict(primary={0:'assigned provisional',1:'insufficient support',2:'unresolved alternatives',3:'invalid source / no representative'},L0_reason_codes='original v03 values; baseline_reason_code always retained',auxiliary_does_not_establish_topology=True))
    carrier_arrays(e,out/'CARRIERS.npz');js(out/'LINEAGE.json',dict(predecessor=predecessor,events=e.events))
    fresh,audit=fresh_geometry(c,a);render_whole(c,out,fresh,cold['edge_id'],render,cams,label);js(out/'GEOMETRY_AUDIT.json',audit)
    verify(c['input_files']);verify(c['helper_files']);verify(c['source_files'])
    checkpoint(out,['MEMBERSHIP.npz','CARRIERS.npz','LINEAGE.json','DISPLAY_COLORS.npz','DISPLAY_SOURCE.json','GEOMETRY_AUDIT.json','REASON_SCHEMA.json']+[v+'_FULL.png' for v in c['views']],stage,all_rows=len(ids))
    print('NATIVE_DELIVERY',label,len(ids),flush=True)
    return cold,None

def read_groups(out):
    return json.loads((out/'GROUPS.json').read_text())['groups'] if (out/'GROUPS.json').exists() else None

def statistics(out,e,ids,pre,baseids,label):
    if (out/'STATS_CHECKPOINT.json').exists():
        cp=json.loads((out/'STATS_CHECKPOINT.json').read_text());verify({str(out/k):v for k,v in cp['files'].items()});return read_groups(out)
    groups=tables(e,ids,pre,baseids)
    if label!='M2_MERGE_ONLY':
        for g in groups:
            g['predecessor_contributions']=g.pop('L1_contributions');g['gain_over_predecessor_p']=g.pop('gain_over_largest_L1_p');g['growth_gate']=False
    js(out/'GROUPS.json',dict(scene=common.CFG['scene'] if common.CFG else 'fixture',stage=label,p=e.p,groups=groups))
    metric=dict(stage=label,kernels=len(ids),assigned=int((ids>=0).sum()),UNKNOWN=int((ids<0).sum()),coverage=float(np.mean(ids>=0)),groups=len(groups),fit_attempts=e.fit_count,reasons=dict(e.stats),accepted_events=len(e.events),growth_gate_groups=[g['edge_id'] for g in groups if g['growth_gate']],physical_identity_verified=False,all_unknown_seedlets_eligible=True)
    js(out/'METRICS.json',metric);record_arrays(out/'CANDIDATE_STATUS.npz',e)
    js(out/'STATS_CHECKPOINT.json',dict(complete=True,files={n:sha(out/n) for n in ['GROUPS.json','METRICS.json','CANDIDATE_STATUS.npz']}));return groups

def diagnostics(c,out,e,a,ids,groups,pre,base,prev,render,cams):
    if (out/'CHECKPOINT.json').exists():verify_checkpoint(out,'M2_DIAGNOSTICS');return
    out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):raise RuntimeError('INCOMPLETE_DIAGNOSTICS_PRESERVED')
    chosen=select_groups(groups);js(out/'VISUAL_SELECTION.json',dict(rule=c['visual_selection'],edge_ids=[g['edge_id'] for g in chosen],growth_edge_ids=[g['edge_id'] for g in chosen if g['growth_gate']],missing_models=[kind for kind in ('line','polyline') if not any(g['growth_gate'] and g['model']==kind for g in chosen)]))
    group_figures(out,a,{g['edge_id']:e.carriers[g['edge_id']].rows for g in chosen},dict(L0=base['edge_id'],L1=prev['edge_id'],M2=ids,PARENTS=a['primitive_id']),render,cams,ids)
    contexts=[];crops=[]
    for name,reasons in [('parallel',('parallel',)),('branch',('branch',)),('crossing_tangent',('tangent','endpoint_tangent')),('gap',('endpoint_gap','unsupported_gap')),('ambiguity',('ambiguous',)),('accepted_worst_margin',('accepted',))]:
        rr=[r for r in e.records if r['reason'] in reasons]
        if not rr:contexts.append(dict(category=name,status='NO_RECORDED_CASE'));continue
        rec=min(rr,key=lambda r:(geometry_margin(e,r,pre),r['cost'],r['a'],r['b']));aa,bb=pre[rec['a']],pre[rec['b']];rows=np.r_[aa.rows,bb.rows];labels=np.r_[np.full(len(aa.rows),aa.cid),np.full(len(bb.rows),bb.cid)]
        nz(out/f'CONTEXT_{name}.npz',rows=rows,input_ids=np.array([aa.cid,bb.cid]),input_versions=np.array([aa.version,bb.version]),row_labels=labels)
        contexts.append(dict(category=name,record=rec,input_versions=[[aa.cid,aa.version],[bb.cid,bb.version]],ranking_value=geometry_margin(e,rec,pre),rows_file=f'CONTEXT_{name}.npz'))
        for cam in cams:
            file=out/f"CONTEXT_{name}_{cam['view']}.png";render_rows(a,rows,labels,render,cam,file);crops.append(crop_family([file],out/f"CROP_CONTEXT_{name}_{cam['view']}"))
    js(out/'CONTEXT_SELECTION.json',contexts);js(out/'CONTEXT_CROPS.json',crops);checkpoint(out,[str(p.relative_to(out)) for p in sorted(out.rglob('*')) if p.is_file()],'M2_DIAGNOSTICS')

def run(c):
    common.configure(c);unit=Path(c['unit']);facts=dict(status='error',completed=[],missing=['L3','L4','scan65'],science_claim='PENDING_VISUAL_ANALYSIS',physical_identity_verified=False);start=time.time();stage='CONTROL'
    try:
        common.PHASE='control';guard();verify(c['input_files']);verify(c['source_files']);verify(c['helper_files']);assert sha(c['decision_path'])==c['decision_sha256']
        control_replay(c);facts['completed'].append('SCAN24_SAVED_CONTROL');stage='L0';common.PHASE='L0';a,r,base,chains,cams,e=load_ficus(c);render=helpers(c)['render'];root=unit/'scenes'/c['scene'];states=root/'states';l0state=states/'L0'
        if (l0state/'CHECKPOINT.json').exists():verify_checkpoint(l0state,'L0_STATE');resume_state(e,load_state(l0state/'STATE.pkl'))
        else:
            l0state.mkdir(parents=True,exist_ok=True)
            if any(l0state.iterdir()):raise RuntimeError('INCOMPLETE_L0_PRESERVED')
            js(l0state/'START.json',dict(utc=now(),pid=os.getpid(),stage='L0_INITIALIZE'));e.initialize(base['edge_id'],chains);save_state(e,l0state,'L0_STATE')
        pre0=dict(e.carriers);l0=root/'stages/L0';m0,_=export_stage(c,l0,e,a,r,base,base,pre0,render,cams,'L0',c['baseline_membership']);statistics(l0,e,m0['edge_id'],pre0,base['edge_id'],'L0');facts['completed'].append('ficus/L0')
        stage='L1';common.PHASE='L1';reset_level(e,1)
        complete_pass(e,states/'L1_PASS1','L1_PASS1_STATE',True);facts['completed'].append('ficus/L1_PASS1_STATE')
        complete_pass(e,states/'L1_PASS2','L1_PASS2_STATE',True);facts['completed'].append('ficus/L1_PASS2_STATE')
        l1=root/'stages/L1';m1,_=export_stage(c,l1,e,a,r,base,m0,pre0,render,cams,'L1',str(l0/'LINEAGE.json'));statistics(l1,e,m1['edge_id'],pre0,base['edge_id'],'L1');facts['completed'].append('ficus/L1');pre1=dict(e.carriers)
        stage='M2';common.PHASE='M2';reset_level(e,2);complete_pass(e,states/'M2','M2_STATE',False);facts['completed'].append('ficus/M2_STATE')
        common.PHASE='final';stage='M2_EXPORT';m2dir=root/'stages/M2_MERGE_ONLY';m2,_=export_stage(c,m2dir,e,a,r,base,m1,pre1,render,cams,'M2_MERGE_ONLY',str(l1/'LINEAGE.json'));facts['completed'].append('ficus/M2_NATIVE');facts['delivery_gate']=True
        groups=statistics(m2dir,e,m2['edge_id'],pre1,base['edge_id'],'M2_MERGE_ONLY');stage='M2_DIAGNOSTICS';diagnostics(c,m2dir/'diagnostics',e,a,m2['edge_id'],groups,pre1,base,m1,render,cams)
        compare=dict(L0=json.loads((l0/'METRICS.json').read_text()),L1=json.loads((l1/'METRICS.json').read_text()),M2=json.loads((m2dir/'METRICS.json').read_text()),controls='Saved scan24 only, no new scan24 fitting')
        js(root/'COMPARISONS.json',compare);verify(c['input_files']);verify(c['source_files']);verify(c['helper_files']);facts.update(status='complete',comparisons=compare,output_stage=str(m2dir));facts['completed'].append('ficus/M2_DIAGNOSTICS')
    except BaseException as exc:
        facts.update(status='partial' if facts['completed'] else 'error',failed_stage=stage,error=repr(exc),traceback=traceback.format_exc());raise
    finally:
        requested=['SCAN24_SAVED_CONTROL','ficus/L0','ficus/L1_PASS1_STATE','ficus/L1_PASS2_STATE','ficus/L1','ficus/M2_STATE','ficus/M2_NATIVE','ficus/M2_DIAGNOSTICS']
        facts['missing_requested_stages']=[v for v in requested if v not in facts['completed']]
        facts['not_requested']=['post_merge_pooling','L3','L4','scan65']
        facts.update(utc=now(),elapsed_seconds=time.time()-start,parent_exit_authoritative=True,config_sha256=c['_config_sha256']);target=unit/'RUN_RESULT.json'
        if target.exists():target=unit/f'RUN_RESULT_REENTRY_{time.time_ns()}.json'
        js(target,facts)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);arg=ap.parse_args();c=json.loads(Path(arg.config).read_text());c['_config_sha256']=sha(arg.config)
    def terminate(signum,frame):raise InterruptedError('parent signal '+str(signum))
    signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate);run(c)
