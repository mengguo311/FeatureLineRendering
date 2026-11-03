"""Parent-owned full-model numerical job; no producer or old-root writes."""
import limits
import argparse, datetime, json, shutil, signal, time, traceback
from pathlib import Path
import numpy as np
from io_tools import load_asset, save_npz, write_json, sha, same_bytes, array_sha
from batching import transform, group_index, Journal
from rendering import load_renderer
from delivery import deliver

class Budget:
    def __init__(self,c):
        self.c=c;self.start=time.monotonic();self.phase='startup';self.phase_start=self.start;self.times={};self.last=0
        self.absolute=datetime.datetime.fromisoformat(c['science_deadline']).timestamp()
    def stage(self,name):
        now=time.monotonic();self.times[self.phase]=now-self.phase_start;self.phase=name;self.phase_start=now
        left=min(self.c['max_seconds']-(now-self.start),self.absolute-time.time(),self.c['budgets'][name])
        if left<=0:raise TimeoutError('no time remaining '+name)
        signal.setitimer(signal.ITIMER_REAL,left)
        self.guard('stage_'+name)
    def guard(self,phase):
        now=time.monotonic()
        if time.time()>=self.absolute or now-self.start>=self.c['max_seconds']:
            raise TimeoutError('absolute/total deadline '+phase)
        if self.phase in self.c['budgets'] and now-self.phase_start>=self.c['budgets'][self.phase]:
            raise TimeoutError('phase deadline '+self.phase)
        if now-self.last>5:
            if shutil.disk_usage('/').free<2**30 or shutil.disk_usage(self.c['unit_root']).free<10*2**30:
                raise RuntimeError('disk reserve insufficient')
            if sum(p.stat().st_size for p in Path(self.c['output_root']).rglob('*') if p.is_file())>self.c['max_output_bytes']:
                raise RuntimeError('output cap')
            self.last=now
    def receipt(self):
        return dict(total_seconds=time.monotonic()-self.start,phase=self.phase,
                    phase_seconds={**self.times,self.phase:time.monotonic()-self.phase_start})

def alarm(signum,frame):raise TimeoutError('phase/absolute timer')

def copy_atomic(source,dest):
    source=Path(source);dest=Path(dest)
    if dest.exists():
        if sha(dest)!=sha(source):raise ValueError('existing backup differs '+str(dest))
        return
    tmp=dest.with_suffix(dest.suffix+'.tmp');shutil.copyfile(source,tmp);tmp.replace(dest)

def load_membership(path,guard):
    guard('membership_begin')
    with np.load(path,allow_pickle=False) as d:
        m={k:d[k].copy() for k in d.files}
    guard('membership_end');return m

def verify_bindings(c,guard):
    if sha(c['decision_path'])!=c['decision_sha256']:raise ValueError('decision hash mismatch')
    for label in ['source_files','helper_files','input_files']:
        for p,h in c[label].items():
            guard('verify_'+label)
            if sha(p)!=h:raise ValueError('binding mismatch '+p)
    cp=json.loads(Path(c['checkpoint']).read_text())
    if cp.get('complete') is not True:raise ValueError('incomplete input checkpoint')
    for n,h in cp['files'].items():
        if sha(Path(c['checkpoint']).parent/n)!=h:raise ValueError('input checkpoint mismatch '+n)

def geometry_audit(original,derived,membership,batch,p):
    edge=membership['edge_id'];preserved=edge<0
    for r in batch['ledger']:
        if r['status']!='SUCCESS':preserved[np.asarray(r['rows'],dtype=np.int64)]=True
    fields={}
    for k,a in original.items():
        b=derived[k]
        fields[k]=dict(dtype_unchanged=a.dtype==b.dtype,shape_unchanged=a.shape==b.shape,
            original_sha256=array_sha(a),derived_sha256=array_sha(b))
        if k!='means':fields[k]['all_rows_bitwise']=same_bytes(a,b)
        else:
            fields[k]['unknown_bitwise']=same_bytes(a[edge<0],b[edge<0])
            fields[k]['all_unprocessed_bitwise']=same_bytes(a[preserved],b[preserved])
        if not all(v for name,v in fields[k].items() if name.endswith(('unchanged','bitwise'))):
            raise ValueError('preservation violation '+k)
    changed=np.any(original['means'].view(np.uint64)!=derived['means'].view(np.uint64),axis=1)
    delta=np.linalg.norm(derived['means']-original['means'],axis=1)/p
    valid=(edge>=0)&np.isfinite(delta)
    return dict(fields=fields,row_count=len(edge),assigned_rows=int(np.sum(edge>=0)),unknown_rows=int(np.sum(edge<0)),
        changed_mean_rows=int(changed.sum()),changed_unknown_rows=int(changed[edge<0].sum()),
        assigned_displacement_quantiles_p=np.quantile(delta[valid],[0,.5,.9,.95,.99,1]) if np.any(valid) else [],
        nonfinite_displacement_rows=np.flatnonzero(~np.isfinite(delta)),
        coverage=batch['summary'],allocation=batch['allocation'],membership_frozen=True,
        canonical_geometry_frozen=True,only_assigned_means_may_change=True,
        original_controls_are_provenance_only=True),np.flatnonzero(changed),delta

def execute(c,result,budget):
    u=Path(c['unit_root']);budget.stage('readiness');verify_bindings(c,budget.guard)
    original=load_asset(c['gaussians'],budget.guard,c['kernel_count'],allow_nonfinite_geometry=True)
    membership=load_membership(c['membership'],budget.guard);index=group_index(original,membership)
    expected=c['expected_inventory'];edge=membership['edge_id']
    if len(index)!=expected['groups'] or int(np.sum(edge>=0))!=expected['assigned'] or int(np.sum(edge<0))!=expected['unknown']:
        raise ValueError('complete inventory mismatch')
    groups=json.loads(Path(c['groups']).read_text())['groups'];indexed=dict(index)
    for g in groups:
        rows=indexed.get(g['id'])
        if rows is None or not np.array_equal(rows,np.sort(g['rows'])) or not np.all(membership['group_model_version'][rows]==g['version']):
            raise ValueError('tracked composite mismatch')
    rows30579=indexed[30579]
    if len(rows30579)!=596 or array_sha(rows30579.astype('<i8'))!=c['regression_rows_sha256']:
        raise ValueError('30579 regression row mismatch')
    cameras_all=json.loads(Path(c['cameras']).read_text())[c['scene']]
    cameras=[next(x for x in cameras_all if x['view']==v) for v in c['views']]
    for cam in cameras:
        if [cam['width'],cam['height']]!=[777,581] or 'COLMAP' not in cam['coordinate']:
            raise ValueError('camera convention or shape changed')
        if not np.isfinite(np.asarray(cam['extrinsic'])).all():raise ValueError('nonfinite camera')
    paths=dict(ORIGINAL=u/'ORIGINAL_GAUSSIANS.npz',FULL_POSITION_ONLY=u/'FULL_POSITION_ONLY_GAUSSIANS.npz')
    copy_atomic(c['gaussians'],paths['ORIGINAL']);copy_atomic(c['membership'],u/'MEMBERSHIP.npz')
    lengths=np.array([len(rows) for _,rows in index],dtype=np.int64)
    save_npz(u/'GROUP_INDEX.npz',dict(group_id=np.array([g for g,_ in index],dtype=np.int64),
        row_offsets=np.r_[0,np.cumsum(lengths)],rows=np.concatenate([rows for _,rows in index]),unknown_rows=np.flatnonzero(edge<0)))
    write_json(u/'READINESS.json',dict(passed=True,inventory=expected,tracked_composites_checked=len(groups),
        group_enumeration='all nonnegative edge_id in complete MEMBERSHIP',cameras=cameras,
        canonical_sha256=sha(c['gaussians']),membership_sha256=sha(c['membership'])))
    result['completed'].append('READINESS')
    budget.stage('transform')
    batch=transform(original,membership,c['p'],budget.guard,Journal(u/'group_journal',c['_config_sha256'],c['checkpoint_groups']))
    write_json(u/'GROUP_LEDGER.json',dict(groups=batch['ledger'],summary=batch['summary'],complete=batch['complete'],failure=batch['failure']))
    result.update(group_status=batch['summary'],transform_complete=batch['complete'])
    derived=batch['asset'];audit,changed,displacement=geometry_audit(original,derived,membership,batch,c['p'])
    audit.update(source_sha256_before=c['input_files'][c['gaussians']],source_sha256_after=sha(c['gaussians']))
    if audit['source_sha256_before']!=audit['source_sha256_after']:raise ValueError('canonical source changed')
    save_npz(paths['FULL_POSITION_ONLY'],derived)
    save_npz(u/'UPDATED_ROWS.npz',dict(row_index=changed,line_kernel_id=membership['line_kernel_id'][changed],
        edge_id=edge[changed],old_means=original['means'][changed],new_means=derived['means'][changed],
        displacement_p=displacement[changed]))
    cold={stage:load_asset(path,budget.guard,c['kernel_count'],allow_nonfinite_geometry=True) for stage,path in paths.items()}
    memory=dict(ORIGINAL=original,FULL_POSITION_ONLY=derived)
    checks={s:{k:same_bytes(a[k],memory[s][k]) for k in a} for s,a in cold.items()}
    if not all(all(v.values()) for v in checks.values()):raise ValueError('cold reload mismatch')
    with np.load(u/'MEMBERSHIP.npz',allow_pickle=False) as m:
        if set(m.files)!=set(membership) or not all(same_bytes(m[k],membership[k]) for k in m.files):raise ValueError('membership changed')
    with np.load(c['regression_asset'],allow_pickle=False) as old:
        reference=old['means'][rows30579]
    candidate=cold['FULL_POSITION_ONLY']['means'][rows30579]
    maxdiff=float(np.max(np.abs(candidate-reference)));atol=c['regression_atol_p']*c['p']
    regression=dict(group_id=30579,row_count=596,bitwise=same_bytes(candidate,reference),maximum_absolute_difference=maxdiff,
        rtol=0,atol=atol,passed=bool(np.allclose(candidate,reference,rtol=0,atol=atol)))
    audit.update(cold_reload_fields_bitwise=checks,regression30579=regression)
    write_json(u/'GEOMETRY_AUDIT.json',audit)
    files=[*paths.values(),u/'MEMBERSHIP.npz',u/'GROUP_INDEX.npz',u/'GROUP_LEDGER.json',u/'UPDATED_ROWS.npz',u/'GEOMETRY_AUDIT.json']
    files.extend(p for p in (u/'group_journal').rglob('*') if p.is_file() and not p.name.endswith('.tmp'))
    write_json(u/'CHECKPOINT.json',dict(complete=batch['complete'] and regression['passed'],
        stage='FULL_POSITION_ONLY_COLD_LOADABLE_BEFORE_RENDER',row_count=len(edge),group_count=len(index),
        config_sha256=c['_config_sha256'],files={str(p.relative_to(u)):sha(p) for p in files}))
    result['completed'].append('FULL_ASSET_COLD_CHECKPOINT')
    if not batch['complete']:raise RuntimeError('PARTIAL_TRANSFORM: '+str(batch['failure']))
    if not regression['passed']:raise ValueError('30579 v11 regression failed')
    budget.stage('render');renderer=load_renderer(c['renderer'],c['helper_files'])
    render=deliver(u,renderer,cold,memory,cameras,paths,batch['ledger'],budget.guard)
    result['completed'].append('FULL_FRAMES_AND_ALL_FIXED_QUADRANTS')
    budget.stage('audit')
    cp=json.loads((u/'CHECKPOINT.json').read_text())
    for n,h in cp['files'].items():
        budget.guard('final_checkpoint_hash')
        if sha(u/n)!=h:raise ValueError('final checkpoint hash mismatch')
    if sha(c['gaussians'])!=audit['source_sha256_before'] or sha(c['membership'])!=sha(u/'MEMBERSHIP.npz'):
        raise ValueError('original source protection failed')
    write_json(u/'DELIVERY_AUDIT.json',dict(checkpoint_verified=True,cold_full_render_bitwise=True,
        full_frames=render['native_full_images'],all_quadrant_records=len(render['quadrants']),
        source_and_membership_unchanged=True,all_existing_groups_accounted=True,
        canonical_geometry_frozen=True,unknown_rows_preserved=expected['unknown'],uses_gpu=False,uses_training=False))
    result.update(status='completed',assets={k:str(v) for k,v in paths.items()},
        changed_mean_rows=audit['changed_mean_rows'],scientific_verdict='UNASSESSED_FULL_MODEL_POSITION_ONLY',
        next_science='STOP_FULL_MODEL_DEMO',actual_render_backend='CPU Gaussian EWA replica')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);args=parser.parse_args()
    path=Path(args.config);c=json.loads(path.read_text());c['_config_sha256']=sha(path)
    u=Path(c['unit_root']);u.mkdir(parents=True,exist_ok=True);b=Budget(c)
    result=dict(status='running',completed=[],config_sha256=c['_config_sha256'],parent_exit_authoritative=True)
    signal.signal(signal.SIGALRM,alarm);rc=0
    try:execute(c,result,b)
    except Exception as exc:
        rc=1;signal.setitimer(signal.ITIMER_REAL,0)
        result.update(status='partial' if isinstance(exc,TimeoutError) or 'PARTIAL_' in str(exc) else 'failed',
                      error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc())
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);result.update(timing=b.receipt(),runner_returncode=rc)
        write_json(u/'RUN_RESULT.json',result);print(json.dumps({'status':result['status'],'returncode':rc,'completed':result['completed']}))
    return rc

if __name__=='__main__':raise SystemExit(main())
