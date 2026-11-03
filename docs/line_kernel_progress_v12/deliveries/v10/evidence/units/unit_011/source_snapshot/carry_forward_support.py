"""Fixed finite-carrier support diagnostics; never consulted by growth decisions."""
from runtime_io import *
from geometry_base import project,extended_s,arc,EPS,union_intervals
import whole_core

def account(d,q,inherited,current):
 rows=np.unique(np.asarray(current,int));inherited=np.unique(np.asarray(inherited,int))
 assert np.isin(inherited,rows).all(),'FIXED_REFERENCE_MEMBERS_LOST'
 x=d['asset']['means'][rows]/d['p'];s,residual,tan,segment,near=project(x,q)
 ext=extended_s(x,q)[0];t=d['tangents'][rows]
 valid=np.isfinite(t).all(1)&(np.linalg.norm(t,axis=1)>EPS)
 axis=np.zeros_like(t);axis[valid]=t[valid]/np.linalg.norm(t[valid],axis=1)[:,None]
 cov=d['asset']['covariance'][rows]/d['p']**2
 half=np.minimum(.5,np.sqrt(np.maximum(0,np.einsum('ni,nij,nj->n',axis,cov,axis))));half[~valid]=0
 raw=np.c_[s-half,s+half];iv=np.clip(raw,0,arc(q)[-1]);old=np.isin(rows,inherited)
 masks=dict(inherited=old,current=np.ones(len(rows),bool),new=~old);sets={};unions={}
 for name,mask in masks.items():
  union,length,run,gap,total=union_intervals(iv[mask&valid]);unions[name]=union
  sets[name]=dict(rows=int(mask.sum()),valid_rows=int((mask&valid).sum()),union_p=float(length),longest_run_p=float(run),max_gap_p=float(gap),total_gap_p=float(total),clipped_interval_endpoints=int((raw[mask]!=iv[mask]).sum()))
 evidence=dict(rows=rows,valid=valid,inherited=old,new=~old,finite_s=s,extended_s=ext,residual_p=residual,segment=segment,nearest=near,derivative_axis=axis,half=half,raw_intervals=raw,clipped_intervals=iv,clipped=raw!=iv,reference_q=q.copy())
 evidence.update({name+'_union':u for name,u in unions.items()})
 return dict(summary=dict(sets=sets,new_minus_inherited_p=whole_core.union_difference(unions['new'],unions['inherited']),reference_length_p=float(arc(q)[-1]),used_for_decision=False,extended_s_is_only_endpoint_directional_proxy=True,fixed_finite_support_is_internal_filling_not_external_curve=True),evidence=evidence)

def load_references(c,d,guard):
 refs={}
 for name,entry in c['fixed_reference_stages'].items():
  guard('readiness');stage=Path(entry['stage']);verify_checkpoint(stage,entry['binding'])
  with np.load(stage/'MODELS.npz',allow_pickle=False) as bank:
   lookup={int(g):i for i,g in enumerate(bank['group_id'])};ref={}
   for sid in c['seed_ids']:
    j=lookup[sid];ref[sid]=dict(q=bank['knots_p'][bank['knot_offsets'][j]:bank['knot_offsets'][j+1]].copy(),rows=bank['rows'][bank['row_offsets'][j]:bank['row_offsets'][j+1]].copy())
    assert np.isin(ref[sid]['rows'],d['objects'][sid]['rows']).all()
   refs[name]=ref
 d['_fixed_references']=refs

def save_diagnostics(stage,c,d,guard):
 stage=Path(stage);groups=json.loads((stage/'GROUPS.json').read_text())['groups'];report=[];pack={}
 with np.load(stage/'MODELS.npz',allow_pickle=False) as bank:
  lookup={int(g):i for i,g in enumerate(bank['group_id'])}
  for g in groups:
   gid=int(g['id']);j=lookup[gid];rows=bank['rows'][bank['row_offsets'][j]:bank['row_offsets'][j+1]];q=bank['knots_p'][bank['knot_offsets'][j]:bank['knot_offsets'][j+1]]
   for sid in g['seed_origins']:
    for name,refs in d['_fixed_references'].items():
     guard();result=account(d,refs[sid]['q'],refs[sid]['rows'],rows);prefix=f'{gid}_{sid}_{name}_'
     result['evidence']['unit_start_member']=np.isin(rows,d['objects'][sid]['rows'])
     for k,v in result['evidence'].items():pack[prefix+k]=v
     dynamic=whole_core.support(d,rows,q)
     report.append(dict(group=gid,seed_origin=sid,reference=name,arrays_prefix=prefix,**result['summary'],dynamic_Q=dict(union_p=dynamic['union'],longest_run_p=dynamic['run'],max_gap_p=dynamic['gap'],not_same_coordinate_system=True)))
 nz(stage/'FIXED_SUPPORT_ROWS.npz',**pack)
 js(stage/'FIXED_SUPPORT.json',dict(references=c['fixed_reference_stages'],records=report,used_for_decision=False,original_kernel_ink_only=True))

def compare_saved(current,path):
 """Exact complete-library replay, or completed prefix of an interrupted library."""
 from group_fit_delivery import compare_library,serial
 path=Path(path);old=json.loads(path.read_text())
 if old['complete']:return compare_library(current,path)
 assert current['complete'],'REPLAY_NEW_LIBRARY_INCOMPLETE'
 assert serial(current['neighbors'])==old['neighbors'],'REPLAY_NEIGHBORS_MISMATCH'
 ignored={'branch_diagnostic','q','template','local_movable','q_array','template_array','local_movable_array','branch_witness_file','branch_witness_index','score_evidence','score_evidence_file','score_evidence_arrays','fit_evidence','fit_evidence_file','fit_evidence_arrays'}
 completed=[];interrupted=[]
 for i,rec in enumerate(old['records']):
  if rec['reason']=='template':interrupted.append(i)
  else:completed.append(i)
 assert interrupted==list(range(len(completed),len(old['records']))),'NON_SUFFIX_INTERRUPTION'
 assert len(current['records'])>=len(old['records']),'REPLAY_PREFIX_MISSING'
 with np.load(path.parent/'GEOMETRY.npz',allow_pickle=False) as arrays:
  count=0
  for i in completed:
   a=current['records'][i];b=old['records'][i]
   assert {k:serial(v) for k,v in a.items() if k not in ignored}=={k:serial(v) for k,v in b.items() if k not in ignored},'REPLAY_PREFIX_RECORD_MISMATCH '+str(i)
   for key in ['q','template','local_movable']:
    if key+'_array' in b:np.testing.assert_array_equal(a[key],arrays[b[key+'_array']]);count+=1
 return dict(complete=True,source=str(path),source_sha256=sha(path),archived_library_complete=False,completed_prefix_records=len(completed),excluded_interrupted_records=interrupted,geometry_arrays=count,all_neighbors_requeried=True,new_library_records=len(current['records']),new_selected=current['selected'],old_selected_was_null=old['selected'] is None)
