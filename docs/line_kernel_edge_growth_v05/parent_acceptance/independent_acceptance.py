"""Read-only final acceptance, not a fitting or science runner.
Writes only orchestration/parent_acceptance, preserving every closed unit.
"""
import os,sys
sys.dont_write_bytecode=True
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='2'
os.environ['CUDA_VISIBLE_DEVICES']=''
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
from pathlib import Path
import json,hashlib,datetime,time,ast,ctypes,shutil,zipfile,traceback
import numpy as np
from PIL import Image
from acceptance_math import project,interval_union
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031');R=O/'orchestration';A=R/'parent_acceptance';START=time.time();END=datetime.datetime.fromisoformat('2026-10-31T12:43:00+09:00').timestamp();A.mkdir(exist_ok=True)
def read(p):return json.loads(Path(p).read_text())
def dump(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def guard():
 if time.time()>END:raise TimeoutError('Parent acceptance absolute bound')
 if shutil.disk_usage('/').free<2**30 or shutil.disk_usage('/mnt/hdd1').free<10*2**30:raise RuntimeError('parent acceptance free-space bound')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
HASHES={}
def checked(p,h):
 p=Path(p).resolve();assert isinstance(h,str) and len(h)==64,(str(p),h)
 if str(p) not in HASHES:HASHES[str(p)]=sha(p)
 assert HASHES[str(p)]==h,('SHA mismatch',str(p),h,HASHES[str(p)])
 return HASHES[str(p)]
def close(x,y,label):
 if not np.allclose(x,y,rtol=2e-8,atol=2e-7):raise AssertionError((label,np.asarray(x).tolist(),np.asarray(y).tolist()))
def piece(c,i,name):return c[name][c[{'knots':'knot_offsets','rows':'row_offsets','seedlets':'seed_offsets','supported_intervals':'interval_offsets'}[name]][i]:c[{'knots':'knot_offsets','rows':'row_offsets','seedlets':'seed_offsets','supported_intervals':'interval_offsets'}[name]][i+1]]
def support(reps,q,r):return interval_union(project(r['endpoints'][reps].reshape(-1,3),q)[0].reshape(-1,2))
def palette(ids):
 h=(ids.astype(np.int64)*2654435761)%4294967296;c=np.stack([.12+.72*((h>>s)&255)/255 for s in (0,8,16)],1);c[ids<0]=.68;return c

def main():
 summary=read(R/'FINAL_SUMMARY.json');delivery=read(O/'DELIVERY_STATUS.json');records=summary['reported_units'];assert len(records)==19==delivery['reported_units_count'];assert summary['execution_state']=='FINISHED' and not Path('/proc',str(summary['pid'])).exists();assert not summary.get('child_pid')
 sys.path.insert(0,str(R));import supervisor as sup;sup.protection(check_runtime=False)
 result={'scope':'independent read-only data/contract/raster replay; not physical-edge ground truth','started_jst':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'stop_classification':'administrative no-new-unit cutoff, not scientific exhaustion','original_stop_string':summary['reason'],'units':[],'scenes':[],'limitations':['No independent physical-edge labels','Branch/parallel/depth safety not certified by these numeric checks','No held-out generalization or temporal test','No fitting/rerunning production science','Derived archives preserve source attributes; colors remain separate visualization data']}
 original={};png_seen=set();png_paths=0;sealed_entries=0;all_maps=0
 for rec in records:
  guard();U=Path(rec['output']);D=R/U.name;f=read(U/'PARENT_RUN_FROZEN.json');cfg=read(U/'CONFIG.json');ce=read(D/'COMPUTE_EXIT.json');assert ce['returncode']==0 and ce['reason'] is None and ce['actual_child_exit'];assert ce==read(U/'PARENT_COMPUTE_RECEIPT.json');checked(U/'DECISION.json',f['decision_sha256']);checked(U/'CONFIG.json',f['config_sha256']);assert cfg['decision_sha256']==f['decision_sha256']
  for src,h in f['source_files'].items():checked(f['immutable_source_snapshot'][src],h)
  for src,h in f['helper_files'].items():checked(src,h)
  for name,h in read(U/'PARENT_SEAL.json')['files'].items():
   p=(U/name).resolve();assert p.is_relative_to(U.resolve());checked(p,h);sealed_entries+=1
   if p.suffix.lower()=='.png':
    png_paths+=1
    if h not in png_seen:
     with Image.open(p) as im:im.load();assert im.width>0 and im.height>0
     png_seen.add(h)
  scene=cfg['scene'];src=Path(cfg['gaussians'])
  if scene not in original:
   original[scene]=dict(np.load(src,allow_pickle=False));checked(src,cfg['input_files'][str(src)])
  a=original[scene];N=len(a['means']);maps=[]
  for p in sorted(U.rglob('MEMBERSHIP.npz')):
   m=dict(np.load(p,allow_pickle=False));assert np.array_equal(m['line_kernel_id'],np.arange(N));assert m['edge_id'].shape==(N,);assert np.array_equal(m['primitive_id'],a['primitive_id']);assert np.all(m['edge_id']>=-1);assert not np.any((m['edge_id']>=0)&(m['reason_code']!=0));assert np.all(m['provisional'])
   metrics=read(p.parent/'METRICS.json') if (p.parent/'METRICS.json').exists() else None;counts={'assigned':int(np.count_nonzero(m['edge_id']>=0)),'UNKNOWN':int(np.count_nonzero(m['edge_id']<0)),'groups':len(np.unique(m['edge_id'][m['edge_id']>=0]))}
   if metrics:
    for k,n in counts.items():assert metrics[k]==n,(str(p),k)
   maps.append(dict(path=str(p),**counts));all_maps+=1
  assert len(maps)==rec['membership_files'];result['units'].append({'unit':rec['unit'],'actual_compute_exit':ce,'source_snapshot_files':len(f['source_files']),'tdd_status':f['tdd_status'],'memberships':maps});print('VERIFIED_UNIT',rec['unit'],flush=True)
 result.update(parent_seal_entries_verified=sealed_entries,png_paths_integrity_checked=png_paths,png_distinct_encodings_decoded=len(png_seen),membership_maps_verified=all_maps)
 for item in delivery['latest_saved_scene_assets']:
  guard();scene=item['scene'];U=O/'units'/item['unit'];P=Path(item['directory']);cfg=read(U/'CONFIG.json');a=original[scene];m=dict(np.load(P/'MEMBERSHIP.npz'));c=dict(np.load(P/'CARRIERS.npz'));gg=read(P/'GROUPS.json');groups=gg['groups'];p=gg['p'];r=dict(np.load(cfg['representatives']));r['endpoints']=r['endpoints']/p;metrics=read(P/'METRICS.json');previous=dict(np.load(cfg['previous_membership']));pc=dict(np.load(cfg['previous_carriers']));pi={int(cid):i for i,cid in enumerate(pc['carrier_id'])};ci={int(cid):i for i,cid in enumerate(c['carrier_id'])};N=len(m['edge_id'])
  owner=np.full(N,-1,np.int64)
  for i,cid in enumerate(c['carrier_id']):
   rows=piece(c,i,'rows');assert np.all(owner[rows]<0);owner[rows]=cid
  assert np.array_equal(owner,m['carrier_id']);assert np.array_equal(np.sort(c['rows']),np.flatnonzero(np.load(cfg['representatives'])['kernel_rep']>=0))
  geo=read(P/'GEOMETRY_AUDIT.json')
  for k,v in geo['all_original_noncolor_fields'].items():assert hashlib.sha256(a[k].tobytes()).hexdigest()==v['sha256'] and str(a[k].dtype)==v['dtype'] and list(a[k].shape)==v['shape']
  with np.load(cfg['controls']) as z:t=(z['control'][z['control_index']]*z['derivative_basis'][:,:,None]).sum(1)
  norm=np.linalg.norm(t,axis=1);t=t/np.maximum(norm[:,None],1e-15)
  prior_support={};recomputed=[];new_checks=[];support_maxerr=0.;outward_maxerr=0.
  for g in groups:
   cid=g['edge_id'];i=ci[cid];rows=piece(c,i,'rows');reps=piece(c,i,'seedlets');q=piece(c,i,'knots')/p;assert np.all(m['edge_id'][rows]==cid) and len(rows)==g['kernels'];iv,length,run,gap,total=support(reps,q,r);close(iv,piece(c,i,'supported_intervals')/p,(scene,cid,'saved union'));close([length,run,gap,total],[g[k] for k in ['supported_length_p','longest_continuous_run_p','max_gap_p','total_gap_p']],(scene,cid,'interval stats'));support_maxerr=max(support_maxerr,abs(length-g['supported_length_p']))
   parent_ids,parent_n=np.unique(a['primitive_id'][rows],return_counts=True);assert list(zip(parent_ids.tolist(),parent_n.tolist()))==[(z['parent'],z['kernels']) for z in g['parent_contributions']]
   pred=gg['immediate_predecessor'];parts=g[pred+'_contributions'];ownparts=[]
   for part in parts:
    j=pi[part['carrier_id']];oldrep=piece(pc,j,'seedlets');oldq=piece(pc,j,'knots')/p
    if j not in prior_support:prior_support[j]=support(oldrep,oldq,r)[1]
    prior=prior_support[j];dom=project(oldq,q)[0];lo,hi=float(dom.min()),float(dom.max());outside=sum(max(0.,min(float(b),lo)-float(a0))+max(0.,float(b)-max(float(a0),hi)) for a0,b in iv);close(prior,part['supported_length_p'],(scene,cid,'predecessor length'));close(outside,part['support_outside_domain_p'],(scene,cid,'outside domain'));ownparts.append(dict(cid=part['carrier_id'],length=prior,kernels=len(piece(pc,j,'rows')),outside=outside))
   ownparts.sort(key=lambda z:(-z['length'],z['cid']));largest=ownparts[0];gain=length-largest['length'];outward=largest['outside'];gate=gain>=max(4.,.25*largest['length']) and sum(z['kernels']>=6 and z['length']>=2 for z in ownparts)>=2 and outward>1e-8;assert gate==g['growth_gate'];close(gain,g['gain_over_largest_'+pred+'_p'],(scene,cid,'gain'));close(outward,g['outward_support_p'],(scene,cid,'outward'));outward_maxerr=max(outward_maxerr,abs(outward-g['outward_support_p']))
   unchanged=cid in pi and c['version'][i]==pc['version'][pi[cid]]
   if not unchanged:
    _,resid,qt=project(a['means'][rows]/p,q);angles=np.degrees(np.arccos(np.clip(np.abs(np.sum(t[rows]*qt,axis=1)),0,1)));rm=float(resid.max());rq=float(np.quantile(resid,.95));ta=float(angles.max());new_checks.append({'edge_id':cid,'residual_max_p':rm,'residual_q95_p':rq,'tangent_max_deg':ta,'numeric_contract_ok':bool(rm<=1+1e-7 and rq<=.5+1e-7 and ta<=30+1e-6)})
   if gate:recomputed.append({'edge_id':cid,'support_p':length,'longest_run_p':run,'total_gap_p':total,'outward_p':outward,'gain_p':gain,'model':g['model'],'eligible_new_growth':g.get('eligible_new_growth',True),'inherited_dispute':g.get('inherited_dispute',False),'substantial_original_parents':g.get('substantial_original_parents'),'substantial_L1_fragments':g.get('substantial_L1_fragments')})
  assert {g['edge_id'] for g in recomputed}==set(metrics['growth_gate_groups']);lost=int(np.count_nonzero((previous['edge_id']>=0)&(m['edge_id']<0)));assert lost==0
  pairs=np.unique(np.c_[previous['edge_id'][previous['edge_id']>=0],m['edge_id'][previous['edge_id']>=0]],axis=0);oldid,oldn=np.unique(pairs[:,0],return_counts=True);splits=int(np.count_nonzero(oldn>1));assert splits==0
  display=read(P/'DISPLAY_SOURCE.json');cols=np.load(P/'DISPLAY_COLORS.npz')['colors'];assert np.array_equal(cols,palette(m['edge_id']));checked(display['camera_source'],display['camera_sha256']);cams=read(display['camera_source']);cams=cams[scene] if isinstance(cams,dict) and scene in cams else cams
  ns={'np':np,'ctypes':ctypes,'ROOT':Path(cfg['libroot']),'_lib':None,'Path':Path};tree=ast.parse(Path(cfg['renderer']).read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'colors','project_cov','render'}];assert len(nodes)==3;exec(compile(ast.Module(body=nodes,type_ignores=[]),cfg['renderer'],'exec'),ns)
  asset={k:a[k] for k in ('means','covariance','opacity')};asset['colors']=cols;replays=[]
  for view in cfg.get('views',['test_r_1','test_r_79'] if scene=='ficus' else ['0012','0036']):
   guard();cam=next(v for v in cams if v['view']==view and v.get('scene',scene)==scene);rgb=ns['render'](asset,cam,tuple(display['background']),display['floor'])['rgb'];actual=np.uint8(np.rint(np.clip(rgb,0,1)*255));stored=np.asarray(Image.open(P/(view+'_FULL.png')).convert('RGB'));assert np.array_equal(actual,stored),(scene,view,int(np.abs(actual.astype(int)-stored).max()));replays.append({'view':view,'RGB8_bitexact':True,'width':int(actual.shape[1]),'height':int(actual.shape[0])})
  out=A/'assets'/scene;out.mkdir(parents=True,exist_ok=False);payload=dict(a);payload.update(line_kernel_id=m['line_kernel_id'],edge_id=m['edge_id'],reason_code=m['reason_code'],provisional=m['provisional']);np.savez_compressed(out/'CANONICAL_WITH_EDGE_IDS.npz',**payload)
  with np.load(out/'CANONICAL_WITH_EDGE_IDS.npz') as z:
   for k,v in a.items():assert z[k].dtype==v.dtype and z[k].shape==v.shape and z[k].tobytes()==v.tobytes()
   assert np.array_equal(z['edge_id'],m['edge_id'])
  for n in ['MEMBERSHIP.npz','CARRIERS.npz','GROUPS.json','METRICS.json','LINEAGE.json','DISPLAY_COLORS.npz','DISPLAY_SOURCE.json','GEOMETRY_AUDIT.json','REASON_SCHEMA.json']:
   if (P/n).exists():shutil.copy2(P/n,out/n)
  for z in replays:shutil.copy2(P/(z['view']+'_FULL.png'),out/(z['view']+'_FULL.png'))
  violations=[z for z in new_checks if not z['numeric_contract_ok']];record={'scene':scene,'unit':item['unit'],'level':item['level'],'kernel_count':N,'assigned':int(np.count_nonzero(m['edge_id']>=0)),'UNKNOWN':int(np.count_nonzero(m['edge_id']<0)),'coverage_percent':float(np.mean(m['edge_id']>=0)*100),'groups':len(groups),'primary_groups_interval_and_growth_recomputed':len(groups),'max_support_stat_error_p':support_maxerr,'max_outward_error_p':outward_maxerr,'modified_primary_groups_geometry_checked':len(new_checks),'modified_numeric_contract_violations':violations,'incumbent_rows_lost':lost,'incumbent_groups_split':splits,'growth_groups':recomputed,'native_full_frame_replays':replays,'original_fields_bitexact_in_delivery':list(a),'original_npz_sha256':sha(cfg['gaussians']),'output_asset':str(out/'CANONICAL_WITH_EDGE_IDS.npz'),'physical_identity_verified':False,'all_groups_provisional':True}
  result['scenes'].append(record);dump(A/(scene+'_INDEPENDENT_GEOMETRY.json'),record);dump(out/'INDEPENDENT_ACCEPTANCE.json',record);print('VERIFIED_SCENE',scene,'groups',len(groups),'new_geometry_checks',len(new_checks),'numeric_violations',len(violations),flush=True)
 sup.protection(check_runtime=False)
 result.update(completed_jst=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),elapsed_seconds=time.time()-START,old_inputs_worktrees_and_seals_unchanged=True,structural_acceptance='PASS',scientific_verdict='PARTIAL; physical identity and complete visual/safety acceptance not established',distinct_source_files_hashed=len(HASHES))
 dump(A/'PARENT_INDEPENDENT_ACCEPTANCE.json',result);dump(A/'HASH_READBACK.json',HASHES);print('PARENT_ACCEPTANCE_SAVED',str(A/'PARENT_INDEPENDENT_ACCEPTANCE.json'),flush=True)
if __name__=='__main__':
 try:main()
 except BaseException as exc:
  dump(A/'PARENT_ACCEPTANCE_FAILURE.json',{'error':repr(exc),'traceback':traceback.format_exc(),'elapsed_seconds':time.time()-START});raise
