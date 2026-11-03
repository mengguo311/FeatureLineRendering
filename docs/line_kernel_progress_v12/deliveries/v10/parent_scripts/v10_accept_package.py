from pathlib import Path
import json,hashlib,subprocess,os,time,zipfile,io,collections,sys
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='2'
if hasattr(os,'sched_setaffinity'):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
import numpy as np
from PIL import Image
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103');R=O/'orchestration';A=R/'parent_acceptance/final_0542';A.mkdir(exist_ok=True)
def load(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def save(n,d):
 (A/n).write_text(json.dumps(d,ensure_ascii=False,indent=2,default=lambda x:int(x) if isinstance(x,np.integer) else x.tolist())+'\n')
def log(s):print(s,flush=True)
D=load(O/'DELIVERY_STATUS.json');audit={'scope':'read-only saved-output acceptance; no fit/render/model resumed','issues':[],'units':[],'continuation_exists':(R/'PARENT_CONTINUATION.json').exists()};files={};figs=[]
def add(p):
 p=Path(p)
 if p.is_file():files[str(p)]=p
log('START')
for name in ['DELIVERY_STATUS.json','FINAL_REPORT_ZH.md','WINDOW_RESULT.json']:add(O/name)
for n in ['WINDOW.json','BRIEF.md','JOB_REGISTRATION.json','INPUT_LOCK.json','INHERITED_SOURCE_LOCK.json']:add(R/n)
asset={}
for p,z in D['original_assets_verified'].items():
 add(p);assert sha(p)==z['sha256']
 if z['role']=='gaussians':
  scene=Path(p).parts[-3];asset[scene]=dict(np.load(p,allow_pickle=False))
# Audit immutable historical refs; every comparison remains read-only.
start=time.monotonic();protect={}
for name in ['PROTECTED_BEFORE.json','INHERITED_SOURCE_LOCK.json','PROTECTED_REFERENCE_FILES.json']:
 d=load(R/name);bad=[];count=0
 for p,v in d.items():
  if name=='PROTECTED_BEFORE.json':
   now={'head':subprocess.check_output(['git','--no-optional-locks','-C',p,'rev-parse','HEAD'],text=True).strip(),'status':subprocess.check_output(['git','--no-optional-locks','-C',p,'status','--porcelain'],text=True)};okay=now==v
  else:okay=Path(p).is_file() and sha(p)==v
  count+=1
  if not okay:bad.append(p)
 protect[name]={'expected':len(d),'checked':count,'mismatches':bad};log(name+' '+str(count)+' mismatch='+str(len(bad)))
 audit['protection']=protect;save('PROTECTION.json',protect)
# Auxiliary background provenance closure; byte copies, no model fitting.
seen=set()
def dependency(p,depth=0):
 p=Path(p)
 if depth>18 or str(p) in seen or not p.exists():return
 seen.add(str(p))
 if p.is_dir():
  for n in ['CHECKPOINT.json','MEMBERSHIP.npz','MODELS.npz','GROUPS.json','LINEAGE.json','GROWTH_STATE.json','CARRIERS.npz','STATE.pkl','CONFIG.json']:dependency(p/n,depth+1)
 elif p.is_file():
  add(p)
  if p.suffix=='.json' and p.name in ['GROUPS.json','CONFIG.json']:
   d=load(p)
   for k,v in d.items():
    if isinstance(v,str) and v.startswith('/') and k in ['unchanged_background','initial_stage','restore_stage','raw_config','state','carriers','membership','gaussians','controls','representatives','cameras','m4_membership','predecessor_config','predecessor_checkpoint','groups','lineage','renderer']:dependency(v,depth+1)
for u in sorted((O/'units').iterdir()):
 scene='scan24' if (u/'scenes/scan24').exists() else 'scan65';n=len(asset[scene]['means']);info={'unit':u.name,'scene':scene,'rows':n,'checkpoints':0,'mapping_count':0,'libraries':0,'rank_checks':0,'incomplete_libraries':0,'finals':[],'errors':[]}
 for p in u.glob('*'):
  if p.is_file():add(p)
 for p in (u/'source_snapshot').rglob('*'):add(p)
 for p in (u/'tests').rglob('*'):add(p)
 c=load(u/'CONFIG.json');dependency(u/'CONFIG.json')
 ga=load(u/'GEOMETRY_AUDIT.json');info['seven_arrays_before_after_equal']=ga['fields_before']==ga['fields_after'];info['actual_array_digests']={k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in asset[scene].items()};info['saved_geometry_hashes']=ga['fields_before']
 # seal check and all full-row maps including every accepted transaction checkpoint
 for cp in sorted(u.glob('scenes/*/stages/*/CHECKPOINT.json')):
  dd=load(cp);st=cp.parent;info['checkpoints']+=1
  for name,h in dd['files'].items():
   if sha(st/name)!=h:info['errors'].append('checkpoint_sha '+str(st/name))
  with np.load(st/'MEMBERSHIP.npz',allow_pickle=False) as m:
   if not np.array_equal(m['line_kernel_id'],np.arange(n)):info['errors'].append('row_order '+str(st))
   if not np.array_equal(m['primitive_id'],asset[scene]['primitive_id']):info['errors'].append('parent_ids '+str(st))
   info['mapping_count']+=1
   if st.name.endswith('_FINAL'):
    ids,cnt=np.unique(m['edge_id'][m['edge_id']>=0],return_counts=True);ii=np.argmax(cnt);info['finals'].append({'stage':str(st.relative_to(O)),'assigned':int(np.sum(m['edge_id']>=0)),'unknown':int(np.sum(m['edge_id']<0)),'largest_id':int(ids[ii]),'largest_count':int(cnt[ii])})
  if st.name in ['START','NO_FURTHER_GROWTH'] or st.name.endswith('_FINAL'):
   for p in st.iterdir():add(p)
 # Independently verify the selected index is globally lowest finite saved eligible score.
 for p in u.glob('scenes/*/libraries/*/*/LIBRARY.json'):
  lib=load(p);info['libraries']+=1
  if not lib['complete']:
   info['incomplete_libraries']+=1
   if lib.get('selected') is not None:info['errors'].append('incomplete selected '+str(p))
  pick=lib.get('selected');records=lib['records']
  if pick is not None:
   eligible=[(r['metrics']['score'],i) for i,r in enumerate(records) if r.get('connectable')]
   if not eligible or abs(records[pick]['metrics']['score']-min(x[0] for x in eligible))>1e-12:info['errors'].append('not_minimum '+str(p))
   if not np.isfinite(records[pick]['metrics']['score']):info['errors'].append('nonfinite '+str(p))
   info['rank_checks']+=1
 # Actual model read-only phase receipts, decisions and exits.
 for p in (R/u.name).rglob('*.json'):
  if p.name in ['LAUNCH.json','EXIT.json','COMPUTE_EXIT.json','COMPUTE_START.json','REVIEW_RECEIPT.json','VALIDATED_RUN_REQUEST.json','READ_ONLY_BEFORE.json','READ_ONLY_AFTER.json']:add(p)
 ex=load(R/u.name/'COMPUTE_EXIT.json');info['actual_compute_exit']=ex
 info['failure_analysis']=load(u/'FAILURE_ANALYSIS.json');info['status']=load(u/'STATUS.json')
 for s in D['units']:
  if s['unit']==u.name:
   for rel in s.get('recorded_observed_images',[]):
    p=O/rel
    if p.is_file():
     add(p);figs.append(rel)
 # all whole-frame FINAL images and top diagnostic examples selected by existing recorded images
 audit['units'].append(info);log(u.name+' maps='+str(info['mapping_count'])+' ranks='+str(info['rank_checks'])+' errors='+str(len(info['errors'])))
 audit['issues']+=info['errors']
# Collect all final/START inputs closure, including legacy NPZ/STATE but do not execute old code.
for rel in D['latest_cold_loadable'].values():dependency(O/rel)
for name in ['finalization_0/EXIT.json','parent_acceptance/PARENT_SUPERVISOR_EXIT_READBACK.json']:add(R/name)
audit['original_asset_shapes']={s:{k:list(v.shape) for k,v in z.items()} for s,z in asset.items()}
audit['all_intermediate_evidence_included']=False
audit['omissions']='Full intermediate candidate libraries, intermediate checkpoint arrays and all unselected PNGs remain unchanged server-side; included all unit reports/configs/frozen source snapshots, all START/final checkpoints, selected real observed PNGs, original kernel/control/representative/camera bytes, dependency auxiliary models.'
audit['elapsed_seconds']=time.monotonic()-start
save('AUDIT.json',audit);add(A/'AUDIT.json');add(A/'PROTECTION.json');save('FIGURES.json',sorted(set(figs)));add(A/'FIGURES.json')
# Package exact source member bytes in distinct per-part manifest ZIPs (<45 MB compressed target).
entries=[];names={}
for source,p in sorted(files.items()):
 name='v10/'+str(p.relative_to(O)) if p.is_relative_to(O) else 'dependencies/'+str(p).lstrip('/')
 if name.casefold() in names and names[name.casefold()]!=name:raise RuntimeError('CASE_COLLISION '+name)
 names[name.casefold()]=name;entries.append({'source':source,'member':name,'bytes':p.stat().st_size,'sha256':sha(p)})
save('PAYLOAD_MANIFEST.json',entries);add(A/'PAYLOAD_MANIFEST.json')
# Distribute by source bytes <=38MiB so every finished part remains within delivery limit.
batches=[];batch=[];size=0
for e in entries:
 if batch and size+e['bytes']>38*1024**2:batches.append(batch);batch=[];size=0
 batch.append(e);size+=e['bytes']
if batch:batches.append(batch)
parts=[]
for i,batch in enumerate(batches,1):
 p=A/f'v10_assets_part{i:02d}_of_{len(batches):02d}.zip'
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
  for e in batch:z.write(e['source'],e['member'])
  z.writestr(f'PART_{i:02d}_MANIFEST.json',json.dumps(batch,ensure_ascii=False,indent=2))
 with zipfile.ZipFile(p) as z:
  assert z.testzip() is None
  for e in batch:assert hashlib.sha256(z.read(e['member'])).hexdigest()==e['sha256']
 parts.append({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'payload_members':len(batch),'zip_members':len(batch)+1});log(p.name+' bytes='+str(p.stat().st_size))
# Cold load FROM ACTUAL ZIP MEMBER BYTES: no reference to unpackaged Gaussian/model data.
lookup={e['member']:p['path'] for p,b in zip(parts,batches) for e in b}
def zipped(name):
 with zipfile.ZipFile(lookup[name]) as z:return z.read(name)
cold=[]
for scene,rel in D['latest_cold_loadable'].items():
 orig=next(p for p,z in D['original_assets_verified'].items() if z['role']=='gaussians' and '/'+scene+'/' in p)
 gauname='dependencies/'+orig.lstrip('/');ga=np.load(io.BytesIO(zipped(gauname)),allow_pickle=False);m=np.load(io.BytesIO(zipped('v10/'+rel+'/MEMBERSHIP.npz')),allow_pickle=False);q=np.load(io.BytesIO(zipped('v10/'+rel+'/MODELS.npz')),allow_pickle=False)
 assert len(m['edge_id'])==len(ga['means']);np.testing.assert_array_equal(m['line_kernel_id'],np.arange(len(ga['means'])));np.testing.assert_array_equal(m['primitive_id'],ga['primitive_id'])
 for k in ga.files:np.testing.assert_array_equal(ga[k],asset[scene][k])
 assert q['knot_offsets'][-1]==len(q['knots_p']) and q['row_offsets'][-1]==len(q['rows'])
 cold.append({'scene':scene,'rows':len(m['edge_id']),'geometry_arrays':ga.files,'active_auxiliary_models':len(q['group_id']),'all_original_arrays_equal':True,'mapping_row_order_equal':True,'loaded_from_zip_member_bytes':True})
save('ZIP_VERIFICATION.json',{'parts':parts,'payload_members':len(entries),'casefold_collisions':[],'crc_sha_all_members_pass':True,'cold_load':cold,'all_intermediate_evidence_included':False})
log('DONE '+json.dumps({'parts':len(parts),'members':len(entries),'issues':len(audit['issues']),'cold':cold}))
