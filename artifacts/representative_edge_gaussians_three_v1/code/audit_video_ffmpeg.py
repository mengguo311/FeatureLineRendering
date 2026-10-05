"""Additional independent ffmpeg decoder: all33, original RGB crop without titles."""
from io_utils import *
import imageio_ffmpeg
import subprocess,hashlib

def stage():
 f=json.loads((ART/'FINAL.json').read_text());rows=[];ff=imageio_ffmpeg.get_ffmpeg_exe()
 for scene in CFG['scenes']:
  for key in ('video_native','video_telegram1600'):
   v=f['media'][scene][key];path=Path(v['path']);assert sha(path)==v['sha256'];w,h=v['dimensions'];cw=w//5;y0=round(h*84/1768);y1=round(h*884/1768);ch=y1-y0;guard(256*1024**2)
   cmd=[ff,'-v','error','-nostdin','-threads','2','-i',str(path),'-vf',f'crop={cw}:{ch}:0:{y0},format=rgb24','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
   p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE);size=cw*ch*3;hashes=[]
   while True:
    chunks=[];remaining=size
    while remaining:
     data=p.stdout.read(remaining)
     if not data:break
     chunks.append(data);remaining-=len(data)
    if not chunks:break
    assert remaining==0,'Truncated independently decoded frame';hashes.append(hashlib.sha256(b''.join(chunks)).hexdigest())
   error=p.stderr.read().decode();assert p.wait()==0,error;assert len(hashes)==33 and len(set(hashes))==33
   specs=frames(scene,'arc');assert v['camera_hashes']==[s['camera_hash'] for s in specs] and len(set(v['camera_hashes']))==33
   rows.append(dict(scene=scene,variant=key,path=str(path),video_sha256=sha(path),decoded_count=len(hashes),distinct_original_RGB_without_title=len(set(hashes)),crop_xywh=[0,y0,cw,ch],RGB_sha256=hashes,camera_hashes=v['camera_hashes'],ffmpeg_command=cmd));print(scene,key,'independent RGB decode33/distinct33',flush=True)
 atomic(ART/'INDEPENDENT_VIDEO_DECODE.json',dict(utc=utc(),all_pass=True,decoder='Separate ffmpeg rawvideo pipe; does not call OpenCV/media_helpers video validators',ffmpeg_sha256=sha(ff),source_code_sha256=sha(__file__),rows=rows,human_verdict='PENDING'))
if __name__=='__main__':stage()
