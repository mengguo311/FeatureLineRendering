"""Freeze the next single DTU scene after actual scan24 quality review."""
import json,sys,shutil,time,subprocess,importlib.util,difflib
from pathlib import Path
P=Path(__file__).resolve().parent;W=P.parents[4]
sys.path.insert(0,str(W/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,sha256
from pipeline_scope import validate_scope
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');O=H/'official_code_fix_v01';D=O/'suite_v01/scan37'
assert not D.exists() and not (O/'models/scan37_official_half30k').exists()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=W,text=True).strip()=='00bb67c4ae39157906bcda6abc8760cc37679414'
assert shutil.disk_usage('/').free>=10*1024**3 and shutil.disk_usage(O).free>=50*1024**3
q=O/'review_v01/QUALITY_GATE.json';assert json.loads(q.read_text())['status']=='PASS_SINGLE_SCENE_QUALITY_REVIEW'
verified=json.loads((O/'review_v01/REVERIFIED.json').read_text());assert verified['status']=='PASS'
old=O/'pilot/state/runner_config.json';c=json.loads(old.read_text());assert sha256(old)==verified['config_sha256']
manifest=H/'full_reproduction_v01/suite_execution_v01/SCAN37_DATA.json';data=json.loads(manifest.read_text())
assert data['scene']=='scan37' and data['images']==data['camera_views']==49 and data['initial_COLMAP_points']==50807
for key in ('training_hashes','evaluation_hashes'):
 for f,h in data[key].items():assert sha256(f)==h,f
from PIL import Image
images=sorted((Path(data['prepared'])/'images').glob('[0-9][0-9][0-9][0-9].png'));assert len(images)==49
image_records=[]
for p in images:
 with Image.open(p) as im:
  assert im.mode=='RGBA' and im.size==(1554,1162);im.load()
  image_records.append({'view':p.stem,'size':list(im.size),'mode':im.mode,'alpha_range':list(im.getchannel('A').getextrema())})
spec=importlib.util.spec_from_file_location('colmap_reader',O/'source/scene/colmap_loader.py');reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
root=Path(data['prepared'])/'sparse/0';cams=reader.read_intrinsics_binary(root/'cameras.bin');poses=reader.read_extrinsics_binary(root/'images.bin');xyz,_,_=reader.read_points3D_binary(root/'points3D.bin');assert len(poses)==49 and len(xyz)==50807
assert set(x.name for x in poses.values())=={p.name for p in images}
files={p:h for p,h in c['immutable_files'].items() if '/data/' not in p}
for p,h in files.items():assert sha256(p)==h,p
files.update(data['training_hashes']);files.update(data['evaluation_hashes'])
for p in [manifest,q,O/'review_v01/REVERIFIED.json',O/'suite_v01/FULL_SUITE_PROTOCOL.json',*P.glob('*.py')]:files[str(p)]=sha256(p)
D.mkdir();(D/'state').mkdir()
atomic_json(D/'DATA_REVERIFIED.json',{'source_manifest':str(manifest),'source_manifest_sha256':sha256(manifest),'training_files':len(data['training_hashes']),'evaluation_files':len(data['evaluation_hashes']),'image_records':image_records,'COLMAP_points':len(xyz),'camera_poses':len(poses),'GT_role':'evaluation only','no_trained_PLY_initialization':True})
files[str(D/'DATA_REVERIFIED.json')]=sha256(D/'DATA_REVERIFIED.json')
model=O/'models/scan37_official_half30k'
c.update(scene='scan37',purpose='official_C24_scan37_half30k',model=str(model),data=data['prepared'],state_dir=str(D/'state'),log_dir=str(D/'logs'),expected_scene={'views':49,'half_resolution':[777,581],'initial_colmap_points':50807},artifact_dir=str(W/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01/official_code_fix_v01/suite_v01'),tmux='radegs-official-scan37-v01',launch_script=str(D/'launch.sh'),preflight_report=str(D/'state/preflight.json'))
c['inputs'].update(scan24_quality_review=sha256(q),frozen_protocol=sha256(O/'suite_v01/FULL_SUITE_PROTOCOL.json'),data_manifest=sha256(D/'DATA_REVERIFIED.json'),scene_entry='official_code_fix_v01_DTU_scan37_half30k_TSDF',pipeline_revision=sha256(P/'control.py'))
c['runtime_env']['PYTHONPATH']=str(P)+':'+c['runtime_env']['PYTHONPATH']
c['reports']={s:str(D/'state'/(s+'.report.json')) for s in ('smoke','train','export','tsdf','eval')}
c['stage_commands']={s:[str(O/'env/bin/python'),str(P/'stages.py'),'--config',str(D/'state/runner_config.json'),'--stage',s] for s in c['reports']}
c['train_command']=[str(O/'env/bin/python'),str(P.parent/'train_entry.py'),'--config',str(D/'state/runner_config.json')]
c['eval_command']=[str(O/'env/bin/python'),str(O/'source/evaluate_dtu_mesh.py'),'-s',c['data'],'-m',str(model),'-r','2','--iteration','30000','--DTU',data['evaluation_GT']]
c['immutable_files']=files;validate_scope(c)
atomic_json(D/'state/preflight.json',{'passed':True,'scope':'one independent scan37, actual-scene GPU smoke required before training','scan24_quality_gate_sha256':sha256(q),'root_free_GiB':shutil.disk_usage('/').free/1024**3,'HDD_free_GiB':shutil.disk_usage(O).free/1024**3,'estimated_working_GiB':20,'estimate_basis':'scan24 observed complete output plus fixed checkpoints and two49view exports; not a time prediction'})
atomic_json(D/'state/runner_config.json',c)
launch=D/'launch.sh';launch.write_text('#!/bin/bash\nset -eu\nexport PYTHONDONTWRITEBYTECODE=1\nexec '+str(O/'env/bin/python')+' '+str(P/'control.py')+' --config '+str(D/'state/runner_config.json')+' >> '+str(D/'supervisor.log')+' 2>&1\n');launch.chmod(0o700)
diff=''
for name in ('control.py','runner.py','pipeline_scope.py','stages.py','postprocess.py'):
 previous=P.parent/'pipeline_v01'/name if name in ('control.py','runner.py','pipeline_scope.py') else P.parent/name
 diff+=''.join(difflib.unified_diff(previous.read_text().splitlines(True),(P/name).read_text().splitlines(True),fromfile=str(previous),tofile=str(P/name)))
(D/'PIPELINE_GENERALIZATION.diff').write_text(diff)
atomic_json(D/'LAUNCH.json',{'config_sha256':sha256(D/'state/runner_config.json'),'immutable_files':len(files),'command':['tmux','new-session','-d','-s',c['tmux'],str(launch)],'native_unchanged':c['inputs']['native'],'stage_order':list(c['reports']),'next_scene_automatic_launch':False,'scientificdone':False})
print({'config_sha256':sha256(D/'state/runner_config.json'),'immutable_files':len(files),'training_files_verified':len(data['training_hashes']),'GT_files_verified':len(data['evaluation_hashes'])})
