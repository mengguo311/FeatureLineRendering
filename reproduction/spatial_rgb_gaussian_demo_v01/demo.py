"""CPU-only fixed-source spatial RGB -> new Gaussian ink demonstration."""
import os
os.environ.setdefault('OMP_NUM_THREADS','2');os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import json,hashlib,time,sys,importlib.util,ctypes,subprocess,zipfile,shutil
from pathlib import Path
import numpy as np
import cv2
from scipy.ndimage import maximum_filter,minimum_filter,distance_transform_edt
from scipy.spatial.transform import Rotation
from PIL import Image,ImageDraw,ImageFont
import core
T=core.TASK;E=T/'evidence';OUT=T/'results_v1';BUILD=core.BUILD;HOLD=('0012','0036');SCENES=('scan24','scan65','scan63')
cv2.setNumThreads(2)
spec=importlib.util.spec_from_file_location('original_boundary',E/'boundary.py');boundary=importlib.util.module_from_spec(spec);spec.loader.exec_module(boundary)
FONT=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',19)
SMALL=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def writejson(p,o):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False));tmp.replace(p)
def status(phase,**kw):
 p=T/'STATUS.json';old=json.loads(p.read_text()) if p.exists() else {};old.update(phase=phase,status='IN_PROGRESS',utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),**kw);writejson(p,old)
 print(json.dumps({'phase':phase,**kw}),flush=True)
def guard():
 assert shutil.disk_usage('/').free>=1024**3;assert shutil.disk_usage(T).free>=10*1024**3
 total=sum(p.stat().st_size for p in T.rglob('*') if p.is_file());assert total<15*1024**3,total

def cameras(scene):return {r['view']:r for r in json.loads((E/(scene+'_cameras_30000.json')).read_text())}
def read(scene,view):
 a=np.load(E/(scene+'_'+view+'.npz'));return {'rgb':np.moveaxis(a['rgb'],0,-1).copy(),'z':a['median_camera_z'][0].copy(),'alpha':a['alpha'][0].copy()}
def saveimage(p,a):
 p.parent.mkdir(parents=True,exist_ok=True);Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(p)
def panel(p,items,title,cols=2):
 w,h=items[0][1].shape[1],items[0][1].shape[0];rows=(len(items)+cols-1)//cols
 canvas=Image.new('RGB',(cols*w,rows*(h+32)+65),'white');d=ImageDraw.Draw(canvas);d.text((10,9),title,font=FONT,fill='black');d.text((10,36),'True projected Gaussian covariance + front-to-back alpha; same full camera frame',font=SMALL,fill='black')
 for i,(label,a) in enumerate(items):
  x=i%cols*w;y=65+i//cols*(h+32);d.text((x+8,y+6),label,font=FONT,fill='black');canvas.paste(Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)),(x,y+32))
 canvas.save(p,quality=92)

def detect(a):
 f=boundary.analyze(a['rgb']);dark=1-boundary.ink(f['union'],gain=1.,sigma=.5)[...,0]
 assert np.isfinite(dark).all();np.testing.assert_array_equal(f['union'],np.maximum(f['structural'],f['detail']))
 return {'dark':dark,'normal2':f['normal'],'confidence':f['confidence'],'union':f['union'],'marked':dark>.2}

def fields(a,f,c):
 h,w=a['z'].shape;y,x=np.mgrid[:h,:w];uv=np.stack([x,y],-1);world=core.backproject(uv.reshape(-1,2),a['z'].ravel(),c).reshape(h,w,3)
 du=np.gradient(world,axis=1);dv=np.gradient(world,axis=0);normal=core.normalize(np.cross(du,dv));tx=-f['normal2'][...,1];ty=f['normal2'][...,0];tan=core.normalize(du*tx[...,None]+dv*ty[...,None])
 z=a['z'];span=maximum_filter(z,3)-minimum_filter(z,3);fit=core.valid_depth(z)&np.isfinite(a['alpha'])&(a['alpha']>=.5)&(span<=.02*z)&np.isfinite(tan).all(-1)&(np.linalg.norm(np.cross(du,dv),axis=-1)>1e-14)
 fit[[0,-1],:]=False;fit[:,[0,-1]]=False
 _,inds=distance_transform_edt(~f['marked'],return_indices=True)
 return {'world':world,'tangent':tan,'normal':normal,'fit':fit,'nearest':inds}

def save_ply(path,asset):
 n=len(asset['means']);props=[('x','<f4'),('y','<f4'),('z','<f4')]+[(x,'<f4') for x in ['cov_xx','cov_xy','cov_xz','cov_yy','cov_yz','cov_zz','opacity']]+[(x,'u1') for x in ['red','green','blue','view_votes']]+[('source_count','<u2'),('source_anchor','<i4')]
 a=np.zeros(n,dtype=props)
 for j,k in enumerate(['x','y','z']):a[k]=asset['means'][:,j]
 for k,i,j in [('cov_xx',0,0),('cov_xy',0,1),('cov_xz',0,2),('cov_yy',1,1),('cov_yz',1,2),('cov_zz',2,2)]:a[k]=asset['covariance'][:,i,j]
 a['opacity']=asset['opacity'];a['view_votes']=asset['view_votes'];a['source_count']=asset['source_count'];a['source_anchor']=asset['source_anchor']
 typ={'<f4':'float','u1':'uchar','<u2':'ushort','<i4':'int'}
 hdr='ply\nformat binary_little_endian 1.0\ncomment New Gaussian INK primitives; NOT original GS IDs; covariance in scene units squared\ncomment NPZ plus source_samples.npz carries complete provenance\nelement vertex '+str(n)+'\n'+''.join('property '+typ[t]+' '+k+'\n' for k,t in props)+'end_header\n'
 with open(path,'wb') as f:f.write(hdr.encode());a.tofile(f)

def construct(scene):
 guard();core.assert_build_views(BUILD);cs=cameras(scene);dst=OUT/scene;dst.mkdir(parents=True,exist_ok=True)
 aa={v:read(scene,v) for v in BUILD};ff={v:detect(aa[v]) for v in BUILD};gg={v:fields(aa[v],ff[v],cs[v]) for v in BUILD};records=[];summary={}
 for vid,v in enumerate(BUILD):
  a=aa[v];f=ff[v];g=gg[v];marked=f['marked'];valid=marked&core.valid_depth(a['z']);y,x=np.nonzero(valid);u=np.stack([x,y],-1);n=len(x);pixel=a['z'][y,x]/np.sqrt(cs[v]['fx']*cs[v]['fy'])
  records.append({'means':g['world'][y,x],'uv':u,'source_view':np.full(n,vid,np.int8),'depth':a['z'][y,x],'darkness':f['dark'][y,x],'line_confidence':f['confidence'][y,x],'alpha':a['alpha'][y,x],'pixel':pixel,'tangent':g['tangent'][y,x],'normal':g['normal'][y,x],'fit_valid':g['fit'][y,x]})
  rejected=marked&~valid
  np.savez_compressed(dst/(v+'_source_maps.npz'),darkness=f['dark'],union=f['union'],marked=marked,invalid_depth_rejected=rejected,alpha_unqualified=marked&(~np.isfinite(a['alpha'])|(a['alpha']<.5)),fit_valid=g['fit'])
  saveimage(dst/(v+'_marked.png'),marked.astype(float));saveimage(dst/(v+'_invalid_depth_rejected.png'),rejected.astype(float))
  uv2,z2=core.project(records[-1]['means'],cs[v]);err=float(abs(uv2-u).max()) if n else 0;assert err<1e-8
  summary[v]={'marked':int(marked.sum()),'raw_created':n,'invalid_depth_rejected':int(rejected.sum()),'alpha_unqualified_but_raw_kept':int((valid&(~np.isfinite(a['alpha'])|(a['alpha']<.5))).sum()),'fit_valid':int(g['fit'][y,x].sum()),'roundtrip_max_pixel_error':err,'depth_range':[float(a['z'][y,x].min()),float(a['z'][y,x].max())]}
 samples={k:np.concatenate([r[k] for r in records]) for k in records[0]};n=len(samples['means']);votes=np.zeros((n,3),np.int8)
 for vid,v in enumerate(BUILD):
  c=cs[v];a=aa[v];f=ff[v];g=gg[v];uv,z=core.project(samples['means'],c);inside=np.isfinite(uv).all(-1)&(z>0)&(uv[:,0]>=0)&(uv[:,0]<=c['width']-1)&(uv[:,1]>=0)&(uv[:,1]<=c['height']-1)
  xy=np.rint(np.nan_to_num(uv,nan=0,posinf=0,neginf=0)).astype(np.int64);x=np.clip(xy[:,0],0,c['width']-1);y=np.clip(xy[:,1],0,c['height']-1)
  ny,nx=g['nearest'][:,y,x];depth=a['z'][y,x];tol=np.maximum(.005*depth,2*depth/np.sqrt(c['fx']*c['fy']));targetpixel=a['z'][ny,nx]/np.sqrt(c['fx']*c['fy'])
  compatible=(np.linalg.norm(uv-np.stack([nx,ny],-1),axis=1)<=1.5)&g['fit'][ny,nx]&(np.linalg.norm(samples['means']-g['world'][ny,nx],axis=1)<=2.5*np.minimum(samples['pixel'],targetpixel))&(abs(np.sum(samples['tangent']*g['tangent'][ny,nx],axis=1))>=np.sqrt(.5))&(abs(z-a['z'][ny,nx])<=tol)
  votes[:,vid]=core.visibility_class(z,depth,a['alpha'][y,x],inside,compatible,tol);own=samples['source_view']==vid;votes[own,vid]=np.where(samples['fit_valid'][own],1,0)
 support=(votes==1).sum(1);counter=(votes<0).sum(1);keep=samples['fit_valid']&(support>=2)&(counter==0);ids=np.flatnonzero(keep)
 groups=core.group_samples(samples['means'][ids],samples['source_view'][ids],samples['pixel'][ids],samples['tangent'][ids],samples['darkness'][ids]);ng=len(groups)
 assign=np.full(n,-1,np.int32);means=[];covs=[];opacity=[];anchors=[];counts=[];votefused=[]
 for gid,local in enumerate(groups):
  members=ids[local];anchor=members[0];assign[members]=gid;weight=samples['darkness'][members];means.append(np.average(samples['means'][members],weights=weight,axis=0));anchors.append(anchor);counts.append(len(members));opacity.append(min(.95,float(weight.max())))
  covs.append(core.ink_covariance(samples['tangent'][anchor:anchor+1],samples['normal'][anchor:anchor+1],samples['pixel'][anchor:anchor+1],True)[0]);votefused.append(int(np.any(votes[members]==1,axis=0).sum()))
 raw={'means':samples['means'],'covariance':core.ink_covariance(samples['tangent'],samples['normal'],samples['pixel'],False),'opacity':np.minimum(.95,samples['darkness']),'view_votes':support.astype(np.uint8),'source_count':np.ones(n,np.uint16),'source_anchor':np.arange(n,dtype=np.int32)}
 fused={'means':np.array(means).reshape(-1,3),'covariance':np.array(covs).reshape(-1,3,3),'opacity':np.array(opacity),'view_votes':np.array(votefused,np.uint8),'source_count':np.array(counts,np.uint16),'source_anchor':np.array(anchors,np.int32)}
 samples.update(votes=votes,supported=keep,fused_id=assign)
 np.savez_compressed(dst/'source_samples.npz',**samples)
 for name,asset in [('raw',raw),('fused',fused)]:
  asset['colors']=np.zeros((len(asset['means']),3),np.float32);assert np.isfinite(asset['means']).all();assert (np.linalg.eigvalsh(asset['covariance'])>0).all()
  np.savez_compressed(dst/(name+'_gaussians.npz'),**asset);save_ply(dst/(name+'_gaussians.ply'),asset)
  reload=dict(np.load(dst/(name+'_gaussians.npz')));before=core.render(asset,cs['0024'],aa['0024']['z'],aa['0024']['alpha']);after=core.render(reload,cs['0024'],aa['0024']['z'],aa['0024']['alpha']);np.testing.assert_array_equal(before,after)
  saveimage(dst/(name+'_build0024_persistence.png'),after)
 summary.update(raw_gaussians=n,supported_samples=int(keep.sum()),fused_gaussians=ng,merged_samples=int(len(ids)-ng),votes_histogram={str(i):int((votes==i).sum()) for i in [-2,-1,0,1,2]},asset_reload_render_exact=True,all_covariances_spd=True)
 writejson(dst/'BUILD_SUMMARY.json',summary)
 # build preview ONLY; no heldout content read before all-scene asset freeze.
 panel(dst/'BUILD_ONLY_0024.jpg',[('Original RGB / build0024',aa['0024']['rgb']),('Original spatial RGB soft ink',boundary.ink(ff['0024']['union'])),('Raw all-pixel Gaussians',core.render(raw,cs['0024'],aa['0024']['z'],aa['0024']['alpha'])),('Conservative supported Gaussians',core.render(fused,cs['0024'],aa['0024']['z'],aa['0024']['alpha']))],scene+' | BUILD ONLY | v1 frozen recipe')
 return summary

def ffmpeg():
 d=T/'dependencies';binary=next(d.glob('unpacked/imageio_ffmpeg/binaries/ffmpeg-*'),None)
 if binary is None:
  wheel=next(d.glob('*.whl'))
  with zipfile.ZipFile(wheel) as z:z.extractall(d/'unpacked')
  binary=next(d.glob('unpacked/imageio_ffmpeg/binaries/ffmpeg-*'));binary.chmod(0o755)
 return str(binary)

def arc_cameras(raw,c):
 # All raw centers + 3 sigma included in bounding sphere, no semantic cropping.
 m=raw['means'];center=(m.min(0)+m.max(0))/2;radius=float(np.max(np.linalg.norm(m-center,axis=1)+3*np.sqrt(np.linalg.eigvalsh(raw['covariance'])[:,-1])))
 E0=np.array(c['extrinsic']);cam0=-np.linalg.solve(E0[:3,:3],E0[:3,3]);direction=core.normalize((cam0-center)[None])[0];upworld=-E0[1,:3];upworld=core.normalize(upworld[None])[0];h=581;w=777;fx=float(c['fx']);fy=float(c['fy']);half=np.arctan(min((w-40)/2/fx,(h-40)/2/fy));distance=radius/np.sin(half)*1.03
 result=[]
 for angle in np.linspace(-8,8,33):
  direction2=Rotation.from_rotvec(upworld*np.deg2rad(angle)).apply(direction);C=center+direction2*distance;forward=core.normalize((center-C)[None])[0];right=core.normalize(np.cross(forward,upworld)[None])[0];down=np.cross(forward,right);R=np.stack([right,down,forward]);extr=np.eye(4);extr[:3,:3]=R;extr[:3,3]=-R@C
  cc=dict(c,extrinsic=extr.tolist(),width=w,height=h,view='arc',arc_degrees=float(angle));result.append(cc)
 return result,{'center':center.tolist(),'bounding_radius':radius,'camera_distance':distance,'framing':'all raw centers plus 3 sigma; fixed 20px margin; no original-scene occlusion'}

def evaluate(scene):
 guard();dst=OUT/scene;cs=cameras(scene);assets={arm:dict(np.load(dst/(arm+'_gaussians.npz'))) for arm in ['raw','fused']};metrics={}
 for v in (*BUILD,*HOLD):
  a=read(scene,v);f=detect(a);role='build' if v in BUILD else 'GS training-view selection HOLDOUT';items=[('Original rendered RGB',a['rgb']),('Original spatial RGB soft ink',boundary.ink(f['union']))];over=[]
  metric={}
  for arm,asset in assets.items():
   r=core.render(asset,cs[v],a['z'],a['alpha']);saveimage(dst/(v+'_'+arm+'_ink.png'),r);saveimage(dst/(v+'_'+arm+'_overlay.png'),a['rgb']*r);items.append((arm+' fixed 3D Gaussians / depth visibility',r));over.append((arm+' on original rendered RGB',a['rgb']*r))
   d=1-r[...,0];marked=f['marked'];target_dist=distance_transform_edt(~marked);pred=d>.2;pred_dist=distance_transform_edt(~pred)
   metric[arm]={'render_pixels_darkness_gt_0_2':int(pred.sum()),'visible_2D_precision_within_2px':float(np.mean(target_dist[pred]<=2)) if pred.any() else 0,'visible_2D_recall_within_2px':float(np.mean(pred_dist[marked]<=2)) if marked.any() else 0,'metric_warning':'2D detector agreement, not 3D identity/accuracy; holdout only evaluated after fixed asset seal'}
  panel(dst/(v+'_comparison.jpg'),items,scene+' | '+v+' | '+role);panel(dst/(v+'_overlays.jpg'),over,scene+' | '+v+' | Original RGB reference overlays',cols=2);metrics[v]=metric
 # fixed assets; do NOT call detector in this loop
 arc,framing=arc_cameras(assets['raw'],cs['0024']);writejson(dst/'ARC_CAMERAS.json',{'framing':framing,'cameras':arc});frame_dir=dst/'arc_frames';frame_dir.mkdir(exist_ok=True)
 for i,c in enumerate(arc):
  frames=[core.render(assets[arm],c) for arm in ['raw','fused']]
  panel(frame_dir/(f'{i:03d}.png'),[('RAW: fixed all-pixel Gaussians',frames[0]),('SUPPORTED: fixed fused Gaussians',frames[1])],scene+' | '+f'Arc {i+1}/33 ({c["arc_degrees"]:+.1f} deg)'+' | ink only; NO original-scene occlusion',cols=2)
 # even dimensions for yuv420p; padding only, no crop
 exe=ffmpeg();video=dst/'fixed_gaussian_arc.mp4';log=dst/'VIDEO_LOG.txt'
 cmd=[exe,'-y','-framerate','12','-i',str(frame_dir/'%03d.png'),'-vf','pad=ceil(iw/2)*2:ceil(ih/2)*2','-c:v','libx264','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(video)]
 with log.open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 # full decode frame count and pixel-format independently read by ffmpeg
 decoded=dst/'DECODE_LOG.txt';proc=subprocess.run([exe,'-i',str(video),'-f','null','-'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);decoded.write_text(proc.stdout);assert proc.returncode==0
 import re
 counts=re.findall(r'frame=\s*(\d+)',proc.stdout);assert counts and int(counts[-1])==33,counts;assert 'yuv420p' in proc.stdout
 # ISO BMFF top-level atom scan: moov precedes mdat = faststart
 atoms=[]
 with video.open('rb') as f:
  while True:
   hdr=f.read(8)
   if len(hdr)<8:break
   size=int.from_bytes(hdr[:4],'big');tag=hdr[4:].decode('ascii',errors='replace');atoms.append(tag)
   if size==1:size=int.from_bytes(f.read(8),'big');f.seek(size-16,1)
   elif size>=8:f.seek(size-8,1)
   else:break
 assert atoms.index('moov')<atoms.index('mdat')
 contacts=Image.new('RGB',(1554,678*3),'white')
 for row,i in enumerate([0,16,32]):
  im=Image.open(frame_dir/(f'{i:03d}.png'));contacts.paste(im,(0,row*678))
 contacts.save(dst/'ARC_FIRST_MIDDLE_LAST.jpg',quality=90)
 writejson(dst/'RENDER_EVALUATION.json',{'views':metrics,'video':{'frames_generated':33,'frames_fully_decoded':int(counts[-1]),'h264':True,'pixel_format':'yuv420p','faststart_atom_order':atoms,'command':cmd},'asset_hashes':{arm:sha(dst/(arm+'_gaussians.npz')) for arm in assets},'novel_scene_occlusion':False})
 return metrics

def main():
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['build','evaluate']);args=ap.parse_args();guard()
 if args.phase=='build':
  assert not (T/'ASSET_FREEZE.json').exists(),'Do not overwrite fixed assets'
  summary={}
  for scene in SCENES:
   status('CONSTRUCTING',current_scene=scene,heldout_content_read=False);summary[scene]=construct(scene);status('BUILD_COMPLETE',current_scene=scene,models_created=2*len(summary),scenes_built=len(summary))
  writejson(T/'BUILD_RESULTS.json',summary)
  files=[p for scene in SCENES for p in (OUT/scene).glob('*gaussians.*')]
  writejson(T/'ASSET_FREEZE.json',{'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'build_views':BUILD,'holdouts':HOLD,'heldout_content_read':False,'files':[{'path':str(p),'sha256':sha(p)} for p in files],'code_files':[{'path':str(p),'sha256':sha(p)} for p in Path(__file__).parent.iterdir() if p.is_file()]})
  status('AWAITING_BUILD_VISUAL_REVIEW',scenes_built=3,models_created=6,heldout_content_read=False)
 else:
  freeze=json.loads((T/'ASSET_FREEZE.json').read_text())
  for row in freeze['files']+freeze['code_files']:assert sha(row['path'])==row['sha256'],row['path']
  for i,scene in enumerate(SCENES):
   status('RENDER_EVALUATION',current_scene=scene,heldout_content_read=True);evaluate(scene);status('SCENE_RENDER_COMPLETE',scenes_rendered=i+1,models_rendered=2*(i+1),exact_camera_frames=(i+1)*10,arc_frames=(i+1)*33)
if __name__=='__main__':main()
