from pathlib import Path
GPU='GPU-d2d1e4fd-e246-0633-3343-ccc0a0bd981a'
def validate_scope(c):
 root=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/depth_only_v01')
 expected={'method_variant':'official_code_fix_v01','scene':'scan40','automatic_scene_limit':1,'allowed_gpu_uuids':[GPU],'stable_seconds':60,'purpose':'official_C24_scan40_depth_only_half30k','workflow':'depth_only_v01','iterations':30000,'resolution_divisor':2,'wd':100,'wn':.05,'regularization_from_iter':15000,'geometry_start_inclusive':True,'optimizer_final_step':False,'data':'/mnt/hdd1/u00134/radegs_paper_reproduction_v01/data/prepared/scan40'}
 if any(c.get(k)!=v for k,v in expected.items()):raise ValueError('C24 configuration scope mismatch')
 if set(c.get('stage_commands',{}))!={'smoke','train','export','depth_review'}:raise ValueError('depth-only stage set required')
 if not all(c.get('inputs',{}).get(k) for k in ('native_validated','runtime_validated','previous_depth_review')):raise ValueError('GPU native/runtime gates missing')
 if any(not Path(c[k]).resolve().is_relative_to(root) for k in ('model','state_dir')):raise ValueError('isolated output scope mismatch')
