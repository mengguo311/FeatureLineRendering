from pathlib import Path
import copy,datetime,hashlib,json,shutil,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from src.corrected_sampling import stock_intrinsics,resize_intrinsics
from src.foundation import freeze_json
old=ROOT/'out/multiscene_foundation';out=ROOT/'out/multiscene_foundation_corrected'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
cfg=json.loads((old/'config.json').read_text());original=copy.deepcopy(cfg)
cfg.update(branch='multiscene-foundation-corrected',start_head='5c5837ff5de68498d1c0388269808a30041a8774',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),version=2)
shutil.copyfile(old/'PREREG.md',out/'inherited_protocol.md')
inputs={};posteriors={};parents={}
for p in [Path('/home/u00134/codex_astra_point_feature_foundation_decision.md'),Path('/home/u00134/codex_astra_point_feature_foundation_experiment_report.md'),Path('/home/u00134/codex_astra_multiscene_foundation_report.md')]+[ROOT/'out'/name/file for name in ['point_feature_foundation','multiscene_foundation'] for file in ['PREREG.md','RESULTS.md','results.json','VERIFICATION.json','REPRODUCE.md','config.json']]+[old/'EXECUTION_NOTES.md',old/'input_hashes.json']:
 inputs[str(p)]=dict(sha256=sha(p),bytes=p.stat().st_size)
for scene in cfg['scene_order']:
 for seed in cfg['training']['seeds']:
  complete=json.loads((old/f'training/{scene}/seed_{seed}/completion.json').read_text());p=Path(complete['path'])
  assert sha(p)==complete['sha256'];posteriors[f'{scene}_{seed}']=complete
 parent=old/f'controlled/{scene}/measurements/parent_frozen.json';parents[scene]=json.loads(parent.read_text());inputs[str(parent)]=dict(sha256=sha(parent),bytes=parent.stat().st_size)
 for split in ['train','val']:
  p=Path(cfg['scenes'][scene]['dataset'])/f'transforms_{split}.json';meta=json.loads(p.read_text());inputs[str(p)]=dict(sha256=sha(p),bytes=p.stat().st_size)
  fovx=meta['camera_angle_x'];fovy=2*np.arctan(np.tan(fovx/2))
  native=stock_intrinsics(fovx,fovy);small=resize_intrinsics(native,(800,800),(400,400))
  for camera in cfg['scenes'][scene]['cameras'].values():
   if camera['split']!=split:continue
   assert np.allclose(native[:2,:2]/2,np.array(camera['K'])[:2,:2],rtol=1e-12)
   camera.update(native_K=native.tolist(),K=small.tolist(),FoVx=fovx,FoVy=float(fovy),native_height=800,native_width=800)
 for p in (old/'annotations').glob(f'{scene}*'):
  shutil.copyfile(p,out/'annotations'/p.name);inputs[str(p)]=dict(sha256=sha(p),bytes=p.stat().st_size)
cfg['sampling']=dict(native_size=[800,800],measurement_size=[400,400],filter='float64_nonoverlapping_2x2_area_fixed_row_major_sum',pixel_centers='u_dst=(u_src+0.5)*scale-0.5',depth='equal mixture of four native contribution streams',rerasterize_at400=False)
cfg['decision_scope']=dict(core=['lego','chair'],expanded_min_scenes=3,expanded_requires_any=['drums','ficus'],video_trigger='per eligible scene G1 and G2 machine pass',manual='PENDING_INDEPENDENT_REVIEW')
cfg['frozen_posteriors']=posteriors;cfg['frozen_parents']=parents
cfg['prior_config_sha256']=sha(old/'config.json');cfg['prereg_sha256']=sha(out/'PREREG.md')
for key in ['budget','controls','detector','eligibility','gates','native','perturbations','probe','queries','scene_order','splits','surface','training','visuals']:
 assert cfg[key]==original[key]
cfg['input_hashes_sha256']=freeze_json(out/'input_hashes.json',inputs)
freeze_json(out/'config.json',cfg)
freeze_json(out/'annotations/preservation.json',dict(author='Codex implementing assistant; not independent',improved=False,prior_annotation_hashes={str(p):sha(p) for p in (old/'annotations').glob('*') if p.is_file()},status='coarse TRAIN-only prior candidates; not certified spans',frozen_before_local_output=True))
print('configuration',sha(out/'config.json'),'posteriors',len(posteriors),'parents',len(parents))
