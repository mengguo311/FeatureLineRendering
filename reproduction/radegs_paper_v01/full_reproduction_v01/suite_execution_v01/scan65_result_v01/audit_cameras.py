"""CPU audit: COLMAP binary -> sealed export extrinsics -> official eval scale.

Calibration is used only to audit the evaluator coordinate transform.
"""
import ast
import importlib.util
import json
from pathlib import Path
import numpy as np
import cv2

HDD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
SOURCE=HDD/'sources/RaDe-GS'
spec=importlib.util.spec_from_file_location('c24_colmap',SOURCE/'scene/colmap_loader.py')
colmap=importlib.util.module_from_spec(spec);spec.loader.exec_module(colmap)
sparse=HDD/'data/prepared/scan65/sparse/0'
images=colmap.read_extrinsics_binary(sparse/'images.bin')
intrinsics=colmap.read_intrinsics_binary(sparse/'cameras.bin')
images={Path(im.name).stem:im for im in images.values()}
cameras=json.loads((HDD/'models/scan65_paper_text_precision_v01_half_30k/depth_normal/cameras_and_conventions.json').read_text())
rows=[];centers=[]
for c in cameras:
    im=images[c['view']];raw=intrinsics[im.camera_id]
    r=colmap.qvec2rotmat(im.qvec);expected=np.eye(4);expected[:3,:3]=r;expected[:3,3]=im.tvec
    actual=np.array(c['extrinsic']);centers.append(np.linalg.inv(actual)[:3,3])
    rows.append({'view':c['view'],'extrinsic_abs_error':float(abs(actual-expected).max()),
        'rotation_determinant':float(np.linalg.det(actual[:3,:3])),
        'rotation_orthogonality_error':float(abs(actual[:3,:3]@actual[:3,:3].T-np.eye(3)).max()),
        'focal_half_abs_error':float(max(abs(c['fx']-raw.params[0]/2),abs(c['fy']-raw.params[1]/2))),
        'resolution_half_exact':(c['width']*2,c['height']*2)==(raw.width,raw.height),
        'original_principal_point_is_center':bool(np.allclose(raw.params[2:],[raw.width/2,raw.height/2]))})
assert max(r['extrinsic_abs_error'] for r in rows)<1e-6
assert all(r['resolution_half_exact'] for r in rows)
# Execute only these original numpy/cv2 functions; no Scene/torch/CUDA import.
module=ast.parse((SOURCE/'evaluate_dtu_mesh.py').read_text())
functions=[x for x in module.body if isinstance(x,ast.FunctionDef) and x.name in ['best_fit_transform','load_dtu_camera']]
scope={'np':np,'cv2':cv2,'path':__import__('os').path}
exec(compile(ast.Module(body=functions,type_ignores=[]),'C24_evaluation_pure_functions','exec'),scope)
gt=np.array([c[:,3] for c in scope['load_dtu_camera'](str(HDD/'data/eval_gt/dtu_eval_scan65'))])[:len(centers)]
points=np.array(centers)
scale=np.linalg.norm(gt-gt.mean(0),axis=1).mean()/np.linalg.norm(points-points.mean(0),axis=1).mean()
_,rot,trans=scope['best_fit_transform'](points*scale,gt)
residual=np.linalg.norm((points*scale)@rot.T+trans-gt,axis=1)
result={'views':rows,'world_to_camera_matches_COLMAP_binary':True,
    'evaluation_only_mm_per_scene_unit':float(scale),'voxel_size_scene_units':.002,
    'evaluation_equivalent_voxel_mm':float(scale*.002),
    'camera_center_alignment_residual_mm':{'mean':float(residual.mean()),'max':float(residual.max())},
    'evaluation_rotation':rot.tolist(),'evaluation_translation_mm':trans.tolist(),
    'GT_role':'coordinate audit for evaluation only; not training or parameter selection',
    'conclusion':'raw depth camera-z is in normalized reconstruction units, not millimeters; depth_scale=1 matches C24'}
out=HDD/'full_reproduction_v01/suite_execution_v01/scan65_result_v01/diagnosis/camera_and_scale_audit.json'
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='views'}))
