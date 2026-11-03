"""BUILD configuration and immutable input verification only; no numerical scene execution."""
from pathlib import Path
import json,hashlib,argparse
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101');PREV=O/'units/unit_003'
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(2**20),b''):h.update(block)
    return h.hexdigest()
def prepare(u):
    u=Path(u);assert u==O/'units/unit_004';assert not (u/'RUN_REQUEST.json').exists(),'ALREADY_FROZEN'
    expected='739636ada8e953befbb72aa4dc82c95a9536a0e849216fa3b31eafd2d2ec5e2f';assert sha(PREV/'CONFIG.json')==expected
    c=json.loads((PREV/'CONFIG.json').read_text());decision=json.loads((u/'DECISION.json').read_text());frozen=json.loads((PREV/'PARENT_RUN_FROZEN.json').read_text())
    for p,h in c['input_files'].items():assert sha(p)==h,'INPUT_HASH_MISMATCH '+p
    for p,h in c['helper_files'].items():assert sha(p)==h,'HELPER_HASH_MISMATCH '+p
    for p,snap in frozen['immutable_source_snapshot'].items():assert sha(snap)==frozen['source_files'][p],'SNAPSHOT_HASH_MISMATCH '+snap
    for name in ('adapter.py','runtime_io.py','geometry_base.py','port_paths.py','delivery.py','paired_delivery.py'):assert sha(S/name)==sha(PREV/'source_snapshot'/name),'PINNED_CORE_CHANGED '+name
    refs=[PREV/'CONFIG.json',PREV/'PARENT_RUN_FROZEN.json',PREV/'tests/REAL_COMPONENT.npz']+[Path(p) for p in frozen['immutable_source_snapshot'].values()]
    for arm in ('greedy','joint'):
        out=PREV/'scenes/scan24/stages'/arm;cp=json.loads((out/'CHECKPOINT.json').read_text());assert cp['complete'] and cp['config_sha256']==expected
        refs.append(out/'CHECKPOINT.json')
        for name,h in cp['files'].items():assert sha(out/name)==h;refs.append(out/name)
    for p in refs:c['input_files'][str(p)]=sha(p)
    for k in ('expected_ambiguity_components','expected_scope_audit','prior_reference_config_sha256','paired_progress'):c.pop(k,None)
    c.update(unit=str(u),output=str(u),decision_path=str(u/'DECISION.json'),decision_sha256=sha(u/'DECISION.json'),scientific_decision=decision['recommended_next_step'],changed_variable=decision['changed_variable'],falsification=decision['falsification'],previous_config_sha256=expected,previous_arms={a:str(PREV/'scenes/scan24/stages'/a) for a in ('greedy','joint')},expected_candidate_records=112414,expected_successful_overlap=5452,max_components=8,decision_carrier_cap=128,overlap_priority_ids=[53254,334283,10975,273281,347158],reference_leaf_groups={'53254':[53254,334283],'10975':[10975,273281,347158],'201906':[201906,202626]},max_seconds=1800,absolute_deadline_jst='2026-11-01T09:38:00+09:00')
    c['stage_budgets']=dict(readiness_and_banks_seconds=600,solver_seconds=600,mapping_deadline_elapsed_seconds=1200,delivery_reserved_seconds=600,total_seconds=1800)
    c['solver']=dict(per_context_seconds=120,total_seconds=600,mip_rel_gap=0,threads=2,parallel=False,scientific_cost_perturbation=False)
    c['model_fit']=False;c['new_candidate_generation']=False
    c['implementation_details']=dict(representation='immutable original finite anchor plus whole observation leaves; no topology degree consumed',selection='all-successful-overlap closure; eight ranked components; oversized whole NOT_RUN',donor_validation=dict(all_original_kernel_rows=True,residual_max_p=1,residual_q95_p=.5,tangent_degrees=30,donor_sample_spacing_p=1,finite_domain_tolerance_p=1e-8,monotone_allow_reverse=True,cost='residual_max+tangent_max/30'),bank='every nonempty compatible-donor prefix sorted by cost then ID; no pruning; all anchor interpretations retained',benefit='sum_donors(2-cost); anchor contributes zero',group_guards=dict(max_kernels=8192,parallel='unchanged pinned predicate',branch='unchanged original predicate; anchor knots; reps in anchor/donor-prefix leaf order',vertex_turn=30,window_p=8,window_turn=60,contact_p=.5,unsupported_gap_p=1.5,EPS=1e-8),support='leaf supported-interval endpoints mapped to finite anchor; union deduplicated; no extrapolation/no bridges',activation=dict(seedlets=3,kernels=6,support_p=4),aux='preserve predecessor membership aux; separately store up to two competing hypothesis references per leaf',fallback='M4 identities outside or unselected; report unit003 withdrawals separately',resume='hash-verified complete stages only; incomplete files preserved and blocked',diagnostics='same original rows in both arms; inherited RGB8<254 union bbox/pad16/clip/4xnearest',physical_truth=False,threshold_sweeps=False)
    c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    (u/'CONFIG.draft.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
    (u/'INPUT_HASH_RECEIPT.json').write_text(json.dumps(dict(input_files=c['input_files'],helper_files=c['helper_files'],source_snapshot_files_verified=len(frozen['source_files']),pinned_core_unchanged=True,science_run=False),indent=2)+'\n')
    print(json.dumps(dict(config_draft=str(u/'CONFIG.draft.json'),decision_sha256=c['decision_sha256'],input_files=len(c['input_files']),source_files=len(c['source_files']))))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',required=True);a=p.parse_args();prepare(a.unit)
