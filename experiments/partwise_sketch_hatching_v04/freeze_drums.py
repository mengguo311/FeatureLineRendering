"""One bounded Drums transfer, using original cameras without a registry cache."""
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
    root=runtime.OUTPUT_ROOT;manifest=root/'orchestration/EXISTING_MODEL_INPUTS.json'
    original=json.loads(manifest.read_text())['drums']
    assert sha(original['original_ply'])==original['sha256']
    inp=Path(original['input_directory'])
    train=json.loads((inp/'transforms_train.json').read_text())
    test=json.loads((inp/'transforms_test.json').read_text())
    frames=train['frames'];directions=normalize(np.array([f['transform_matrix'] for f in frames])[:,:3,3])
    chosen=[next(i for i,f in enumerate(frames) if f['file_path'].endswith('/r_7'))]
    while len(chosen)<24:
        dist=np.min(1-directions@directions[chosen].T,axis=1);dist[chosen]=-1
        chosen.append(int(np.argmax(dist)))
    def camera(frame,data,split,size=400):
        return camera_from_gl(frame['transform_matrix'],data['camera_angle_x'],size,size,
                              split+'_'+Path(frame['file_path']).name,split)
    build=[camera(frames[i],train,'train') for i in chosen]
    selected=[('train',train,frames[chosen[0]])]
    selected += [('test',test,next(f for f in test['frames'] if f['file_path'].endswith('/r_'+str(i)))) for i in (1,27,79)]
    static=[camera(f,d,s) for s,d,f in selected]
    refs={c['view']:str((inp/(f['file_path']+'.png')).resolve()) for c,(_,_,f) in zip(static,selected)}
    static += [orbit_camera(a,24,4.9) for a in (67,157,247,337)]
    previous=root/'units/unit_004'
    inputs=[manifest,inp/'transforms_train.json',inp/'transforms_test.json',Path(original['original_ply']),
            *map(Path,refs.values()),unit/'INVENTORY.json',previous/'STATUS.json',previous/'REPORT_ZH.md',
            previous/'NEXT.json',previous/'ENGINEERING_SEAL.json']
    p=dict(version=5,frozen_utc=now(),scene='drums',previous_unit=str(previous),original=original,
      inputs_sha256={str(f):sha(f) for f in inputs},input_cache_probe=None,references=refs,
      build_cameras=build,static_cameras=static,
      camera_selection='24 original training poses by greedy angular farthest from train_r_7; evaluation original test names 1/27/79 plus frozen virtual poses',
      geometry='CPU covariance-plane median z from exact frozen vanilla 3DGS; confidence/jump-gated TSDF; exploratory, not RaDe-trained, not GT',
      filtering=dict(alpha_min=.95,near=.2,far=6.,max_center_difference=.06,max_3x3_jump=.08,voxel=.012,
        sdf_trunc=.036,remove_components_below_triangles=40,simplify_faces=30000,bounds='opacity > .5 centers min/max plus .06'),
      region_rule=dict(axis='z',cuts=[-.15,.42],assignment='face centroid, persisted face IDs'),
      regions={'1':'Lower: z < -0.15 (blue)','2':'Middle: -0.15 <= z < 0.42 (amber)','3':'Upper: z >= 0.42 (green)'},
      region_provenance='authored world-height thresholds from original PLY coordinate inventory; NOT semantic drum/cymbal parts; no manual geometric repair',
      styles={str(i):dict(angle=a,spacing=.045,length=.22,width=1.) for i,a in [(1,0.),(2,45.),(3,-25.)]},
      changed_variable=dict(region=2,angle=95.,fixed='same geometry/labels/non-target paths/cameras/all other styles'),
      renderer=dict(size=512,supersample=2,depth_tolerance=.004,contour='view mask/depth edges, separate from fixed paths'),
      orbit=[orbit_camera(67+30*k,24,4.9) for k in range(12)],
      zoom=[orbit_camera(97,28,float(d)) for d in np.linspace(5.5,4.5,6)],
      viewer_camera=dict(azimuth=67,elevation=24,distance=4.9),
      expected_tests=['original model direct CPU extraction','local target change and exact non-target paths/layers',
        'full-object reference/proxy/regions/hatch and weak views','cold reload exact','all four HTTP style controls',
        'actual browser orbit/zoom/reload','export ZIP cold reload','portable relocated cold reload','full video decode'],
      comparison_scope='third-model engineering transfer; no H1/H2 test, no accuracy or visual superiority claim',
      exposure='training views used for fusion; existing Drums dataset may be historically exposed; new virtual poses frozen before outputs, not blind evaluation',
      previous_review=dict(inspected='unit004 actual reference/proxy/region/hatch all 8 rows',
        positives='Lego whole-object edit/browser/export/reload functional, authored front region separate from roof',
        negatives='short fragments, crowded wavy base, side/rear holes and missing thin rods; manual region includes support',
        ranked=['bounded Drums transfer','one Lego hatch readability candidate','click/brush selector'],
        choice='retain runnable pipeline, test materially different curved/thin real model; no perfect toy gate'),
      resource_limits=dict(cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,serial=True,gpu=False,nested_models=False),
      unit_deadline_jst='2026-10-22T04:33:43+09:00',no_new_science_after_jst='2026-10-22T09:20:00+09:00',science_wrap_jst='2026-10-22T09:45:00+09:00')
    js(unit/'PROTOCOL.json',p);js(Path('docs/partwise_sketch_hatching_v04/UNIT005_PROTOCOL.json'),p)
    js(unit/'DEPENDENCIES.json',dict(python=__import__('platform').python_version(),packages={k:importlib.metadata.version(k)
      for k in ['numpy','scipy','Pillow','open3d','scikit-image','plyfile']},installed_new_dependencies=False))
    print(json.dumps(dict(protocol=str(unit/'PROTOCOL.json'),sha256=sha(unit/'PROTOCOL.json'))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',required=True,type=Path);freeze(p.parse_args().unit)
