"""Plain configured-scene transfer; no old-scene replay or child processes."""
from common import *
import common,argparse,signal,traceback
from transfer import (TransferEngine,load_ficus as load_scene,save_state,reset_level,
                      complete_pass,export_stage,statistics,diagnostics)
from transfer_behavior import resume_state
from pipeline import load_state,verify_checkpoint

def run(c):
    common.configure(c);unit=Path(c['unit']);scene=c['scene']
    facts=dict(status='error',completed=[],science_claim='PENDING_VISUAL_ANALYSIS',physical_identity_verified=False)
    start=time.time();stage='VERIFY'
    try:
        common.PHASE='L0';guard();verify(c['input_files']);verify(c['source_files']);verify(c['helper_files'])
        assert sha(c['decision_path'])==c['decision_sha256']
        stage='L0';a,r,base,chains,cams,e=load_scene(c);render=helpers(c)['render']
        root=unit/'scenes'/scene;states=root/'states';l0state=states/'L0'
        if (l0state/'CHECKPOINT.json').exists():
            verify_checkpoint(l0state,'L0_STATE');resume_state(e,load_state(l0state/'STATE.pkl'))
        else:
            l0state.mkdir(parents=True,exist_ok=True)
            if any(l0state.iterdir()):raise RuntimeError('INCOMPLETE_L0_PRESERVED')
            js(l0state/'START.json',dict(utc=now(),pid=os.getpid(),stage='L0_INITIALIZE'))
            e.initialize(base['edge_id'],chains);save_state(e,l0state,'L0_STATE')
        pre0=dict(e.carriers);l0=root/'stages/L0'
        m0,_=export_stage(c,l0,e,a,r,base,base,pre0,render,cams,'L0',c['baseline_membership'])
        statistics(l0,e,m0['edge_id'],pre0,base['edge_id'],'L0');facts['completed'].append(scene+'/L0')
        stage='L1';common.PHASE='L1';reset_level(e,1)
        complete_pass(e,states/'L1_PASS1','L1_PASS1_STATE',True);facts['completed'].append(scene+'/L1_PASS1_STATE')
        complete_pass(e,states/'L1_PASS2','L1_PASS2_STATE',True);facts['completed'].append(scene+'/L1_PASS2_STATE')
        l1=root/'stages/L1';m1,_=export_stage(c,l1,e,a,r,base,m0,pre0,render,cams,'L1',str(l0/'LINEAGE.json'))
        statistics(l1,e,m1['edge_id'],pre0,base['edge_id'],'L1');facts['completed'].append(scene+'/L1');pre1=dict(e.carriers)
        stage='M2';common.PHASE='M2';reset_level(e,2)
        complete_pass(e,states/'M2','M2_STATE',False);facts['completed'].append(scene+'/M2_STATE')
        common.PHASE='final';stage='M2_EXPORT';m2dir=root/'stages/M2_MERGE_ONLY'
        m2,_=export_stage(c,m2dir,e,a,r,base,m1,pre1,render,cams,'M2_MERGE_ONLY',str(l1/'LINEAGE.json'))
        facts['completed'].append(scene+'/M2_NATIVE');facts['delivery_gate']=True
        groups=statistics(m2dir,e,m2['edge_id'],pre1,base['edge_id'],'M2_MERGE_ONLY')
        stage='M2_DIAGNOSTICS';diagnostics(c,m2dir/'diagnostics',e,a,m2['edge_id'],groups,pre1,base,m1,render,cams)
        compare=dict(L0=json.loads((l0/'METRICS.json').read_text()),L1=json.loads((l1/'METRICS.json').read_text()),M2=json.loads((m2dir/'METRICS.json').read_text()),controls=c.get('reference_results',[]),old_scene_replay=False)
        js(root/'COMPARISONS.json',compare);verify(c['input_files']);verify(c['source_files']);verify(c['helper_files'])
        facts.update(status='complete',comparisons=compare,output_stage=str(m2dir));facts['completed'].append(scene+'/M2_DIAGNOSTICS')
    except BaseException as exc:
        facts.update(status='partial' if facts['completed'] else 'error',failed_stage=stage,error=repr(exc),traceback=traceback.format_exc());raise
    finally:
        requested=[scene+'/'+s for s in ('L0','L1_PASS1_STATE','L1_PASS2_STATE','L1','M2_STATE','M2_NATIVE','M2_DIAGNOSTICS')]
        facts['missing_requested_stages']=[v for v in requested if v not in facts['completed']]
        facts['not_requested']=['post_merge_pooling','L3','L4','old_scene_replays']
        facts.update(utc=now(),elapsed_seconds=time.time()-start,parent_exit_authoritative=True,config_sha256=c['_config_sha256'],scene=scene)
        target=unit/'RUN_RESULT.json'
        if target.exists():target=unit/f'RUN_RESULT_REENTRY_{time.time_ns()}.json'
        js(target,facts)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);arg=parser.parse_args()
    config=json.loads(Path(arg.config).read_text());config['_config_sha256']=sha(arg.config)
    def terminate(signum,frame):raise InterruptedError('parent signal '+str(signum))
    signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate);run(config)
