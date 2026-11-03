"""BUILD configuration and immutable input verification only; no numerical scene execution."""
from pathlib import Path
import json,hashlib,argparse
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101');PREV=O/'units/unit_004'
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(2**20),b''):h.update(block)
    return h.hexdigest()
def prepare(u):
    u=Path(u);assert u==O/'units/unit_005';assert not (u/'RUN_REQUEST.json').exists(),'ALREADY_FROZEN'
    expected='8833bdc5483c456e7803effe5b88f82df0d7c730e6d2119fe8b2dd6d9f223b1c';assert sha(PREV/'CONFIG.json')==expected
    c=json.loads((PREV/'CONFIG.json').read_text());decision=json.loads((u/'DECISION.json').read_text());frozen=json.loads((PREV/'PARENT_RUN_FROZEN.json').read_text())
    for p,h in c['input_files'].items():assert sha(p)==h,'INPUT_HASH_MISMATCH '+p
    for p,h in c['helper_files'].items():assert sha(p)==h,'HELPER_HASH_MISMATCH '+p
    for p,snap in frozen['immutable_source_snapshot'].items():assert sha(snap)==frozen['source_files'][p],'SNAPSHOT_HASH_MISMATCH '+snap
    for name in ('adapter.py','runtime_io.py','geometry_base.py','port_paths.py','delivery.py','paired_delivery.py','overlap_model.py','overlap_delivery.py','overlap_runner.py'):assert sha(S/name)==sha(PREV/'source_snapshot'/name),'PINNED_CORE_CHANGED '+name
    refs=[PREV/'CONFIG.json',PREV/'PARENT_RUN_FROZEN.json',PREV/'scenes/scan24/readiness/SELECTION.json']+[Path(p) for p in frozen['immutable_source_snapshot'].values()]
    for arm in ('greedy','joint'):
        out=PREV/'scenes/scan24/stages'/arm;cp=json.loads((out/'CHECKPOINT.json').read_text());assert cp['complete'] and cp['config_sha256']==expected
        refs.append(out/'CHECKPOINT.json')
        for name,h in cp['files'].items():assert sha(out/name)==h;refs.append(out/name)
    for p in refs:c['input_files'][str(p)]=sha(p)
    for k in ('expected_ambiguity_components','expected_scope_audit','prior_reference_config_sha256','paired_progress'):c.pop(k,None)
    c.update(unit=str(u),output=str(u),decision_path=str(u/'DECISION.json'),decision_sha256=sha(u/'DECISION.json'),scientific_decision=decision['recommended_next_step'],changed_variable=decision['changed_variable'],falsification=decision['falsification'],previous_config_sha256=expected,previous_arms={a:str(PREV/'scenes/scan24/stages'/a) for a in ('greedy','joint')},expected_candidate_records=112414,expected_successful_overlap=5452,max_components=8,decision_carrier_cap=128,overlap_priority_ids=[53254,334283,10975,273281,347158],reference_leaf_groups={'53254':[53254,334283],'10975':[10975,273281,347158],'201906':[201906,202626]},max_seconds=1800,absolute_deadline_jst='2026-11-01T09:38:00+09:00')
    c['stage_budgets']=dict(readiness_and_banks_seconds=600,solver_seconds=600,mapping_deadline_elapsed_seconds=1200,delivery_reserved_seconds=600,total_seconds=1800)
    c['solver']=dict(per_context_seconds=120,total_seconds=600,mip_rel_gap=0,threads=2,parallel=False,scientific_cost_perturbation=False)
    for sub in ('readiness','banks','progress'):
        for cp in sorted((PREV/'scenes/scan24'/sub).rglob('CHECKPOINT.json')):
            record=json.loads(cp.read_text());assert record['complete'] and record['config_sha256']==expected
            c['input_files'][str(cp)]=sha(cp)
            for name,h in record['files'].items():
                p=cp.parent/name;assert sha(p)==h;c['input_files'][str(p)]=h
    for p in [PREV/'scenes/scan24/diagnostics/SELECTION.json']:
        c['input_files'][str(p)]=sha(p)
    core=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_018/source_snapshot/core.py')
    assert sha(core)=='c1565d2c33ee1f75e1a58469f14d8e153a138eb5f3c0dc73fbbcc5a9ab20e512'
    c.update(prior_unit=str(PREV),prior_selection=str(PREV/'scenes/scan24/readiness/SELECTION.json'),prior_diagnostics=str(PREV/'scenes/scan24/diagnostics/SELECTION.json'),fit_source=str(core),expected_contexts=8,expected_decision_leaves=42,expected_selected_pairs=38,expected_old_hypotheses=11,unit003_arms={a:str(O/'units/unit_003/scenes/scan24/stages'/a) for a in ('greedy','joint')})
    c['helper_files'][str(core)]=sha(core)
    c['model_fit']=dict(enabled=True,maximum_attempts=38,source=str(core),source_sha256=sha(core),source_import='AST definitions only; no common or producer execution',metric_rtol=0,metric_atol=1e-10,rows_order='canonical original a then b',proposal='original proposal(a,b,False); overlap only',kernel_cap=8192,knot_cap=128,knot_spacing_p=4,IRLS_iterations=3,Huber_delta_p=.5,occupied_bin_p=1)
    c['new_candidate_generation']=False
    c['implementation_details']=dict(old_bank='exact11 old hypotheses; both old selectors replayed before augmentation',model_key='old:[0,anchor]; new:[1,canonical_a,canonical_b]',host='original proposal host; zero benefit contribution; validated like every other member',mandatory='both generating leaves; every compatible donor prefix containing partner',donors='original successful overlap neighbors of host only; cost then ID',benefit='sum_donors(2-(max_residual+tangent_max/30))',member_validation=dict(residual_max_p=1,residual_q95_p=.5,tangent_degrees=30,sampling_p=1,finite_domain_tolerance_p=1e-8,monotone_allow_reverse=True),support='all original leaf intervals projected to auxiliary model, including host',guards='unit004 complete group guards unchanged,8192kernel cap,parallel,branch,turn30/window8p60/contact0.5/gap1.5',activation=dict(seedlets=3,kernels=6,support_p=4),fallback='affected component retains unit004 choices; partial bank never promoted',model_library_failure='mismatch blocks component; retain failures without retries',resume='only hash-verified complete stages',physical_truth=False,threshold_sweeps=False)
    c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    (u/'CONFIG.draft.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
    (u/'INPUT_HASH_RECEIPT.json').write_text(json.dumps(dict(input_files=c['input_files'],helper_files=c['helper_files'],source_snapshot_files_verified=len(frozen['source_files']),pinned_core_unchanged=True,science_run=False),indent=2)+'\n')
    print(json.dumps(dict(config_draft=str(u/'CONFIG.draft.json'),decision_sha256=c['decision_sha256'],input_files=len(c['input_files']),source_files=len(c['source_files']))))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',required=True);a=p.parse_args();prepare(a.unit)
