"""Create actual-count Chinese delivery, complete media, hashes and resumable status."""
import json,shutil,subprocess,hashlib,datetime,traceback
from pathlib import Path
import numpy as np
from PIL import Image
from io_utils import *
import visuals
from media_helpers import make_contact,encode_video,_save

def records(scene):
 return [json.loads(p.read_text()) for p in sorted((OUT/scene/'evaluation').glob('*/METRICS.json')) if (p.parent/'SEAL.json').exists()]
def means(records,arm,count):
 rows=[m for r in records for m in r['metrics'] if m['arm']==arm and m['count']==count]
 return {key:float(np.mean([m[key] for m in rows if m[key] is not None])) if any(m[key] is not None for m in rows) else None for key in ['major_coverage','detail_coverage','offedge_alpha_fraction','offedge_selected_mass_fraction','visible_mass','Q_weighted_distance_to_evidence_pixels']},len(rows)
def fmt(x):return '未运行' if x is None else f'{x:.4f}'
def frontier(scene,rs,path):
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 s=load(OUT/scene/'assets/scorebank.npz');selection=json.loads((OUT/scene/'assets/selected_ids.json').read_text());fig,axs=plt.subplots(1,3,figsize=(15,4.5))
 labels=dict(A='A historical algorithm new',B='B new independent',C='joint lambda0',D='joint lambda.1',E='joint lambda.3');colors=dict(A='black',B='gray',C='tab:blue',D='tab:orange',E='tab:green')
 for arm in labels:
  u=s[arm+'_utility_curve'];cost=s[arm+'_cumulative_nonedge_cost'];axs[0].plot(np.arange(1,len(u)+1),u,label=labels[arm],color=colors[arm]);axs[1].plot(cost,u,color=colors[arm],label=labels[arm])
  cr=[r for r in rs if r['phase']=='C'];xs=[];ys=[]
  for b in selection['budgets']:
   count=min(b,len(s[arm+'_ordered_ids']));m,n=means(cr,arm,count)
   if n:xs.append(m['offedge_alpha_fraction']);ys.append(m['major_coverage'])
  if xs:axs[2].plot(xs,ys,'o-',color=colors[arm],label=labels[arm])
 axs[0].set(xlabel='original ID count (F prefixes)',ylabel='balanced F utility, demand .5 full alpha');axs[1].set(xlabel='F additive offedge cost',ylabel='balanced F utility');axs[2].set(xlabel='C native offedge alpha fraction',ylabel='C major coverage (all8 views mean)')
 for ax in axs:ax.grid(alpha=.25)
 axs[0].legend(fontsize=8);fig.suptitle(scene+' | frozen all lambdas, original mass, no C tuning');fig.tight_layout();guard(8*1024**2);path.parent.mkdir(parents=True,exist_ok=True);fig.savefig(path,dpi=180);plt.close(fig)

def video_content_audit(info):
 # Independently decode every video; title/footer are excluded from RGB content checks.
 import cv2
 cap=cv2.VideoCapture(info['path']);full=[];rgb=[];sizes=[]
 while True:
  ok,frame=cap.read()
  if not ok:break
  h,w=frame.shape[:2];x1=int(w*.2);y0=int(round(h*84/1768));y1=int(round(h*884/1768));roi=frame[y0:y1,:x1]
  full.append(hashlib.sha256(frame.tobytes()).hexdigest());rgb.append(hashlib.sha256(roi.tobytes()).hexdigest());sizes.append([w,h])
 cap.release();assert len(full)==33 and len(set(full))==33 and len(set(rgb))==33
 return dict(decoded_count=33,distinct_full_frames=33,distinct_RGB_content_without_labels=33,RGB_content_sha256=rgb,full_frame_sha256=full,dimensions=sizes[0],consistent_dimensions=len(set(map(tuple,sizes)))==1)

def coverage_match_panels(scene,rs):
 selection=json.loads((OUT/scene/'assets/selected_ids.json').read_text());paths=[]
 for record in rs:
  if record['phase'] not in ('F','C'):continue
  key=record['key'];spec=next(f for f in INPUTS['scenes'][scene]['frames'] if f['key']==key);raw=read(scene,spec,'MEDIA_F_SELECTED_COVERAGE_MATCH');d=OUT/scene/'evaluation'/key
  q=load(d/'projection.npz')['Q'];e=load(OUT/scene/('F' if record['phase']=='F' else 'evaluation')/key/'evidence.npz');chosen=[];labels=[]
  for arm in 'ABCDE':
   count=selection['coverage_match_counts'][arm]
   if count is None:continue
   index=next(j for j,f in enumerate(record['fields']) if f['arm']==arm and f['count']==count);chosen.append(q[:,:,index]);labels.append(arm+' F匹配前缀 | '+str(count)+' IDs')
  path=d/'coverage_matched.jpg';visuals.comparison(path,raw,e,np.stack(chosen,-1),labels,scene+' '+key+' | 前缀只由F选择；当前视图未强行匹配覆盖')
  if record['phase']=='C':paths.append(path)
 if paths:
  guard(48*1024**2);return make_contact(paths,ART/'figures'/(scene+'_C_coverage_match.jpg'),tile_width=1600,columns=2)
 return None

def scene_media(scene,rs):
 d=OUT/scene/'media';curated=ART/'figures';curated.mkdir(exist_ok=True);d.mkdir(parents=True,exist_ok=True);media={'coverage_matched_C_contact':coverage_match_panels(scene,rs)}
 allkeys=[f['key'] for f in INPUTS['scenes'][scene]['frames']];valid={r['key'] for r in rs};ordered=[k for k in allkeys if k in valid];paths=[OUT/scene/'evaluation'/k/'comparison.jpg' for k in ordered]
 if paths:
  guard(96*1024**2);media['all_views_contact']=make_contact(paths,curated/(scene+'_all_views.jpg'),tile_width=1600,columns=2)
 ckeys=[f['key'] for f in frames(scene,'C') if f['key'] in valid]
 if ckeys:
  guard(48*1024**2);media['C_contact']=make_contact([OUT/scene/'evaluation'/k/'comparison.jpg' for k in ckeys],curated/(scene+'_C8.jpg'),tile_width=1600,columns=2)
 fkeys=[f['key'] for f in frames(scene,'F') if f['key'] in valid]
 if fkeys:
  guard(48*1024**2);media['F_contact']=make_contact([OUT/scene/'evaluation'/k/'comparison.jpg' for k in fkeys],d/'F8.jpg',tile_width=1600,columns=2)
 source=OUT/scene/'F/F_041/preview.jpg'
 if source.exists():guard(source.stat().st_size);shutil.copyfile(source,curated/(scene+'_F041_evidence.jpg'));media['F_evidence']=dict(path=str(curated/(scene+'_F041_evidence.jpg')),sha256=sha(curated/(scene+'_F041_evidence.jpg')))
 arc=[f['key'] for f in frames(scene,'arc')];ap=[OUT/scene/'evaluation'/k/'comparison.jpg' for k in arc]
 if all(k in valid for k in arc):
  guard(96*1024**2);media['arc_first_mid_last']=make_contact([ap[0],ap[16],ap[-1]],curated/(scene+'_arc_first_mid_last.jpg'),tile_width=2400,columns=1)
  guard(96*1024**2);media['arc_all33_contact']=make_contact(ap,d/'arc_all33.jpg',tile_width=1600,columns=2)
  for name,width in [('native',None),('telegram1600',1600)]:
   guard(128*1024**2);v=encode_video(ap,d/('arc33_'+name+'.mp4'),width=width,fps=CFG['video_fps']);v['content_audit']=video_content_audit(v);v['camera_hashes']=[f['camera_hash'] for f in frames(scene,'arc')];v['RGB_original_content_hashes']=[next(r['rgb_content_sha256'] for r in rs if r['key']==k) for k in arc];assert len(set(v['RGB_original_content_hashes']))==33;media['video_'+name]=v
   if name=='telegram1600':guard(Path(v['path']).stat().st_size);q=ART/'media'/scene/Path(v['path']).name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(v['path'],q);v['curated_path']=str(q);v['curated_sha256']=sha(q)
 else:media.update(video_native=None,video_telegram1600=None,actual_arc_frames=sum(k in valid for k in arc),requested_arc_frames=33)
 frontier(scene,rs,curated/(scene+'_frontier.png'));media['frontier']=dict(path=str(curated/(scene+'_frontier.png')),sha256=sha(curated/(scene+'_frontier.png')))
 atomic(d/'MEDIA.json',media);event('MEDIA_COMPLETE',scene=scene,actual_poses=len(rs),actual_arc=sum(r['phase']=='arc' for r in rs));return media

def summarize(scene,rs):
 sp=OUT/scene/'assets/selected_ids.json';selection=json.loads(sp.read_text()) if sp.exists() else None;meta=json.loads((OUT/scene/'assets/ASSET.json').read_text()) if sp.exists() else None
 result=dict(scene=scene,requested_pose_count=49,actual_pose_count=len(rs),actual_counts={p:sum(r['phase']==p for r in rs) for p in ['F','C','arc']},asset=meta,selection_path=str(sp) if sp.exists() else None,standard=[],coverage_matched=[],projection_kind='FULL_NATIVE_ORIGINAL_T' if rs else None)
 if selection:
  for phase in ['F','C']:
   rr=[r for r in rs if r['phase']==phase]
   for b in selection['budgets']:
    for arm in ['A','B','C','D','E']:
     count=min(b,selection['arms'][arm]['actual_prefix_length']);m,actual=means(rr,arm,count);result['standard'].append(dict(phase=phase,budget=b,arm=arm,count=count,actual_views=actual,metrics=m if actual else None))
   for arm,count in selection['coverage_match_counts'].items():
    m,actual=means(rr,arm,count) if count is not None else ({},0);result['coverage_matched'].append(dict(phase=phase,arm=arm,count=count,F_target=selection['coverage_match_F_target'],actual_views=actual,metrics=m if actual else None))
  q=ART/'assets'/scene;q.mkdir(parents=True,exist_ok=True);guard(sp.stat().st_size);shutil.copyfile(sp,q/'selected_ids.json');shutil.copyfile(OUT/scene/'assets/ASSET.json',q/'ASSET.json')
 atomic(ART/('SUMMARY_'+scene+'.json'),result);return result

