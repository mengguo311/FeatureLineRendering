"""TRAIN metadata and checkpoint adapters; unchanged inherited scientific computation."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import numpy as np
from scipy.spatial.transform import Rotation, Slerp

ROOT=Path(__file__).resolve().parents[3]
ART=ROOT/'artifacts/hybrid_raster_trained_models_v1/transport'
OUT=ROOT/'out/hybrid_raster_trained_models_v1/transport'
OLD=Path('/home/u00134/3dgs_line/hybrid_raster_evidence_v2')
F=[1,14,27,41,53,67,79,93]
C=[7,21,33,47,59,73,86,99]
SCENES=('hotdog','materials','mic','ship')
LOCK_SHA='d5ec038e8ebc8a7160bc9e31ebb6ac8ce755fdbf1677a32ad55102a48c6a0926'
PARAMETER_HASH='6c4ef4afa648f54794d7094a7b21368a89e14cdbc792766441aa3d3639d487c9'
# Python imports are read-only, including the old modules; no .pyc in references.
sys.dont_write_bytecode=True
sys.path.insert(0,str(OLD))
from src.hybrid_raster_io import hash_file, canonical_hash, atomic_json, valid_seal, seal_frame


def frozen_json(path,value):
    path=Path(path)
    if path.exists():
        if canonical_hash(json.loads(path.read_text())) != canonical_hash(value):
            raise RuntimeError('Frozen manifest differs: '+str(path))
    else: atomic_json(path,value)


def inherited():
    path=OLD/'out/hybrid_raster_evidence_v2/LOCK.json'
    if hash_file(path)!=LOCK_SHA:raise RuntimeError('Inherited LOCK bytes changed')
    lock=json.loads(path.read_text())
    if lock['parameter_hash']!=PARAMETER_HASH:raise RuntimeError('Inherited parameters changed')
    if canonical_hash({k:v for k,v in lock.items() if k!='lock_hash'})!=lock['lock_hash']:raise RuntimeError('Invalid inherited lock hash')
    if canonical_hash({'config':lock['config'],'normalization':lock['normalization']})!=PARAMETER_HASH:raise RuntimeError('Invalid inherited parameter hash')
    sources={key:hash_file(OLD/key) for key in lock['config']['sources']}
    if sources!=lock['config']['sources']:raise RuntimeError('Inherited scientific source changed')
    from src.hybrid_raster_native import source_hashes
    native=source_hashes()
    if native!=lock['config']['native_build']:raise RuntimeError('Inherited native build metadata changed')
    for variant in native['variants'].values():
        if hash_file(variant['path'])!=variant['sha256']:raise RuntimeError('Native binary changed')
    return lock,{'lock_path':str(path),'lock_sha256':LOCK_SHA,'parameter_hash':PARAMETER_HASH,
                 'sources':sources,'native_build':native,'arc_source_sha256':hash_file(OLD/'artifacts/direct_curve_global_fit_probe/freeze.py')}


def camera_from_train(metadata,index,width,height):
    if (width,height)!=(800,800):raise ValueError('Experiment predeclares native 800x800')
    if index not in F+C:raise ValueError('Unexpected camera index')
    transform=np.asarray(metadata['frames'][index]['transform_matrix'],dtype=np.float64)
    if transform.shape!=(4,4) or not np.isfinite(transform).all():raise ValueError('Malformed TRAIN pose')
    w2c=np.linalg.inv(transform@np.diag([1.,-1.,-1.,1.]))
    fov=float(metadata['camera_angle_x']);fx=width/(2*np.tan(fov/2))
    if not 0<fov<np.pi:raise ValueError('Invalid FoV')
    return dict(w2c=w2c.tolist(),native_K=[[float(fx),0.,(width-1)/2],[0.,float(fx),(height-1)/2],[0.,0.,1.]],
                native_width=width,native_height=height,FoVx=fov,FoVy=float(2*np.arctan(height/(2*fx))),index=index,split='train')


def predeclare():
    _,heritage=inherited();scenes={}
    for scene in SCENES:
        data=Path('/home/u00134/cglib/data/full')/scene
        path=data/'transforms_train.json';meta=json.loads(path.read_text())
        for i in F+C:
            if Path(meta['frames'][i]['file_path']).as_posix().removeprefix('./') != f'train/r_{i}':
                raise ValueError('TRAIN frame order does not match predeclared numerical camera index')
        # Header only: no PIL/open-image decode, and never C image bytes.
        header_path=data/'train/r_1.png'
        with header_path.open('rb') as stream:header=stream.read(24)
        if header[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Invalid PNG header')
        width,height=struct.unpack('>II',header[16:24])
        scenes[scene]={'metadata':{'path':str(path),'sha256':hash_file(path),'frame_count':len(meta['frames'])},
                       'size_evidence':{'path':str(header_path),'bytes_read':24,'pixel_decode':False,'sha256':hashlib.sha256(header).hexdigest()},
                       'checkpoint_destination':str(ROOT/f'out/hybrid_raster_trained_models_v1/training/{scene}/seed_1729/checkpoints/point_cloud/iteration_30000/point_cloud.ply'),
                       'cameras':{str(i):camera_from_train(meta,i,width,height) for i in F+C}}
    value={'schema':'trained-transport-predeclared-v1','scenes':scenes,'F':F,'C':C,'expected_frames':196,
           'inherited':heritage,'arc_recipe':{'endpoints':[7,33],'count':33,'t':'numpy.linspace(0,1,33)',
           'center':'mean of float64 checkpoint mu per-axis quantiles .001/.999; same center as symmetric .1*diagonal expanded eligibility box',
           'algorithm':'exact inherited freeze.py spherical position interpolation, linear radius, SciPy rotation Slerp; no look-at',
           'resolution_time':'checkpoint hash and exact resulting poses freeze+commit/push before NPR render'},
           'C_disclosure':'C cameras belong to vanilla GS TRAIN; only held out from NPR fitting. No new NPR fitting anywhere.'}
    frozen_json(ART/'PREDECLARED_CAMERAS.json',value)
    lockbytes=(OLD/'out/hybrid_raster_evidence_v2/LOCK.json').read_bytes()
    lockpath=ART/'INHERITED_LOCK.json'
    if lockpath.exists():
        if lockpath.read_bytes()!=lockbytes:raise RuntimeError('Copied inherited LOCK differs')
    else:
        with lockpath.open('xb') as stream:stream.write(lockbytes)
    return value


def arc_from_center(cameras,center):
    # Algebra and operation order are inherited from freeze.py, with fixed pair C7->C33.
    center=np.asarray(center,np.float64)
    poses=np.array([np.linalg.inv(cameras[str(i)]['w2c']) for i in [7,33]])
    loc=poses[:,:3,3]-center;r=np.linalg.norm(loc,axis=1);u=loc/r[:,None]
    ang=np.degrees(np.arccos(np.clip(u@u.T,-1,1)));ts=np.linspace(0,1,33);theta=np.radians(ang[0,1])
    if not np.isfinite(theta) or abs(np.sin(theta))<1e-12:raise ValueError('Degenerate inherited spherical arc')
    dirs=(np.sin((1-ts)*theta)[:,None]*u[0]+np.sin(ts*theta)[:,None]*u[1])/np.sin(theta)
    radius=(1-ts)*r[0]+ts*r[1];rotation=Slerp([0,1],Rotation.from_matrix(poses[:,:3,:3]))(ts).as_matrix();frames=[]
    for n,t in enumerate(ts):
        pose=np.eye(4);pose[:3,:3]=rotation[n];pose[:3,3]=center+dirs[n]*radius[n]
        frames.append(dict(w2c=np.linalg.inv(pose).tolist(),native_K=cameras['7']['native_K'],native_height=800,native_width=800,t=float(t)))
    if len({canonical_hash(c['w2c']) for c in frames})!=33:raise ValueError('Arc poses not all distinct')
    return {'endpoints':[7,33],'angle':float(ang[0,1]),'frames':frames}


def validate_training_lock(scene,checkpoint,digest,lock):
    if (lock.get('schema'),lock.get('state'),lock.get('scene'),lock.get('seed'),lock.get('iterations'))!=(1,'COMPLETE',scene,1729,30000):
        raise RuntimeError('Training checkpoint lock qualification mismatch')
    if set(lock.get('checkpoints',{}))!={'7000','30000'}:
        raise RuntimeError('Training checkpoint lock lacks both required iterations')
    row=lock['checkpoints']['30000']
    if row.get('iteration')!=30000 or Path(row['path']).resolve()!=Path(checkpoint).resolve() or row.get('sha256')!=digest:
        raise RuntimeError('Frozen final checkpoint does not match training lock')
    return True


def resolve(scene):
    if scene not in SCENES:raise ValueError(scene)
    from src.hybrid_raster_native import load_checkpoint
    inherited();pre=json.loads((ART/'PREDECLARED_CAMERAS.json').read_text());data=pre['scenes'][scene]
    checkpoint=data['checkpoint_destination'];digest=hash_file(checkpoint)
    training_lock=ROOT/f'out/hybrid_raster_trained_models_v1/training/{scene}/seed_1729/CHECKPOINT_LOCK.json'
    if not training_lock.is_file():raise RuntimeError('Training CHECKPOINT_LOCK missing')
    lineage=json.loads(training_lock.read_text())
    validate_training_lock(scene,checkpoint,digest,lineage)
    training_manifest=json.loads(Path(lineage['manifest_path']).read_text())
    if canonical_hash(training_manifest)!=lineage['manifest_sha256']:
        raise RuntimeError('Training manifest identity changed')
    if not json.loads(Path(lineage['audit']).read_text()).get('passed'):
        raise RuntimeError('Training syscall audit did not pass')
    g=load_checkpoint(checkpoint,digest)
    lo=np.quantile(g['mu'].astype(np.float64),.001,axis=0);hi=np.quantile(g['mu'].astype(np.float64),.999,axis=0)
    center=np.array([lo,hi]).mean(0);arc=arc_from_center(data['cameras'],center)
    value={'schema':'trained-transport-exact-cameras-v1','scene':scene,'F':F,'C':C,
           'predeclared_sha256':hash_file(ART/'PREDECLARED_CAMERAS.json'),
           'checkpoint':{'path':checkpoint,'sha256':digest,'qualification':g['_metadata']},
           'training_checkpoint_lock':{'path':str(training_lock),'sha256':hash_file(training_lock)},
           'center':center.tolist(),'quantile_box':[lo.tolist(),hi.tolist()],
           'cameras':data['cameras'],'arcs':[arc],'expected_frames':49,'parameter_hash':PARAMETER_HASH}
    frozen_json(ART/scene/'CAMERAS.json',value)
    return value


def frame_specs(manifest):
    scene=manifest['scene'];result=[]
    for split,indices in [('F',F),('C',C)]:
        result.extend({'scene':scene,'split':split,'index':i,'key':f'{split}_{i:03d}','camera':manifest['cameras'][str(i)]} for i in indices)
    arc=manifest['arcs'][0]['frames']
    if len(arc)!=33:raise ValueError('Expected 33 arc frames')
    result.extend({'scene':scene,'split':'arc0','index':i,'key':f'arc0_{i:03d}','camera':cam} for i,cam in enumerate(arc))
    return result

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--predeclare',action='store_true');parser.add_argument('--resolve',choices=SCENES)
    args=parser.parse_args()
    if args.predeclare:predeclare();print(ART/'PREDECLARED_CAMERAS.json')
    elif args.resolve:resolve(args.resolve);print(ART/args.resolve/'CAMERAS.json')
    else:parser.error('choose --predeclare or --resolve')
