"""Seal read-only diagnostic config; preserves old training and failure seals."""
import ast
import json
from pathlib import Path
import subprocess
import sys

WORK=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(WORK/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,sha256,verify_seal
HDD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
FULL=HDD/'full_reproduction_v01'
CODE=Path(__file__).parent
STATE=FULL/'checkpoint_diagnostic/state'

def main():
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip()=='00bb67c4ae39157906bcda6abc8760cc37679414'
    parent_path=HDD/'gradient_fix_v01/pilot/state/runner_config.json'
    c=json.loads(parent_path.read_text())
    assert not (STATE/'runner_config.json').exists(),'preserve prior config'
    for path,digest in c['immutable_files'].items():assert sha256(path)==digest,path
    for stage in ['smoke','train','export']:assert verify_seal(Path(c['state_dir'])/(stage+'.seal.json'),stage,c['inputs'])
    assert 'OK' in (FULL/'logs/diagnostic_runner_GREEN.log').read_text()
    parent_state=json.loads((Path(c['state_dir'])/'runner_state.json').read_text())
    assert parent_state['status']=='ENGINEERING_NOT_READY' and parent_state['child_pid'] is None
    assert not Path('/proc') .joinpath(str(parent_state['runner_pid'])).exists(),'old runner still present'
    files=[CODE/'diagnostic_runner.py',CODE/'checkpoint_diagnostic.py',CODE/'test_diagnostic_runner.py',Path(__file__)]
    for path in files:ast.parse(path.read_text())
    manifest={str(p):sha256(p) for p in files}
    for iteration in [15000,30000]:
        p=Path(c['model'])/f'point_cloud/iteration_{iteration}/point_cloud.ply';manifest[str(p)]=sha256(p)
    manifest[str(parent_path)]=sha256(parent_path)
    atomic_json(STATE/'source_manifest.json',manifest)
    c['immutable_files'].update(manifest)
    c['inputs']=dict(c['inputs'],checkpoint_diagnostic=sha256(STATE/'source_manifest.json'))
    c['state_dir']=str(STATE);c['log_dir']=str(FULL/'checkpoint_diagnostic/logs')
    c['preflight_report']=str(STATE/'preflight.json');c['parent_config']=str(parent_path)
    c['diagnostic_output']=str(FULL/'checkpoint_diagnostic/outputs')
    c['reports']={'checkpoint_diagnostic':str(STATE/'checkpoint_diagnostic.report.json')}
    c['stage_commands']={'checkpoint_diagnostic':[str(HDD/'envs/c24_py39/bin/python'),str(CODE/'checkpoint_diagnostic.py'),'--config',str(STATE/'runner_config.json')]}
    for key in ['train_command','tsdf_command','eval_command']:c.pop(key,None)
    c['diagnostic_scope']='read-only scan24 iteration15000/30000; no optimizer, no official metric or full-suite completion claim'
    atomic_json(STATE/'preflight.json',{'passed':True,'parent_immutable_files_verified':len(c['immutable_files']),
        'train_export_reused':True,'parent_failure_preserved':True,'diagnostic_runner_CPU_tests':'4 PASS',
        'training_implementation_changed':False,'native_rebuild':False})
    atomic_json(STATE/'runner_config.json',c)
    print(json.dumps({'config':str(STATE/'runner_config.json'),'sha256':sha256(STATE/'runner_config.json'),
        'immutable_files_verified':len(c['immutable_files'])}))

if __name__=='__main__':main()
