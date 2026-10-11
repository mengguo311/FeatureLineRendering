"""A new single-scene depth-only config; all previous configs/seals stay intact."""
import json,sys,shutil,subprocess,importlib.util,ast,shlex
from pathlib import Path
P=Path(__file__).resolve().parent;W=P.parents[4];H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');D=H/'depth_only_v01';O=H/'official_code_fix_v01';S=D/'scan69_v01'
sys.path.insert(0,str(W/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,sha256,verify_seal
from pipeline_scope import validate_scope
assert not S.exists() and not (D/'models/scan69_official_half30k_eigen_fallback_v01').exists()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=W,text=True).strip()=='00bb67c4ae39157906bcda6abc8760cc37679414'
assert shutil.disk_usage('/').free>=10*2**30 and shutil.disk_usage(H).free>=70*2**30
review_path=D/'REVIEWS_SCAN24_SCAN37_SCAN40_SCAN55_SCAN63_SCAN65.json';review=json.loads(review_path.read_text());assert review['counts']['depth_review_passed']==6 and all(x['status']=='DEPTH_REVIEW_PASSED_WITH_LIMITATIONS' for x in review['reviews'])
old=D/'scan65_v01/state/runner_config.json';c=json.loads(old.read_text())
assert verify_seal(Path(c['state_dir'])/'depth_review.seal.json','depth_review',c['inputs'])
manifest=H/'full_reproduction_v01/suite_execution_v01/scan69_data_v01/DATA.json';data=json.loads(manifest.read_text());assert data['scene']=='scan69' and data['images']==data['camera_views']==49 and data['initial_COLMAP_points']==23221
for path,digest in data['training_hashes'].items():assert sha256(path)==digest,path
from PIL import Image
images=sorted((Path(data['prepared'])/'images').glob('[0-9][0-9][0-9][0-9].png'));assert len(images)==49;image_rows=[]
for p in images:
 with Image.open(p) as im:
  im.load();assert im.mode=='RGBA' and im.size==(1554,1162)
  image_rows.append({'view':p.stem,'size':list(im.size),'mode':im.mode,'alpha_range':list(im.getchannel('A').getextrema())})
spec=importlib.util.spec_from_file_location('colmap_cpu',O/'source/scene/colmap_loader.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);root=Path(data['prepared'])/'sparse/0';poses=mod.read_extrinsics_binary(root/'images.bin');cameras=mod.read_intrinsics_binary(root/'cameras.bin');xyz,_,_=mod.read_points3D_binary(root/'points3D.bin');assert len(poses)==49 and len(xyz)==23221;assert {x.name for x in poses.values()}=={p.name for p in images}
files={p:h for p,h in c['immutable_files'].items() if not '/data/' in p}
for p,h in files.items():assert sha256(p)==h,p
files.update(data['training_hashes']);S.mkdir();(S/'state').mkdir()
atomic_json(S/'DATA_REVERIFIED.json',{'scene':'scan69','legacy_data_manifest':str(manifest),'legacy_manifest_sha256':sha256(manifest),'training_archive_provenance':data['training_archive_provenance'],'training_file_count':len(data['training_hashes']),'training_hashes':data['training_hashes'],'camera_poses':len(poses),'COLMAP_points':len(xyz),'image_rows':image_rows,'GT_geometry_loaded':False,'legacy_GT_entries_not_used':True,'initialization':'author-preprocessed COLMAP; no trained checkpoint','half_dimensions':[777,581]})
proto={'parent_protocol':str(D/'FULL_SUITE_PROTOCOL.json'),'parent_sha256':sha256(D/'FULL_SUITE_PROTOCOL.json'),'method_variant':'official_code_fix_v01','numerical_revision':c['numerical_revision'],'scene':'scan69','scene_entry':'depth_only_v01_DTU_scan69_half30k','resolution_divisor':2,'iterations':30000,'wd':100,'wn':.05,'regularization_from_iter':15000,'geometry_start_inclusive':True,'optimizer_final_step':False,'data_provenance':str(S/'DATA_REVERIFIED.json'),'native_source_manifest':c['native_build_manifest'],'native_sha256':c['inputs']['native'],'previous_depth_review':str(review_path),'stage_order':['smoke','train','export','depth_review'],'acceptance':'complete float15k/30k depth+camera/hash/finite-alpha checks and independent visual review; not GT accuracy','GT_used':False,'new_mesh_eval':False,'automatic_next_scene':False}
atomic_json(S/'PROTOCOL_ADDENDUM.json',proto)
cfg=S/'state/runner_config.json';c.update(scene='scan69',purpose='official_C24_scan69_depth_only_half30k',data=data['prepared'],model=str(D/'models/scan69_official_half30k_eigen_fallback_v01'),state_dir=str(S/'state'),log_dir=str(S/'logs'),config_path=str(cfg),preflight_report=str(S/'state/preflight.json'),tmux='radegs-depth-scan69-v01',launch_script=str(S/'launch.sh'),delivery_dir=str(D/'deliveries/scan69_eigen_fallback_v01'),expected_scene={'views':49,'half_resolution':[777,581],'initial_colmap_points':23221},active_protocol_addendum=str(S/'PROTOCOL_ADDENDUM.json'))
c['inputs'].update(data_manifest=sha256(S/'DATA_REVERIFIED.json'),previous_depth_review=sha256(review_path),scene_entry='depth_only_v01_DTU_scan69_half30k',revision_protocol=sha256(S/'PROTOCOL_ADDENDUM.json'),pipeline_revision=sha256(P/'control.py'))
c['runtime_env']['PYTHONPATH']=str(P)+':'+c['runtime_env']['PYTHONPATH']
c['reports']={s:str(S/'state'/(s+'.report.json')) for s in proto['stage_order']};c['stage_commands']={s:[str(O/'env/bin/python'),str(P/'stages.py'),'--config',str(cfg),'--stage',s] for s in c['reports']};c['train_command']=[str(O/'env/bin/python'),str(P.parent.parent/'official_code_fix_v01/train_entry.py'),'--config',str(cfg)]
for p in [*P.glob('*.py'),review_path,manifest,S/'DATA_REVERIFIED.json',S/'PROTOCOL_ADDENDUM.json',D/'logs/SCAN69_DEPTH_CPU_GREEN.log']:
 if p.suffix=='.py':ast.parse(p.read_text())
 files[str(p)]=sha256(p)
c['immutable_files']=files;validate_scope(c)
atomic_json(S/'state/preflight.json',{'passed':True,'scope':'one new scan69 depth-only run; shared GPU gate and scene smoke before train','previous_reviews':6,'training_files_rehashed':len(data['training_hashes']),'root_free_GiB':shutil.disk_usage('/').free/2**30,'HDD_free_GiB':shutil.disk_usage(H).free/2**30,'estimated_working_GiB':20,'estimate_basis':'observed earlier checkpoint+98NPZ+tar footprints plus margin; no timing prediction','GT_geometry_loaded':False,'mesh_eval_not_required':True})
atomic_json(cfg,c);(S/'launch.sh').write_text('#!/bin/bash\nset -euo pipefail\nexport PYTHONDONTWRITEBYTECODE=1\nexec '+shlex.join([str(O/'env/bin/python'),str(P/'control.py'),'--config',str(cfg)])+' > '+shlex.quote(str(S/'supervisor.log'))+' 2>&1\n')
atomic_json(S/'LAUNCH.json',{'config':str(cfg),'config_sha256':sha256(cfg),'parent_config':str(old),'parent_config_sha256':sha256(old),'native_unchanged':c['inputs']['native'],'native_build_manifest':c['native_build_manifest'],'numerical_revision':c['numerical_revision'],'training_files':len(data['training_hashes']),'immutable_files':len(files),'stage_order':proto['stage_order'],'command':['tmux','new-session','-d','-s',c['tmux'],'bash',str(S/'launch.sh')],'automatic_next_scene':False,'scientificdone':False})
print(json.dumps({'config':str(cfg),'sha256':sha256(cfg),'training_files':len(data['training_hashes']),'COLMAP_points':len(xyz),'immutable_files':len(files)}))
