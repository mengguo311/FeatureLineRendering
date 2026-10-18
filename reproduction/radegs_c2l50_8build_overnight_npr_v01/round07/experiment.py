from env import *
from appearance import ARMS,render_mode,color_mode,activate_source
from protocol import authorize_fit,pack,calibrate
from format import read_ply
sys.path.append(str(CODE.parent/'round03'));from density import fit_density,predict
import signal,traceback
CFG=json.loads((R/'CONFIG.json').read_text())
def alarm(*a):raise TimeoutError('600 second unit budget')
signal.signal(signal.SIGALRM,alarm)
def source(s):
 row=reg()[s];p=Path(row['model']);assert sha(p)==row['model_sha256'];ranges=json.loads((ROOT.parent/'c2l50_8build_joint_gs_v01/scenes'/s/'model/RANGES.json').read_text());rec=read_ply(p);a=activate_source(rec,ranges['source']['stop']);return a,dict(count=len(rec),source_path=str(p),sha256=sha(p),raw_positive_inf=int(np.isposinf(rec['opacity']).sum()),has_filter='filter_3D' in rec.dtype.names,SH_shape=list(a['SH'].shape),source_only=True)
def digest(a):return {k:hashlib.sha256(np.ascontiguousarray(v).view(np.uint8)).hexdigest() for k,v in a.items()}
def old(s,v,which=5):
 p=R5/'B'/s/'withdraw_conflict'/('fit' if v in [DEV[s],AUX[s]] else v)/(v+'.npz') if which==5 else R3/'inference'/s/'pooled_rgb'/v/'RESULT.npz'
 return npz(p)
def render_arrays(a,s,v,arm):return render_mode(a,cam(s,v),arm,cam(s,DEV[s]),CFG['render']['bg'][s],CFG['render']['floor_variance'][s])
def rendered(s,v,arm):return npz(R/'renders'/s/v/(arm+'.npz'))
def result(s,v,arm):return npz(R/'inference'/s/arm/v/'RESULT.npz')
def render_view(a,s,v):
 p=R/'renders'/s/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);signal.alarm(600);rawrgb,z,alpha=raw(s,v);ref=npz(V1/'stageA'/s/v/'REFERENCE.npz');before=digest(a);times={};rr={}
 for arm in ARMS:
  t=time.monotonic();x=render_arrays(a,s,v,arm);times[arm]=time.monotonic()-t;assert times[arm]<120,(arm,times);assert np.isfinite(x['rgb']).all();np.savez_compressed(p/(arm+'.npz'),**x);rr[arm]=x
 cal=calibrate(rr['full_sh'],ref,rawrgb,z,alpha)
 for arm in ARMS[1:]:
  for k in ['alpha','median_center_z','expected_center_z']:np.testing.assert_array_equal(rr[arm][k],rr['full_sh'][k])
 if v==DEV[s]:np.testing.assert_array_equal(rr['anchor_sh']['rgb'],rr['full_sh']['rgb'])
 assert digest(a)==before
 stats=dict(scene=s,view=v,seconds=times,calibration=cal,geometry_bitexact=True,source_arrays_unchanged=True,color_vs_full={arm:dict(mae=float(abs(rr[arm]['rgb']-rr['full_sh']['rgb']).mean()),p99=float(np.quantile(abs(rr[arm]['rgb']-rr['full_sh']['rgb']),.99)),above_one=int((rr[arm]['rgb']>1).sum())) for arm in ARMS})
 js(p/'COUNT.json',stats)
 items=[('Original cached RGB | native / CPU proxy',rawrgb)]+[(arm+' | NEW source-only render',rr[arm]['rgb']) for arm in ARMS]+[('DC - full absolute difference x4',np.clip(abs(rr['dc_only']['rgb']-rr['full_sh']['rgb'])*4,0,1)),('Anchor - full difference x4',np.clip(abs(rr['anchor_sh']['rgb']-rr['full_sh']['rgb'])*4,0,1))]
 panel(p/'SOURCE_APPEARANCE.jpg',items,s+' / '+v+' | SH angular-appearance counterfactual','Same geometry, opacity, depth sort, background. DC is NOT recovered albedo. Difference display x4 only.',3);seal(p);signal.alarm(0);print('RENDER',s,v,stats,flush=True)
def seed_data(s,arm):
 authorize_fit(s,[DEV[s],AUX[s]],3 if s=='ficus' else 2);data=[];seeds={}
 for v in [DEV[s],AUX[s]]:
  sd=npz(R3/'models'/s/'pooled_rgb'/(v+'_SEEDS.npz'));uv=sd['uv'];rgb=rendered(s,v,arm)['rgb'];x=rgb[uv[:,1],uv[:,0]];data.append((x,sd['labels']));seeds[v]=dict(uv=uv,labels=sd['labels'],rgb=x)
 return data,seeds
def fit_model(s,arm):
 p=R/'models'/s/arm
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);data,seeds=seed_data(s,arm);m=fit_density(data,3 if s=='ficus' else 2);np.savez_compressed(p/'MODEL.npz',**m)
 for v,x in seeds.items():np.savez_compressed(p/(v+'_SEEDS.npz'),**x)
 js(p/'COUNT.json',dict(scene=s,arm=arm,fit_views=[DEV[s],AUX[s]],classes=int(m['classes']),threshold=m['threshold'].tolist(),seed_counts={v:np.bincount(x['labels']).tolist() for v,x in seeds.items()},new_GT=False));seal(p)
def infer_arrays(s,v,arm):
 b=old(s,v,3);m=b['inference_mask'];u=b['unknown']&~m;rgb=rendered(s,v,arm)['rgb'];model=npz(R/'models'/s/arm/'MODEL.npz');l,q,d=predict(model,rgb[m]);out=pack(m,u,l,q);out['density']=d;return out
def infer(s,v,arm):
 p=R/'inference'/s/arm/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);a=infer_arrays(s,v,arm);np.savez_compressed(p/'RESULT.npz',**a);m=a['inference_mask'];b=old(s,v,3)
 row=dict(scene=s,view=v,arm=arm,mask_pixels=int(m.sum()),counts=np.bincount(a['labels'][m],minlength=4 if s=='ficus' else 3).tolist(),unknown=int((m&(a['labels']==0)).sum()),change_from_r03=int((m&(a['labels']!=b['labels'])).sum()),known_change_from_r03=int((m&(a['labels']>0)&(b['labels']>0)&(a['labels']!=b['labels'])).sum()));js(p/'COUNT.json',row);seal(p);print('INFER',row,flush=True)
def figure(s,v):
 p=R/'figures'/s/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);rgb,_,_=raw(s,v);ref=npz(V1/'stageA'/s/v/'REFERENCE.npz');items=[('Original cached RGB',rgb)]
 for arm in ARMS:
  a=result(s,v,arm);items.append((arm+' likelihood | fixed mask/seeds',colors(rgb,a['labels'],a['unknown'])))
 prev=old(s,v);items.append(('r05 graph | strong historical context',colors(rgb,prev['labels'],prev['unknown'])));b=old(s,v,3);items.append(('r03 raw RGB | historical reference',colors(rgb,b['labels'],b['unknown'])))
 legend='Blue pot-prior; orange wood-prior; green crown-prior; gray UNKNOWN.' if s=='ficus' else 'Blue foreground-prior; orange background-prior; gray UNKNOWN. NOT roof/wall or skull parts.'
 panel(p/'FULL.jpg',items,s+' / '+v+' | r07 appearance-controlled likelihood',legend+' Diagnostic overlays, NOT styled GS.',3)
 panel(p/'CONTEXT.jpg',[('Original cached RGB',rgb),('Original C8 ink | XRAY reference',ref['line_rgb']),('Original TRUE joint | frozen CPU EWA',ref['joint_rgb'])],s+' / '+v+' | Immutable context','No C8 pixels/GS were used to construct these source-only color counterfactuals.',3);seal(p)
def run(s,vv,fit=False):
 a,info=source(s);p=R/'sources'/s
 if not (p/'SEAL.json').exists():
  p.mkdir(parents=True,exist_ok=True);js(p/'SOURCE.json',info);np.savez_compressed(p/'COLOR_PROVENANCE.npz',source_index=np.arange(info['count'],dtype=np.int32),dc_color=color_mode(a,cam(s,DEV[s]),'dc_only'),anchor_color=color_mode(a,cam(s,DEV[s]),'anchor_sh',cam(s,DEV[s])));seal(p)
 for v in vv:guard();render_view(a,s,v)
 del a
 if fit:
  for arm in ARMS:fit_model(s,arm)
 if all((R/'models'/s/arm/'SEAL.json').exists() for arm in ARMS):
  for v in vv:
   for arm in ARMS:infer(s,v,arm)
   figure(s,v)
def main():
 import argparse;p=argparse.ArgumentParser();p.add_argument('--phase',choices=['pilot','fit','reserved'],required=True);a=p.parse_args();status('RUN_'+a.phase,children=[os.getpid()]);failed=[]
 if a.phase=='reserved':assert (R/'reviews/03_reserved_GO.md').exists()
 for s in (['ficus'] if a.phase=='pilot' else ['ficus','scan24','scan65']):
  try:run(s,[DEV[s]] if a.phase=='pilot' else [DEV[s],AUX[s]] if a.phase=='fit' else RES[s],a.phase=='fit')
  except Exception as e:
   signal.alarm(0);failed.append(s);js(R/('ENGINEERING_'+s+'_'+a.phase+'.json'),dict(error=repr(e),traceback=traceback.format_exc()));print(traceback.format_exc(),flush=True)
 status('DONE_'+a.phase,children=[],failed=failed);raise SystemExit(bool(failed))
if __name__=='__main__':main()
