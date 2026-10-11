"""Render fixed expanded-view assets with the unchanged native EWA implementation."""
import os
os.environ['OMP_NUM_THREADS']='2';os.environ['OPENBLAS_NUM_THREADS']='2';os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['PYTHONDONTWRITEBYTECODE']='1'
import ctypes,json,time,fcntl,subprocess,re,resource
from pathlib import Path
import numpy as np
from PIL import Image
import core,demo,multiview,pipeline
T=core.TASK
ARMS=('balanced','density_compensated');VIEWS=('0000','0024','0048','0012','0036');TIERS=(3,12,24,47)
FFMPEG=T.parent/'spatial_rgb_gaussian_demo_v01/dependencies/unpacked/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
_lib=None

def render_pair(asset,c,nviews,depth=None,alpha=None):
 global _lib
 if _lib is None:
  _lib=ctypes.CDLL(str(T/'build/libewa.so'));_lib.ewa.argtypes=[ctypes.c_int]*3+[ctypes.c_void_p]*7+[ctypes.c_double,ctypes.c_void_p];_lib.ewa.restype=None
 uv,z,S=core.project_cov(np.asarray(asset['means']),np.asarray(asset['covariance']),c,.12)
 n=len(z);h=c['height'];w=c['width'];out={}
 vals=[uv,z,S,asset['opacity'],asset.get('colors',np.zeros((n,3))),depth,alpha]
 arr=[np.ascontiguousarray(v,dtype=np.float64) if v is not None else None for v in vals]
 for arm in ARMS:
  if arm=='density_compensated':arr[3]=np.ascontiguousarray(multiview.density_opacity(asset['opacity'],nviews),dtype=np.float64)
  dst=np.empty((h,w,3),np.float64)
  _lib.ewa(n,h,w,*[a.ctypes.data if a is not None else None for a in arr],float(np.sqrt(c['fx']*c['fy'])),dst.ctypes.data)
  out[arm]=dst.astype(np.float32)
 return out

def freeze():
 files=[Path(__file__),Path(__file__).with_name('test_render_expanded.py'),T/'build/libewa.so',T/'RECIPE_FREEZE.json',T/'VIEW_SELECTION.json']
 for scene in demo.SCENES:
  files.append(T/'models'/scene/'ARC_CAMERAS.json')
  for n in TIERS:
   d=T/'models'/scene/f'views_{n:02d}';assert pipeline.checkseal(d);files.extend([d/'SEAL.json',d/'balanced.npz',d/'density_compensated.npz'])
 rows=[{'path':str(p.resolve()),'sha256':demo.sha(p),'bytes':p.stat().st_size} for p in files]
 f=T/'RENDER_FREEZE.json'
 if f.exists():
  a=json.loads(f.read_text());assert a['files']==rows
 else:demo.writejson(f,{'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'files':rows,'heldout_content_not_read_before_this_freeze':True,'all_primary_assets':12,'exact_cameras':VIEWS,'novel_original_scene_occlusion':False,'threads':2})

def verified(d):
 if not pipeline.checkseal(d):return False
 a=json.loads((d/'SEAL.json').read_text());assert a['extra']['render_freeze_sha256']==demo.sha(T/'RENDER_FREEZE.json');return True

def finish(d,extra):
 pipeline.seal(d,dict(extra,render_freeze_sha256=demo.sha(T/'RENDER_FREEZE.json')))

def render_tier(scene,n,cs,arc):
 d=T/'renders'/scene/f'views_{n:02d}'
 if verified(d):return
 pipeline.guard();started=time.monotonic();model=T/'models'/scene/f'views_{n:02d}'
 a=dict(np.load(model/'balanced.npz'));b=dict(np.load(model/'density_compensated.npz'))
 for k in a:
  np.testing.assert_array_equal(b[k],multiview.density_opacity(a[k],n) if k=='opacity' else a[k])
 del b
 stats={};pipeline.update('RENDER_TIER',current_scene=scene,current_tier=n)
 for v in VIEWS:
  im=demo.read(scene,v);rs=render_pair(a,cs[v],n,im['z'],im['alpha']);stats[v]={}
  for arm,r in rs.items():
   demo.saveimage(d/f'{v}_{arm}_ink.png',r);demo.saveimage(d/f'{v}_{arm}_overlay.png',im['rgb']*r)
   stats[v][arm]={'darkness_gt_02_pixels':int(((1-r[...,0])>.2).sum()),'mean_darkness':float((1-r[...,0]).mean()),'finite':bool(np.isfinite(r).all())}
  if v=='0024':
   reload=dict(np.load(model/'balanced.npz'));again=core.render(reload,cs[v],im['z'],im['alpha']);np.testing.assert_array_equal(again,rs['balanced']);del reload,again
 for i,c in enumerate(arc):
  rs=render_pair(a,c,n)
  for arm,r in rs.items():demo.saveimage(d/f'arc_{i:03d}_{arm}.png',r)
  if i%8==0:pipeline.update('RENDER_ARC',current_scene=scene,current_tier=n,arc_frame=i+1,arc_frames_expected=len(arc))
 summary={'scene':scene,'tier':n,'gaussians':len(a['means']),'same_camera_frames_per_arm':len(VIEWS),'novel_camera_frames_per_arm':len(arc),'asset_reload_render_bit_exact':True,'density_asset_verified':True,'evaluation_views':stats,'novel_original_scene_occlusion':False,'seconds':time.monotonic()-started,'maxrss_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 demo.writejson(d/'SUMMARY.json',summary);finish(d,summary);del a
 pipeline.update('RENDER_UNIT_SEALED',current_scene=scene,current_tier=n,render_units_completed=len(list((T/'renders').glob('*/views_*/SEAL.json'))))

def image_array(p):return np.asarray(Image.open(p).convert('RGB'),dtype=np.float32)/255.

def verify_video(path,log):
 cmd=[str(FFMPEG),'-threads','2','-i',str(path),'-threads','2','-f','null','-']
 p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);log.write_text(p.stdout);assert p.returncode==0
 nums=re.findall(r'frame=\s*(\d+)',p.stdout);assert nums and int(nums[-1])==33,(str(path),nums);assert 'yuv420p' in p.stdout and 'h264' in p.stdout
 atoms=[]
 with path.open('rb') as f:
  while True:
   b=f.read(8)
   if len(b)<8:break
   size=int.from_bytes(b[:4],'big');atoms.append(b[4:].decode('ascii',errors='replace'))
   if size==1:size=int.from_bytes(f.read(8),'big');f.seek(size-16,1)
   elif size>=8:f.seek(size-8,1)
   else:break
 assert atoms.index('moov')<atoms.index('mdat')
 return {'decoded_frames':int(nums[-1]),'codec':'h264','pixel_format':'yuv420p','faststart_atom_order':atoms,'decode_command':cmd}

def assemble_panels(scene):
 d=T/'previews'/scene
 if verified(d):return
 pipeline.guard();started=time.monotonic()
 for v in VIEWS:
  im=demo.read(scene,v);f=demo.detect(im);demo.saveimage(d/f'{v}_original_rendered_rgb.png',im['rgb']);demo.saveimage(d/f'{v}_original_spatial_rgb.png',demo.boundary.ink(f['union'],gain=1.,sigma=.5))
  role='BUILD' if v in core.BUILD else 'CONSTRUCTION HOLDOUT (not blind GS test)'
  for arm in ARMS:
   for mode in ['ink','overlay']:
    items=[(str(n)+' build views / '+('BALANCED' if arm=='balanced' else 'density compensation'),image_array(T/'renders'/scene/f'views_{n:02d}'/f'{v}_{arm}_{mode}.png')) for n in TIERS]
    demo.panel(d/f'{v}_{arm}_{mode}_comparison.jpg',items,scene+' | camera '+v+' | '+role+' | '+mode+' | source-depth visibility',cols=4)
 finish(d,{'scene':scene,'same_camera_comparisons':20,'reference_images':10,'seconds':time.monotonic()-started})

def make_video(scene,arm):
 d=T/'videos'/scene/arm
 if verified(d):return
 pipeline.guard();started=time.monotonic();cmd=None
 # Composite frames are saved in this sealed unit, no rerunning of line detector.
 for i in range(33):
  items=[(str(n)+' views / '+('BALANCED' if arm=='balanced' else 'density compensated'),image_array(T/'renders'/scene/f'views_{n:02d}'/f'arc_{i:03d}_{arm}.png')) for n in TIERS]
  demo.panel(d/f'{i:03d}.png',items,scene+f' | fixed 3D Gaussians | {i+1}/33 | ink ONLY / NO original-scene occlusion | '+arm,cols=4)
 video=d/'arc.mp4';cmd=[str(FFMPEG),'-y','-threads','2','-filter_threads','2','-framerate','12','-i',str(d/'%03d.png'),'-vf','pad=ceil(iw/2)*2:ceil(ih/2)*2','-c:v','libx264','-threads','2','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(video)]
 with (d/'ENCODE_LOG.txt').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 info=verify_video(video,d/'DECODE_LOG.txt');info.update(encode_command=cmd,frames_generated=33,scene=scene,arm=arm,seconds=time.monotonic()-started,source_arc_sha256=demo.sha(T/'models'/scene/'ARC_CAMERAS.json'))
 frames=[Image.open(d/f'{i:03d}.png').convert('RGB') for i in [0,16,32]];w,h=frames[0].size;contact=Image.new('RGB',(w,h*3),'white')
 for i,f in enumerate(frames):contact.paste(f,(0,h*i))
 contact.save(d/'FIRST_MIDDLE_LAST.jpg',quality=92);demo.writejson(d/'VIDEO_VERIFICATION.json',info);finish(d,info);pipeline.update('VIDEO_SEALED',current_scene=scene,current_arm=arm,videos_verified=len(list((T/'videos').glob('*/*/SEAL.json'))))

def main():
 lock=open(T/'pipeline.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);freeze();pipeline.update('ASSETS_FROZEN_BEFORE_EVALUATION',models_completed=12,render_units_completed=len(list((T/'renders').glob('*/views_*/SEAL.json'))))
 try:
  for scene in demo.SCENES:
   cs=demo.cameras(scene);arc=json.loads((T/'models'/scene/'ARC_CAMERAS.json').read_text())['cameras'];assert len(arc)==33
   for n in TIERS:render_tier(scene,n,cs,arc)
   assemble_panels(scene)
   for arm in ARMS:make_video(scene,arm)
  pipeline.update('AWAITING_ACTUAL_VISUAL_REVIEW',models_completed=12,render_units_completed=12,videos_verified=6,same_camera_renders_per_arm=60,novel_renders_per_arm=396,source_detector_in_animation=False)
 except Exception:
  import traceback
  pipeline.update('RENDER_ENGINEERING_FAILURE',failure=traceback.format_exc());raise
if __name__=='__main__':main()
