"""One-time administrative freeze; no scene decoding, training or rendering."""
import ast, hashlib, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
ROOT=Path('/home/u00134/3dgs_line/tier1'); sys.path.insert(0,str(ROOT))
from src.foundation import freeze_json
out=ROOT/'out/multiscene_foundation'; gs=out/'vendor/gaussian-splatting'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def record(p):
 p=Path(p).resolve(); return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))
def git(*args,cwd=ROOT): return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()
assert git('rev-parse','HEAD')=='6b098a5cb538fc4fc09d48d927dc97b77acc0b28'
assert git('branch','--show-current')=='multiscene-foundation'
assert git('diff',cwd=gs)==''
train=[1,7,14,21,27,33,41,47,53,59,67,73,79,86,93,99]
F=train[::2]; C=train[1::2]; dev=[2,22,42,62]; test=list(range(5,100,10))
opt=[i for i in range(100) if i not in dev+test]
source_files=[record(gs/p) for p in git('ls-files',cwd=gs).splitlines() if (gs/p).is_file()]
inputs=[]; scenes={}
for scene in ['lego','chair','drums','ficus']:
 d=Path('/home/u00134/cglib/data/full')/scene
 scenes[scene]={'dataset':str(d),'cameras':{},'route_b_parent':f'training/{scene}/seed_1729/checkpoints/point_cloud/iteration_30000/point_cloud.ply'}
 for split,indices in [('train',list(range(100))),('val',train)]:
  m=d/f'transforms_{split}.json'; inputs.append(record(m)); meta=json.loads(m.read_text()); assert len(meta['frames'])==100
  f=200/np.tan(meta['camera_angle_x']/2)
  for i in indices:
   fr=meta['frames'][i]; p=(d/fr['file_path']).with_suffix('.png'); inputs.append(record(p))
   c2w=np.array(fr['transform_matrix'])@np.diag([1,-1,-1,1])
   scenes[scene]['cameras'][f'{split}_{i:03d}']=dict(index=i,split=split,path=str(p),sha256=sha(p),K=[[float(f),0,200],[0,float(f),200],[0,0,1]],w2c=np.linalg.inv(c2w).tolist())
prior=[Path('/home/u00134/codex_astra_point_feature_foundation_decision.md'),Path('/home/u00134/codex_astra_point_feature_foundation_experiment_report.md')]
prior+=sorted((ROOT/'out/point_feature_foundation').glob('*.md'))+sorted((ROOT/'out/point_feature_foundation').glob('*.json'))
# Parse every prior machine report in full; the previous manifest is an inventory,
# not an additional source of scientific thresholds.
for p in prior:
 if p.suffix=='.json': json.loads(p.read_text())
dirty=Path('/home/u00134/3dgs_line/ext/gaussian-splatting')
freeze_json(out/'input_hashes.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),files=inputs,prior_reports=[record(p) for p in prior],pristine_training_source=source_files,source_commit=git('rev-parse','HEAD',cwd=gs),submodules=git('submodule','status','--recursive',cwd=gs),external_dirty_source=dict(head=git('rev-parse','HEAD',cwd=dirty),status=git('status','--porcelain',cwd=dirty),files=[record(dirty/'gaussian_renderer/__init__.py'),record(dirty/'patch_render.py')]),image_content_inspected=False,hashing_only=True))
# Read official argument defaults without importing CUDA or the training program.
argtree=ast.parse((gs/'arguments/__init__.py').read_text()); defaults={}
for cls in argtree.body:
 if isinstance(cls,ast.ClassDef) and cls.name in ['ModelParams','PipelineParams','OptimizationParams']:
  values={}
  for node in ast.walk(cls):
   if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Attribute) and isinstance(node.targets[0].value,ast.Name) and node.targets[0].value.id=='self':
    try: values[node.targets[0].attr.lstrip('_')]=ast.literal_eval(node.value)
    except (ValueError,TypeError): pass
  defaults[cls.name]=values
cfg=dict(version=1,created_utc=datetime.now(timezone.utc).isoformat(),branch='multiscene-foundation',start_head=git('rev-parse','HEAD'),prereg_sha256=sha(out/'PREREG.md'),input_hashes_sha256=sha(out/'input_hashes.json'),scene_order=list(scenes),scenes=scenes,
 training=dict(seeds=[1729,2718],source_commit='472689c0dc70417448fb451bf529ae532d32c095',official_defaults=defaults,overrides=dict(white_background=True,eval=True),optimization_indices=opt,validation_indices=train,iterations=30000,test_iterations=[7000,30000],save_iterations=[7000,30000],gpu_for_seed={'1729':0,'2718':1},cpu_threads=4,min_free_mib=16384,min_disk_gib=30,resource_poll_seconds=60,resource_wait_seconds=21600,timeout_seconds=21600),
 splits=dict(TRAIN=train,F=F,C=C,DEV=dev,TEST=test),detector=dict(size=400,sigma=1.2,canny=[50,120],aperture=3,L2gradient=False,tangent_window=5,min_tangent_pixels=3,tangent_eigen_ratio_max=.25),
 queries=dict(primary=[1,27,53,79],exchange=[7,33,59,86],grid=8,max_per_view=64,negative_per_view=16,negative_min_dt=6,seed=20260918),
 eligibility=dict(independent=dict(mean_psnr_min=25,worst_psnr_min=20,mean_ssim_min=.90,worst_ssim_min=.80,mean_psnr_gap_max=2,mean_ssim_gap_max=.03,pair_rmse_factor_max=1.5,pair_rmse_epsilon=1e-6,pair_mean_ssim_min=.90),controlled=dict(psnr_min=40,ssim_min=.995,p99_max=8/255,selected_mass_min=.20,child_mass_min=.005,backgrounds=[0,1])),
 perturbations=dict(parent_seed=1729,parent_hash_seed=20260919,parent_fraction=.5,redistribute_q=[1/32,1/16,1/8,1/4,1/2],moment_split_q=.25,moment_split_d=[.025,.05,.1,.2]),
 native=dict(kernel_commit='59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d',binary_sha256='583e896f3aaa1c2dece9c67eaaa26d919f98aae0597591bf6693b9a19530e9e9',calibration_max=1/255,alpha_roi=.5,outside_mass_max=.01,alpha_clamp=.99,alpha_cutoff=1/255,terminate_transmittance=.0001,visible_transmittance_min=.8,hidden_transmittance_max=.1,depth_margin_delta=2,layer_quantiles=[.05,.95]),
 probe=dict(box_quantiles=[.001,.999],box_margin_diagonal=.1,ray_min_samples=256,ray_max_samples=2048,ray_max_step_delta=.5,refine_levels=2,refine_samples=8,min_views=3,min_baseline_degrees=20,residual_clip=6,gauss_newton_steps=5,max_displacement_delta=1,max_step_delta=.5,detector_offsets=[[0,0],[1,0],[-1,0],[0,1],[0,-1]],lambda1_lambda2_max=.1,lambda3_lambda2_max=25,transverse_factor=5.99,uncertainty_delta_max=1,rms_max=1.5,angle_median_max=10,foreshortening_pixels=.25,ambiguity_rms_gap=.5,ambiguity_transverse_delta=2),
 controls=dict(shift_pixels=32,random_seed=20260918,pca_seed_fraction=.3,pca_dt_sigma=2,pca_radius_mult=3,pca_k_scale=8),
 gates=dict(G1_min_count=64,G2_coverage_min=.8,G2_joint_min=.8,G2_min_views=2,G2_dt_max=2,G2_angle_max=20,G3_match_min=.8,G3_distance_delta_max=2,G3_angle_max=20,G3_median_delta_max=.5,G3_p90_delta_max=1,G3_median_angle_max=10,G3_p90_angle_max=20,G3_count_change_max=.15,G4_shift_ratio_max=1/3,G4_random_angle_ratio_max=.5,G4_precision_loss_max=.02,G4_wrong_depth_reduction_min=.25,G4_count_gain_min=.20,G2_manual_precision_min=.85,G2_manual_pca_gain_min=.10,manual_status='UNCERTIFIED'),
 surface=dict(max_locations=128,radii_delta=[2,4,8],cell_delta=.5,bootstrap_samples=32,min_sheet_cells=30,min_plane_cells=15,p90_h_max=.15,normal_p90_max=15,plane_spread_min=.1,twoplane_gain_min=.3,twoplane_angle_min=25),
 visuals=dict(fixed_train=[1,27,53,79],fixed_dev=dev,glyph_count=64,glyph_half_length_delta=1,glyph_width=1,ink_fraction=.6,ink_tolerance=.05,video_frames=120,fps=24,phase_degrees=22.5,elevation_base=25,elevation_amplitude=8),
 budget=dict(prerequisite_seconds_per_scene=7200,probe_seconds_per_scene=28800))
freeze_json(out/'config.json',cfg)
print('frozen',len(inputs),'input files; config',sha(out/'config.json'))
