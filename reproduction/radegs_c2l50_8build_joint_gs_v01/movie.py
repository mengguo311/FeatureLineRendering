from common import *
from produce import load_model
from renderer import render
import re,traceback
FF=ROOT.parent/'spatial_rgb_gaussian_demo_v01/dependencies/unpacked/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
def movie(scene):
 guard();out=ROOT/'scenes'/scene/'media';out.mkdir(parents=True,exist_ok=True)
 if (out/'VALIDATION.json').exists():
  d=json.loads((out/'VALIDATION.json').read_text());assert sha(d['video'])==d['sha256'];return d
 raw=json.loads((BASE/'scenes'/scene/'media/ARC_CAMERAS.json').read_text());cams=raw['cameras'];assert len(cams)==33
 keys=[hashlib.sha256(np.asarray(c['extrinsic']).tobytes()).hexdigest() for c in cams];assert len(set(keys))==17 and keys[0]==keys[-1]
 js(out/'ARC_CAMERAS.json',dict(cameras=cams,source=str(BASE/'scenes'/scene/'media/ARC_CAMERAS.json'),source_sha256=sha(BASE/'scenes'/scene/'media/ARC_CAMERAS.json'),poses=33,distinct_poses=17,actual_fresh_render_each_frame=True))
 a,s,l,floor=load_model(scene);n=len(s['means']);bg=[1]*3 if scene=='ficus' else [0]*3;frames=out/'frames';frames.mkdir(exist_ok=True);records=[];start=time.monotonic();first=None
 for i,c in enumerate(cams):
  guard();assert time.monotonic()-start<1800,'Per-scene video budget exceeded; static assets retained'
  # No image reuse or screen warp: render the fixed reloaded merged asset each time.
  sr=render(s,c,bg,floor[:n])['rgb'];j=render(a,c,bg,floor)['rgb'];hashes=dict(source=hashlib.sha256(sr.tobytes()).hexdigest(),joint=hashlib.sha256(j.tobytes()).hexdigest())
  if i==0:first=hashes
  if i==32:assert hashes==first,'Return view mismatch'
  panel(frames/f'{i:03d}.png',[('Original source | same CPU renderer',sr),('TRUE joint | source + C2L50 8BUILD C',j)],f'{scene} | {i+1}/33 | 17 distinct poses / return arc','Fixed merged Gaussians; unified depth sort; CPU approximation; inherited ink artifacts retained',cols=2)
  records.append(dict(frame=i,pose_sha256=keys[i],hashes=hashes,elapsed=time.monotonic()-start));js(out/'FRAME_PROGRESS.json',records);print(scene,'frame',i+1,round(time.monotonic()-start,2),flush=True)
 video=out/f'{scene}_SOURCE_JOINT.mp4';enc=[str(FF),'-hide_banner','-loglevel','error','-threads','2','-filter_threads','2','-framerate','8','-i',str(frames/'%03d.png'),'-c:v','libx264','-threads','2','-crf','19','-pix_fmt','yuv420p','-vf','pad=ceil(iw/2)*2:ceil(ih/2)*2','-movflags','+faststart',str(video)];r=subprocess.run(enc,capture_output=True,text=True);(out/'ENCODE.log').write_text(r.stderr);assert r.returncode==0,r.stderr
 dec=[str(FF),'-threads','2','-i',str(video),'-threads','2','-f','null','-'];r=subprocess.run(dec,capture_output=True,text=True);(out/'DECODE.log').write_text(r.stderr);assert r.returncode==0;nf=re.findall(r'frame=\s*(\d+)',r.stderr);assert int(nf[-1])==33 and 'yuv420p' in r.stderr and 'h264' in r.stderr
 atoms=[]
 with video.open('rb') as f:
  while True:
   h=f.read(8)
   if len(h)<8:break
   z=int.from_bytes(h[:4],'big');atoms.append(h[4:].decode());assert z>=8;f.seek(z-8,1)
 assert atoms.index('moov')<atoms.index('mdat')
 ims=[Image.open(frames/f'{i:03d}.png') for i in [0,8,16,24,32]];sheet=Image.new('RGB',(ims[0].width,ims[0].height*5),'white')
 for i,im in enumerate(ims):sheet.paste(im,(0,i*im.height))
 sheet.save(out/'CONTACT_FIRST_EXTREMES_MIDDLE_RETURN.jpg',quality=92)
 d=dict(video=str(video),sha256=sha(video),frames=33,full_decoded_frames=33,distinct_poses=17,actual_fresh_renders=33,independent_return_bitexact=True,h264=True,yuv420p=True,faststart=True,seconds=time.monotonic()-start,commands=[enc,dec]);js(out/'VALIDATION.json',d);return d
if __name__=='__main__':
 rows=[];failures=[];state('OPTIONAL_JOINT_MOVIES',status='RUNNING',worker_pid=os.getpid(),children=[])
 for s in SCENES:
  try:rows.append(dict(scene=s,validation=movie(s)))
  except Exception:failures.append(dict(scene=s,traceback=traceback.format_exc()))
  js(ROOT/'VIDEO_PROGRESS.json',dict(completed=rows,failures=failures))
 state('MOVIES_COMPLETE',status='READY_FOR_REVIEW',worker_pid=None,children=[],video_scenes=len(rows),video_failures=failures)
