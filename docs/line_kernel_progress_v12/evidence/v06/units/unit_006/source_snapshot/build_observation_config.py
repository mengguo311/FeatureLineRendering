"""Unit006 build-only hash binding and config; no numerical scene execution."""
from pathlib import Path
import json,hashlib,argparse
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101')
PREV=O/'units/unit_005'
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
def prepare(u):
    u=Path(u);assert u==O/'units/unit_006';assert not (u/'RUN_REQUEST.json').exists(),'ALREADY_FROZEN'
    expected='0a7e8e75c4a378c6ccaf39d26e9b3cfad5f5f31bf6e13bfb461b58c8db003701';assert sha(PREV/'CONFIG.json')==expected
    c=json.loads((PREV/'CONFIG.json').read_text());decision=json.loads((u/'DECISION.json').read_text());frozen=json.loads((PREV/'PARENT_RUN_FROZEN.json').read_text())
    for p,h in c['input_files'].items():assert sha(p)==h,'INPUT_HASH '+p
    for p,h in c['helper_files'].items():assert sha(p)==h,'HELPER_HASH '+p
    for p,snap in frozen['immutable_source_snapshot'].items():
        assert sha(snap)==frozen['source_files'][p];assert sha(S/Path(p).name)==sha(snap),'OLD_SOURCE_CHANGED '+p
    refs=[PREV/'CONFIG.json',PREV/'PARENT_RUN_FROZEN.json']+[Path(p) for p in frozen['immutable_source_snapshot'].values()]
    for sub in ['readiness','models','banks','stages/greedy','stages/joint']:
        for cp in sorted((PREV/'scenes/scan24'/sub).rglob('CHECKPOINT.json')):
            rec=json.loads(cp.read_text());assert rec['complete'] and rec['config_sha256']==expected;refs.append(cp)
            for name,h in rec['files'].items():assert sha(cp.parent/name)==h;refs.append(cp.parent/name)
    refs.append(PREV/'scenes/scan24/diagnostics/SELECTION.json')
    for p in refs:c['input_files'][str(p)]=sha(p)
    base=Path(c['prior_unit']);base_binding=c['previous_config_sha256']
    c.update(unit=str(u),output=str(u),decision_path=str(u/'DECISION.json'),decision_sha256=sha(u/'DECISION.json'),scientific_decision=decision['recommended_next_step'],changed_variable=decision['changed_variable'],falsification=decision['falsification'],prior_unit=str(PREV),previous_config_sha256=expected,previous_arms={a:str(PREV/'scenes/scan24/stages'/a) for a in ('greedy','joint')},prior_selection=str(PREV/'scenes/scan24/readiness/SELECTION.json'),prior_diagnostics=str(PREV/'scenes/scan24/diagnostics/SELECTION.json'),base_bank_unit=str(base),base_bank_config_sha256=base_binding,expected_old_hypotheses=11,expected_control_hypotheses=12,max_seconds=1800,absolute_deadline_jst='2026-11-01T09:38:00+09:00')
    c.pop('fit_source',None);c['model_fit']=dict(enabled=False,maximum_attempts=0,source='unit005 closed MODEL.json files',expected_models=38,metric_rtol=0,metric_atol=1e-10)
    c['implementation_details'].update(old_bank='unit005 exact12 hypotheses/selectors/full membership replay; retain unit004 original11 unchanged',finite_domain_witness='all original kernel means/p; extended_s inside[0,L]+/-1e-8; oldq samples diagnostic only',monotonicity='unchanged <=1p original leaf q samples; forward or reverse',diagnostics='oldq and centers left/right overshoot; center counts/worst rows; old/new result; original support endpoint unclamped/clamped coordinates',fallback='control mismatch blocks promotion; solver budget fallback preserves M4; incomplete stages not resumed',model_library_failure='saved model/version/metric mismatch blocks, no retries or fits')
    c['new_candidate_generation']=False;c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    (u/'CONFIG.draft.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
    (u/'INPUT_HASH_RECEIPT.json').write_text(json.dumps(dict(input_files=c['input_files'],helper_files=c['helper_files'],snapshot_files_verified=len(frozen['source_files']),prior_source_unchanged=True,full_asset_science_run=False),indent=2)+'\n')
    print(json.dumps(dict(config_draft=str(u/'CONFIG.draft.json'),decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),input_files=len(c['input_files']))))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',required=True);a=p.parse_args();prepare(a.unit)
