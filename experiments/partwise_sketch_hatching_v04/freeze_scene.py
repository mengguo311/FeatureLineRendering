"""Unit003: one explicit Lego protocol, frozen before new outputs."""
import runtime
from runtime import sha,js,now,output_guard
from pathlib import Path
import argparse,json,os,importlib.metadata
import numpy as np
from model_adapter import camera_from_gl
from geometry import normalize,orbit_camera

def freeze(unit):
    unit=output_guard(unit)
    if (unit/'PROTOCOL.json').exists():raise FileExistsError('protocol already frozen')
    root=runtime.OUTPUT_ROOT
    manifest=root/'orchestration/EXISTING_MODEL_INPUTS.json'
    original=json.loads(manifest.read_text())['lego']
    assert sha(original['original_ply'])==original['sha256']
    registry=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/synthetic_three_gaussian_v01/REGISTRY.json')
    reg=json.loads(registry.read_text())['scenes']['lego']
    assert reg['model_sha256']==original['sha256']
    inp=Path(original['input_directory']);train=json.loads((inp/'transforms_train.json').read_text())
    frames=train['frames'];directions=normalize(np.array([f['transform_matrix'] for f in frames])[:,:3,3])
    chosen=[next(i for i,f in enumerate(frames) if f['file_path'].endswith('/r_7'))]
    while len(chosen)<24:
        dist=np.min(1-directions@directions[chosen].T,axis=1);dist[chosen]=-1
        chosen.append(int(np.argmax(dist)))
    build=[camera_from_gl(frames[i]['transform_matrix'],train['camera_angle_x'],400,400,
            'train_'+Path(frames[i]['file_path']).name,'train') for i in chosen]
    names=['train_r_7','test_r_1','test_r_27','test_r_79']
    static=[next(c for c in reg['cameras'] if c['view']==v) for v in names]
    static += [orbit_camera(a,28,4.9) for a in [23,113,203,293]]
    refs={v:reg['reference_images'][v] for v in names}
    cache=registry.parent/'scenes/lego/inputs/train_r_7.npz'
    previous=root/'units/unit_002'
    inputs={str(f):sha(f) for f in [manifest,registry,inp/'transforms_train.json',inp/'transforms_test.json',
        Path(original['original_ply']),cache,*[Path(v) for v in refs.values()],unit/'INVENTORY.json',
        previous/'STATUS.json',previous/'REPORT_ZH.md',previous/'NEXT.json',previous/'ENGINEERING_SEAL.json']}
    protocol=dict(version=3,frozen_utc=now(),scene='lego',previous_unit=str(previous),original=original,
      inputs_sha256=inputs,input_cache_probe=str(cache),references=refs,build_cameras=build,static_cameras=static,
      camera_selection='24 training poses by greedy angular farthest from train_r_7; no new image selection',
      geometry='CPU covariance-plane median z on exact frozen vanilla 3DGS; confidence/jump-gated TSDF; exploratory, not RaDe-trained or GT',
      filtering=dict(alpha_min=.95,near=.2,far=6.,max_center_difference=.06,max_3x3_jump=.08,voxel=.012,
        sdf_trunc=.036,remove_components_below_triangles=40,simplify_faces=30000,bounds='opacity > .5 centers min/max plus .06'),
      region_rule=dict(axis='z',cuts=[-.2,.45],assignment='face centroid, persisted face IDs'),
      regions={'1':'Lower: z < -0.20 (blue)','2':'Middle: -0.20 <= z < 0.45 (amber)','3':'Upper: z >= 0.45 (green)'},
      region_provenance='authored world-height thresholds after PLY coordinate inventory; NOT semantic parts; no PartField or manual geometric repair',
      styles={str(i):dict(angle=a,spacing=.045,length=.22,width=1.) for i,a in [(1,0.),(2,45.),(3,-25.)]},
      changed_variable=dict(region=2,angle=95.,fixed='same geometry, labels, non-target paths, cameras and all other styles'),
      renderer=dict(size=512,supersample=2,depth_tolerance=.004,contour='view mask/depth edges, separate from fixed paths'),
      orbit=[orbit_camera(23+30*k,28,4.9) for k in range(12)],
      zoom=[orbit_camera(53,32,float(d)) for d in np.linspace(5.5,4.5,6)],
      viewer_camera=dict(azimuth=23,elevation=28,distance=4.9),
      expected_tests=['nonzero local edit; exact non-target paths/layers','two-pixel boundary-band residual reported unchanged',
        'actual PLY build and source RGB','full-object weak views','frozen paths + cold reload exact',
        'real browser controls/export/reload','complete orbit/zoom decode','portable relocated cold run'],
      comparison_scope='engineering cross-model transfer, not comparative H1/H2 science or geometric accuracy gain',
      exposure='original training cameras used in reconstruction; archived views historically exposed; new virtual views frozen before candidate, not blind',
      previous_review=dict(chair='complete-object CLI/browser/export cold replay already works',
        negatives='sparse legs, side crowding; smoother option worsened source geometry in all 8 views; no further smoothing sweep',
        choice='next genuine model Lego, retaining same extraction/style backend'),
      resource_limits=dict(cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,serial=True,gpu=False,nested_models=False),
      unit_deadline_jst='2026-10-22T03:55:50+09:00')
    js(unit/'PROTOCOL.json',protocol)
    js(Path('docs/partwise_sketch_hatching_v04/UNIT003_PROTOCOL.json'),protocol)
    js(unit/'DEPENDENCIES.json',dict(python=__import__('platform').python_version(),
       packages={k:importlib.metadata.version(k) for k in ['numpy','scipy','Pillow','open3d','scikit-image','plyfile']},installed_new_dependencies=False))
    print(json.dumps(dict(protocol=str(unit/'PROTOCOL.json'),sha256=sha(unit/'PROTOCOL.json'))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True);freeze(p.parse_args().unit)
