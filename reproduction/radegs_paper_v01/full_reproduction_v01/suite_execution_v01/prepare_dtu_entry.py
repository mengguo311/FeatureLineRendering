"""Prepare one explicit DTU half30k entry from already downloaded author data."""
import argparse,datetime,importlib.util,json,shutil,sys
from pathlib import Path
import numpy as np
from PIL import Image
from plyfile import PlyData
from scipy.io import loadmat
ROOT=Path(__file__).resolve().parents[4];sys.path.append(str(ROOT/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,sha256,safe_extract_zip_selected
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');SUITE=H/'full_reproduction_v01/suite_execution_v01'

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--scene',required=True);args=ap.parse_args();scene=args.scene
 protocol=ROOT/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01/FULL_SUITE_PROTOCOL.json'
 assert sha256(protocol)=='f2b623124d648180ed31704f0070f50248fab945a84a92d0232fd69958784aba'
 entry=next(e for e in json.loads(protocol.read_text())['entries'] if e['id']==f'DTU_{scene}_half30k_TSDF');assert not entry['unresolved']
 assert scene.startswith('scan') and scene[4:].isdigit();number=int(scene[4:]);out=SUITE/(scene+'_data_v01');out.mkdir(exist_ok=False)
 raw=H/'data/raw/dtu_original/DTU'/scene;prepared=H/'data/prepared'/scene;gt=H/'data/eval_gt'/('dtu_eval_'+scene)
 assert raw.is_dir() and not prepared.exists() and not gt.exists(),'fresh scene only; partial state requires explicit review'
 rawfiles=[p for p in raw.rglob('*') if p.is_file()];size=sum(p.stat().st_size for p in rawfiles)
 assert shutil.disk_usage('/').free>=10*1024**3 and shutil.disk_usage(H).free-size-12*1024**3>=50*1024**3
 shutil.copytree(raw,prepared)
 for p in [prepared,*prepared.rglob('*')]:p.chmod(0o755 if p.is_dir() else 0o644)
 assert all(sha256(f)==sha256(prepared/f.relative_to(raw)) for f in rawfiles)
 spec=importlib.util.spec_from_file_location('c24_colmap',H/'sources/RaDe-GS/scene/colmap_loader.py');col=importlib.util.module_from_spec(spec);spec.loader.exec_module(col)
 cams=col.read_intrinsics_binary(prepared/'sparse/0/cameras.bin');ext=col.read_extrinsics_binary(prepared/'sparse/0/images.bin');points=col.read_points3D_binary(prepared/'sparse/0/points3D.bin')
 ims=sorted((prepared/'images').glob('*.png'));assert {p.name for p in ims}=={im.name for im in ext.values()};assert len(cams)==1
 cam=next(iter(cams.values()));assert cam.model=='PINHOLE' and (cam.width,cam.height)==(1554,1162)
 inventory=[]
 for p in ims:
  with Image.open(p) as im:
   im.load();assert im.mode=='RGBA' and im.size==(1554,1162);mask=np.asarray(im.getchannel('A'));assert mask.max()==255
   inventory.append({'name':p.name,'dimensions':list(im.size),'mode':im.mode,'alpha_range':[int(mask.min()),int(mask.max())],'sha256':sha256(p)})
 ply=PlyData.read(prepared/'sparse/0/points3D.ply')['vertex'].data;assert 'opacity' not in ply.dtype.names and all(k in ply.dtype.names for k in ['x','y','z','red','green','blue']);assert all(np.isfinite(ply[k]).all() for k in ['x','y','z']) and len(ply)==len(points[0])
 selected={'Points':[f'Points/stl/stl{number:03d}_total.ply'],'SampleSet':[f'SampleSet/MVS Data/ObsMask/ObsMask{number}_10.mat',f'SampleSet/MVS Data/ObsMask/Plane{number}.mat']};archives={}
 for name,members in selected.items():
  archive=H/'downloads'/(name+'.zip');source=json.loads((H/'stage2/state'/(name+'_archive.json')).read_text());assert sha256(archive)==source['sha256']
  dst=out/'selected_GT'/name;receipt=safe_extract_zip_selected(archive,dst,lambda n:n in members);files={str(p):sha256(p) for p in dst.rglob('*') if p.is_file()};assert len(files)==len(members)
  archives[name]={'archive':str(archive),'provenance':source,'extraction':receipt,'files':files};print(name,'verified and safely extracted',flush=True)
 mapping={out/'selected_GT/Points'/selected['Points'][0]:gt/'Points/stl'/f'stl{number:03d}_total.ply'}
 for src in (H/'data/eval_gt/SampleSet/SampleSet/MVS Data/Calibration/cal18').glob('pos_*.txt'):mapping[src]=gt/'Calibration/cal18'/src.name
 for name in selected['SampleSet']:mapping[out/'selected_GT/SampleSet'/name]=gt/'ObsMask'/Path(name).name
 for src,dst in mapping.items():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha256(src)==sha256(dst)
 assert len(list((gt/'Calibration/cal18').glob('*.txt')))==64
 obs=loadmat(gt/'ObsMask'/f'ObsMask{number}_10.mat');plane=loadmat(gt/'ObsMask'/f'Plane{number}.mat');assert {'ObsMask','BB','Res'}<=obs.keys() and 'P' in plane
 gtp=PlyData.read(gt/'Points/stl'/f'stl{number:03d}_total.ply')['vertex'].data
 result={'scene':scene,'entry_id':entry['id'],'raw':str(raw),'prepared':str(prepared),'evaluation_GT':str(gt),'raw_bytes':size,'images':len(ims),'camera_views':len(ext),'initial_COLMAP_points':len(ply),'initial_PLY_schema':list(ply.dtype.names),'native_resolution':[1554,1162],'half_resolution':[777,581],'image_inventory':inventory,'training_hashes':{str(p):sha256(p) for p in prepared.rglob('*') if p.is_file()},'evaluation_hashes':{str(p):sha256(p) for p in gt.rglob('*') if p.is_file()},'GT_points':len(gtp),'GT_ObsMask_shape':list(obs['ObsMask'].shape),'GT_BB':obs['BB'].tolist(),'GT_Res':obs['Res'].tolist(),'GT_Plane':plane['P'].tolist(),'GT_role':'evaluation only','raw_copy_hashes_equal':True,'training_archive_provenance':json.loads((H/'stage2/state/dtu_archive.json').read_text()),'GT_archives_verified':archives,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scientificdone':False}
 atomic_json(out/'DATA.json',result);print(json.dumps({k:result[k] for k in ['scene','images','initial_COLMAP_points','GT_points','raw_bytes']}))
if __name__=='__main__':main()
