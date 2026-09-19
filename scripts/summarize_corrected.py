#!/usr/bin/env python3
"""Assemble reports only after complete per-scene execution and access audit."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.foundation import freeze_json
from src.corrected_execution import scope_decisions
from src.corrected_reporting import sha256,render_results,check_markdown


def read(path):return json.loads(Path(path).read_text())


def main():
    root=ROOT/'out/multiscene_foundation_corrected';cfg=read(root/'config.json');audit=read(root/'ACCESS_AUDIT.json')
    if not audit['passed']:raise RuntimeError('access validity blocker must be resolved before scientific report')
    scenes=[];quality=[];doses=[];arms=[];calibration=[]
    for scene in cfg['scene_order']:
        eligibility=read(root/f'scenes/{scene}/eligibility.json')
        for seed in cfg['training']['seeds']:
            q=read(root/f'quality/{scene}/seed_{seed}/measurements/quality.json')
            quality.append(dict(scene=scene,seed=seed,**q))
            calibration.extend(dict(scene=scene,asset=f'seed_{seed}',stage='quality',**r) for r in q['calibration'])
        controlled=read(root/f'controlled/{scene}/measurements/qualification.json')
        doses.extend(dict(scene=scene,**v) for v in controlled['variants'])
        calibration.extend(dict(scene=scene,asset='parent',stage='controlled',**r) for r in controlled['calibration'])
        for v in controlled['variants']:calibration.extend(dict(scene=scene,asset=v['name'],stage='controlled',**r) for r in v['calibration'])
        row=dict(scene=scene,eligible=eligibility['eligible'],route_a=eligibility['route_a'],route_b=eligibility['route_b'],qualified_doses=len(eligibility['qualified_doses']),eligibility=eligibility)
        if eligibility['eligible']:
            local=root/f'local/{scene}';execution=read(local/'execution_complete.json');ev=root/f'evaluation/{scene}'
            for task in ['machine','surface','visual']:read(ev/task/'complete.json')
            machine=read(ev/'machine/machine.json');visual=read(ev/'visual/complete.json');video=read(ev/'visual/video_status.json');dev=read(ev/'visual/DEV_render_equivalence.json')
            if machine['access_status']!='PENDING_FINAL_NATIVE_OPEN_AUDIT':raise ValueError('unexpected machine provenance state')
            row.update(verdict=machine['verdict'],invariance_scope=machine['invariance_scope'],machine=machine['machine'],manual='PENDING_INDEPENDENT_REVIEW',query_count=machine['baseline_summary']['query_count'],mode_count=machine['baseline_summary']['mode_count'],accepted_count=machine['baseline_summary']['accepted_count'],machine_detail=machine,execution=execution,visual=visual,video=video,access_status='PASS_FINAL_NATIVE_OPEN_AUDIT',DEV_diagnostics=dict(rows=len(dev['rows']),calibration_views=len(dev['calibration']),calibration_passed=all(c['passed'] for c in dev['calibration']),controlled_rows=sum(not v['asset'].startswith('seed_') for v in dev['rows']),controlled_equivalence_passed=all(v['passed'] for v in dev['rows'] if not v['asset'].startswith('seed_')),independent_seed_rows=sum(v['asset'].startswith('seed_') for v in dev['rows']),independent_seed_is_not_subject_to_synthetic_40dB_gate=True))
            for group in [local/'F',local/'C',*sorted((local/'repeats').glob('*'))]:
                for p in sorted(group.glob('*/summary.json')):arms.append(dict(scene=scene,path=str(p.parent.relative_to(root)),**read(p)))
        else:
            photometric_fail=all(not all(g['passed'] for g in q['groups']) for q in eligibility['quality'])
            row.update(verdict='INSUFFICIENT_POSTERIOR_QUALITY' if photometric_fail else 'ENGINEERING_NOT_READY',invariance_scope='NONE',manual='NOT_REACHED',query_count=0,mode_count=0,accepted_count=0)
        scenes.append(row)
    totals=dict(posteriors=len(quality),doses=len(doses),quality_rows=sum(len(q['rows']) for q in quality),dose_rows=sum(len(d['rows']) for d in doses),eligible_scenes=sum(s['eligible'] for s in scenes),eligible_posteriors=sum(q['eligibility']['passed'] for q in quality),qualified_doses=sum(d['eligibility']['passed'] for d in doses),calibration_views=len(calibration),local_arms=len(arms),local_queries=sum(a['query_count'] for a in arms),local_modes=sum(a['mode_count'] for a in arms),local_accepted=sum(a['accepted_count'] for a in arms),local_raw_accepted=sum(a['raw_accepted_count'] for a in arms),local_rejected=sum(a['rejected_count'] for a in arms),local_ambiguous=sum(a['ambiguous_count'] for a in arms))
    assert (totals['posteriors'],totals['doses'],totals['quality_rows'],totals['dose_rows'])==(8,36,512,1152)
    totals['local_rejected_nonambiguous']=totals['local_rejected']-totals['local_ambiguous']
    totals['qualification_calibration_views']=totals.pop('calibration_views')
    totals['DEV_calibration_views']=sum(s.get('DEV_diagnostics',{}).get('calibration_views',0) for s in scenes)
    totals['DEV_controlled_rows']=sum(s.get('DEV_diagnostics',{}).get('controlled_rows',0) for s in scenes)
    expected_arms=sum(40+5*(len(s['execution']['assets'])-1) for s in scenes if s['eligible'])
    if totals['local_arms']!=expected_arms:raise ValueError('missing registered local arm')
    result=dict(protocol=dict(config_sha256=sha256(root/'config.json'),prereg_sha256=sha256(root/'PREREG.md'),prereg_commit='fb4488e',start_head=cfg['start_head'],nonblind=True,sampling=cfg['sampling']),totals=totals,scenes=scenes,scope=scope_decisions(scenes),quality=quality,doses=doses,calibration=calibration,local_arms=arms,manual='PENDING_INDEPENDENT_REVIEW',access_audit={k:audit[k] for k in ['passed','trace_count','forbidden_successes','unparsed_open_lines']},limitations=[
        'The native800/area400 correction was motivated by a known post-hoc diagnostic. Thresholds, scenes, seeds, all 36 doses and checkpoint identities remain frozen.',
        'Lego and Chair are separate core tests. Expanded generality requires at least three eligible scenes including Drums or Ficus; ineligible scenes are scope limitations, not scientific negatives for B.',
        'All image-quality groups and backgrounds remain required. A stock/native equality pass does not waive a separate native replay calibration failure.',
        'Image-only, old PCA, shifted-association and random-axis controls are reported with original denominators. Empty image-only output cannot support PIVOT_IMAGE_ONLY.',
        'The copied TRAIN annotations were authored by the implementing assistant and are not independent. G2 manual precision, G4 independently measured GS benefit and G5 review remain pending.',
        'The video stage is reached only when the per-scene G1 and G2 machine gates pass. Failure PNGs, all-mode projections and full-depth profiles are generated regardless.',
        'Resource-only interrupted attempts are retained. The final single-thread forked execution is compared with completed serial arms; the earlier four-thread eigensolver attempt has separately quantified floating-point differences.',
        'Local surface-sample fits are diagnostic only. They neither generate nor rescue any accepted linelet. No subsequent UDF or curve investment is authorized by a STOP_B result.'
    ])
    freeze_json(root/'results.json',result)
    text=render_results(result);check_markdown(result,text);(root/'RESULTS.md').write_text(text)
    print(json.dumps(dict(totals=totals,scope=result['scope']),indent=2))

if __name__=='__main__':main()
