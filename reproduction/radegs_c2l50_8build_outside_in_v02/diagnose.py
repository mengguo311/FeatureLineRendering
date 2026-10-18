from env import *
from anchor import *
from regions import *
from run_b import load_model,draw_v1
def native_contact(path,items,title,subtitle,cols=3):panel(path,items,title,subtitle,cols)
def scatter(rgb,uv,lab,radius=2):
 im=Image.fromarray(np.uint8(np.clip(rgb,0,1)*255));d=ImageDraw.Draw(im)
 for pt,g in zip(uv,lab):
  if g<=0 or not np.isfinite(pt).all():continue
  x,y=pt;co=tuple(np.uint8(PALETTE[int(g)%len(PALETTE)]*255));d.ellipse([x-radius,y-radius,x+radius,y+radius],fill=co)
 return np.asarray(im)/255.
def do():
 state('FINAL_SCIENTIFIC_DIAGNOSTICS',children=[os.getpid()]);delivery=ROOT/'delivery';delivery.mkdir(exist_ok=True)
 countA=[]
 for s in SCENES:
  items=[]
  for v in views(s):
   rgb,z,a=raw(s,v);sa=npz(ROOT/'stageA'/s/v/'SUBJECT.npz');old=npz(V1/'stageA'/s/v/'SUBJECT.npz');row=json.loads((ROOT/'stageA'/s/v/'COUNT.json').read_text());countA.append(row);items += [(v+' | frozen source RGB',rgb),(v+' | v01 subject',overlay(rgb,old['candidate'],old['unknown'])),(v+' | v02 candidate / UNKNOWN',overlay(rgb,sa['candidate'],sa['unknown']))]
  native_contact(delivery/(s+'_A_FOUR_VIEWS.jpg'),items,s+' | All four frozen cameras, Stage A','Green: candidate. Orange: unknown. Historical views; no mask changes after reserved inspection.',3)
  m=json.loads((ROOT/'stageA'/s/'model/MODEL.json').read_text())
  if m['plane']:
   ss=npz(ROOT/'stageA'/s/'model/FIT_SAMPLES.npz');plane=m['plane'];r=(ss['world']@np.array(plane['normal'])+plane['offset'])*plane['sign']/ss['pixel_scale'];imgs=[]
   for vi,v in enumerate([DEV[s],AUX[s]]):
    rgb,z,a=raw(s,v);sel=ss['view_id']==vi;lab=np.where(abs(r[sel])<=2.5,2,1);imgs += [('Source '+v,rgb),('Actual joint plane inliers RED / non-inlier BLUE',scatter(rgb,ss['uv'][sel],lab))]
   panel(delivery/(s+'_PLANE_SUPPORT.jpg'),imgs,s+' | Shared depth-plane hypothesis: actual sampled inliers','Red points explain plane fit, NOT certified background. No source Gaussian center/normal used.',2)
   np.savez_compressed(delivery/(s+'_PLANE_RESIDUALS.npz'),source_uv=ss['uv'],source_view=ss['view_id'],normalized_residual=r)
 s='ficus';items=[];statsB=[]
 for v in views(s):
  rgb,z,a=raw(s,v);old=npz(V1/'stageB'/s/v/'rgb_only.npz')['levels'][-1];r=npz(ROOT/'stageB'/s/v/'shared_xyz_lab_width_k3.npz');ctrl=npz(ROOT/'stageB'/s/v/'shared_rgb_only_k3.npz');items += [(v+' | original RGB',rgb),(v+' | v01 RGB-only / larger region budget',draw_v1(rgb,old)),(v+' | v02 shared K=3 + UNKNOWN',colors(rgb,r['labels'],r['unknown']))];statsB+=json.loads((ROOT/'stageB'/s/v/'COUNTS.json').read_text())
 panel(delivery/'ficus_B_FOUR_VIEWS.jpg',items,'Ficus | Real multi-block attempt across all four views','Shared colors encode hypotheses, not physical part certification. Grey: unknown. Native frames, fixed display.',3)
 matches=[]
 for f in sorted((ROOT/'stageB/ficus/matches').glob('*/COUNTS.json')):matches.append(json.loads(f.read_text()))
 for tv in [AUX[s],*RES[s]]:
  p=ROOT/'stageB'/s/'matches'/('shared_xyz_lab_width_k3_'+tv);row=json.loads((p/'COUNTS.json').read_text());ar=npz(p/'FORWARD.npz');rgb=raw(s,DEV[s])[0];trgb=raw(s,tv)[0];lab=npz(ROOT/'stageB'/s/DEV[s]/'shared_xyz_lab_width_k3.npz');tl=npz(ROOT/'stageB'/s/tv/'shared_xyz_lab_width_k3.npz');ix=ar['state']==1;im=scatter(trgb,ar['target_uv'][ix],ar['region'][ix],1)
  panel(delivery/('ficus_MATCH_'+tv+'.jpg'),[('DEV raw RGB',rgb),('Target raw RGB',trgb),('DEV shared K3 label',colors(rgb,lab['labels'],lab['unknown'])),('Target independently queried raw depth/RGB',colors(trgb,tl['labels'],tl['unknown'])),('Visible DEV samples projected to target | source region colors',im),('Target labels, not projected source ink',colors(trgb,tl['labels']))],'Ficus | '+DEV[s]+' -> '+tv+' | mutual candidates '+str(row['mutual_pairs']),'Visibility from source-only camera-z; occluded/front-inconsistent/unknown excluded and recorded. IDs alone are NOT evidence.',2)
 # Post-hoc explanatory zooms never fed into the algorithm. Preserve full-frame boards above.
 rois=[('scan24','0024',(0,70,260,581),'Left facade mistaken for background-plane support'),('scan65','0036',(0,100,380,581),'Table residuals remain despite more complete bone'),('ficus','train_r_80',(260,250,500,620),'K3 branch and lower-trunk mixing'),('ficus','test_r_14',(260,380,510,720),'Unseen pot underside is UNKNOWN, not filled')]
 for i,(s,v,roi,label) in enumerate(rois):
  rgb=raw(s,v)[0];x0,y0,x1,y1=roi
  if s=='ficus':r=npz(ROOT/'stageB'/s/v/'shared_xyz_lab_width_k3.npz');candidate=colors(rgb,r['labels'],r['unknown'])
  else:r=npz(ROOT/'stageA'/s/v/'SUBJECT.npz');candidate=overlay(rgb,r['candidate'],r['unknown'])
  panel(delivery/f'FAILURE_DETAIL_{i}.jpg',[('Original pixels',rgb[y0:y1,x0:x1]),('Actual candidate pixels',candidate[y0:y1,x0:x1])],label,'Explanatory post-hoc zoom only; not selection mask or GT.',2)
 js(delivery/'EXPLANATORY_ROIS.json',[dict(scene=s,view=v,roi=roi,label=lab,not_algorithm_input=True) for s,v,roi,lab in rois])
 overview=[]
 for s in SCENES:
  v=DEV[s];rgb=raw(s,v)[0];old=npz(V1/'stageA'/s/v/'SUBJECT.npz')
  if s=='ficus':r=npz(ROOT/'stageB'/s/v/'shared_xyz_lab_width_k3.npz');im=colors(rgb,r['labels'],r['unknown']);title='v02 multiple coarse hypotheses | B NO_GO'
  else:r=npz(ROOT/'stageA'/s/v/'SUBJECT.npz');im=overlay(rgb,r['candidate'],r['unknown']);title='v02 subject hypothesis | A NO_GO'
  # Overview uses letterboxing only; separate fullnative boards are the scientific evidence.
  for title2,array in [('Source RGB',rgb),('v01 subject',overlay(rgb,old['candidate'],old['unknown'])),(title,im)]:
   h,w=array.shape[:2];out=np.ones((800,800,3),np.float32);out[(800-h)//2:(800-h)//2+h,(800-w)//2:(800-w)//2+w]=array;overview.append((s+' | '+title2,out))
 panel(delivery/'OVERVIEW.jpg',overview,'Outside-in v02 | Shared visible 3D samples before coarse grouping','Real attempt; all original source/C8 assets unchanged. A: building/skull NO_GO. B: Ficus multi-block but no clean part identity.',3)
 js(ROOT/'COUNTS.json',dict(stageA=countA,stageB=statsB,matches=matches,fit_models=6,stageA_views=12,stageB_views=4,stageB_arm_view_maps=24,formal_source_regions=0,new_Gaussian_models=0,videos=0))
 js(ROOT/'STAGE_B_GATE.json',dict(ficus=dict(status='NO_GO',primary_k=3,visual_gate=False,mutual_counts=dict(train_r_7=1,test_r_14=2,test_r_79=1),reason='Pot mostly coherent but lower trunk included; leaf appearance and stem mixing. K5 predeclared diagnostic not primary replacement. XYZ-only matches high but spatial slices and unknown stem, not semantic proof.'),scan24='NOT_RUN',scan65='NOT_RUN',stageC='NOT_RUN',stageD='NOT_RUN',formal_physical_primitives=0))
 review('06_FINAL_B_NO_GO_STOP','已查看Ficus两个reserved PAIREd完整图：主K3确实多块，盆大部分稳定但下干混入；绿/橙仍按叶色/明暗与枝干混合，test79仅1配对；test14盆底在训练未观测邻域为UNKNOWN，不能补。K5仍叶色碎分，不能事后替代K3。XYZ-only配对3/3/3但只是空间分块且干大量UNKNOWN，反证配对数不是部件质量。主B NO_GO，C/D NOT_RUN。允许只读复算/证据图/归档，不允许新分割或v03。',[ROOT/'STAGE_B_GATE.json',ROOT/'B_RESERVED_COUNTS.json',ROOT/'stageB/ficus/test_r_14/PAIRED_ARMS.jpg',ROOT/'stageB/ficus/test_r_79/PAIRED_ARMS.jpg'])
 js(ROOT/'SCIENTIFIC_STOP.json',dict(utc=now(),bounded_pilot_complete=True,stageA_scenes=3,stageB_scenes=1,stageC='NOT_RUN',stageD='NOT_RUN',no_v03=True));state('SCIENCE_STOPPED_VERIFY_PENDING',children=[],scientific_status='PARTIAL_DIAGNOSTIC_NO_GO_FOR_UPGRADE')
if __name__=='__main__':do()
