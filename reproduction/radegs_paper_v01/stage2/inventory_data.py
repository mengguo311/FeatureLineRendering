"""Verify the downloaded scan24 input and eval-only GT without loading CUDA."""
import importlib.util
import json
from pathlib import Path
import shutil
import struct

import numpy as np
from PIL import Image
from plyfile import PlyData
from scipy.io import loadmat
from safety import atomic_json,sha256

ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')


def main():
    raw=ROOT/'data/raw/dtu_original/DTU'
    prepared=ROOT/'data/prepared/scan24'
    loader=ROOT/'sources/RaDe-GS/scene/colmap_loader.py'
    spec=importlib.util.spec_from_file_location('standalone_colmap_loader',loader)
    colmap=importlib.util.module_from_spec(spec);spec.loader.exec_module(colmap)
    scenes={}
    for scene in sorted(raw.glob('scan*')):
        files=list(scene.rglob('*'));images=sorted((scene/'images').glob('*.png'))
        dimensions=set()
        for path in images:
            with Image.open(path) as image:dimensions.add((image.width,image.height,image.mode))
        scenes[scene.name]={'files':sum(p.is_file() for p in files),'images':len(images),
                            'image_dimensions_modes':sorted(dimensions)}
    expected={f'scan{i}' for i in [24,37,40,55,63,65,69,83,97,105,106,110,114,118,122]}
    assert set(scenes)==expected
    cameras=colmap.read_intrinsics_binary(str(prepared/'sparse/0/cameras.bin'))
    extr=colmap.read_extrinsics_binary(str(prepared/'sparse/0/images.bin'))
    image_names={p.name for p in (prepared/'images').glob('*.png')}
    assert len(extr)==49 and {x.name for x in extr.values()}==image_names
    assert len(cameras)==1
    camera=next(iter(cameras.values()))
    assert camera.model=='PINHOLE' and (camera.width,camera.height)==(1554,1162)
    assert np.isfinite(camera.params).all() and camera.params[0]>0 and camera.params[1]>0
    masks=[]
    for path in sorted((prepared/'images').glob('*.png')):
        with Image.open(path) as image:
            image.load();assert image.mode=='RGBA' and image.size==(camera.width,camera.height)
            alpha=np.asarray(image.getchannel('A'))
            assert alpha.min()==0 and alpha.max()==255
            masks.append({'name':path.name,'alpha_nonzero':int(np.count_nonzero(alpha)),
                          'alpha_min':int(alpha.min()),'alpha_max':int(alpha.max())})
    ply=PlyData.read(prepared/'sparse/0/points3D.ply')
    vertices=ply['vertex'].data
    assert len(vertices)==31205
    assert all(np.isfinite(vertices[k]).all() for k in ['x','y','z'])
    # Copy eval prerequisites into the layout C24's evaluator expects. Never
    # put them under the training source path.
    gt=ROOT/'data/eval_gt/dtu_eval_scan24'
    mapping={
      ROOT/'data/eval_gt/Points/Points/stl/stl024_total.ply':gt/'Points/stl/stl024_total.ply'}
    samples=ROOT/'data/eval_gt/SampleSet/SampleSet/MVS Data'
    for path in (samples/'Calibration/cal18').glob('pos_*.txt'):
        mapping[path]=gt/'Calibration/cal18'/path.name
    for name in ['ObsMask24_10.mat','Plane24.mat']:
        mapping[samples/'ObsMask'/name]=gt/'ObsMask'/name
    for src,dst in mapping.items():
        dst.parent.mkdir(parents=True,exist_ok=True)
        if not dst.exists():shutil.copy2(src,dst)
        assert sha256(src)==sha256(dst)
    calibrations=sorted((gt/'Calibration/cal18').glob('pos_*.txt'));assert len(calibrations)==64
    for p in calibrations:
        a=np.loadtxt(p);assert a.shape==(3,4) and np.isfinite(a).all()
    obs=loadmat(gt/'ObsMask/ObsMask24_10.mat');plane=loadmat(gt/'ObsMask/Plane24.mat')
    assert all(k in obs for k in ['ObsMask','BB','Res']) and 'P' in plane
    schemas={'obs':{k:{'shape':list(v.shape),'dtype':str(v.dtype)} for k,v in obs.items() if not k.startswith('__')},
             'plane':{k:{'shape':list(v.shape),'dtype':str(v.dtype)} for k,v in plane.items() if not k.startswith('__')}}
    gt_ply=PlyData.read(gt/'Points/stl/stl024_total.ply')
    input_hashes={str(p):sha256(p) for p in sorted(prepared.rglob('*')) if p.is_file()}
    gt_hashes={str(p):sha256(p) for p in sorted(gt.rglob('*')) if p.is_file()}
    for p in sorted((raw/'scan24').rglob('*')):
        if p.is_file():assert sha256(p)==input_hashes[str(prepared/p.relative_to(raw/'scan24'))]
    report={'passed':True,'datasets':scenes,'pilot':{'scene':'scan24','raw':str(raw/'scan24'),
            'prepared':str(prepared),'native_image':[1554,1162],'half_image':[777,581],
            'images':49,'train_views':49,'test_views':0,'split':'C24 README no --eval; all views for geometry',
            'camera_model':camera.model,'intrinsics':camera.params.tolist(),'colmap_points':len(vertices),
            'initialization':'fresh Gaussian parameters from provided COLMAP sparse/0/points3D.ply',
            'appearance':True,'masks':masks,'gt_depth_supervision':False},
            'evaluation':{'path':str(gt),'calibrations':64,'gt_vertices':len(gt_ply['vertex'].data),
                          'schemas':schemas,'role':'evaluation only, including masks in mesh extraction'},
            'training_file_hashes':input_hashes,'eval_file_hashes':gt_hashes,
            'archive_provenance':{name:json.loads((ROOT/'stage2/state'/f'{name}_archive.json').read_text())
                                  for name in ['dtu','Points','SampleSet']}}
    atomic_json(ROOT/'stage2/state/DATA_STATUS.json',report)
    for tree in [raw,ROOT/'data/eval_gt/Points',ROOT/'data/eval_gt/SampleSet',gt]:
        for p in tree.rglob('*'):
            if p.is_file():p.chmod(0o444)
            elif p.is_dir():p.chmod(0o555)
        tree.chmod(0o555)
    print(json.dumps({'passed':True,'scenes':len(scenes),'images':49,'half_image':[777,581],
                      'colmap_points':len(vertices),'gt_vertices':len(gt_ply['vertex'].data)},indent=2))


if __name__=='__main__':main()
