"""Read-only parent audit; saved-data checks, not a scientific rerun."""
from pathlib import Path
import os,json,hashlib,subprocess,datetime
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
import numpy as np
from PIL import Image
B=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_best_fragment_growth_v09_20261102');C=B/'continuation_001';R=C/'orchestration'
def load(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def audit_hook(event,args):
 if event=='open':
  mode=args[1];flags=args[2]
  if isinstance(mode,str) and any(c in mode for c in 'wax+'):raise RuntimeError('READ_ONLY_AUDIT_REFUSES_WRITE')
  if isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise RuntimeError('READ_ONLY_AUDIT_REFUSES_FLAGS')
 if event in ['os.mkdir','os.remove','os.rename','os.rmdir','os.chmod','os.truncate','os.link','os.symlink']:raise RuntimeError('READ_ONLY_AUDIT_REFUSES_MUTATION')
import sys
sys.addaudithook(audit_hook)
cache={};png=set();out={'audit_scope':'saved immutable outputs only; no fitting/rendering/source changes','units':[],'physical_identity_certified':False,'heldout_certified':False,'temporal_certified':False}
units=[B/'units/unit_001']+sorted((C/'units').glob('unit_*'))
assert len(units)==4
for u in units:
 cfg=load(u/'CONFIG.json');seal=load(u/'PARENT_SEAL.json')['files'];frozen=load(u/'PARENT_RUN_FROZEN.json');scene=cfg['scene'];N=cfg['kernel_count'];sd=u/'scenes'/scene
 item={'unit_output':str(u),'scene':scene,'rows':N,'seal_entries':len(seal),'arms':{},'snapshots':len(frozen['source_files'])}
 for rel,digest in seal.items():
  p=(u/rel).resolve();assert p.is_relative_to(u.resolve()),p;actual=sha(p);assert actual==digest,p
  if p.suffix.lower()=='.png' and actual not in png:
   with Image.open(p) as im:im.load();assert im.width>0 and im.height>0
   png.add(actual)
 assert sha(u/'CONFIG.json')==frozen['config_sha256'];assert sha(u/'DECISION.json')==frozen['decision_sha256']
 for old,digest in frozen['source_files'].items():assert sha(frozen['immutable_source_snapshot'][old])==digest,old
 for p,h in frozen['helper_files'].items():assert sha(p)==h,p
 geom=load(u/'GEOMETRY_AUDIT.json');assert geom['fields_before']==geom['fields_after'] and geom['rows']==N
 with np.load(cfg['gaussians'],allow_pickle=False) as z:
  for k,v in geom['fields_before'].items():
   a=z[k];assert str(a.dtype)==v['dtype'] and list(a.shape)==v['shape'] and hashlib.sha256(a.tobytes()).hexdigest()==v['sha256'],(u,k)
  primitive=z['primitive_id'].copy()
 stages=sd/'stages';start=stages/'START'
 with np.load(start/'MEMBERSHIP.npz',allow_pickle=False) as z:
  initial=z['edge_id'].copy();ids=z['line_kernel_id'].copy();assert np.array_equal(ids,np.arange(N));assert np.array_equal(z['primitive_id'],primitive)
 libraries=list((sd/'libraries').rglob('LIBRARY.json'));selected_count=0;all_complete=True
 for lp in libraries:
  lib=load(lp);assert lib['complete'] and lib['all_neighbors_queried'] and lib['no_top_k'] and not lib['unattempted_donors'],lp
  good=[(i,x) for i,x in enumerate(lib['records']) if x.get('connectable')];sel=lib['selected']
  assert bool(good)==(sel is not None),(lp,'selection completeness')
  if sel is not None:
   chosen=lib['records'][sel];assert chosen['connectable'];assert chosen['metrics']['score']==min(x['metrics']['score'] for i,x in good),(lp,'not minimum score');selected_count+=1
 item['libraries']=len(libraries);item['minimum_score_selected_libraries']=selected_count
 result=load(u/'RUN_RESULT.json')
 for arm,rec in result['outputs'].items():
  final=Path(rec['stage']);events=load(final/'LINEAGE.json')['events'];assert len(events)==rec['accepted']
  previous=initial.copy();old_groups={}
  with np.load(start/'MODELS.npz',allow_pickle=False) as z:
   for j,g in enumerate(z['group_id']):old_groups[int(g)]=z['rows'][z['row_offsets'][j]:z['row_offsets'][j+1]].copy()
  for n,ev in enumerate(events,1):
   stage=stages/f'{arm}_{n:04d}';gid=int(ev['group']);added=np.asarray(ev['added_rows'],dtype=np.int64);expected=previous.copy();expected[added]=gid
   with np.load(stage/'MEMBERSHIP.npz',allow_pickle=False) as z:
    current=z['edge_id'];assert np.array_equal(z['line_kernel_id'],ids) and np.array_equal(z['primitive_id'],primitive);assert np.array_equal(current,expected),(stage,'unexpected change/loss')
   with np.load(stage/'MODELS.npz',allow_pickle=False) as z:
    groups={int(g):z['rows'][z['row_offsets'][j]:z['row_offsets'][j+1]].copy() for j,g in enumerate(z['group_id'])}
   assert np.array_equal(np.sort(groups[gid]),np.union1d(old_groups[gid],added)),(stage,'union')
   for g,rows in groups.items():assert np.array_equal(np.sort(rows),np.flatnonzero(current==g)),(stage,g,'model/map mismatch')
   old_groups=groups;previous=current.copy()
  with np.load(final/'MEMBERSHIP.npz',allow_pickle=False) as z:
   assert np.array_equal(z['edge_id'],previous);assert np.array_equal(z['line_kernel_id'],ids);assert np.array_equal(z['primitive_id'],primitive)
  gained=int(((initial<0)&(previous>=0)).sum());lost=int(((initial>=0)&(previous<0)).sum());assert lost==0
  item['arms'][arm]={'accepted':len(events),'assigned':int((previous>=0).sum()),'unknown':int((previous<0).sum()),'newly_assigned':gained,'withdrawn':lost,'stop':rec['stop'],'events_per_group':{str(g):sum(int(e['group'])==g for e in events) for g in sorted({int(e['group']) for e in events})}}
 item['checkpoints']=len(list(stages.glob('*/CHECKPOINT.json')));item['png_paths']=len(list(u.rglob('*.png')));out['units'].append(item)
# Re-hash all old-science references and exact old worktree status bytes.
refs=load(R/'PROTECTED_REFERENCE_FILES.json')
for p,h in refs.items():assert sha(p)==h,p
before=load(R/'PROTECTED_BEFORE.json')
for w,s in before.items():
 head=subprocess.run(['git','-C',w,'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip();status=subprocess.run(['git','-C',w,'status','--porcelain=v1'],capture_output=True,text=True,check=True).stdout
 assert head==s['head'] and status==s['status'],(w,'old git state changed')
owned=set();phases=[]
for root in [B,C]:
 rr=root/'orchestration'
 for p in rr.rglob('EXIT.json'):
  x=load(p);phases.append({'path':str(p),'returncode':x.get('returncode'),'reason':x.get('reason')})
 for p in rr.rglob('LAUNCH.json'):
  x=load(p)
  for k in ['pid','child_pid']:
   if isinstance(x.get(k),int):owned.add(x[k])
 for n in ['FINAL_SUMMARY.json','SUPERVISOR_STATUS.json']:
  x=load(rr/n)
  for k in ['pid','child_pid']:
   if isinstance(x.get(k),int):owned.add(x[k])
 for p in rr.glob('unit_*/COMPUTE_EXIT.json'):
  x=load(p);assert x.get('returncode',x.get('child_returncode',x.get('exit_code'))) ==0,(p,x)
  phases.append({'path':str(p),'numerical_exit':0})
alive=[{'pid':p,'comm':(Path('/proc')/str(p)/'comm').read_text().strip()} for p in owned if (Path('/proc')/str(p)/'comm').exists()];assert not alive,alive
out.update({'old_reference_hashes_verified':len(refs),'old_worktrees_unchanged':len(before),'unique_png_encodings_decoded':len(png),'checkpoint_count':sum(x['checkpoints'] for x in out['units']),'seal_entries':sum(x['seal_entries'] for x in out['units']),'png_paths':sum(x['png_paths'] for x in out['units']),'phases':phases,'owned_pids_checked':sorted(owned),'owned_pids_alive':alive,'completed_jst':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'status':'PASS_SAVED_DATA_INVARIANTS_SCIENTIFIC_PARTIAL'})
print(json.dumps(out,ensure_ascii=False,indent=2))
