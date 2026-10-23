"""Validate completed outputs before recording explicit resume skips."""
import runtime
from runtime import js,sha,now,OUTPUT_ROOT
from pathlib import Path
import json,os,tempfile
import numpy as np
from run_expanded_unit import load
from run_path_unit import read_npz,load_scene
from membership import load_binding,resolve
from path_control import resolve_path
from footprint import resolve_footprint
from validate_path_unit import audit_trace
from run_unit import metrics

unit=OUTPUT_ROOT/'units/unit_005';parent=OUTPUT_ROOT/'orchestration/continuation_001'
assert Path(tempfile.gettempdir())==parent/'scratch'
assert os.environ['CUDA_VISIBLE_DEVICES']=='' and len(os.sched_getaffinity(0))<=2
with tempfile.TemporaryDirectory() as scratch:assert Path(scratch).parent==parent/'scratch'
p=load(unit)
before=json.loads((parent/'UNIT005_FILES_BEFORE.json').read_text())
errors=[name for name,h in before.items() if sha(name)!=h];assert not errors,errors
for name,h in p['input_hashes'].items():assert sha(name)==h,name
for name,h in p['source_hashes'].items():assert sha(unit/'source_snapshot'/name)==h,name
out=unit/'continuation_001';out.mkdir(exist_ok=True)
skips=[]
def skip(name,outputs,check):
    file=unit/'logs'/(name+'.receipt.json');r=json.loads(file.read_text())
    assert r['returncode']==0 and r['interrupt_signals']==[]
    skips.append(dict(stage=name,receipt_sha256=sha(file),original_child_returncode=0,
        reason=check,output_hashes={str(f.relative_to(unit)):sha(f) for f in outputs}))
s,a,mesh,meta,strokes,paths=load_scene(p,'chair');root=unit/'results/chair';m=p['membership']
b,_=load_binding(root/'SOURCE_BINDING.npz',s['source']['sha256'],len(a['means']))
q=resolve(b['per_view_score'],m['min_exposure'],m['min_views'],m['min_fraction'],m['view_mass'])
for k,v in q.items():np.testing.assert_array_equal(v,b[k])
pb=read_npz(root/'PATH_BINDING.npz');q=resolve_path(pb['per_view_total'],pb['per_view_accepted'],b)
for k,v in q.items():np.testing.assert_array_equal(v,pb[k])
fp=read_npz(root/'FOOTPRINT_BINDING.npz');q=resolve_footprint(fp['per_view_mass'],pb)
for k,v in q.items():np.testing.assert_array_equal(v,fp[k])
cand=read_npz(root/'CANDIDATES.npz');np.testing.assert_array_equal(cand['specific'],q['strength'])
skip('build_chair',[root/name for name in ('SOURCE_BINDING.npz','PATH_BINDING.npz','FOOTPRINT_BINDING.npz','CANDIDATES.npz','BUILD_AUDIT.json')],
     'Source/config/input hashes match; every saved original-row M1/path/footprint result independently re-resolved exactly.')
totals={k:0. for k in p['diagnostic']['arms']}
for i,c in enumerate(s['budget_cameras']):
    folder=root/c['view'];budget=json.loads((folder/'BUDGET.json').read_text())
    files=[folder/'BUDGET.json']
    for arm in totals:
        file=folder/f'budget_{arm}.npz';d=read_npz(file)['delta'];v=float(np.abs(d).sum())
        assert v==budget['full_image_L1'][arm];totals[arm]+=v;files.append(file)
    skip('budget_chair_'+str(i),files,'All four actual-render saved RGB delta L1 budgets reconstructed exactly.')
match=json.loads((root/'BUDGET_MATCH.json').read_text());assert totals==match['full_image_unit_strength_L1']
assert match['target']==.85*min(totals.values())
sel=read_npz(root/'EDIT_SELECTION.npz')
for arm in totals:np.testing.assert_array_equal(sel[arm],cand[arm]*match['scales'][arm])
for name,h in json.loads((root/'BINDING_LOCK.json').read_text())['files'].items():assert sha(root/name)==h
skip('match_chair',[root/'EDIT_SELECTION.npz',root/'BUDGET_MATCH.json',root/'BINDING_LOCK.json'],
     'Locked strengths exactly equal candidates times frozen BUILD-effect scales; no re-fitting.')
c=s['cameras'][0];folder=root/c['view'];f=read_npz(folder/'baseline.npz');t=read_npz(folder/'trace.npz')
check=audit_trace(a,c,t,f);row=json.loads((folder/'EVALUATION.json').read_text())
intent=np.where(f['proxy_regions']>0,1,0);intent[f['path_mask']]=4
for arm in totals:
    e=read_npz(folder/f'tint_{arm}.npz');assert metrics(f['rgb'],e['rgb'],intent,f['contribution'],p)==row['arms'][arm]
skip('evaluate_chair_0',[f for f in folder.iterdir() if f.is_file()],
     'Completed child rc0; original-ID remapping/alpha/T/full-SH RGB audited; all four saved edit metrics exact. Full saved-evidence validation follows.')
failed=json.loads((unit/'logs/evaluate_chair_1.receipt.json').read_text());assert failed['returncode']==-15
assert (unit/'interrupted_chair_view_1').is_dir() and not (root/s['cameras'][1]['view']).exists()
failures={name:dict(path=str(OUTPUT_ROOT/'orchestration/unit_005'/name/'EXIT.json'),
    receipt=json.loads((OUTPUT_ROOT/'orchestration/unit_005'/name/'EXIT.json').read_text())) for name in ('attempt_0','recovery_1')}
result=dict(utc=now(),protocol_sha256=sha(unit/'PROTOCOL.json'),parent_before_file_count=len(before),all_existing_files_exact=True,
    all_frozen_inputs_and_source_exact=True,skipped_stages=skips,completed_Chair_view_check=check,
    preserved_failed_science_stage=failed,preserved_engine_exits=failures,
    preserved_outer_exit=json.loads((unit/'logs/PIPELINE_INTERRUPTION.json').read_text()),
    missing_stages=['Chair evaluation 1,2,3','Lego build, budgets 0..3, match, evaluations 0..3','validation','query/replay/media','final handoff'],
    runtime_wrapper_check=dict(continuation_scratch_verified=True,cpu_affinity_at_most_2=True,CUDA_disabled=True))
js(out/'RESUME_INVENTORY.json',result)
progress=dict(actual_advance='Chair expanded original-row M1/path/footprint bindings and one actual evaluation validated for reuse.',
    reasoning='Resume only missing stages under identical scientific protocol; incomplete Lego and remaining Chair views are not counted as complete.')
js(unit/'STATUS.json',dict(unit='unit_005',stage='resuming_missing_frozen_stages',execution_state='partial',work_in_progress=True,
    scientific_verdict='UNCERTIFIED_CPU_MAPPING',gaussian_link_progress=progress,artifacts={'resume_inventory':'continuation_001/RESUME_INVENTORY.json'},
    original_failed_exits_preserved=True,scientific_seal=False,updated_utc=now()))
js(unit/'NEXT.json',dict(action='stop',recommended_next_step='Finish this bounded unit; any further experiment requires a new authorization.',
    gaussian_link_progress=progress,reasoning='Current authorization is exactly one resumed unit005; no unit006.'))
(unit/'REPORT_ZH.md').write_text('# Unit005 续跑中间状态\n\n已核对源、协议、输入与所有旧文件哈希。Chair BUILD、四个预算、配平、首个评估均有rc0并通过数组一致性审计，明确跳过。旧配额rc1、外层143、Chair视角1子进程-15及未完成输出均保留。其余步骤尚未完成，当前为partial，scientific_seal=false。最终结论以完成后的本报告及STATUS为准。\n')
print(json.dumps(dict(skipped=[s['stage'] for s in skips],existing_files=len(before),protocol_unchanged=True),default=runtime.json_default),flush=True)
