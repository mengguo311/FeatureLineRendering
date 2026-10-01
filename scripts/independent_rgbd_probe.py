#!/usr/bin/env python3
"""Role-isolated independent real RGB-D probe. Run only named stages."""
import argparse, hashlib, json, os, sys, time, shutil, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from src.independent_rgbd.core import *
A=ROOT/'artifacts/independent_rgbd_asset_probe'; O=ROOT/'out/independent_rgbd_asset_probe'

def write_json(path,obj):
 path.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n')
def inputs():
 p=A/'INPUTS.json'
 if sha256(p)!=(A/'INPUTS.json.sha256').read_text().strip(): raise ValueError('inputs seal')
 if sha256(A/'PROTOCOL.md')!=(A/'PROTOCOL.sha256').read_text().split()[0]: raise ValueError('protocol seal')
 return json.loads(p.read_text())
def resources():
 disk=shutil.disk_usage(O).free; total=sum(p.stat().st_size for base in [O,A] for p in base.rglob('*') if p.is_file())
 if disk<12*2**30 or total>=8*2**30: raise RuntimeError('disk budget STOP')
 return dict(free_disk_bytes=disk,new_output_bytes=total)
def confine(cfg,role,extra_ro=[],extra_rw=[]):
 reader=RawReader(cfg,role,A/'RAW_ACCESS.jsonl')
 allowed=[str(Path(cfg['raw_root'])/p) for p in reader.allowed]
 ro=[sys.prefix,'/usr','/lib','/lib64','/etc','/proc','/sys',str(ROOT/'src/independent_rgbd'),str(Path(__file__)),str(A/'INPUTS.json'),str(A/'PROTOCOL.md'),str(A/'INPUTS.json.sha256'),str(A/'PROTOCOL.sha256'),*allowed,*extra_ro]
 restrict_filesystem([p for p in ro if Path(p).exists()],[str(O),str(A),'/dev',*extra_rw])
 # Real native opens, no reading of contents when forbidden.
 denied=[]
 for f in [next(f for f in cfg['frames'] if f['split']=='F'),next(f for f in cfg['frames'] if f['split']=='C')]:
  for key in ['rgb','depth']:
   if f[key] in reader.allowed: continue
   p=Path(cfg['raw_root'])/f[key]
   try: fd=os.open(p,os.O_RDONLY)
   except PermissionError: denied.append(str(p))
   else: os.close(fd); raise RuntimeError('RAW boundary leaked')
 write_json(A/f'BOUNDARY_{role}.json',dict(role=role,denied_native_opens=denied,allowed_raw_files=len(allowed),policy='Landlock allowlist, native opens covered'))
 return reader

def init_stage():
 import cv2
 from PIL import Image
 from scipy.spatial.transform import Rotation
 cfg=inputs(); resources(); reader=confine(cfg,'train')
 frames=[f for f in cfg['frames'] if f['split']=='F']; K=np.array(cfg['K']); data=O/'training_input'; (data/'images').mkdir(parents=True,exist_ok=False); sparse=data/'sparse/0'; sparse.mkdir(parents=True)
 sift=cv2.SIFT_create(nfeatures=6000); feats=[]; colors=[]
 for f in frames:
  rgb=reader.read(f['rgb']); Image.fromarray(rgb).save(data/'images'/f"{f['id']}.png")
  kp,ds=sift.detectAndCompute(cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY),None); feats.append((np.array([k.pt for k in kp]),ds)); colors.append(rgb)
 points=[]; rgbs=[]; counts=[]; bf=cv2.BFMatcher()
 for i in range(len(frames)-1):
  a,da=feats[i]; b,db=feats[i+1]; matches=[m for m,n in bf.knnMatch(da,db,k=2) if m.distance<.75*n.distance]
  if not matches: continue
  u=np.array([a[m.queryIdx] for m in matches]); v=np.array([b[m.trainIdx] for m in matches]); ca=np.array(frames[i]['c2w']); cb=np.array(frames[i+1]['c2w'])
  pa=K@np.linalg.inv(ca)[:3]; pb=K@np.linalg.inv(cb)[:3]; x=cv2.triangulatePoints(pa,pb,u.T,v.T); p=(x[:3]/x[3]).T
  ua,za=project(p,K,ca); ub,zb=project(p,K,cb)
  ra=p-ca[:3,3]; rb=p-cb[:3,3]; cos=(ra*rb).sum(1)/(np.linalg.norm(ra,axis=1)*np.linalg.norm(rb,axis=1)); angle=np.degrees(np.arccos(np.clip(cos,-1,1)))
  ok=(za>.25)&(za<5)&(zb>.25)&(zb<5)&(np.linalg.norm(ua-u,axis=1)<=2)&(np.linalg.norm(ub-v,axis=1)<=2)&(angle>=1)&np.isfinite(p).all(1)
  points.append(p[ok]); ij=np.rint(u[ok]).astype(int); rgbs.append(colors[i][ij[:,1],ij[:,0]]); counts.append(dict(pair=[frames[i]['id'],frames[i+1]['id']],matches=len(matches),survived=int(ok.sum())))
 p=np.concatenate(points); rgb=np.concatenate(rgbs); _,idx=np.unique(np.rint(p/.01).astype(int),axis=0,return_index=True); idx=np.sort(idx)[:60000]; p=p[idx]; rgb=rgb[idx]
 write_json(A/'RGB_INITIALIZATION.json',dict(points=len(p),pairs=counts,source='F RGB SIFT plus independent F mocap poses; no depth',resources=resources()))
 if len(p)<1000: raise RuntimeError('ENGINEERING BLOCKED: <1000 RGB triangulation points')
 with (sparse/'cameras.txt').open('w') as f: f.write('1 PINHOLE 640 480 525 525 319.5 239.5\n')
 with (sparse/'images.txt').open('w') as f:
  for i,fr in enumerate(frames):
   w=np.linalg.inv(np.array(fr['c2w'])); q=Rotation.from_matrix(w[:3,:3]).as_quat(); vals=[q[3],*q[:3],*w[:3,3]]
   f.write(f"{i+1} "+' '.join(map(str,vals))+f" 1 {fr['id']}.png\n\n")
 with (sparse/'points3D.txt').open('w') as f:
  for i,(point,color) in enumerate(zip(p,rgb)): f.write(f'{i+1} '+ ' '.join(map(str,[*point,*color,0.]))+'\n')
 np.savez(O/'rgb_init.npz',points=p,rgb=rgb)
 print('RGB-only initialization',len(p),flush=True)

def stage_vendor():
 cfg=inputs(); resources()
 src=Path('/home/u00134/3dgs_line/tier1/out/multiscene_foundation/vendor/gaussian-splatting'); target=O/'vendor/gaussian-splatting'
 # Only code and licence, explicitly no upstream datasets/checkpoints/assets.
 names=['train.py','LICENSE.md','arguments','scene','utils','gaussian_renderer']
 manifest=[]
 for name in names:
  origin=src/name
  files=[origin] if origin.is_file() else [p for p in origin.rglob('*.py') if '__pycache__' not in p.parts]
  for p in files:
   rel=p.relative_to(src); dest=target/rel; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(p,dest); manifest.append(dict(path=str(rel),origin=str(p),sha256=sha256(dest)))
 for name,origin in [('diff_gaussian_rasterization',Path('/home/u00134/3dgs_line/tier1/out/vrss/vendor/official_site/diff_gaussian_rasterization')),('simple_knn',Path('/home/u00134/3dgs_line/tier1/out/multiscene_foundation/vendor/training_site/simple_knn'))]:
  for p in origin.iterdir():
   if p.suffix in ['.so','.py']:
    dest=O/'vendor/site'/name/p.name; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(p,dest); manifest.append(dict(path=str(dest.relative_to(O)),origin=str(p),sha256=sha256(dest)))
 write_json(A/'TRAINER_SOURCE.json',dict(files=manifest,changes='existing official trainer source includes seed plumbing; stock RGB renderer returning two arrays; no geometric losses',upstream_commit='472689c0dc70417448fb451bf529ae532d32c095'))

def train_stage():
 cfg=inputs(); res=resources()
 gpu=subprocess.check_output(['nvidia-smi','--id=0','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True).strip()
 used,util=map(int,gpu.split(','))
 if used>512 or util>5: raise RuntimeError('GPU occupied STOP')
 # Durable exclusive launch claim; never rerun even after a failed training process.
 claim=A/'TRAINING_LAUNCH.json'
 with claim.open('x') as f: json.dump(dict(gpu=0,occupancy=gpu,resources=res,iterations=7000,seed=0),f)
 import torch
 torch.cuda.init()
 source=O/'vendor/gaussian-splatting'; site=O/'vendor/site'; data=O/'training_input'; model=O/'model'
 confine(cfg,'train',extra_ro=[str(source),str(site)])
 # RAW F RGB allowed by role, but training has no references to it; all data is RGB-only staged.
 sys.path.insert(0,str(site)); sys.path.insert(0,str(source))
 sys.argv=[str(source/'train.py'),'-s',str(data),'-m',str(model),'-r','2','--iterations','7000','--densify_until_iter','3500','--seed','0','--ip','127.0.0.1','--port','26871','--test_iterations','7000','--save_iterations','7000']
 import runpy
 runpy.run_path(str(source/'train.py'),run_name='__main__')
 model_file=model/'point_cloud/iteration_7000/point_cloud.ply'
 write_json(A/'MODEL_SEAL.json',dict(path=str(model_file),sha256=sha256(model_file),bytes=model_file.stat().st_size,iterations=7000,source='F RGB-only vanilla 3DGS; no Kinect depth',resources=resources()))

def calibrate_stage():
 import torch,cv2
 from src.independent_rgbd.native import StockRenderer
 cfg=inputs(); seal=json.loads((A/'MODEL_SEAL.json').read_text())
 if sha256(seal['path'])!=seal['sha256']:raise ValueError('model seal')
 gpu=subprocess.check_output(['nvidia-smi','--id=0','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True).strip()
 if int(gpu.split(',')[0])>512 or int(gpu.split(',')[1])>5:raise RuntimeError('GPU occupied STOP')
 torch.cuda.init();confine(cfg,'train')
 renderer=StockRenderer(seal['path'],O/'vendor/site');K=np.array(cfg['K']);K[0:2]*=.5;K[0,2]=159.5;K[1,2]=119.5
 f=next(x for x in cfg['frames'] if x['split']=='F');rgb,result=renderer.render(K,np.array(f['c2w']),(240,320),True)
 target=cv2.resize(cv2.imread(str(O/'training_input/images'/f"{f['id']}.png"))[:,:,::-1],(320,240),interpolation=cv2.INTER_AREA)
 cv2.imwrite(str(A/'F_GS_calibration.png'),np.concatenate([target,(np.clip(rgb,0,1)*255).astype('uint8')],axis=1)[:,:,::-1])
 result.update(model_sha256=seal['sha256'],frame=f['id'],source='stock GS RGB, F calibration; no sensor depth',gaussians=len(renderer.mu))
 write_json(A/'MODEL_CALIBRATION.json',result)
 if not result['passed']:raise RuntimeError('ENGINEERING BLOCKED: stock renderer calibration')
 print(json.dumps(result),flush=True)

def build_stage():
 import cv2
 from src.independent_rgbd.geometry import valid_depth,depth_edges,fused_cloud,extract_curves
 cfg=inputs();seal=json.loads((A/'MODEL_SEAL.json').read_text())
 if sha256(seal['path'])!=seal['sha256'] or not json.loads((A/'MODEL_CALIBRATION.json').read_text())['passed']:raise ValueError('model gate')
 posefile=A/'DEPTH_TIME_POSES.json'
 if sha256(posefile)!=(A/'DEPTH_TIME_POSES.sha256').read_text().strip():raise ValueError('depth pose seal')
 posemap=json.loads(posefile.read_text())['poses'];reader=confine(cfg,'build')
 frames=[f for f in cfg['frames'] if f['split']=='F'];K=np.array(cfg['K']);poses=[np.array(posemap[f['id']]) for f in frames];depths=[];audit=[]
 for f,c in zip(frames,poses):
  raw=reader.read(f['depth'])
  if raw.shape!=(480,640) or raw.dtype not in [np.dtype('uint16'),np.dtype('int32')]:raise ValueError('sensor format')
  d=depth_metres(raw);depths.append(d);v=valid_depth(d);rc=np.array(f['c2w']);delta=np.linalg.inv(rc)@c
  audit.append(dict(frame=f['id'],zero_fraction=float((d==0).mean()),operational_valid_fraction=float(v.mean()),nonzero_depth_quantiles=np.quantile(d[d>0],[0,.1,.5,.9,1]).tolist(),association_dt=f['association_dt'],depth_rgb_translation_m=float(np.linalg.norm(delta[:3,3])),depth_rgb_rotation_deg=float(np.degrees(np.arccos(np.clip((np.trace(delta[:3,:3])-1)/2,-1,1))))))
 write_json(A/'F_SENSOR_AUDIT.json',dict(frames=audit,operational_domain=[.3,4],invalid_rule='zero/out-of-range and 2px invalid/border neighbourhood',C_depth_reads=0))
 d0,d1=depths[:2];yy,xx=np.mgrid[0:480:4,0:640:4];ok=valid_depth(d0)[yy,xx];uv0=np.c_[xx[ok],yy[ok]];p=unproject(uv0,d0[yy[ok],xx[ok]],K,poses[0]);uv,z=project(p,K,poses[1]);lab=visibility(uv,z,d1)
 pair=dict(frames=[f['id'] for f in frames[:2]],baseline_m=float(np.linalg.norm(poses[0][:3,3]-poses[1][:3,3])),samples=len(lab),categories={k:int((lab==k).sum()) for k in ['consistent','occluded','contradiction','unknown']})
 write_json(A/'TWO_VIEW_CHECK.json',pair)
 panels=[]
 for d in depths[:2]:
  im=cv2.applyColorMap(np.clip(d/4*255,0,255).astype('uint8'),cv2.COLORMAP_TURBO);im[d==0]=0;im[depth_edges(d)]=[255,255,255];panels.append(im)
 cv2.imwrite(str(A/'TWO_VIEW_SENSOR.png'),np.concatenate(panels,axis=1))
 cloud,summary=fused_cloud(depths,poses,K);np.savez_compressed(O/'F_fused_cloud.npz',points=cloud)
 write_json(A/'FUSION.json',summary);print('fused cloud',summary,flush=True)
 asset,metrics=extract_curves(depths,poses,K,[f['id'] for f in frames]);asset['model_sha256']=seal['sha256'];asset['inputs_sha256']=sha256(A/'INPUTS.json');asset['source']='F independent Kinect depth only; fixed world curves, no GS geometry or C depth'
 write_json(A/'ASSET.json',asset);np.savez_compressed(A/'ASSET.npz',**asset_arrays(asset));write_json(A/'CURVE_SURVIVAL.json',metrics)
 edited=edit_asset(asset,asset['curves'][0]['id'],[.02,0,0],2) if asset['curves'] else asset
 edited['edit']=dict(identity=asset['curves'][0]['id'] if asset['curves'] else None,displacement_world_m=[.02,0,0],width_multiplier=2)
 write_json(A/'EDITED_ASSET.json',edited);np.savez_compressed(A/'EDITED_ASSET.npz',**asset_arrays(edited))
 files=[A/'ASSET.json',A/'ASSET.npz',A/'EDITED_ASSET.json',A/'EDITED_ASSET.npz',O/'F_fused_cloud.npz']
 write_json(A/'ASSET_SEAL.json',dict(files=[dict(path=str(p),sha256=sha256(p),bytes=p.stat().st_size) for p in files],model_sha256=seal['sha256'],C_depth_reads=0,resources=resources()))
 print('curves',metrics['retained_curves'],'length survival',metrics['surviving_length_ratio'],flush=True)

def reproduce_stage():
 from src.independent_rgbd.geometry import fused_cloud,extract_curves
 cfg=inputs();seal=json.loads((A/'ASSET_SEAL.json').read_text())
 for entry in seal['files']:
  if sha256(entry['path'])!=entry['sha256']:raise ValueError('asset seal')
 poses=json.loads((A/'DEPTH_TIME_POSES.json').read_text())['poses'];reader=confine(cfg,'build');frames=[f for f in cfg['frames'] if f['split']=='F'];K=np.array(cfg['K']);ps=[np.array(poses[f['id']]) for f in frames];ds=[depth_metres(reader.read(f['depth'])) for f in frames]
 cloud,_=fused_cloud(ds,ps,K);asset,metrics=extract_curves(ds,ps,K,[f['id'] for f in frames]);asset['model_sha256']=seal['model_sha256'];asset['inputs_sha256']=sha256(A/'INPUTS.json');asset['source']='F independent Kinect depth only; fixed world curves, no GS geometry or C depth'
 dest=O/'reproduction';dest.mkdir(exist_ok=True);write_json(dest/'ASSET.json',asset);np.savez_compressed(dest/'ASSET.npz',**asset_arrays(asset));np.savez_compressed(dest/'F_fused_cloud.npz',points=cloud)
 original=[A/'ASSET.json',A/'ASSET.npz',O/'F_fused_cloud.npz'];rows=[dict(original=str(p),reproduced=str(dest/p.name),original_sha256=sha256(p),reproduced_sha256=sha256(dest/p.name),equal=sha256(p)==sha256(dest/p.name)) for p in original]
 write_json(A/'REPRODUCTION.json',dict(files=rows,passed=all(r['equal'] for r in rows),C_depth_reads=0))
 if not all(r['equal'] for r in rows):raise ValueError('deterministic reproduction failed')
 print('bitwise reproduction PASS',flush=True)

if __name__=='__main__':
 ap=argparse.ArgumentParser(); ap.add_argument('stage',choices=['init','vendor','train','calibrate','build','reproduce']); args=ap.parse_args()
 globals()[{'init':'init_stage','vendor':'stage_vendor','train':'train_stage','calibrate':'calibrate_stage','build':'build_stage','reproduce':'reproduce_stage'}[args.stage]]()
