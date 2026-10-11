"""Private prepared copy and exact file/schema inventory; no CUDA or downloads."""
from pathlib import Path
import sys,json,shutil,importlib.util,datetime
import numpy as np
from PIL import Image
from plyfile import PlyData
from scipy.io import loadmat
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,sha256
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');O=H/'full_reproduction_v01/suite_execution_v01';raw=H/'data/raw/dtu_original/DTU/scan37';prepared=H/'data/prepared/scan37';gt=H/'data/eval_gt/dtu_eval_scan37'
assert shutil.disk_usage('/').free>10*1024**3 and shutil.disk_usage(H).free-12*1024**3>50*1024**3
# Resume only the verified partial preparation; never overwrite existing data.
size=sum(x.stat().st_size for x in raw.rglob('*') if x.is_file())
if not prepared.exists():shutil.copytree(raw,prepared)
else:
 assert {str(f.relative_to(raw)) for f in raw.rglob('*') if f.is_file()}=={str(f.relative_to(prepared)) for f in prepared.rglob('*') if f.is_file()}
 assert all(sha256(f)==sha256(prepared/f.relative_to(raw)) for f in raw.rglob('*') if f.is_file()),'partial copy mismatch'
for p in prepared.rglob('*'):p.chmod(0o755 if p.is_dir() else 0o644)
prepared.chmod(0o755)
sp=importlib.util.spec_from_file_location('colmap',H/'sources/RaDe-GS/scene/colmap_loader.py');col=importlib.util.module_from_spec(sp);sp.loader.exec_module(col)
cams=col.read_intrinsics_binary(prepared/'sparse/0/cameras.bin');ext=col.read_extrinsics_binary(prepared/'sparse/0/images.bin');points=col.read_points3D_binary(prepared/'sparse/0/points3D.bin')
ims=sorted((prepared/'images').glob('*.png'));assert {x.name for x in ims}=={x.name for x in ext.values()};assert len(cams)==1;cam=next(iter(cams.values()));assert cam.model=='PINHOLE' and (cam.width,cam.height)==(1554,1162)
image_rows=[]
for f in ims:
 with Image.open(f) as im:
  im.load();assert im.mode=='RGBA' and im.size==(1554,1162);alpha=np.asarray(im.getchannel('A'));image_rows.append({'name':f.name,'size':list(im.size),'alpha_min':int(alpha.min()),'alpha_max':int(alpha.max()),'sha256':sha256(f)})
p=prepared/'sparse/0/points3D.ply';assert p.exists(),'must inspect missing standard COLMAP PLY before making it';ply=PlyData.read(p)['vertex'].data;assert all(k in ply.dtype.names for k in ['x','y','z','red','green','blue']) and 'opacity' not in ply.dtype.names;assert all(np.isfinite(ply[k]).all() for k in ['x','y','z']);assert len(ply)==len(points[0])
samples=H/'data/eval_gt/SampleSet/SampleSet/MVS Data';mapping={O/'gt_extract_scan37/Points/Points/stl/stl037_total.ply':gt/'Points/stl/stl037_total.ply'}
for src in (samples/'Calibration/cal18').glob('pos_*.txt'):mapping[src]=gt/'Calibration/cal18'/src.name
for name in ['ObsMask37_10.mat','Plane37.mat']:mapping[O/'gt_extract_scan37/SampleSet/SampleSet/MVS Data/ObsMask'/name]=gt/'ObsMask'/name
for src,dst in mapping.items():
 dst.parent.mkdir(parents=True,exist_ok=True)
 if not dst.exists():shutil.copy2(src,dst)
 assert sha256(src)==sha256(dst)
assert len(list((gt/'Calibration/cal18').glob('*.txt')))==64
obs=loadmat(gt/'ObsMask/ObsMask37_10.mat');plane=loadmat(gt/'ObsMask/Plane37.mat');assert {'ObsMask','BB','Res'}<=obs.keys() and 'P' in plane;gtp=PlyData.read(gt/'Points/stl/stl037_total.ply')['vertex'].data
hashes={str(f):sha256(f) for f in prepared.rglob('*') if f.is_file()};assert all(sha256(f)==hashes[str(prepared/f.relative_to(raw))] for f in raw.rglob('*') if f.is_file())
r={'scene':'scan37','raw':str(raw),'prepared':str(prepared),'evaluation_GT':str(gt),'raw_bytes':size,'images':len(ims),'camera_views':len(ext),'initial_COLMAP_points':len(ply),'initial_PLY_schema':list(ply.dtype.names),'native_resolution':[1554,1162],'half_resolution':[777,581],'image_inventory':image_rows,'training_hashes':hashes,'evaluation_hashes':{str(f):sha256(f) for f in gt.rglob('*') if f.is_file()},'GT_points':len(gtp),'selected_GT_archive_receipt':sha256(O/'SCAN37_GT_ARCHIVE_RECEIPT.json'),'GT_ObsMask_shape':list(obs['ObsMask'].shape),'GT_BB':obs['BB'].tolist(),'GT_Res':obs['Res'].tolist(),'GT_Plane':plane['P'].tolist(),'GT_role':'evaluation only','training_supervision':'images only, no metric GT','raw_copy_hashes_equal':True,'archive_provenance':{name:json.loads((H/'stage2/state'/f'{name}_archive.json').read_text()) for name in ['dtu','Points','SampleSet']},'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
atomic_json(O/'SCAN37_DATA.json',r);print(json.dumps({k:r[k] for k in ['scene','raw_bytes','images','initial_COLMAP_points','GT_points','raw_copy_hashes_equal']}))
