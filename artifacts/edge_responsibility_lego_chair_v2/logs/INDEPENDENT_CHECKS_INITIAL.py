"""Read-only validation of actual outputs; identities alone do not prove a scorer."""
import json,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/edge_responsibility_lego_chair_v2/src'))
from runtime import ART,sha,source_hashes,atomic_json

def main():
    frozen=json.loads((ART/'INPUT_FREEZE.json').read_text());tests=[]
    tests.append(dict(name='original protected bytes',passed=all(sha(p)==h for p,h in frozen['protected_sha256'].items()),files=len(frozen['protected_sha256'])))
    tests.append(dict(name='frozen production code',passed=source_hashes()==frozen['source_hashes']))
    for p in (ART/'seals').glob('*.json'):
        obj=json.loads(p.read_text());tests.append(dict(name='sealed unit '+obj['unit'],passed=all(sha(ROOT/q)==h for q,h in obj['outputs'].items())))
    synth=json.loads((ART/'results/synthetic.json').read_text())
    tests.append(dict(name='24 actual native Gaussian frames',passed=synth['frames']==24 and len(synth['records'])==24))
    tests.append(dict(name='24 signed/background/total weight identities',passed=all(r['native_identity_pass'] for r in synth['records'])))
    tests.append(dict(name='preserve failed native fixtures and localization',passed=not synth['gate1_pass'] and len([r for r in synth['records'] if not r['presence_absence_pass']])==3))
    branching=[];flat_unverified={}
    for scene in ['lego','chair']:
        scores=json.loads((ART/'results'/f'{scene}_scores.json').read_text())
        val=json.loads((ART/'results'/f'{scene}_independent.json').read_text())
        cal=json.loads((ART/'results'/f'{scene}_calibration.json').read_text())
        loc=json.loads((ART/'results'/f'{scene}_localization_appendix.json').read_text())
        tests.append(dict(name=scene+' native calibrated full SH3',passed=cal['pass']))
        tests.append(dict(name=scene+' aggregate cache SHA',passed=sha(ROOT/scores['aggregate_path'])==scores['aggregate_sha256']))
        tests.append(dict(name=scene+' reference-only evidence ablation',passed=set(scores['evidence_only_ablation'])=={'old_broad','old_trusted_equal'}))
        tests.append(dict(name=scene+' fixed evidence weighting ablation',passed=set(scores['segment_equal_vs_arclength_ablation'])=={'old_trusted_equal','old_trusted_arc'}))
        tests.append(dict(name=scene+' actual independent parameter probes',passed=all(r['independent_probes'][p]['delta']==.006 and r['construction_probes'][p]['delta']==.01 and r['independent_probes'][p]['direction']!=r['construction_probes'][p]['direction'] for r in val['groups'] for p in ['dc','scale'])))
        tests.append(dict(name=scene+' equal group kernel count / random strata',passed=all(r['count']==64 and r['random_matching']['joint_strata_equal'] for r in val['groups'])))
        tests.append(dict(name=scene+' response selection frozen before independent test',passed=val['response_selection_freeze_sha256']==sha(ART/f'{scene}_RESPONSE_SELECTION_FREEZE.json')))
        tests.append(dict(name=scene+' at least four actual native selected/subset sheets',passed=len(list((ART/'media'/scene).glob('r_*/sheet.png')))>=4))
        tests.append(dict(name=scene+' source models unchanged',passed=sha(frozen['scenes'][scene]['model'])==frozen['scenes'][scene]['model_sha256']))
        flat_unverified[scene]=sorted({r['view'] for r in loc['rows'] if r['flat_cost_status']=='UNVERIFIED_NO_MATCHED_FLAT_ROI'})
        for i,r in enumerate(cal['views']):
            for param,d in r['parameter_derivatives'].items():
                branching.append(dict(scene=scene,view_index=i,param=param,fd_error=d['abs_residual'],half_fd_error=d['half_abs_residual'],
                     native=d['native_parameter_derivative'],fd=d['finite_difference'],half_fd=d['half_delta_fd'],
                     numerically_consistent=d['abs_residual']<max(.0005,abs(d['finite_difference'])*.3)))
    extra=json.loads((ART/'results/synthetic_kernel_score_appendix.json').read_text())
    tests.append(dict(name='native synthetic score comparisons on all 24 fixed constructs',passed=extra['frames']==24 and all(set(r['methods'])=={'old_relative','absolute','signed','matched_random'} for r in extra['records'])))
    hidden=next(r for r in extra['additional_native_fixtures'] if r['construct']['id']=='fully_occluded_full_frame')
    cancel=next(r for r in extra['additional_native_fixtures'] if r['construct']['id']=='signed_cancellation')
    tests.append(dict(name='additional truly hidden rear full-image zero',passed=hidden['pass_all']))
    tests.append(dict(name='large signed cancellation separately measured',passed=cancel['pass_all'] and cancel['signed']['cancellation']>.9))
    # A real branch failure is exposed, rather than passed by an increased tolerance.
    scale=cancel['parameter_derivatives']['scale']
    tests.append(dict(name='unstable cancellation scale branch exposed',passed=abs(scale['fd']-scale['half_fd'])>.01 and scale['fd_error']>.01))
    final=json.loads((ART/'FINAL.json').read_text())
    tests.append(dict(name='failed gates never trigger optimization',passed=final['optimization_status']=='NOT_RUN' and all(not all(v['gates']['gates']) for v in final['scenes'].values())))
    result=dict(status='CHECKS_PASS' if all(t['passed'] for t in tests) else 'CHECKS_FAIL',checks=tests,
                calibration_native_parameter_branch_records=branching,
                missing_flat_ROI_views=flat_unverified,
                identity_check_is_not_predictor_validation=True,original_failed_scientific_gates_preserved=True,
                independent_human_visual_GO='PENDING',original_TEST_RGB_read=False,
                additional_cancellation_scale_branch='UNSTABLE_RESPONSE',
                cancellation_scale_gradient=scale['native_param_derivative'],cancellation_scale_fd=scale['fd'],
                cancellation_scale_half_fd=scale['half_fd'])
    atomic_json(ART/'INDEPENDENT_ENGINEERING_AUDIT.json',result)
    print(json.dumps(dict(status=result['status'],checks=len(tests),failed=[t['name'] for t in tests if not t['passed']]),ensure_ascii=False))
    return 0 if result['status']=='CHECKS_PASS' else 1

if __name__=='__main__':sys.exit(main())
