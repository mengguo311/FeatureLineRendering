"""Snapshot a verified live pilot runner into reviewable small artifacts."""
import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent/'stage2'))
from safety import atomic_json,sha256


def main():
    state_dir=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/stage2/state')
    artifact=ROOT/'artifacts/radegs_paper_reproduction_v01'
    config_path=state_dir/'runner_config.json'
    config=json.loads(config_path.read_text())
    state=json.loads((state_dir/'runner_state.json').read_text())
    mismatches=[p for p,h in config['immutable_files'].items() if sha256(p)!=h]
    assert not mismatches,mismatches
    assert sha256(config_path)==state['config_sha256']
    pid=state['runner_pid'];assert os.stat('/proc/'+str(pid)).st_uid==os.getuid()
    pane=subprocess.check_output(['tmux','display-message','-p','-t','radegs-scan24-queue-v01:0',
                                  '#{pane_id}:#{pane_pid}:#{pane_dead}'],text=True).strip()
    pane_id,pane_pid,dead=pane.split(':');assert int(pane_pid)==pid and dead=='0'
    locked=False
    with open(state_dir/'runner.lock','r') as f:
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:locked=True
    assert locked
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
    model=Path(config['model'])
    training_started=(model/'iteration_loss.jsonl').exists()
    gpu_started=bool(list((state_dir.parent/'logs/runner').glob('*.log')))
    verification={'utc':utc,'immutable_files_checked':len(config['immutable_files']),'mismatches':mismatches,
                  'runner_pid':pid,'pid_owner':os.getuid(),'tmux_pane':pane,'flock_held':locked,
                  'config_sha256':sha256(config_path),'state_age_seconds':time.time()-state['updated_unix']}
    atomic_json(state_dir/'observed_runner_verification.json',verification)
    atomic_json(artifact/'stage2_evidence/observed_runner_verification.json',verification)
    header={'observed_utc':utc,'kind':'actual_live_runner_not_completion_evidence',
            'tmux_session':'radegs-scan24-queue-v01','tmux_window':0,'tmux_pane':pane_id,'runner_pid':pid,
            'config':str(config_path),'config_sha256':sha256(config_path),
            'supervisor_script':str(state_dir.parent/'run_scan24.sh'),
            'supervisor_script_sha256':sha256(state_dir.parent/'run_scan24.sh'),
            'supervisor_log':str(state_dir.parent/'logs/runner_supervisor_final.log'),
            'source_clone_head':'2d4bc087f1b4bd62c96054fbe89d273490526b81','source_variant':config['cwd'],
            'train_command':config['train_command'],'stage_commands':config['stage_commands'],
            'selected_gpu_uuid':state.get('selected_gpu_uuid'),'training_started':training_started,
            'GPU_workload_started':gpu_started,'scientificdone':False,
            'prior_waiter':'Prior PID 27387 was stopped while it had no child, its state archived, then this final-binary configuration was launched in the same task-specific tmux pane.'}
    atomic_json(artifact/'MODEL_LAUNCH/header.json',header)
    status={'updated_utc':utc,'stage':2,'stage1completed':True,'stage2_preparation_completed':True,
            'status':state['status'],'GPU_validation':'PENDING_EXCLUSIVE_IDLE_GPU' if not gpu_started else 'read live stage reports',
            'training_started':training_started,'training_completed':(state_dir/'train.seal.json').exists(),
            'evaluation_completed':(state_dir/'eval.seal.json').exists(),'scientificdone':False,
            'runner_pid':pid,'tmux_session':header['tmux_session'],'tmux_pane':pane_id,
            'selected_gpu_uuid':state.get('selected_gpu_uuid'),'child_pid':state.get('child_pid'),
            'config':str(config_path),'config_sha256':sha256(config_path),'live_state':str(state_dir/'runner_state.json'),
            'stage_pending':state['stage'],'snapshot_unix':state['updated_unix'],'automatic_scene_limit':1,
            'full_suite_goal_retained':True,'full_suite_completed':False,
            'GPU_snapshot_summary':[{'uuid':g['uuid'],'memory_mib':g['memory_mib'],'util_percent':g['util_percent'],
                                     'context_count':len(g['contexts'])} for g in state.get('gpu_snapshot',[])],
            'nextstep':'automatic_single_scan24_chain_subject_to_GPU_idle_and_verified_stage_gates',
            'nextstepawaitinguser':False,'authorization':'Latest user instruction overrides Stage1 wait; paper-text wn5 only, stop after scan24.',
            'packages_installed':True,'large_datasets_downloaded':True,'agents_delegated':False,
            'GPU_workload_started':gpu_started,'CPU_reference_tests_run':True,'scheduler_created':True,
            'launch_header_is_not_completion_evidence':True,'stage1_immutable_snapshot':'stage1_frozen/SEAL.json',
            'publication_note':'Snapshot precedes publication; final response reports actual commit/push outcome.'}
    atomic_json(artifact/'PILOT_STATUS.json',status)
    atomic_json(artifact/'STATUS.json',status)
    print(json.dumps({'status':state['status'],'runner_pid':pid,'config_sha256':sha256(config_path),
                       'GPU_workload_started':gpu_started,'training_started':training_started,
                       'immutable_files_checked':len(config['immutable_files'])},indent=2))


if __name__=='__main__':main()
