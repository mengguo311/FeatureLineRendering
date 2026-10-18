from env import *
from subject import run_arrays
from responsibility import ProjectedSource
from produce import load_model
from scipy import ndimage as ndi
import traceback,signal

def timeout(*args):raise TimeoutError('900-second unit budget reached')
signal.signal(signal.SIGALRM,timeout)

def overlay(rgb,mask,unknown=None):
 x=rgb.copy();x[mask]=x[mask]*.55+np.array([.05,.85,.4])*.45
 if unknown is not None:x[unknown]=x[unknown]*.55+np.array([1,.45,.02])*.45
 return x

def grey(x):return np.repeat(x[...,None],3,axis=2)
def stats(mask):
 lab,n=ndi.label(mask);bg,n2=ndi.label(~mask);border=np.unique(np.r_[bg[0],bg[-1],bg[:,0],bg[:,-1]]);return dict(pixels=int(mask.sum()),fraction=float(mask.mean()),components=int(n),holes=int(sum(j not in border for j in range(1,n2+1))))
def color_depth(z,a):
 valid=np.isfinite(z)&(z>.2)&(a>.5);im=np.zeros((*z.shape,3));lo,hi=np.quantile(z[valid],[.02,.98]);q=np.clip((z-lo)/max(hi-lo,1e-12),0,1);q=np.nan_to_num(q);im[...,0]=q;im[...,1]=1-abs(2*q-1);im[...,2]=1-q;im[~valid]=[.5,.5,.5];return im,dict(display_only_limits=[float(lo),float(hi)],not_used_for_segmentation=True)

def calibration(s,c,raw,src,proj):
 z=raw['median_camera_z'].squeeze();al=raw['alpha'].squeeze();good=(z>.2)&np.isfinite(z)&(al>=.5)&(src['median_center_z']>.2)
 m=dict(rgb_mae=float(abs(src['rgb']-raw['rgb']).mean()),alpha_mae=float(abs(src['alpha']-al).mean()),center_surface_p95=float(np.quantile(abs(src['median_center_z'][good]-z[good])/z[good],.95)));assert m['rgb_mae']<=.02 and m['alpha_mae']<=.02 and m['center_surface_p95']<=.15,m
 yy,xx=np.nonzero(good);allerr=[];renderr=[];records=[]
 for k in np.linspace(0,len(xx)-1,12,dtype=int):
  uv=[int(xx[k]),int(yy[k])];r=proj.query(uv);exact=proj.query(uv,all_N=True);assert np.array_equal(r['ids'],exact['ids']);error=float(np.max(abs(r['weight']-exact['weight']),initial=0));assert error<=2e-12
  rgb=r['rgb']+r['trans']*(1 if s=='ficus' else 0);e=float(max(np.max(abs(rgb-src['rgb'][uv[1],uv[0]])),abs(r['alpha']-src['alpha'][uv[1],uv[0]])));assert e<=5e-7
  allerr.append(error);renderr.append(e);records.append(dict(uv=uv,source_ids=r['ids'].tolist(),weight=r['weight'].tolist(),alpha=float(r['alpha'])))
 m.update(all_N_queries=12,all_N_max_abs=max(allerr),query_render_max_abs=max(renderr),engineering='GO');return m,records

def run(s,views):
 t=time.monotonic();guard();a,source,ink,floor=load_model(s);n=len(source['means']);bg=[1,1,1] if s=='ficus' else [0,0,0];out=[]
 for v in views:
  p=ROOT/'stageA'/s/v
  if (p/'SEAL.json').exists():checkseal(p);out.append(json.loads((p/'RESULT.json').read_text()));continue
  p.mkdir(parents=True,exist_ok=True);state('STAGE_A_UNIT',scene=s,view=v,children=[os.getpid()],status='RUNNING');signal.alarm(900);start=time.monotonic();c=cam(s,v);raw=npz(rawpath(s,v));rgb=raw['rgb'];alpha=raw['alpha'].squeeze();z=raw['median_camera_z'].squeeze()
  src=render(source,c,bg,floor[:n]);proj=ProjectedSource.from_asset(source,c,s);cal,resp=calibration(s,c,raw,src,proj);del proj
  li=render(ink,c,[1,1,1],floor[n:]);joint=render(a,c,bg,floor);np.savez_compressed(p/'REFERENCE.npz',source_rgb=src['rgb'],source_alpha=src['alpha'],source_center_z=src['median_center_z'],line_rgb=li['rgb'],joint_rgb=joint['rgb'],joint_alpha=joint['alpha'])
  js(p/'CALIBRATION.json',cal);js(p/'SOURCE_CONTRIBUTION_CALIBRATION.json',resp)
  panel(p/'REFERENCE.jpg',[('Frozen input RGB (native RaDe / Ficus CPU)',rgb),('Source-only CPU full SH EWA',src['rgb']),('Original C8 ink only / XRAY',li['rgb']),('TRUE jointly sorted source + original C8',joint['rgb'])],s+' / '+v+' | Outside-in input context','Line assets unchanged. CPU EWA is approximate; source-only input drives subject proposal.',2)
  print('REFERENCE_READY',s,v,flush=True)
  arrays,logs=run_arrays(rgb,alpha,z,c);np.savez_compressed(p/'SUBJECT.npz',**arrays);js(p/'FIT_TRACE.json',logs)
  union=arrays['possible'];inter=arrays['masks'].all(0);iou=float(inter.sum()/max(1,union.sum()));unknown=float((arrays['unknown']&union).sum()/max(1,union.sum()))
  result=dict(scene=s,view=v,role='DEV' if v==DEV[s] else 'AUX' if v==AUX[s] else 'RESERVED_FAILURE_DIAGNOSTIC_OR_VALIDATION',candidate=stats(arrays['candidate']),alpha=stats(arrays['alpha_control']),RGB_alpha=stats(arrays['rgb_alpha_control']),depth_continuous=stats(arrays['depth_control']),seed_IoU=iou,unknown_in_possible=unknown,engineering='GO',numeric_preliminary_GO=bool(.01<arrays['candidate'].mean()<.98 and iou>=.90 and unknown<=.15),visual_gate='AWAITING_ACTUAL_INSPECTION',seconds=time.monotonic()-start,not_semantic_GT=True)
  js(p/'RESULT.json',result);dp,dpr=color_depth(z,alpha);js(p/'DEPTH_DISPLAY.json',dpr)
  seedim=rgb.copy();seedim[arrays['fg_seed']]=[.05,.9,.15];seedim[arrays['bg_seed']]=[.1,.25,1]
  panel(p/'SUBJECT_FULL.jpg',[('Original full-frame RGB',rgb),('Subject proposal (green); UNKNOWN (orange)',overlay(rgb,arrays['candidate'],arrays['unknown'])),('Candidate binary / no hole fill',grey(arrays['candidate'])),('Three automatic seeds: disagreement/uncertainty',grey(arrays['unknown'])),('Automatic seed: FG green / BG blue',seedim),('Original camera-z / display-only range',dp)],s+' / '+v+' | Stage A: whole-subject hypothesis','No C8 evidence in mask. No global camera-z cutoff. Unknown is NOT background.',3)
  panel(p/'CONTROLS_FULL.jpg',[('Original RGB',rgb),('Full-scene alpha >= .5 (NOT object mask)',overlay(rgb,arrays['alpha_control'])),('RGB/alpha baseline (NOT semantic)',overlay(rgb,arrays['rgb_alpha_control'])),('Source depth-continuity flood (NOT semantic)',overlay(rgb,arrays['depth_control'])),('RGB + depth-aware grid-cut proposal',overlay(rgb,arrays['candidate'])),('Mask seed agreement 0..1 (NOT calibrated probability)',grey(arrays['seed_agreement']))],s+' / '+v+' | Stage A controls','Same image, native frame, no line input. Completeness and background intrusion require visual review.',3)
  for name in ['candidate','unknown','possible','alpha_control','rgb_alpha_control','depth_control']:save(p/(name+'.png'),grey(arrays[name]))
  signal.alarm(0);seal(p);out.append(result);print('SUBJECT_READY',s,v,round(result['seconds'],2),flush=True);guard()
 return out

def main():
 import argparse;p=argparse.ArgumentParser();p.add_argument('--phase',choices=['dev','remaining'],required=True);a=p.parse_args();rows=[];fail=[]
 state('STAGE_A_'+a.phase.upper(),children=[os.getpid()])
 for s in SCENES:
  views=[DEV[s]] if a.phase=='dev' else [AUX[s],*RESERVED[s]]
  try:rows+=run(s,views)
  except Exception as e:
   signal.alarm(0);err=dict(scene=s,phase=a.phase,error=repr(e),traceback=traceback.format_exc());js(ROOT/('FAILURE_'+a.phase+'_'+s+'.json'),err);fail.append(err);print(err,flush=True)
 js(ROOT/('EXECUTION_'+a.phase+'.json'),dict(rows=rows,failures=fail,exit_code=1 if fail else 0));state('STAGE_A_'+a.phase.upper()+'_COMPLETE',children=[],failures=[x['scene'] for x in fail],status='READY_FOR_REVIEW' if not fail else 'ENGINEERING_PARTIAL');raise SystemExit(1 if fail else 0)
if __name__=='__main__':main()
