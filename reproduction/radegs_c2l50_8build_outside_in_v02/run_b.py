from env import *
from regions import *
import signal
def timeout(*a):raise TimeoutError('unit900s')
signal.signal(signal.SIGALRM,timeout)
def load_model(p):
 m=npz(p)
 for k in ['arm']:m[k]=str(m[k])
 for k in ['k','iterations','sample_count']:m[k]=int(m[k])
 for k in ['scale','reference_p','inertia']:m[k]=float(m[k])
 return m
def draw_v1(rgb,lab):
 rng=np.random.default_rng(1729);pal=rng.uniform(.12,.95,(int(lab.max())+1,3));x=rgb.copy();on=lab>0;x[on]=.32*x[on]+.68*pal[lab[on]];return x
def fit(s):
 q=ROOT/'stageB'/s/'models';q.mkdir(parents=True,exist_ok=True)
 if (q/'SEAL.json').exists():checkseal(q);return
 two=[view_samples(s,v,B['max_samples_per_view']) for v in [DEV[s],AUX[s]]];n=min(len(r['world']) for r in two)
 for r in two:
  ids=np.linspace(0,len(r['world'])-1,n,dtype=int)
  for key in r:r[key]=r[key][ids]
 data={k:np.concatenate([r[k] for r in two]) for k in two[0]};data['view_id']=np.repeat([0,1],n).astype(np.int16);np.savez_compressed(q/'TRAIN_OBSERVATIONS.npz',**data);rows=[]
 for k in [B['k_primary'],B['k_diagnostic']]:
  for arm in B['arms']:
   t=time.monotonic();signal.alarm(900);m=fit_model(data['world'],data['rgb'],data['width'],k,arm,data['pixel_scale']);np.savez_compressed(q/f'{arm}_k{k}.npz',**m);rows.append(dict(arm=arm,k=k,samples=len(data['world']),per_view=n,inertia=m['inertia'],iterations=m['iterations'],seconds=time.monotonic()-t));signal.alarm(0);print('FIT',rows[-1],flush=True)
 js(q/'COUNTS.json',rows);seal(q)
def runviews(s,vs):
 q=ROOT/'stageB'/s
 for v in vs:
  guard();p=q/v
  if (p/'SEAL.json').exists():checkseal(p);continue
  p.mkdir(exist_ok=True);rgb,z,a=raw(s,v);ref=npz(V1/'stageA'/s/v/'REFERENCE.npz');old=npz(V1/'stageA'/s/v/'SUBJECT.npz');v1rgb=npz(V1/'stageB'/s/v/'rgb_only.npz')['levels'][-1];rows=[];results={}
  for k in [B['k_primary'],B['k_diagnostic']]:
   for arm in B['arms']:
    signal.alarm(900);m=load_model(q/'models'/f'{arm}_k{k}.npz');r=predict_view(s,v,m);np.savez_compressed(p/f'{arm}_k{k}.npz',**r);results[(arm,k)]=r;mask=npz(ROOT/'stageA'/s/v/'SUBJECT.npz')['candidate'];cnt=np.bincount(r['labels'].ravel(),minlength=k+1);rows.append(dict(arm=arm,k=k,scene=s,view=v,region_counts=cnt[1:].tolist(),subject_pixels=int(mask.sum()),unknown_subject=int((mask&(r['labels']==0)).sum()),unknown_fraction=float((mask&(r['labels']==0)).sum()/max(mask.sum(),1)),outside_observed_neighborhood=int((~r['observed_neighborhood']).sum())));signal.alarm(0)
  main=results[(B['arms'][0],3)];panel(p/'PRIMARY.jpg',[('Original frozen source RGB',rgb),('Original C8 ink | XRAY reference',ref['line_rgb']),('TRUE joint source + C8 (read-only CPU reference)',ref['joint_rgb']),('v01 whole-subject proxy (one block)',overlay(rgb,old['candidate'],old['unknown'])),('v01 RGB-only hierarchy (different, larger budget)',draw_v1(rgb,v1rgb)),('v02 JOINT XYZ/Lab/width | K=3 + UNKNOWN',colors(rgb,main['labels'],main['unknown']))],s+' / '+v+' | Real coarse-region candidates','Shared model fitted on DEV+AUX. Grey: unknown. Same color is NOT proof of semantic part identity. No line input.',3)
  panel(p/'PAIRED_ARMS.jpg',[(arm+' | K='+str(k),colors(rgb,results[(arm,k)]['labels'],results[(arm,k)]['unknown'])) for k in [3,5] for arm in B['arms']],s+' / '+v+' | Matched K and training-sample budget','Columns: XYZ/Lab/width, RGB-only, XYZ-only. Top K=3 primary; bottom K=5 predeclared diagnostic. Native complete frame.',3)
  for k in [3,5]:
   main=results[(B['arms'][0],k)];panel(p/f'ID_AND_UNKNOWN_K{k}.jpg',[('Source RGB',rgb),('v02 shared coarse regions',colors(rgb,main['labels'])),('UNKNOWN incl ambiguous / unseen (white)',grey(main['unknown'])),('Maximum soft assignment (NOT calibrated probability)',grey(main['probability'].max(2)))],s+' / '+v+' | K='+str(k)+' assignment diagnostics','Do not equate region count with semantic quality. Subject negative spaces are retained.',2)
  js(p/'COUNTS.json',rows);seal(p);print('B_VIEW',v,rows[0],flush=True)
def evaluate(s,targets):
 p=ROOT/'stageB'/s/'matches';p.mkdir(exist_ok=True);rows=[]
 for arm in B['arms']:
  for k in [3,5]:
   for tv in targets:
    name=arm+'_k'+str(k)+'_'+tv;dest=p/name
    if (dest/'SEAL.json').exists():checkseal(dest);rows.append(json.loads((dest/'COUNTS.json').read_text()));continue
    dest.mkdir(exist_ok=True);lab=npz(ROOT/'stageB'/s/DEV[s]/f'{arm}_k{k}.npz')['labels'];tlab=npz(ROOT/'stageB'/s/tv/f'{arm}_k{k}.npz')['labels'];ab,rr,ar=match(s,DEV[s],tv,lab,tlab);ba,tt,br=match(s,tv,DEV[s],tlab,lab);pairs=mutual_pairs(ab,ba);row=dict(arm=arm,k=k,source=DEV[s],target=tv,mutual_pairs=pairs,forward=rr,reverse=tt,colors_not_evidence=True);np.savez_compressed(dest/'FORWARD.npz',**ar);np.savez_compressed(dest/'REVERSE.npz',**br);js(dest/'COUNTS.json',row);seal(dest);rows.append(row);print('MATCH',arm,k,tv,pairs,flush=True)
 return rows
def main():
 import argparse;p=argparse.ArgumentParser();p.add_argument('--phase',choices=['fit','reserved'],required=True);args=p.parse_args();g=json.loads((ROOT/'STAGE_A_GATE.json').read_text());s='ficus';assert g['scenes'][s]['stageA']=='GO_PROXY';assert all(g['scenes'][x]['stageB']=='NOT_RUN' for x in ['scan24','scan65']);state('STAGE_B_'+args.phase.upper(),children=[os.getpid()])
 if args.phase=='fit':fit(s);runviews(s,[DEV[s],AUX[s]]);rows=evaluate(s,[AUX[s]])
 else:runviews(s,RES[s]);rows=evaluate(s,RES[s])
 js(ROOT/f'B_{args.phase.upper()}_COUNTS.json',rows);state('STAGE_B_'+args.phase.upper()+'_DONE',children=[])
if __name__=='__main__':main()
