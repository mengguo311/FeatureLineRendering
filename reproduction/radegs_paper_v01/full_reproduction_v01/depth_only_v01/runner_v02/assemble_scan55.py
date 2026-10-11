"""Freeze one new C24 official-method scene, accepting depth delivery only."""
import json,sys,shutil,subprocess,importlib.util,difflib
from pathlib import Path
P=Path(__file__).resolve().parent;W=P.parents[4]
sys.path.insert(0,str(W/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,sha256
from pipeline_scope import validate_scope
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');O=H/'official_code_fix_v01';D=H/'depth_only_v01';S=D/'scan55';OCODE=P.parent.parent/'official_code_fix_v01'
assert not S.exists() and not (D/'models/scan55_official_half30k').exists()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=W,text=True).strip()=='00bb67c4ae39157906bcda6abc8760cc37679414'
assert shutil.disk_usage('/').free>=10*1024**3 and shutil.disk_usage(D).free>=50*1024**3
review=D/'REVIEWS_SCAN24_SCAN37_SCAN40.json';r=json.loads(review.read_text());assert r['counts']['depth_review_passed']==3 and all(x['status']=='DEPTH_REVIEW_PASSED_WITH_LIMITATIONS' for x in r['reviews'])
old=D/'scan40/state/runner_config.json';assert sha256(old)=='907a778ded509b8c3f2cc544ad56f55ecd350ca0834fb926da78ddc80578ba50';c=json.loads(old.read_text())
manifest=H/'full_reproduction_v01/suite_execution_v01/scan55_data_v01/DATA.json';data=json.loads(manifest.read_text())
assert data['scene']=='scan55' and data['images']==data['camera_views']==49 and data['initial_COLMAP_points']==46774
for f,h in data['training_hashes'].items():assert sha256(f)==h,f
from PIL import Image
images=sorted((Path(data['prepared'])/'images').glob('[0-9][0-9][0-9][0-9].png'));assert len(images)==49
image_records=[]
for p in images:
 with Image.open(p) as im:
  assert im.mode=='RGBA' and im.size==(1554,1162);im.load()
  image_records.append({'view':p.stem,'size':list(im.size),'mode':im.mode,'alpha_range':list(im.getchannel('A').getextrema())})
spec=importlib.util.spec_from_file_location('colmap_reader',O/'source/scene/colmap_loader.py');reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
root=Path(data['prepared'])/'sparse/0';cams=reader.read_intrinsics_binary(root/'cameras.bin');poses=reader.read_extrinsics_binary(root/'images.bin');xyz,_,_=reader.read_points3D_binary(root/'points3D.bin');assert len(poses)==49 and len(xyz)==46774
assert set(x.name for x in poses.values())=={p.name for p in images}
# Keep exact verified scientific sources/build/runtime. Old evaluation outputs and
# quality decisions are provenance only, not dependencies of this new workflow.
excluded=('/data/','/review_v01/','/suite_v01/','/SCAN37_DATA.json')
files={p:h for p,h in c['immutable_files'].items() if not any(s in p for s in excluded)}
for p,h in files.items():assert sha256(p)==h,p
files.update(data['training_hashes'])
proto=D/'FULL_SUITE_PROTOCOL.json'
for p in [manifest,review,proto,*P.glob('*.py'),*P.parent.glob('*.py')]:files[str(p)]=sha256(p)
S.mkdir();(S/'state').mkdir()
atomic_json(S/'DATA_REVERIFIED.json',{'source_manifest':str(manifest),'source_manifest_sha256':sha256(manifest),'training_files':len(data['training_hashes']),'image_records':image_records,'COLMAP_points':len(xyz),'camera_poses':len(poses),'GT_used':False,'GT_mesh_not_required':True,'no_trained_PLY_initialization':True})
files[str(S/'DATA_REVERIFIED.json')]=sha256(S/'DATA_REVERIFIED.json')
config_path=S/'state/runner_config.json';model=D/'models/scan55_official_half30k'
c.update(scene='scan55',purpose='official_C24_scan55_depth_only_half30k',workflow='depth_only_v01',model=str(model),data=data['prepared'],state_dir=str(S/'state'),log_dir=str(S/'logs'),expected_scene={'views':49,'half_resolution':[777,581],'initial_colmap_points':46774},artifact_dir=str(W/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01/depth_only_v01'),tmux='radegs-depth-scan55-v01',launch_script=str(S/'launch.sh'),preflight_report=str(S/'state/preflight.json'),config_path=str(config_path),delivery_dir=str(D/'deliveries/scan55'))
c.pop('eval_command',None);c['inputs'].pop('scan24_quality_review',None)
c['inputs'].update(previous_depth_review=sha256(review),frozen_protocol=sha256(proto),data_manifest=sha256(S/'DATA_REVERIFIED.json'),scene_entry='depth_only_v01_DTU_scan55_half30k',workflow='depth_only_v01',pipeline_revision=sha256(P/'control.py'))
c['runtime_env']['PYTHONPATH']=str(P)+':'+str(P.parent)+':'+c['runtime_env']['PYTHONPATH']
c['runtime_env'].update(PYTHONDONTWRITEBYTECODE='1',MPLCONFIGDIR=str(D/'cache/matplotlib'))
c['reports']={s:str(S/'state'/(s+'.report.json')) for s in ('smoke','train','export','depth_review')}
c['stage_commands']={s:[str(O/'env/bin/python'),str(P/'stages.py'),'--config',str(config_path),'--stage',s] for s in c['reports']}
c['train_command']=[str(O/'env/bin/python'),str(OCODE/'train_entry.py'),'--config',str(config_path)]
c['immutable_files']=files;validate_scope(c)
atomic_json(S/'state/preflight.json',{'passed':True,'scope':'one independent scan55 depth-only; actual-scene GPU smoke before training','previous_depth_review_sha256':sha256(review),'root_free_GiB':shutil.disk_usage('/').free/1024**3,'HDD_free_GiB':shutil.disk_usage(D).free/1024**3,'estimated_working_GiB':20,'estimate_basis':'observed scan24/37 fixed checkpoints, two49view exports and full raw tar plus margin; not a time prediction','mesh_eval_gates':False})
atomic_json(config_path,c)
launch=S/'launch.sh';launch.write_text('#!/bin/bash\nset -eu\nexport PYTHONDONTWRITEBYTECODE=1\nexec '+str(O/'env/bin/python')+' '+str(P/'control.py')+' --config '+str(config_path)+' >> '+str(S/'supervisor.log')+' 2>&1\n');launch.chmod(0o700)
diff=''
for name in ('control.py','runner.py','pipeline_scope.py','stages.py','postprocess.py'):
 previous=OCODE/'pipeline_v02'/name
 diff+=''.join(difflib.unified_diff(previous.read_text().splitlines(True),(P/name).read_text().splitlines(True),fromfile=str(previous),tofile=str(P/name)))
(S/'DEPTH_ONLY_PIPELINE.diff').write_text(diff)
atomic_json(S/'LAUNCH.json',{'config_sha256':sha256(config_path),'before_config':str(old),'before_sha256':sha256(old),'immutable_files':len(files),'command':['tmux','new-session','-d','-s',c['tmux'],str(launch)],'native_unchanged':c['inputs']['native'],'stage_order':list(c['reports']),'next_scene_automatic_launch':False,'terminal':'DEPTH_DELIVERED_VISUAL_REVIEW_REQUIRED','scientificdone':False})
print({'config_sha256':sha256(config_path),'immutable_files':len(files),'training_files_verified':len(data['training_hashes']),'GT_used':False,'stage_order':list(c['reports'])})
