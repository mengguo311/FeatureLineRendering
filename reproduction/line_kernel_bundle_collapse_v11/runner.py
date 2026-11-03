"""Parent-owned plain numerical runner: python -B runner.py --config CONFIG."""
import limits
import argparse
import datetime
import json
import os
import shutil
import signal
import time
import traceback
from pathlib import Path
import numpy as np
from core import collapse
from io_tools import load_asset, save_npz, write_json, sha, array_sha, same_bytes, preservation_audit
from rendering import load_renderer, deliver_images

class Budget:
    def __init__(self, config):
        self.config=config;self.begin=time.monotonic();self.stage_begin=self.begin;self.stage='startup';self.times={}
        self.absolute=datetime.datetime.fromisoformat(config['science_deadline']).timestamp()
        self.last_resource=0
    def set_stage(self, name):
        now=time.monotonic();self.times[self.stage]=now-self.stage_begin;self.stage=name;self.stage_begin=now
        remaining=min(self.config['max_seconds']-(now-self.begin),self.absolute-time.time(),self.config['budgets'][name])
        if remaining<=0:raise TimeoutError('no phase time remaining: '+name)
        signal.setitimer(signal.ITIMER_REAL,remaining)
        self.guard('stage_'+name)
    def guard(self, phase):
        now=time.monotonic()
        if time.time()>=self.absolute or now-self.begin>=self.config['max_seconds']:
            raise TimeoutError('absolute/total deadline: '+phase)
        if self.stage in self.config['budgets'] and now-self.stage_begin>=self.config['budgets'][self.stage]:
            raise TimeoutError('phase deadline: '+self.stage)
        if now-self.last_resource>5:
            if shutil.disk_usage('/').free<2**30 or shutil.disk_usage(self.config['unit_root']).free<10*2**30:
                raise RuntimeError('insufficient disk reserve')
            size=sum(p.stat().st_size for p in Path(self.config['output_root']).rglob('*') if p.is_file())
            if size>self.config['max_output_bytes']:raise RuntimeError('output byte cap')
            self.last_resource=now
    def receipt(self):
        return dict(phase=self.stage,phase_seconds={**self.times,self.stage:time.monotonic()-self.stage_begin},
                    total_seconds=time.monotonic()-self.begin)

def on_alarm(signum, frame): raise TimeoutError('phase/absolute timer')

def verify_bindings(config, guard):
    if sha(config['decision_path'])!=config['decision_sha256']:raise ValueError('decision hash mismatch')
    for label in ('source_files','helper_files','input_files'):
        for path,expected in config[label].items():
            guard('verify_'+label)
            if sha(path)!=expected:raise ValueError(label+' hash mismatch: '+path)
    checkpoint=json.loads(Path(config['checkpoint']).read_text())
    if checkpoint.get('complete') is not True:raise ValueError('incomplete starting checkpoint')
    for name,expected in checkpoint['files'].items():
        if sha(Path(config['checkpoint']).parent/name)!=expected:raise ValueError('checkpoint hash mismatch: '+name)

def target_rows(config, asset, guard):
    guard('membership_load')
    with np.load(config['membership'],allow_pickle=False) as m:
        ids=m['line_kernel_id'].copy();edge=m['edge_id'];rows=np.flatnonzero(edge==config['target_group_id'])
        if len(ids)!=config['kernel_count'] or not np.array_equal(ids,np.arange(len(ids))):raise ValueError('original row identity mismatch')
        if not np.array_equal(m['primitive_id'],asset['primitive_id']):raise ValueError('primitive binding mismatch')
    if len(rows)!=config['target_kernel_count'] or array_sha(rows.astype('<i8'))!=config['target_rows_sha256']:
        raise ValueError('target row/count/hash mismatch')
    groups=json.loads(Path(config['groups']).read_text())['groups']
    g=next(g for g in groups if g['id']==config['target_group_id'])
    if g['version']!=config['target_version'] or not np.array_equal(rows,np.sort(g['rows'])):
        raise ValueError('group version/member mismatch')
    return rows, ids

def execute(config, result, budget):
    unit=Path(config['unit_root']);budget.set_stage('readiness')
    verify_bindings(config,budget.guard)
    original=load_asset(config['gaussians'],budget.guard,config['kernel_count'])
    rows,ids=target_rows(config,original,budget.guard)
    cameras_all=json.loads(Path(config['cameras']).read_text())[config['scene']]
    cameras=[next(c for c in cameras_all if c['view']==v) for v in config['views']]
    for c in cameras:
        if [c['width'],c['height']]!=[777,581] or 'COLMAP' not in c['coordinate']:raise ValueError('camera convention/size mismatch')
        if not np.isfinite(np.asarray(c['extrinsic'])).all():raise ValueError('nonfinite camera')
    write_json(unit/'READINESS.json',dict(passed=True,row_count=len(ids),target_count=len(rows),
               target_rows_sha256=array_sha(rows.astype('<i8')),canonical_sha256=sha(config['gaussians']),
               cameras=cameras,source_files=config['source_files'],helper_files=config['helper_files']))
    result['completed'].append('READINESS')
    budget.set_stage('transform')
    transformed=collapse(original,rows,config['p'])
    memory_assets={'ORIGINAL':original,'POSITION_ONLY':transformed['position_only'],'DERIVED':transformed['derived']}
    audits={stage:preservation_audit(original,a,rows,position_only=(stage!='DERIVED')) for stage,a in memory_assets.items()}
    if audits['DERIVED']['changed_mean_rows']==0 or audits['DERIVED']['changed_covariance_rows']==0:
        raise ValueError('no actual target geometry edit')
    paths={stage:unit/(stage+'_GAUSSIANS.npz') for stage in memory_assets}
    # Byte-for-byte canonical backup, then atomic derived assets before expensive rendering.
    tmp=paths['ORIGINAL'].with_suffix('.npz.tmp');shutil.copyfile(config['gaussians'],tmp);tmp.replace(paths['ORIGINAL'])
    for stage in ('POSITION_ONLY','DERIVED'):
        budget.guard('save_'+stage);save_npz(paths[stage],memory_assets[stage])
    save_npz(unit/'ORIGINAL_TARGET.npz',{k:v[rows] for k,v in original.items()})
    save_npz(unit/'TARGET_ROWS.npz',dict(row_index=rows,line_kernel_id=ids[rows],all_line_kernel_id=ids))
    save_npz(unit/'TARGET_TRANSFORM.npz',transformed['delta'])
    write_json(unit/'MODEL.json',transformed['model']);write_json(unit/'GEOMETRY_METRICS.json',transformed['metrics'])
    assets={stage:load_asset(path,budget.guard,config['kernel_count']) for stage,path in paths.items()}
    cold={stage:{k:same_bytes(a[k],memory_assets[stage][k]) for k in a} for stage,a in assets.items()}
    if not all(all(v.values()) for v in cold.values()):raise ValueError('cold asset mismatch')
    if sha(paths['ORIGINAL'])!=config['input_files'][config['gaussians']]:raise ValueError('canonical backup mismatch')
    eig,axes=np.linalg.eigh(assets['DERIVED']['covariance'][rows])
    tangent=transformed['delta']['tangent'];alignment=np.abs(np.sum(axes[:,:,-1]*tangent,axis=1))
    if not np.allclose(eig[:,:2],(.15*config['p'])**2,rtol=1e-10,atol=0):raise ValueError('transverse width mismatch')
    if not np.allclose(np.sqrt(eig[:,-1]),transformed['delta']['sigma_parallel'],rtol=1e-10,atol=0):raise ValueError('longitudinal width mismatch')
    if np.any(alignment<1-1e-10):raise ValueError('long axis/tangent mismatch')
    if not same_bytes(assets['POSITION_ONLY']['means'],assets['DERIVED']['means']):raise ValueError('stage mean mismatch')
    axial=(assets['DERIVED']['means'][rows]-transformed['model']['center'])@transformed['model']['axis']
    if not np.allclose(axial,transformed['delta']['s'],rtol=0,atol=1e-10*config['p']):raise ValueError('axial sample drift')
    audit=dict(canonical_geometry_frozen=True,derived_geometry_edit_allowed=True,final_ink_carrier='derived_line_gaussians',
               source_sha256_before=config['input_files'][config['gaussians']],
               source_sha256_after=sha(config['gaussians']),canonical_original_copy_sha256=sha(paths['ORIGINAL']),
               stages=audits,cold_reload_fields_bitwise=cold,target_row_order_preserved=True,
               tangent_alignment_absolute_dot_min=float(alignment.min()),
               transverse_sigma_p_quantiles=np.quantile(np.sqrt(eig[:,:2])/config['p'],[0,.5,1]),
               longitudinal_sigma_p_quantiles=np.quantile(np.sqrt(eig[:,-1])/config['p'],[0,.5,1]),
               axial_sample_coordinates_preserved=True,same_means_across_position_and_derived=True,
               control_parameters_are_provenance_only_for_derived_geometry=True)
    write_json(unit/'GEOMETRY_AUDIT.json',audit)
    checkpoint_files=list(paths.values())+[unit/n for n in ('ORIGINAL_TARGET.npz','TARGET_ROWS.npz','TARGET_TRANSFORM.npz','MODEL.json','GEOMETRY_METRICS.json','GEOMETRY_AUDIT.json')]
    write_json(unit/'CHECKPOINT.json',dict(complete=True,stage='DERIVED_GEOMETRY_COLD_LOADABLE_BEFORE_RENDER',
               config_sha256=sha(config['config_path']),files={p.name:sha(p) for p in checkpoint_files},
               row_count=len(ids),target_count=len(rows),membership_unchanged=True))
    result['completed'].append('ALL_ASSETS_COLD_CHECKPOINT');result['assets']={k:str(v) for k,v in paths.items()}
    write_json(unit/'RUN_RESULT.json',result)
    budget.set_stage('render')
    renderer=load_renderer(config['renderer'],config['helper_files'])
    render_receipt=deliver_images(unit,renderer,assets,memory_assets,rows,cameras,paths,budget.guard)
    result['completed'].append('TWELVE_NATIVE_IMAGES_AND_PANELS')
    result['images']=[r['path'] for r in render_receipt['images']]
    budget.set_stage('audit')
    if sha(config['gaussians'])!=audit['source_sha256_before']:raise ValueError('canonical changed during execution')
    for stage,a in assets.items():preservation_audit(original,a,rows,position_only=(stage!='DERIVED'))
    budget.guard('final_audit')
    write_json(unit/'DELIVERY_AUDIT.json',dict(source_unchanged=True,checkpoint_files_verified={p.name:sha(p) for p in checkpoint_files},
               native_images=12,cold_render_bitwise=True,uses_gpu=False,uses_training=False,
               original_kernel_count=len(ids),target_count=len(rows),non_target_rows=len(ids)-len(rows),
               physical_identity_certified=False,visual_verdict='AWAITING_SAVED_IMAGE_ANALYSIS'))
    result.update(status='completed',scientific_verdict='UNASSESSED_VISUAL_REGULARIZATION_DEMO',
                  actual_render_backend='existing CPU Gaussian EWA replica',next_science='STOP_SINGLE_DEMO',
                  geometry_and_identity_audit_passed=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);args=parser.parse_args()
    config_path=Path(args.config).resolve();config=json.loads(config_path.read_text());config['config_path']=str(config_path)
    unit=Path(config['unit_root']);unit.mkdir(parents=True,exist_ok=True)
    result=dict(status='running',completed=[],parent_exit_authoritative=True,scientific_verdict='UNASSESSED',
                config_sha256=sha(config_path),canonical_geometry_frozen=True,derived_geometry_edit_allowed=True)
    budget=Budget(config);signal.signal(signal.SIGALRM,on_alarm)
    rc=0
    try:execute(config,result,budget)
    except Exception as exc:
        rc=1;result.update(status='failed_or_partial',error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        result['timing']=budget.receipt();result['runner_returncode']=rc
        write_json(unit/'RUN_RESULT.json',result)
        print(json.dumps({'status':result['status'],'completed':result['completed'],'returncode':rc}),flush=True)
    return rc

if __name__=='__main__':raise SystemExit(main())
