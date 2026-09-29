"""Every decoded video frame in ordered review pages; no scientific rerendering."""
import argparse,json,sys
from pathlib import Path
import cv2,numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.schedule_direct_curve_probe import atomic_json,sha,now

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--scene',required=True);ap.add_argument('--arc',type=int,required=True);a=ap.parse_args()
 base=ROOT/'out/direct_curve_global_fit_probe/run'/a.scene/'evaluate'
 assert (base/'figures'/f'arc{a.arc}_allframes_5.png').exists(),'arc publishing not complete'
 target=ROOT/'out/direct_curve_global_fit_probe/review'/a.scene/f'arc{a.arc}';target.mkdir(parents=True,exist_ok=False)
 video=base/'videos'/f'arc{a.arc}_complete.mp4';cap=cv2.VideoCapture(str(video));assert cap.isOpened();frames=[];rows=[]
 while True:
  ok,bgr=cap.read()
  if not ok:break
  n=len(frames);rgb=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB);source=base/'frames'/f'arc{a.arc}_{n:03d}.png';original=np.asarray(Image.open(source).convert('RGB'));assert rgb.shape==original.shape
  error=rgb.astype('f4')-original.astype('f4');mse=float(np.mean(error**2));rows.append(dict(frame=n,shape=list(rgb.shape),source=str(source),source_sha256=sha(source),mean_absolute_codec_difference=float(np.mean(abs(error))),psnr_db=10*np.log10(255**2/mse) if mse else None))
  frames.append(cv2.resize(rgb,(rgb.shape[1]//2,rgb.shape[0]//2),interpolation=cv2.INTER_AREA))
 cap.release();assert len(frames)==33
 pages={}
 for start in range(0,len(frames),6):
  end=min(start+6,len(frames));p=target/f'frames_{start:03d}_{end-1:03d}.png';Image.fromarray(np.concatenate(frames[start:end],axis=0)).save(p);pages[str(p)]=dict(first=start,last=end-1,sha256=sha(p))
 atomic_json(target/'DECODE.json',dict(time=now(),scene=a.scene,arc=a.arc,video=str(video),video_sha256=sha(video),decoded_frames=len(frames),frames=rows,pages=pages,scope='Complete ordered decoded frames, uniformly half-size for inspection. Codec differences are descriptive, not a changed science gate.'))
 print(json.dumps(dict(scene=a.scene,arc=a.arc,frames=len(frames),output=str(target)),indent=2))
if __name__=='__main__':main()
