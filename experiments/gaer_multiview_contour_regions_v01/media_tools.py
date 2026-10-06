"""Lossless panels and complete fixed-asset video audits; no geometric edits."""
import hashlib,json,subprocess,tempfile,textwrap
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg
import runtime as rt

def as_rgb(image):
 if isinstance(image,Image.Image):return image.convert('RGB')
 a=np.asarray(image)
 if a.ndim==3 and a.shape[0] in (1,3,4) and a.shape[-1] not in (1,3,4):a=np.moveaxis(a,0,-1)
 if a.dtype.kind=='f':a=np.rint(np.clip(a,0,1)*255).astype(np.uint8)
 elif a.dtype==np.bool_:a=a.astype(np.uint8)*255
 else:a=np.clip(a,0,255).astype(np.uint8)
 if a.ndim==2:a=np.repeat(a[:,:,None],3,axis=2)
 if a.ndim==3 and a.shape[2]==1:a=np.repeat(a,3,axis=2)
 if a.ndim!=3 or a.shape[2] not in (3,4):raise ValueError('expected HxW, HxWx3 or 3xHxW image')
 return Image.fromarray(a).convert('RGB')

def save_image(path,rgb):
 p=rt.scoped(path);as_rgb(rgb).save(p);return p

def _font(size=17):
 p=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
 return ImageFont.truetype(str(p),size) if p.exists() else ImageFont.load_default()

def make_panel(rows,path=None,title='',tile_size=800,label_height=54):
 """rows is list of rows of (label,image), default each tile stays native 800².

 Returns uint8 RGB. Non-native-size inputs are resized only for this explicitly
 labeled presentation panel; saved original singles remain caller responsibility.
 """
 if not rows or not any(rows):raise ValueError('nonempty panel rows required')
 columns=max(map(len,rows));title_h=42 if title else 0
 panel=Image.new('RGB',(columns*tile_size,len(rows)*(tile_size+label_height)+title_h),'white');d=ImageDraw.Draw(panel);font=_font()
 if title:d.text((10,9),str(title),font=font,fill='black')
 for i,row in enumerate(rows):
  y=title_h+i*(tile_size+label_height)
  for j,(label,array) in enumerate(row):
   im=as_rgb(array)
   if im.size!=(tile_size,tile_size):im=im.resize((tile_size,tile_size),Image.Resampling.LANCZOS)
   lines=textwrap.wrap(str(label),width=max(18,tile_size//10))[:2]
   d.multiline_text((j*tile_size+8,y+5),'\n'.join(lines),font=font,fill='black',spacing=2)
   panel.paste(im,(j*tile_size,y+label_height))
 if path is not None:panel.save(rt.scoped(path))
 return np.asarray(panel)

def make_strip(frames_png,path=None,columns=3,thumb_width=480):
 paths=[Path(p) for p in frames_png]
 if not paths:raise ValueError('no frames for strip')
 with Image.open(paths[0]) as im:w,h=im.size
 thumb_h=max(1,round(h*thumb_width/w));label_h=25;rows=(len(paths)+columns-1)//columns
 strip=Image.new('RGB',(columns*thumb_width,rows*(thumb_h+label_h)),'white');d=ImageDraw.Draw(strip);font=_font(14)
 for i,p in enumerate(paths):
  with Image.open(p) as im:
   if im.size!=(w,h):raise ValueError('video frame shape changed')
   thumb=im.convert('RGB').resize((thumb_width,thumb_h),Image.Resampling.LANCZOS)
  x=i%columns*thumb_width;y=i//columns*(thumb_h+label_h);d.text((x+4,y+3),f'{i:02d} | {p.name}',font=font,fill='black');strip.paste(thumb,(x,y+label_h))
 if path is not None:strip.save(rt.scoped(path))
 return np.asarray(strip)

def encode_video(frames_png,out_mp4,fps=12,expected_frames=33,frame_records=None):
 """Encode exactly supplied order; full decode and media manifest alongside MP4.

 frame_records optionally supplies camera/geometry hashes per frame; these are
 copied verbatim into the manifest, never derived from a different camera list.
 Independent camera/geometry invariance validation remains the caller's job.
 """
 paths=[Path(p).resolve() for p in frames_png];out=rt.scoped(out_mp4)
 if len(paths)!=expected_frames:raise ValueError(f'expected {expected_frames} complete frames, got {len(paths)}')
 if frame_records is not None and len(frame_records)!=len(paths):raise ValueError('frame record count mismatch')
 with Image.open(paths[0]) as im:w,h=im.size
 if w%2 or h%2:raise ValueError('H264 yuv420p requires even dimensions; fix panel layout rather than crop')
 for p in paths:
  with Image.open(p) as im:
   if im.size!=(w,h):raise ValueError('video frame resolution changed')
 rt.guard('encode_'+out.stem);exe=imageio_ffmpeg.get_ffmpeg_exe()
 with tempfile.TemporaryDirectory(prefix='video_',dir=rt.OUT/'tmp') as td:
  # Symlinks in new stage preserve exact caller order; no concat quoting hazards.
  for i,p in enumerate(paths):(Path(td)/f'{i:05d}.png').symlink_to(p)
  command=[exe,'-hide_banner','-loglevel','error','-y','-framerate',str(fps),'-i',str(Path(td)/'%05d.png'),'-frames:v',str(len(paths)),'-c:v','libx264','-threads','2','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(out)]
  proc=subprocess.run(command,capture_output=True,text=True)
  if proc.returncode:raise RuntimeError('video encode failed: '+proc.stderr)
 # Full decode every frame in the actual delivered H264, bounded host memory.
 command=[exe,'-hide_banner','-loglevel','error','-threads','2','-i',str(out),'-f','rawvideo','-pix_fmt','rgb24','-']
 p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE);framebytes=w*h*3;pending=bytearray();decoded=[]
 while True:
  b=p.stdout.read(framebytes-len(pending))
  if not b:break
  pending.extend(b)
  if len(pending)==framebytes:decoded.append(hashlib.sha256(pending).hexdigest());pending.clear()
 stderr=p.stderr.read().decode();returncode=p.wait();p.stdout.close();p.stderr.close()
 if returncode or pending or len(decoded)!=len(paths):raise RuntimeError(f'full decode failed rc={returncode}, frames={len(decoded)}, pending={len(pending)} '+stderr)
 probe=subprocess.run([exe,'-hide_banner','-i',str(out)],text=True,capture_output=True).stderr
 probe_path=out.with_suffix('.probe.txt');probe_path.write_text(probe)
 if 'h264' not in probe or 'yuv420p' not in probe:raise RuntimeError('video codec/pixel-format check failed')
 data=out.read_bytes();faststart=0<=data.find(b'moov')<data.find(b'mdat')
 if not faststart:raise RuntimeError('MP4 faststart order failed')
 records=[]
 for i,(p,hsh) in enumerate(zip(paths,decoded)):
  r=dict(frame_records[i]) if frame_records is not None else {}
  r.update(index=i,source_png=str(p),source_png_sha256=rt.sha(p),decoded_frame_sha256=hsh);records.append(r)
 manifest=dict(path=str(out),sha256=rt.sha(out),encoder=exe,encoder_sha256=rt.sha(exe),codec='h264',pixel_format='yuv420p',faststart=faststart,width=w,height=h,fps=fps,expected_frames=expected_frames,full_decode=True,decoded_frames=len(decoded),distinct_decoded_frames=len(set(decoded)),all_frames_preserved=True,probe=str(probe_path),frames=records)
 rt.atomic_json(out.with_suffix('.manifest.json'),manifest);return manifest
