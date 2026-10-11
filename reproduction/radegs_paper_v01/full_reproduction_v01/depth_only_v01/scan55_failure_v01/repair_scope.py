from pathlib import Path
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/depth_only_v01/scan55_failure_v01')
def validate(c):
 expected={'method_variant':'official_code_fix_v01','scene':'scan55','purpose':'scan55_eigen_fallback_validation','replay_limit':2,'stable_seconds':60,'allowed_gpu_uuids':['GPU-d2d1e4fd-e246-0633-3343-ccc0a0bd981a'],'automatic_scene_limit':1}
 if any(c.get(k)!=v for k,v in expected.items()):raise ValueError('bounded replay scope mismatch')
 if set(c.get('stage_commands',{}))!={'smoke'} or any(k in c for k in ('train_command','eval_command','tsdf_command')):raise ValueError('diagnostic only, no pipeline dispatch')
 if any(not Path(c[k]).resolve().is_relative_to(ROOT) for k in ('model','state_dir')):raise ValueError('isolated replay output required')
