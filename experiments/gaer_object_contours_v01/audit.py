"""Independent process: source/hash scope, saved IDs, native replay, every media frame."""
import json,subprocess,time
from pathlib import Path
import numpy as np
import torch
from PIL import Image
import runtime as rt
from adapter import backend,scene_io,NativeWeights,ShapeWeights,shape_extension,query_extension
FFMPEG=Path('/home/u00134/bin/miniconda3/envs/vfsdgs/lib/python3.9/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2')

def verify_style(op,camera,record,path,raw_native,alpha=None):
 z=np.load(path);np.testing.assert_array_equal(z['original_ids'],np.arange(op.n,dtype=np.int32));assert str(z['camera_sha256'])==camera['camera_sha256'];assert str(z['source_model_sha256'])==record['model_sha256'];s=z['strength'];assert np.isfinite(s).all() and s.min()>=0 and s.max()<=1
 use=op
 if 'edited_original_ids' in z and len(z['edited_original_ids']):
  R,_,_,g,b,i=op.state;cov=query_extension().geometry(g,op.n)[1];ids=z['edited_original_ids'];assert (ids>=0).all() and (ids<op.n).all();cov[torch.as_tensor(ids.astype(np.int64),device='cuda')]=torch.as_tensor(z['temporary_covariance_rows'],device='cuda');use=ShapeWeights(shape_extension(),op.s,op.model,cov)
 actual=use.ink_rgb(torch.as_tensor(s,device='cuda')).cpu().numpy().transpose(1,2,0);error=float(np.abs(actual-raw_native).max());assert error<=3e-6,(path,error);formula=float(np.abs((1-actual[...,0])-use.A(torch.as_tensor(s,device='cuda')).cpu().numpy()).max());assert formula<=3e-6
 return dict(style=rt.rel(path),max_native_replay_error=error,max_native_formula_error=formula,all_original_N=op.n,active_ids=int((s>1e-5).sum()),edited_ids=int(len(z['edited_original_ids'])) if 'edited_original_ids' in z else 0)

def media_audit(path,frame_dir,count):
 info=subprocess.run([str(FFMPEG),'-hide_banner','-i',str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);desc=next(line.strip() for line in info.stderr.splitlines() if 'Video:' in line);assert 'h264' in desc and 'yuv420p' in desc and '800x800' in desc
 r=subprocess.run([str(FFMPEG),'-hide_banner','-loglevel','error','-threads','2','-i',str(path),'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True);buf=np.frombuffer(r.stdout,np.uint8);assert len(buf)==count*800*800*3;frames=buf.reshape(count,800,800,3);errors=[]
 for j in range(count):
  original=np.asarray(Image.open(frame_dir/f'{j:03d}.png').convert('RGB'));errors.append(float(np.abs(frames[j].astype(np.float32)-original).mean()/255))
 data=path.read_bytes();assert data.find(b'moov')<data.find(b'mdat') and data.find(b'moov')>=0
 return dict(path=rt.rel(path),actual_stream_description=desc,decoded_frames=count,all_frame_png_MAE_max=max(errors),faststart=True,sha256=rt.sha(path))

def main():
 rt.guard('independent_audit');f=json.loads((rt.ART/'INPUT_FREEZE.json').read_text());default=json.loads((rt.ART/'DEFAULT_FREEZE.json').read_text());prot=json.loads((rt.ART/'PROTOCOL.json').read_text());hasherrors=[p for p,h in f['protected_before'].items() if rt.sha(p)!=h];assert not hasherrors,hasherrors
 frozenerrors=[p for p,h in default['source_hashes'].items() if rt.sha(rt.ROOT/p)!=h];assert not frozenerrors;assert rt.sha(rt.ART/'PROTOCOL.json')==default['protocol_sha256']
 heads=dict(line.split(' ',1) for line in subprocess.check_output(['git','for-each-ref','--format=%(refname) %(objectname)','refs/heads'],cwd=rt.ROOT,text=True).splitlines());headchanges={k:[h,heads.get(k)] for k,h in f['heads_before'].items() if heads.get(k)!=h and k!='refs/heads/gaer-object-contours-v01'};assert not headchanges
 seals=[]
 for p in sorted((rt.ART/'seals').glob('*.json')):
  s=json.loads(p.read_text())
  for q,h in s['files'].items():
   assert any(q.startswith(prefix+'/gaer_object_contours_v01/') for prefix in ['artifacts','experiments','out']),q;assert rt.sha(rt.ROOT/q)==h,q
  seals.append(dict(unit=s['unit'],files=len(s['files']),passed=True))
 replay=[];original_exports=[];arc_replay=[];module=backend()
 for scene in prot['scenes']:
  rt.guard(scene+'_independent_native_replay');rec=f['scenes'][scene];model=scene_io.load_model(rec)
  for camera in rec['cameras']:
   op=NativeWeights(module,scene_io.make_settings(module,camera),model);raw=op.original().cpu().numpy().transpose(1,2,0);out=rt.ART/'downloads'/scene/camera['key']/'original_full_SH3_float.npz';rt.npz(out,original_rgb_SH3=raw,camera_json=np.array(json.dumps(camera)),source_model_sha256=np.array(rec['model_sha256']));original_exports.append(rt.rel(out));render8=np.uint8(np.clip(raw,0,1)*255+.5);saved=np.asarray(Image.open(rt.ART/'media'/scene/camera['key']/'original_RGB_SH3.png'));np.testing.assert_array_equal(render8,saved)
   for arm in ['A','B','C','P','S']:
    path=rt.ART/'downloads'/scene/camera['key']/(arm+'_style.npz');z=np.load(path);replay.append(verify_style(op,camera,rec,path,z['native_rgb']))
   old=np.load(rt.ROOT/'artifacts/gaer_view_selection_v01/downloads'/(scene+'_'+camera['key']+'_scores_ids.npz'));ids=old['gaer_ratio_0.005_ids'];a=np.load(rt.ART/'downloads'/scene/camera['key']/'A_style.npz')['strength'];b=np.load(rt.ART/'downloads'/scene/camera['key']/'B_style.npz')['strength'];np.testing.assert_array_equal(np.flatnonzero(a),np.sort(ids));assert np.count_nonzero(b[np.setdiff1d(np.arange(op.n),ids)])==0
  for j,index in enumerate(default['choices'][scene]['arc_indices']):
   camera=rec['arc'][index];rt.guard(scene+'_arc_replay_'+str(j));op=NativeWeights(module,scene_io.make_settings(module,camera),model);path=rt.ART/'downloads'/scene/'arc'/camera['key']/'style.npz';raw=np.load(rt.OUT/'arc_raw'/scene/(camera['key']+'.npz'));r=verify_style(op,camera,rec,path,raw['native_rgb']);original=op.original().cpu().numpy().transpose(1,2,0);r['original_SH3_replay_error']=float(np.abs(original-raw['original_rgb_SH3']).max());assert r['original_SH3_replay_error']<=3e-6;np.testing.assert_allclose(raw['native_ink'],1-raw['native_rgb'][...,0],rtol=0,atol=0);arc_replay.append(r)
  del model
 videos=[]
 for scene in prot['scenes']:
  count=len(default['choices'][scene]['arc_indices']);media=rt.ART/'media'/scene/'arc'
  for kind in ['native_ink','RGB_overlay_PRESENTATION']:
   video=media/(kind+'_33.mp4' if count==33 else kind+'_ENGINEERING3_STOP.mp4');videos.append(media_audit(video,media/kind,count))
  p=media/'native_ink';hashes=[rt.sha(p/f'{j:03d}.png') for j in range(count)];assert len(set(hashes))==count,'actual frames must differ'
  # Check all-frame strips against every exact published frame, row-major.
  for kind,strip in [('native_ink','all_frames_native_strip.png'),('RGB_overlay_PRESENTATION','all_frames_RGB_overlay_strip.png')]:
   image=Image.open(media/strip)
   for j in range(count):
    tile=Image.open(media/kind/f'{j:03d}.png').convert('RGB').resize((200,200),Image.Resampling.LANCZOS);saved=image.crop(((j%11)*200,60+(j//11)*226,(j%11+1)*200,260+(j//11)*226));np.testing.assert_array_equal(np.asarray(tile),np.asarray(saved))
 rt.atomic_json(rt.ART/'tests/INDEPENDENT_NATIVE_MEDIA_AUDIT.json',dict(status='PASS',protected_files=len(f['protected_before']),protected_mismatches=hasherrors,frozen_source_mismatches=frozenerrors,other_head_changes=headchanges,seals=seals,fixed_native_replays=replay,arc_native_replays=arc_replay,original_SH3_float_exports=original_exports,videos=videos,all_frame_strip_exact=True,scope='independent Python process, original full PLY, real GPU/native APIs, actual whole-media decode; no mock image',resource=rt.guard('audit_complete',False)))
 rt.atomic_json(rt.ART/'tests/PROTECTED_AFTER.json',dict(status='PASS',hashes={p:rt.sha(p) for p in f['protected_before']},other_local_heads_unchanged=True))
 print('AUDIT_PASS','fixed',len(replay),'arc',len(arc_replay),'videos',len(videos),'protected',len(f['protected_before']),flush=True)
if __name__=='__main__':main()
