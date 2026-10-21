"""Frozen CPU lamp temporal run. All writes confined to current unit."""
from common import *
import argparse,time,shutil,subprocess
from datetime import datetime,timezone
from PIL import Image,ImageDraw
from renderer_probe_unit007 import render
from run_unit002 import contact
U=OUT.parent/'unit_007'
def read(n):return json.loads((U/n).read_text())
def resources():
 size=sum(p.stat().st_size for p in U.parent.rglob('*') if p.is_file())
 r=dict(root_free=shutil.disk_usage(WORK).free,hdd_free=shutil.disk_usage(U).free,task_bytes=size,cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,gpu=False)
 assert r['root_free']>=2**30 and r['hdd_free']>=10*2**30 and size<20*2**30
 return r
def inputs():
 a=np.load(U/'inputs/lamp_mesh.npz');mesh=core.finalize_mesh(a['vertices'],a['faces'],a['parts'])
 return mesh,load_strokes(U/'inputs/selected.npz'),read('CONFIG.json')
def png(p,a):
 p.parent.mkdir(parents=True,exist_ok=True);Image.fromarray(np.uint8(np.rint(np.clip(a,0,1)*255))).save(p)
def freeze():
 paths=[U/n for n in ('PROTOCOL.json','CONFIG.json','SAMPLE_SELECTION.json','TRAJECTORIES.json','inputs/lamp_mesh.npz','inputs/selected.npz')]
 paths+=list((WORK/'experiments/partwise_sketch_hatching_v02').glob('*unit007.py'))
 paths+=[WORK/'experiments/partwise_sketch_hatching_v02'/n for n in ('common.py','renderer.py','run_unit002.py')]
 paths+=[WORK/'experiments/partwise_sketch_hatching'/n for n in ('core.py','core_walk_v2.py')]
 paths+=[WORK/'docs/partwise_sketch_hatching/experiment_outline_v1.md',U.parent.parent/'orchestration/BRIEF.md']
 for p in paths:
  if p.is_relative_to(WORK):
   dest=U/'source_snapshot'/p.relative_to(WORK);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 write_json(U/'SOURCE_LOCK.json',dict(frozen_utc=datetime.now(timezone.utc).isoformat(),files={str(p):sha(p) for p in paths},commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
 write_json(U/'RESOURCES_INITIAL.json',resources())
def check():
 for p,d in read('SOURCE_LOCK.json')['files'].items():assert sha(p)==d,p
 resources()
def render_frames(seq,start,stop):
 check();mesh,strokes,cfg=inputs();selected=read('SAMPLE_SELECTION.json')['selected'];ids=[r['id'] for r in selected]
 for c in read('TRAJECTORIES.json')[seq][start:stop]:
  i=c['frame'];t=time.perf_counter();r=render(mesh,strokes,cfg,**{k:v for k,v in c.items() if k!='frame'},probe_ids=ids);seconds=time.perf_counter()-t
  folder=U/'frames'/seq;folder.mkdir(parents=True,exist_ok=True)
  png(folder/f'{i:04}.png',r['image']);np.savez_compressed(folder/f'{i:04}.npz',hatch=r['hatch'],parts=r['parts'],depth=r['depth'])
  write_json(folder/f'{i:04}.json',dict(camera=r['camera'],render_seconds=seconds,diagnostics=r['diagnostics']))
  for sid,ink in r['probe_hatch'].items():png(U/'isolated'/seq/sid/f'{i:04}.png',ink)
  print(f'{seq} frame {i} seconds {seconds:.3f}',flush=True);resources()
 write_json(U/f'RENDER_{seq}_{start}_{stop}.json',dict(sequence=seq,start=start,stop=stop,complete=True))
def instrumentation():
 check();from renderer import render as original
 mesh,strokes,cfg=inputs();rows=[];ids=[r['id'] for r in read('SAMPLE_SELECTION.json')['selected']]
 r=render(mesh,strokes,cfg,azimuth=0,probe_ids=ids)
 o=original(mesh,strokes,cfg,azimuth=0)
 checks={k:bool(np.array_equal(r[k],o[k])) for k in ('image','hatch','parts','depth','contours','rings')}
 for p in (1,2,3):
  sid=next(x['id'] for x in read('SAMPLE_SELECTION.json')['selected'] if x['part']==p)
  iso=original(mesh,strokes,cfg,azimuth=0,selected_ids=[sid])['hatch']
  checks[sid]=bool(np.array_equal(iso,r['probe_hatch'][sid]))
  png(U/'controls'/f'original_{p}.png',iso)
 write_json(U/'INSTRUMENTATION_TEST.json',dict(checks=checks,go=all(checks.values()),scope='Implementation regression only; actual per-ID metrics are application gates.'))
 assert all(checks.values())
def metrics():
 check();from temporal_audit_unit007 import evaluate_frame,reference_maps,summarize
 mesh,strokes,cfg=inputs();byid={s['id']:s for s in strokes};rows=[]
 for seq,cameras in read('TRAJECTORIES.json').items():
  for c in cameras:
   i=c['frame'];camera=read(f'frames/{seq}/{i:04}.json')['camera'];ref=reference_maps(cfg['asset'],camera)
   np.savez_compressed(U/'frames'/seq/f'{i:04}_reference.npz',depth=ref['depth'],parts=ref['parts'])
   frame_rows=[]
   for item in read('SAMPLE_SELECTION.json')['selected']:
    sid=item['id'];s=byid[sid];ink=np.array(Image.open(U/'isolated'/seq/sid/f'{i:04}.png'))
    row=evaluate_frame(ink,core.anchor_points(mesh,s),s['part'],camera,cfg['asset'],sid,seq,i,reference=ref)
    frame_rows.append(row);rows.append(row)
   write_json(U/'raw'/f'{seq}_{i:04}.json',frame_rows)
   print(f'metrics {seq} {i}',flush=True)
 write_json(U/'TEMPORAL_SUMMARY.json',summarize(rows));write_json(U/'METRIC_ROWS.json',rows)
def media():
 check()
 records={}
 for seq,cameras in read('TRAJECTORIES.json').items():
  n=len(cameras);files=[U/'frames'/seq/f'{i:04}.png' for i in range(n)]
  labels=[f'{seq} {i:02} | az{c["azimuth"]} d{c["distance"]:.2f}' for i,c in enumerate(cameras)]
  contact(files,labels,U/'figures'/f'{seq}_all_frames.png',columns=6,thumb=256)
  inds=(0,n//2,n-1);contact([files[i] for i in inds],[labels[i] for i in inds],U/'figures'/f'{seq}_first_middle_last.png',columns=3,thumb=512)
  video=U/'videos'/f'{seq}.mkv';video.parent.mkdir(exist_ok=True)
  enc=[FFMPEG,'-v','error','-y','-threads','1','-filter_threads','1','-framerate','12','-i',str(U/'frames'/seq/'%04d.png'),'-c:v','ffv1','-threads','1','-pix_fmt','bgr0',str(video)]
  run=subprocess.run(enc,capture_output=True,timeout=90);assert run.returncode==0,run.stderr.decode()
  dec=[FFMPEG,'-v','error','-threads','1','-i',str(video),'-f','rawvideo','-pix_fmt','rgb24','-threads','1','-']
  result=subprocess.run(dec,capture_output=True,timeout=90);assert result.returncode==0
  arr=np.frombuffer(result.stdout,np.uint8).reshape(-1,512,512,3);assert len(arr)==n
  exact=[bool(np.array_equal(arr[i],np.array(Image.open(files[i]).convert('RGB')))) for i in range(n)]
  assert all(exact)
  records[seq]=dict(encode_command=enc,decode_command=dec,encode_rc=run.returncode,decode_rc=result.returncode,frames=n,all_frames_exact=all(exact),unique_frames=len({x.tobytes() for x in arr}))
 write_json(U/'VIDEO_VALIDATION.json',records)
def main():
 a=argparse.ArgumentParser();a.add_argument('stage',choices=['freeze','render','instrumentation','metrics','media']);a.add_argument('--sequence',default='orbit');a.add_argument('--start',type=int,default=0);a.add_argument('--stop',type=int,default=24);args=a.parse_args()
 if args.stage=='render':render_frames(args.sequence,args.start,args.stop)
 else:globals()[args.stage]()
if __name__=='__main__':main()
