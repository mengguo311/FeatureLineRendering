"""A fresh, bounded runtime validation configuration, after native seal passes."""
import argparse,json,hashlib,os,sys
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.append(str(P.parents[1]/'stage2'))
from safety import sha256,verify_seal,atomic_json
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01')
a=argparse.ArgumentParser();a.add_argument('--revision',required=True,choices=['v01','v02']);args=a.parse_args();old=H/'gpu_validation_v02';c=json.loads((old/'state/runner_config.json').read_text());assert verify_seal(old/'state/smoke.seal.json','smoke',c['inputs'])
D=H/('runtime_validation_'+args.revision);D.mkdir(exist_ok=False);(D/'state').mkdir()
c.update(state_dir=str(D/'state'),log_dir=str(D/'logs'),validation_root=str(D/'outputs'),model=str(D/'model'),preflight_report=str(D/'state/preflight.json'))
c['reports']={'smoke':str(D/'state/smoke.report.json')};c['stage_commands']={'smoke':[str(H/'env/bin/python'),str(P/('runtime_gpu_smoke.py' if args.revision=='v01' else 'runtime_gpu_smoke_v02.py')),'--config',str(D/'state/runner_config.json')]}
overlay=H/('runtime_source' if args.revision=='v01' else 'runtime_source_v02')
c['runtime_env']['PYTHONPATH']=str(overlay)+os.pathsep+c['runtime_env']['PYTHONPATH']
for p in [P/'runtime_gpu_smoke.py',P/'official_runtime.py',overlay/'train.py',old/'state/smoke.seal.json']:
 c['immutable_files'][str(p)]=sha256(p)
c['inputs'].update(native_validation_seal=sha256(old/'state/smoke.seal.json'),runtime=sha256(P/'official_runtime.py'),runtime_train=sha256(overlay/'train.py'))
if args.revision=='v02':
 c['runtime_module']=str(H/'runtime_module_v02')
 c['immutable_files'][str(P/'runtime_gpu_smoke_v02.py')]=sha256(P/'runtime_gpu_smoke_v02.py')
 c['runtime_env']['PYTHONPATH']=str(overlay)+os.pathsep+str(H/'runtime_module_v02')+os.pathsep+c['runtime_env']['PYTHONPATH'].split(os.pathsep,1)[1]
 c['immutable_files'][str(H/'runtime_module_v02/official_runtime.py')]=sha256(H/'runtime_module_v02/official_runtime.py');c['inputs']['runtime']=sha256(H/'runtime_module_v02/official_runtime.py')
atomic_json(D/'state/preflight.json',{'passed':True,'native_gpu_validated':True,'runtime_gpu_validation_pending':True,'formal_train_permitted':False});atomic_json(D/'state/runner_config.json',c)
launch=D/'launch.sh';launch.write_text('#!/bin/bash\nset -eu\nexport PYTHONDONTWRITEBYTECODE=1\nexec '+str(H/'env/bin/python')+' '+str(P/'official_control_v02.py')+' --config '+str(D/'state/runner_config.json')+' >> '+str(D/'supervisor.log')+' 2>&1\n');launch.chmod(0o700);print({'config':str(D/'state/runner_config.json'),'sha256':sha256(D/'state/runner_config.json')})
