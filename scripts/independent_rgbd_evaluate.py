#!/usr/bin/env python3
"""Sealed-asset projection and independent C evaluation. No construction/tuning."""
import sys,json,os,subprocess,time,hashlib,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np,cv2
from src.independent_rgbd.core import *
from src.independent_rgbd.geometry import depth_edges,cloud_zbuffer
from src.independent_rgbd.render import render_asset,compile_asset
from src.independent_rgbd.native import StockRenderer
from independent_rgbd_probe import A,O,inputs,resources,write_json,confine

def panel(image,label):
 if image.ndim==2:image=np.repeat(image[:,:,None],3,2)
 h,w=image.shape[:2];out=np.full((h+28,w,3),245,np.uint8);out[28:]=image;cv2.putText(out,label,(8,20),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,0,0),1,cv2.LINE_AA);return out

def sheet(rgb,gs,mask,edge,depth_edge,edit_mask,edit_only,heading):
 white=lambda m:np.repeat((255-m)[:,:,None],3,2)
 edited=white(edit_mask);edited[edit_only>0]=[210,30,30]
 panels=[panel(rgb,'RAW RGB (real Kinect)'),panel(gs,'Frozen vanilla GS RGB (F only)'),panel(white(mask),'Fixed sensor-3D world curves'),panel(white(edge),'GS RGB Canny (weak RGB-only)'),panel(white(depth_edge),'Kinect depth2d (evaluation only)'),panel(edited,'Edited same ID: +2cm X, width x2')]
 grid=np.concatenate([np.concatenate(panels[:3],axis=1),np.concatenate(panels[3:],axis=1)],axis=0)
 header=np.full((32,grid.shape[1],3),235,np.uint8);cv2.putText(header,heading,(8,23),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,0,0),1,cv2.LINE_AA);return np.concatenate([header,grid],axis=0)

def evaluate():
 import torch,imageio_ffmpeg
 cfg=inputs();model=json.loads((A/'MODEL_SEAL.json').read_text());seal=json.loads((A/'ASSET_SEAL.json').read_text())
 if sha256(model['path'])!=model['sha256']:raise ValueError('model seal')
 for e in seal['files']:
  if sha256(e['path'])!=e['sha256']:raise ValueError('asset seal')
 if not json.loads((A/'REPRODUCTION.json').read_text())['passed']:raise ValueError('reproduction gate')
 asset=json.loads((A/'ASSET.json').read_text());edit=json.loads((A/'EDITED_ASSET.json').read_text());original_bytes=json.dumps(asset,sort_keys=True);edit_bytes=json.dumps(edit,sort_keys=True);compiled=compile_asset(asset);compiled_edit=compile_asset(edit);edited_only={'curves':[edit['curves'][0]]} if edit['curves'] else {'curves':[]};compiled_only=compile_asset(edited_only)
 cloud=np.load(O/'F_fused_cloud.npz')['points'];posemap=json.loads((A/'DEPTH_TIME_POSES.json').read_text())['poses'];K=np.array(cfg['K']);arr=asset_arrays(asset);controls=arr['points'];offsets=arr['offsets'];frames=cfg['frames'];ids=arr['ids'].tolist()
 gpu=subprocess.check_output(['nvidia-smi','--id=0','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True).strip()
 if int(gpu.split(',')[0])>512 or int(gpu.split(',')[1])>5:raise RuntimeError('GPU occupied STOP')
 torch.cuda.init();reader=confine(cfg,'eval');renderer=StockRenderer(model['path'],O/'vendor/site')
 ffmpeg=imageio_ffmpeg.get_ffmpeg_exe();video=O/'full_domain_comparison.mp4';writer=None;metrics=[];states=[];edit_view_ids=[];evidence_indices={int(round(q*(len(frames)-1))):q for q in [0,.1,.25,.5,.75,.9,1]};quantile_files=[];cuts=[];min_ink=(np.inf,None);max_ink=(-1,None);start=time.time()
 targets={k:0 for k in ['predicted_visible_known','visible_consistent','false_visible_occluded','visible_contradiction','unknown_sensor','known_sensor','all_controls','predicted_hidden_known','hidden_sensor_occluded','false_hidden_sensor_visible']}
 try:
  for i,f in enumerate(frames):
   rgb=reader.read(f['rgb']);d=depth_metres(reader.read(f['depth']));c=np.array(f['c2w']);dc=np.array(posemap[f['id']]);occluder=cloud_zbuffer(cloud,K,c,(480,640));mask,rs=render_asset(asset,K,c,occluder,compiled);em,ers=render_asset(edit,K,c,occluder,compiled_edit)
   edit_only,_=render_asset(edited_only,K,c,occluder,compiled_only)
   gs=np.clip(renderer.render(K,c,(480,640)),0,1);gs_u8=np.rint(gs*255).astype('uint8');edge=cv2.Canny(cv2.cvtColor(gs_u8,cv2.COLOR_RGB2GRAY),100,200);de=depth_edges(d).astype('uint8')*255
   uv,z=project(controls,K,c);pred=visibility(uv,z,occluder)
   # Sensor-time primary evaluation: independent depth and pose, no asset changes.
   duv,dz=project(controls,K,dc);truth=visibility(duv,dz,d);dcloud=cloud_zbuffer(cloud,K,dc,(480,640));dpred=visibility(duv,dz,dcloud);known=truth!='unknown';pv=dpred!='occluded'
   counts=dict(predicted_visible_known=int((pv&known).sum()),visible_consistent=int((pv&(truth=='consistent')).sum()),false_visible_occluded=int((pv&(truth=='occluded')).sum()),visible_contradiction=int((pv&(truth=='contradiction')).sum()),unknown_sensor=int((~known).sum()),known_sensor=int(known.sum()),all_controls=len(controls),predicted_hidden_known=int((~pv&known).sum()),hidden_sensor_occluded=int((~pv&(truth=='occluded')).sum()),false_hidden_sensor_visible=int((~pv&(truth=='consistent')).sum()))
   curve_states=[]
   for j in range(len(ids)):
    labels=pred[offsets[j]:offsets[j+1]];nl=labels[labels!='unknown']
    curve_states.append('occluded' if len(nl)>=2 and (nl=='occluded').all() else 'visible' if (labels=='consistent').any() else 'unknown')
   states.append(curve_states)
   effect=int(np.count_nonzero(mask!=em));
   if f['split']=='C' and effect>0:edit_view_ids.append(f['id'])
   row=dict(index=i,frame=f['id'],split=f['split'],timestamp=f['timestamp'],ink_3d=rs['ink_fraction'],ink_gs_rgb=float((edge>0).mean()),ink_depth2d=float((de>0).mean()),visible_ids=len(rs['ids']),projection_unknown_samples=rs['counts']['unknown'],projection_samples=sum(rs['counts'].values()),edit_changed_pixels=effect,gs_psnr=float(-10*np.log10(max(float(((gs-rgb/255.)**2).mean()),1e-12))),sensor_zero_fraction=float((d==0).mean()),**counts)
   metrics.append(row)
   if f['split']=='C':
    for k in targets:targets[k]+=counts[k]
   cut=i>0 and f['timestamp']-frames[i-1]['timestamp']>.15
   if cut:cuts.append(dict(index=i,frame=f['id'],gap=f['timestamp']-frames[i-1]['timestamp']))
   heading=f"{i+1}/{len(frames)} {f['id']} split {f['split']} t={f['timestamp']-frames[0]['timestamp']:.3f}s ink={rs['ink_fraction']:.3f}"+(' CUT/GAP' if cut else '')
   grid=sheet(rgb,gs_u8,mask,edge,de,em,edit_only,heading)
   proxy=cv2.resize(grid,(960,540),interpolation=cv2.INTER_AREA)
   if writer is None:
    writer=subprocess.Popen([ffmpeg,'-y','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s','960x540','-r','24','-i','-','-an','-c:v','libx264','-threads','2','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=(O/'encode.log').open('w'))
   writer.stdin.write(proxy.tobytes())
   if i in evidence_indices:
    name=f"quantile_{int(evidence_indices[i]*100):03d}_{f['id']}.png";cv2.imwrite(str(A/name),grid[:,:,::-1]);quantile_files.append(dict(index=i,frame=f['id'],split=f['split'],quantile=evidence_indices[i],path=str(A/name)))
   if row['ink_3d']<min_ink[0]:min_ink=(row['ink_3d'],dict(index=i,frame=f['id']));cv2.imwrite(str(A/'lowest_ink.png'),grid[:,:,::-1])
   if row['ink_3d']>max_ink[0]:max_ink=(row['ink_3d'],dict(index=i,frame=f['id']));cv2.imwrite(str(A/'highest_ink.png'),grid[:,:,::-1])
   if json.dumps(asset,sort_keys=True)!=original_bytes or json.dumps(edit,sort_keys=True)!=edit_bytes:raise RuntimeError('asset mutated by renderer')
   if i%40==0:resources();print(f'{i+1}/{len(frames)} elapsed={time.time()-start:.1f}s',flush=True)
 finally:
  if writer is not None:writer.stdin.close();writer.wait()
 if writer.returncode!=0:raise RuntimeError('video encode failed')
 decode=subprocess.run([ffmpeg,'-v','error','-i',str(video),'-f','null','-'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 if decode.returncode!=0 or decode.stderr:raise RuntimeError('full video decode failed '+decode.stderr)
 reveals=[]
 for j,identity in enumerate(ids):
  run=[]
  for i in range(1,len(states)-1):
   if states[i][j]=='occluded':run.append(i)
   elif run:
    before=run[0]-1
    if states[before][j]=='visible' and states[i][j]=='visible':reveals.append(dict(id=identity,before=frames[before]['id'],occluded=[frames[k]['id'] for k in run],after=frames[i]['id'],classification='F-cloud projected visibility; sensor correctness separately evaluated'))
    run=[]
 write_json(A/'OCCLUSION_REVEALS.json',dict(events=reveals,cuts=cuts,note='Unknown/outside is never labelled an occlusion event. No asset reselection.'))
 with (A/'FRAME_METRICS.csv').open('w') as out:
  w=csv.DictWriter(out,fieldnames=list(metrics[0]));w.writeheader();w.writerows(metrics)
 quantiles=[0,.1,.25,.5,.75,.9,1];distributions={}
 for split in ['F','C','ALL']:
  rows=[r for r in metrics if split=='ALL' or r['split']==split];distributions[split]={key:np.quantile([r[key] for r in rows],quantiles).tolist() for key in ['ink_3d','ink_gs_rgb','ink_depth2d','visible_ids','gs_psnr','sensor_zero_fraction']};distributions[split]['empty_fraction']=float(np.mean([r['ink_3d']==0 for r in rows]))
 med=distributions['C'];ratios={k:med['ink_3d'][3]/max(med[k][3],1e-10) for k in ['ink_gs_rgb','ink_depth2d']}
 survival=json.loads((A/'CURVE_SURVIVAL.json').read_text());support_rate=targets['visible_consistent']/max(targets['predicted_visible_known'],1);false_visible=targets['false_visible_occluded']/max(targets['predicted_visible_known'],1)
 gates=dict(curves_ge_10=len(ids)>=10,F_length_survival_ge_half=survival['surviving_length_ratio']>=.5,C_sensor_support_ge_80pct=support_rate>=.8,C_false_visible_occluded_le_10pct=false_visible<=.1,occlusion_reveal=len(reveals)>0,edit_effect_ge_2_C_views=len(edit_view_ids)>=2,ink_comparable=all(.5<=v<=2 for v in ratios.values()),C_empty_frames_le_20pct=med['empty_fraction']<=.2)
 summary=dict(status='PASS_PREREGISTERED_MECHANISM_ONLY' if all(gates.values()) else 'NO_GO',gates=gates,C_counts=targets,C_support_rate=support_rate,C_false_visible_occluded_rate=false_visible,C_ink_median_ratios=ratios,distributions=distributions,quantiles=quantiles,frames=len(frames),F_frames=92,C_frames=460,curve_ids=len(ids),edit_C_views_with_raster_change=len(edit_view_ids),edit_example_C_views=edit_view_ids[:10],occlusion_reveal_events=len(reveals),independent_human_review=False,limitations=['extra real scene, independent sensor geometry and mocap change original task','registered Kinect residual and asynchronous sensor timing remain uncertain','GS RGB Canny is a weak non-asset reference, not old I','F filtering rejects dynamic/inconsistent depth but no semantic dynamic-object ground truth','all metrics descriptive; repeated controls across source-view curves are correlated'],resources=resources(),seconds=time.time()-start)
 write_json(A/'EVALUATION.json',summary);write_json(A/'FIGURES.json',dict(quantile_frames=quantile_files,lowest_ink=min_ink[1],highest_ink=max_ink[1],sensor_pair=str(A/'TWO_VIEW_SENSOR.png'),F_GS_calibration=str(A/'F_GS_calibration.png')))
 write_json(A/'VIDEO.json',dict(path=str(video),sha256=sha256(video),bytes=video.stat().st_size,frames_written=len(frames),fps=24,duration_seconds=len(frames)/24,shape=[540,960],full_decode_exit=decode.returncode,full_decode_stderr=decode.stderr,encoding='CPU libx264 threads2, all eligible cameras, timestamp gaps labelled',raw_timestamp_duration=frames[-1]['timestamp']-frames[0]['timestamp'],remote='local regenerable video, manifest tracked'))
 for e in seal['files']:
  if sha256(e['path'])!=e['sha256']:raise ValueError('post-eval asset seal')
 print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':evaluate()
