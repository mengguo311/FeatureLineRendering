"""CPU-only C24 TSDF from sealed exports with the frozen sparse-touch bridge.

No new renderer/train/GPU invocation; old model/exports/seals are read-only inputs.
"""
import datetime
import argparse
import json
from pathlib import Path
import shutil
import sys
import traceback
import numpy as np
from PIL import Image
import open3d as o3d
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tsdf_touch import touch_blocks
from empty_mesh import extract_mesh

WORK=Path(__file__).resolve().parents[4]
HDD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
OUT=HDD/'full_reproduction_v01/scan24_outputs'
ART=WORK/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01'
MODEL=HDD/'models/scan24_paper_text_precision_v01_half_30k'
PARENT=HDD/'full_reproduction_v01/precision_v01/pilot_v02/state'
sys.path.insert(0,str(WORK/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,sha256,verify_seal,seal_stage


def main():
    global OUT
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    OUT=parser.parse_args().output.resolve()
    assert OUT.is_relative_to(HDD/'full_reproduction_v01')
    OUT.mkdir(exist_ok=True,parents=True)
    assert not (OUT/'tsdf_inputs.json').exists(),'use a fresh attempt directory; preserve failure evidence'
    assert not (OUT/'tsdf.seal.json').exists(),'already sealed; do not overwrite'
    assert shutil.disk_usage('/').free>=10*1024**3
    assert shutil.disk_usage(HDD).free>=50*1024**3
    c=json.loads((PARENT/'runner_config.json').read_text())
    for stage in ['train','export']:assert verify_seal(PARENT/(stage+'.seal.json'),stage,c['inputs'])
    rule=HDD/'full_reproduction_v01/tsdf_bridge_v01/FROZEN_RULE.json'
    assert 'OK' in (HDD/'full_reproduction_v01/logs/tsdf_touch_GREEN.log').read_text()
    inputs={'parent_train_seal':sha256(PARENT/'train.seal.json'),'parent_export_seal':sha256(PARENT/'export.seal.json'),
            'frozen_allocation_rule':sha256(rule),'touch_adapter':sha256(Path(__file__).resolve().parents[1]/'tsdf_touch.py'),
            'extractor':sha256(__file__),'empty_reporter':sha256(Path(__file__).resolve().parents[1]/'empty_mesh.py'),
            'training_inputs':c['inputs']}
    atomic_json(OUT/'tsdf_inputs.json',inputs)
    cams=json.loads((MODEL/'depth_normal/cameras_and_conventions.json').read_text())
    rows=[]
    vbg=o3d.t.geometry.VoxelBlockGrid(attr_names=('tsdf','weight'),attr_dtypes=(o3d.core.float32,o3d.core.float32),
        attr_channels=(1,1),voxel_size=.002,block_resolution=16,block_count=50000,device=o3d.core.Device('CPU:0'))
    for cam in cams:
        view=cam['view'];W,H=cam['width'],cam['height']
        with np.load(MODEL/'depth_normal'/(view+'.npz')) as data:
            depth=data['median_camera_z'][0].copy();alpha=data['alpha'][0]
        mask=np.asarray(Image.open(HDD/'data/prepared/scan24/images'/(view+'.png')).split()[3].resize((W,H)))/255
        depth[(mask<.5)|(alpha<.5)]=0
        k=np.array([[cam['fx'],0,W/2],[0,cam['fy'],H/2],[0,0,1]],np.float64)
        e=np.asarray(cam['extrinsic'],np.float64)
        coords,info=touch_blocks(vbg,depth,k,e)
        record={'view':view,**info,'integrated':coords is not None}
        if coords is not None:
            vbg.integrate(coords,o3d.t.geometry.Image(depth),o3d.core.Tensor(k),o3d.core.Tensor(e),1.,8.)
        rows.append(record);atomic_json(OUT/'tsdf_progress.json',{'views':rows,'total_views':len(cams),'scientificdone':False})
        print(json.dumps(record),flush=True)
    assert len(rows)==49 and any(r['integrated'] for r in rows),'no contributing views'
    active=vbg.hashmap().active_buf_indices().numpy().astype(np.int64)
    weights=vbg.attribute('weight').numpy()[active].reshape(-1)
    tsdfs=vbg.attribute('tsdf').numpy()[active].reshape(-1)
    observed=weights>0
    volume={'active_blocks':len(active),'active_voxels':len(weights),
            'observed_voxels':int(observed.sum()),'weight_max':float(weights.max()),
            'weight_histogram':{str(x):int((weights==x).sum()) for x in np.unique(weights)},
            'tsdf_observed_range':[float(tsdfs[observed].min()),float(tsdfs[observed].max())] if observed.any() else None,
            'surface_support':{str(threshold):{'voxels':int((weights>=threshold).sum()),
                'negative_tsdf_voxels':int(((weights>=threshold)&(tsdfs<0)).sum()),
                'nonnegative_tsdf_voxels':int(((weights>=threshold)&(tsdfs>=0)).sum())} for threshold in [1,2,3]},
            'default_mesh_weight_threshold':3.,'parameters_changed':False}
    atomic_json(OUT/'volume_diagnostics.json',volume)
    vbg.save(str(OUT/'tsdf_volume.npz'))
    print(json.dumps({'volume':volume}),flush=True)
    # Same API/default weight threshold as C24. Do not lower it for sparse data.
    mesh,extraction=extract_mesh(vbg)
    if len(mesh.vertices):mesh.compute_vertex_normals()
    vertices=np.asarray(mesh.vertices);triangles=np.asarray(mesh.triangles)
    detail={'vertices':len(vertices),'triangles':len(triangles),'finite_vertices':bool(np.isfinite(vertices).all()),
            'integrated_views':sum(r['integrated'] for r in rows),'skipped_empty_views':[r['view'] for r in rows if not r['integrated']],
            'sparse_allocation_fallback_views':[r['view'] for r in rows if r['mode']=='SPARSE_VALID_DEPTH_STRIDE1_FALLBACK'],
            'bounds_scene':{'min':vertices.min(0).tolist(),'max':vertices.max(0).tolist()} if len(vertices) else None,
            'view_records':rows,'open3d_version':o3d.__version__,'extract_mesh_API':vbg.extract_triangle_mesh.__doc__,
            'native_extraction':extraction,'volume_diagnostics':volume,
            'method':'C24 TSDF values/parameters; explicit sparse-depth allocation bridge; does not repair the training geometry',
            'scientificdone':False,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    atomic_json(OUT/'tsdf_result.json',detail)
    if not len(vertices) or not len(triangles) or not np.isfinite(vertices).all():
        raise RuntimeError('NEGATIVE_GEOMETRY_RESULT: no valid finite triangle mesh under original TSDF thresholds')
    mesh_path=OUT/'recon.ply';assert o3d.io.write_triangle_mesh(str(mesh_path),mesh)
    report={'stage':'tsdf','status':'PASS','operation':'new CPU extraction from verified reused exports; not a new training',
            'inputs':inputs,'details':detail,'outputs':{str(p):sha256(p) for p in [mesh_path,OUT/'tsdf_result.json',OUT/'tsdf_progress.json']},'scientificdone':False}
    atomic_json(OUT/'tsdf.report.json',report)
    seal_stage(OUT/'tsdf.seal.json','tsdf',inputs,[OUT/'tsdf.report.json',*map(Path,report['outputs'])])
    master=json.loads((ART/'MASTER_STATUS.json').read_text());master.update(phase='SCAN24_OFFICIAL_EVAL',status='TSDF_BRIDGE_MESH_CREATED_EVAL_PENDING',last_event='CPU TSDF bridge produced finite mesh; poor opacity/coverage remains a negative result',next_action='official C24 DTU evaluation under authorized GPU0 admission; mesh visuals',utc=detail['utc']);master['verified_stages'].append('tsdf_sparse_allocation_bridge');atomic_json(ART/'MASTER_STATUS.json',master)
    print(json.dumps({k:detail[k] for k in ['vertices','triangles','integrated_views','sparse_allocation_fallback_views']}),flush=True)


if __name__=='__main__':
    try:main()
    except Exception as exc:
        atomic_json(OUT/'failure.json',{'status':'ENGINEERING_NOT_READY','error':repr(exc),'traceback':traceback.format_exc(),'scientificdone':False})
        raise
