"""Metadata/byte-hash-only prefreeze: deliberately no numpy/image decode."""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, datetime

ROOT=Path(__file__).resolve().parents[3]
ART=ROOT/'artifacts/gaussian_edge_attribution_v1'
SOURCE=Path('/home/u00134/3dgs_line/hybrid_raster_trained_models_v1/artifacts/hybrid_raster_trained_models_v1')
TRANSPORT=Path('/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/transport')
F=[1,14,27,41,53,67,79,93]; C=[7,21,33,47,59,73,86,99]

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def atomic(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.partial')
    tmp.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')
    os.replace(tmp,path)

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

def main():
    assert ROOT==Path('/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/gaussian_edge_attribution_v1')
    expected=Path('/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/mic_fixed3d_standalone/.git')
    common=Path(git('rev-parse','--git-common-dir')).resolve()
    assert common==expected and not (common/'objects/info/alternates').exists()
    assert git('branch','--show-current')=='gaussian-edge-attribution-v1'
    assert git('rev-parse','HEAD')=='d5c6d4d114b6b80ec5edb9c1717111e89a191eda'
    assert not os.environ.get('GIT_ALTERNATE_OBJECT_DIRECTORIES')
    payload=20*1024**3; reserve=1024**3
    assert shutil.disk_usage(ROOT).free>payload+reserve
    record={'schema':'gaussian-edge-input-freeze-v1','created_utc':utc(),'workspace':str(ROOT),
        'base_sha':git('rev-parse','HEAD'),'branch':git('branch','--show-current'),
        'git_common_dir':str(common),'alternates':False,'estimated_write_payload_bytes':payload,
        'reserve_bytes':reserve,'available_bytes':shutil.disk_usage(ROOT).free,
        'requested_scenes':['mic','materials'],'requested_pose_count':98,
        'F':F,'C':C,'arc_count':33,'scenes':{},'source_files':{},'root_git_control_snapshot':{}}
    rootgit=Path('/home/u00134/3dgs_line/tier1/.git')
    for p in [rootgit/n for n in ('HEAD','config','index','packed-refs')]:
        if p.is_file():record['root_git_control_snapshot'][str(p)]={'sha256':sha(p),'mtime_ns':p.stat().st_mtime_ns}
    rels=['INHERITED_LOCK.json','CHECKPOINT_CAMERA_FREEZE.json','INPUTS.json','transport/INHERITED_LOCK.json',
          'transport/PREDECLARED_CAMERAS.json','transport/SOURCE_MANIFEST.json','transport/RENDER_FREEZE.json',
          'transport/adapters.py','transport/run_transport.py']
    for scene in ('mic','materials'):
        rels += [f'transport/{scene}/CAMERAS.json',f'transport/{scene}/CALIBRATION.json',
                 f'acquisition/results/{scene}/CHECKPOINT_LOCK.json',f'acquisition/manifests/{scene}.json']
    for rel in rels:
        src=SOURCE/rel;dst=ART/'lineage'/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        data=src.read_bytes()
        if dst.exists():assert dst.read_bytes()==data
        else:dst.write_bytes(data)
        record['source_files'][str(src)]={'sha256':sha(src),'copy':str(dst.relative_to(ROOT))}
    for scene in ('mic','materials'):
        camera=SOURCE/f'transport/{scene}/CAMERAS.json'; cam=json.loads(camera.read_text())
        checkpoint=Path(cam['checkpoint']['path']);assert sha(checkpoint)==cam['checkpoint']['sha256']
        lock=json.loads((SOURCE/f'acquisition/results/{scene}/CHECKPOINT_LOCK.json').read_text())
        assert lock['checkpoints']['30000']['sha256']==cam['checkpoint']['sha256']
        assert lock['seed']==1729 and lock['iterations']==30000 and lock['state']=='COMPLETE'
        specs=[(f'F_{i:03d}',cam['cameras'][str(i)]) for i in F]+[(f'C_{i:03d}',cam['cameras'][str(i)]) for i in C]
        specs += [(f'arc0_{i:03d}',v) for i,v in enumerate(cam['arcs'][0]['frames'])]
        assert len(specs)==49
        frames=[]
        for key,expected_cam in specs:
            base=TRANSPORT/'raw'/scene/key; seal=json.loads((base/'SEAL.json').read_text())
            assert sha(base/'SEAL.json')==(base/'SEAL.sha256').read_text().strip()
            assert seal['context']['checkpoint_sha256']==cam['checkpoint']['sha256']
            assert seal['context']['camera']==expected_cam
            for name,h in seal['files'].items():assert sha(base/name)==h,(scene,key,name)
            frames.append({'key':key,'raw_path':str(base/'native.npz'),'raw_sha256':seal['files']['native.npz'],
              'seal_path':str(base/'SEAL.json'),'seal_sha256':sha(base/'SEAL.json'),
              'camera':expected_cam,'camera_hash':seal['context']['camera_hash'],
              'camera_json_sha256':seal['files']['camera.json']})
        record['scenes'][scene]={'checkpoint':cam['checkpoint'],'camera_manifest_path':str(camera),
            'camera_manifest_sha256':sha(camera),'training_lock':lock,'frames':frames}
    path=ART/'INPUTS_FROZEN.json'
    if path.exists():raise RuntimeError('Input freeze already exists; do not overwrite')
    atomic(path,record)
    seal={'schema':'protocol-freeze-v1','created_utc':utc(),'pixels_decoded_before_seal':False,
      'files':{str(p.relative_to(ROOT)):sha(p) for p in [path,ART/'PROTOCOL.md',ART/'code/config.json']}}
    atomic(ART/'PROTOCOL_SEAL.json',seal)
    atomic(ART/'STATUS.json',{'state':'PROTOCOL_FROZEN_BEFORE_PIXEL_READ','utc':utc(),'protocol_seal_sha256':sha(ART/'PROTOCOL_SEAL.json'),
      'F_assets_sealed':[],'C_pixels_read':[],'actual_pose_count':0,'requested_pose_count':98})
    print(json.dumps({'seal':sha(ART/'PROTOCOL_SEAL.json'),'raw_inputs':98,'payload_bytes':payload,'free_bytes':record['available_bytes']}))

if __name__=='__main__':main()
