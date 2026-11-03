from runtime_io import *
import gzip
import whole_delivery as old
from whole_delivery import serial,native_full
from scan65_delivery import diagnostics,statistics

def save_library(out,lib):
 out=Path(out);witnesses={str(i):serial(z.get('branch_diagnostic',{'status':'NOT_REACHED'})) for i,z in enumerate(lib['records'])}
 atomic(out/'BRANCH_WITNESSES.json.gz',lambda f:f.write(gzip.compress(json.dumps(witnesses,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode(),mtime=0)))
 records=[dict({k:v for k,v in z.items() if k!='branch_diagnostic'},branch_witness_file='BRANCH_WITNESSES.json.gz',branch_witness_index=i) for i,z in enumerate(lib['records'])]
 old.save_library(out,dict(lib,records=records))

def scientific(lib):
 records=[{k:serial(v) for k,v in z.items() if k not in ['branch_diagnostic','q','template','local_movable','q_array','template_array','local_movable_array','branch_witness_file','branch_witness_index']} for z in lib['records']]
 return dict(complete=lib['complete'],reason=lib['reason'],neighbors=serial(lib['neighbors']),selected=lib['selected'],records=records)

def save_stage(out,c,d,objects,events,next_version,binding,changed=None):
 out=Path(out);m=({k:v.copy() for k,v in d['initial_membership'].items()} if not events else old.mapping(d,objects));nz(out/'MEMBERSHIP.npz',**m)
 # Full changed/active model bank relative to immutable original checkpoint.
 selected={gid:o for gid,o in objects.items() if o['seed_origins']};ids=sorted(selected);qs=[selected[i]['q'] for i in ids];rr=[selected[i]['rows'] for i in ids]
 nz(out/'MODELS.npz',group_id=np.asarray(ids,np.int64),version=np.asarray([selected[i]['version'] for i in ids]),knots_p=np.concatenate(qs) if qs else np.empty((0,3)),knot_offsets=np.r_[0,np.cumsum([len(q) for q in qs])],rows=np.concatenate(rr) if rr else np.empty(0,int),row_offsets=np.r_[0,np.cumsum([len(r) for r in rr])])
 groups=[dict(id=gid,version=o['version'],rows=o['rows'].tolist(),leaves=o['leaves'],seed_origins=o['seed_origins'],metrics=o.get('metrics'),geometry_available=o['available']) for gid,o in selected.items()]
 js(out/'GROUPS.json',dict(groups=groups,unchanged_background=c['initial_stage'],no_original_kernel_geometry_copy=True));js(out/'LINEAGE.json',dict(historical=d['historical_events'],events=events,next_version=next_version,changed=changed,checkpoint_replay='immutable initial state plus ordered whole-member donor deltas',original_kernel_ink_only=True))
 checkpoint(out,['MEMBERSHIP.npz','MODELS.npz','GROUPS.json','LINEAGE.json'],binding,'COMPLETE_MONOTONE_GROUP_UNION');verify_checkpoint(out,binding)
 cold=dict(np.load(out/'MEMBERSHIP.npz',allow_pickle=False))
 for key in m:np.testing.assert_array_equal(cold[key],m[key])
 return m
