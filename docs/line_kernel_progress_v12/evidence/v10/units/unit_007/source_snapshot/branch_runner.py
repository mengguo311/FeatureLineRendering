"""Parent-owned LOCAL/WHOLE plain runner. Import performs no data science."""
from runtime_io import *
from branch_loader import load
from branch_delivery import save_stage,save_library,statistics,native_full,diagnostics,serial,scientific
import branch_core
from scene_render import geometry_fingerprint
import whole_core as core
import argparse,copy,traceback

def grow(d,c,policy,start_objects,next_version,guard,save,save_lib):
 if d.get('_catalog_block'):return copy.deepcopy(start_objects),[],next_version,dict(status='PARTIAL',reason=d['_catalog_block'],groups={}),{sid:set() for sid in c['seed_ids']}
 objects=copy.deepcopy(start_objects);active=set(c['seed_ids']);events=[];statuses={};contexts={sid:set() for sid in active};round_index=0;initial_catalogs=dict(d.get('_catalogs',{}).get(policy,{}))
 while True:
  progressed=False
  for gid in sorted(active):
   if gid not in objects:continue
   if statuses.get(gid)=='SUPPORTED_CLOSED_CURVE':continue
   try:
    guard();index=core.CompleteIndex(objects);lib=initial_catalogs.pop(gid) if gid in initial_catalogs else branch_core.library(d,objects,gid,policy,index,guard)
   except TimeoutError as exc:return objects,events,next_version,dict(status='PARTIAL',reason=str(exc),groups=statuses),contexts
   for fid,_ in lib['neighbors']:
    for sid in objects[gid]['seed_origins']:contexts.setdefault(sid,set()).update(objects[fid].get('origin_objects',[fid]))
   save_lib(round_index,gid,lib);round_index+=1
   if not lib['complete']:return objects,events,next_version,dict(status='PARTIAL',reason=lib['reason'],groups=statuses),contexts
   if lib['selected'] is None:statuses[gid]='NO_CONNECTABLE_FRAGMENT';continue
   z=lib['records'][lib['selected']];fid=z['donor'];event=dict(sequence=len(events)+1,group=gid,donor=fid,donor_version=objects[fid]['version'],old_version=objects[gid]['version'],new_version=next_version,added_rows=objects[fid]['rows'].tolist(),relation=z['relation'],direction=z['direction'],score=z['metrics']['score'],old_curve_motion_p=z['old_curve_motion_p'],closed=z['metrics']['closure']['supported'],accepted_merge_is_ground_truth=False)
   def persist(trial,new):save(trial,events+[event],next_version+1,event)
   objects,next_version=core.commit(objects,gid,z,next_version,persist);events.append(event);active.discard(fid);progressed=True;initial_catalogs.clear()
   statuses={k:v for k,v in statuses.items() if v=='SUPPORTED_CLOSED_CURVE' and k in objects}
   if event['closed']:statuses[gid]='SUPPORTED_CLOSED_CURVE'
  if not progressed:return objects,events,next_version,dict(status='completed',reason='NATURAL_SCOPE_EXHAUSTION',groups=statuses),contexts

def copy_prior(c):
 source=Path(c['restore_stage']);out=Path(c['unit_root'])/'scenes'/c['scene']/'stages/NO_FURTHER_GROWTH';cp=json.loads((source/'CHECKPOINT.json').read_text())
 for name in [*cp['files'],'CHECKPOINT.json']:atomic(out/name,lambda f,n=name:f.write((source/n).read_bytes()))
 verify_checkpoint(out,c['restore_binding'])

def prepare_catalogs(d,c,scene,lim):
 d['_catalogs']={};receipt=[]
 for policy in ['RADIAL_BRANCH','TRANSPORT_BRANCH']:
  bank={};d['_catalogs'][policy]=bank
  for gid in c['seed_ids']:
   lib=branch_core.library(d,d['objects'],gid,policy,core.CompleteIndex(d['objects']),lambda:lim.guard('selection'));save_library(scene/'initial_catalogs'/policy/str(gid),lib);bank[gid]=lib
   if not lib['complete']:d['_catalog_block']='INITIAL_CATALOG_INCOMPLETE '+policy+' '+str(gid)+' '+lib['reason']
   if policy=='RADIAL_BRANCH':
    previous=json.loads(Path(c['replay_libraries'][str(gid)]).read_text());assert scientific(lib)==scientific(previous),('RADIAL_LIBRARY_REPLAY',gid);assert lib['selected'] is None
    previous_geometry=np.load(Path(c['replay_libraries'][str(gid)]).parent/'GEOMETRY.npz',allow_pickle=False)
    for new,old in zip(lib['records'],previous['records']):
     for key in ['q','template','local_movable']:
      if key in new:np.testing.assert_array_equal(new[key],previous_geometry[old[key+'_array']])
   receipt.append(dict(policy=policy,group=gid,complete=True,selected=lib['selected']))
 js(scene/'INITIAL_CATALOG_RECEIPT.json',dict(all_frozen_before_promotion=True,records=receipt))

def run(c,config_path):
 root=Path(c['unit_root']);binding=sha(config_path);lim=Limits(c);facts=dict(status='blocked',completed=[],outputs={},parent_exit_authoritative=True,scientific_verdict='UNASSESSED');error=None
 try:
  if (root/'RUN_RESULT.json').exists():raise RuntimeError('CLOSED_RUN')
  d=load(c,lim.guard);copy_prior(c);before=geometry_fingerprint(d['asset']);scene=root/'scenes'/c['scene'];initial=d['objects'];maps={};states={};stage_paths={};contexts={sid:set() for sid in c['seed_ids']}
  for arr in d['asset'].values():arr.flags.writeable=False
  js(scene/'READINESS.json',dict(control=d['control_identity_receipt'],initial_rows=c['kernel_count'],initial_assigned=c['initial_assigned'],initial_next_version=d['next_version'],unavailable=d['unavailable'],seed_ids=c['seed_ids'],all_group_rows_partition_original=True,source_snapshot=c['source_snapshot_root'],no_legacy_validity_gate=True))
  maps['START']=save_stage(scene/'stages/START',c,d,initial,[],d['next_version'],binding);states['START']=initial;stage_paths['START']=scene/'stages/START';facts['completed'].append('START_MAPPING')
  prepare_catalogs(d,c,scene,lim)
  for policy in ('RADIAL_BRANCH','TRANSPORT_BRANCH'):
   def save(objects,events,version,event):
    save_stage(scene/'stages'/f'{policy}_{len(events):04d}',c,d,objects,events,version,binding,event);facts['completed'].append(f'{policy}_{len(events):04d}_MAPPING');print('COMMITTED',policy,event['group'],event['donor'],len(events),flush=True)
   def save_lib(n,gid,lib):save_library(scene/'libraries'/policy/f'{n:04d}_{gid}',lib)
   objects,events,version,status,ctx=grow(d,c,policy,initial,d['next_version'],lambda:lim.guard('selection'),save,save_lib)
   lim.guard('delivery');out=scene/'stages'/(policy+'_FINAL');maps[policy]=save_stage(out,c,d,objects,events,version,binding);states[policy]=objects;js(out/'STOP.json',status);facts['completed'].append(policy+'_FINAL_MAPPING');facts['outputs'][policy]=dict(stage=str(out),accepted=len(events),stop=status,rows=len(maps[policy]['edge_id']))
   stage_paths[policy]=out
   if len(events)>1:
    middle=(len(events)+1)//2;mid=scene/'stages'/f'{policy}_{middle:04d}';verify_checkpoint(mid,binding);maps[policy+'_MID']=dict(np.load(mid/'MEMBERSHIP.npz',allow_pickle=False));stage_paths[policy+'_MID']=mid
   for sid,ids in ctx.items():contexts[sid].update(ids)
  after=geometry_fingerprint(d['asset']);assert before==after and sha(c['gaussians'])==c['input_files'][c['gaussians']];js(root/'GEOMETRY_AUDIT.json',dict(unchanged=True,fields_before=before,fields_after=after,full_row_order=True,rows=c['kernel_count']))
  assert facts['outputs']['RADIAL_BRANCH']['accepted']==0,'RADIAL_CONTROL_CHANGED'
  np.testing.assert_array_equal(maps['RADIAL_BRANCH']['edge_id'],maps['START']['edge_id'])
  cams0=json.loads(Path(c['cameras']).read_text())[c['scene']];cams=[next(z for z in cams0 if z['view']==v) for v in c['views']];render=renderer(c)
  for arm,m in maps.items():
   out=stage_paths[arm];images=native_full(out,c,d,m,render,cams,lambda:lim.guard('delivery'));js(out/'FULL_NATIVE_RECEIPT.json',dict(files={p:sha(out/p) for p in images}));facts['completed'].append(arm+'_FULL_NATIVE')
  facts['delivery_gate']=True
  for arm,objects in states.items():statistics(stage_paths[arm],c,d,objects,maps[arm],lambda:lim.guard('delivery'))
  facts['diagnostic_images']=diagnostics(scene,c,d,maps,states,contexts,render,cams,lambda:lim.guard('delivery'))
  verify(c['source_files']);verify(c['helper_files']);facts['status']='completed' if all(z['stop']['status']=='completed' for z in facts['outputs'].values()) else 'partial'
 except BaseException as exc:error=exc;facts.update(status='partial' if facts['completed'] else 'blocked',error=repr(exc),traceback=traceback.format_exc())
 finally:
  facts.update(ended_utc=now(),elapsed_seconds=time.monotonic()-lim.start,actual_pngs=[str(p.relative_to(root)) for p in sorted(root.glob('scenes/**/*.png'))]);js(root/'RUN_RESULT.json',facts);lim.close()
 if error:raise error
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args();run(json.loads(Path(args.config).read_text()),args.config)
