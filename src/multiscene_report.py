"""Conservative route decisions and cross-checkable prerequisite reporting."""
import re
from pathlib import Path
import numpy as np
from .foundation import qualification_metrics


def pair_measurements(paths,cfg):
    rows=[]
    for split in ['train','val']:
        for i in cfg['splits']['TRAIN']:
            with np.load(Path(paths[0])/f'{split}_{i:03d}.npz') as a, np.load(Path(paths[1])/f'{split}_{i:03d}.npz') as b:
                roi=a['roi']
                if not np.array_equal(roi,b['roi']):raise ValueError('seed ROI mismatch')
                for bg in [0,1]:
                    gt=a[f'gt_{bg}'];aa=a[f'rgb_{bg}'];bb=b[f'rgb_{bg}']
                    if not np.array_equal(gt,b[f'gt_{bg}']):raise ValueError('seed ground-truth mismatch')
                    metrics=qualification_metrics(aa,bb,roi)
                    rows.append(dict(split=split,view=i,background=bg,**metrics,
                        rmse_seed0=float(np.sqrt(np.mean((aa[roi]-gt[roi])**2))),
                        rmse_seed1=float(np.sqrt(np.mean((bb[roi]-gt[roi])**2))),
                        rmse_pair=float(np.sqrt(metrics['mse']))))
    return rows


def scene_prerequisites(scene,quality,pair,controlled):
    parent=bool(quality[0]['eligibility']['passed'])
    rgb=[v['name'] for v in controlled['variants'] if v['eligibility']['passed']]
    engineering=all(q['eligibility'].get('calibration_pass',False) for q in quality)
    engineering=engineering and bool(controlled['valid_parent_geometry'])
    a=bool(engineering and pair['passed'])
    b=bool(engineering and parent and rgb)
    ready=a or b
    states=dict(G0='PENDING_LOCAL' if ready else 'INVALID',G1='NOT_EVALUATED',
        G2_machine='NOT_EVALUATED',G2_manual='UNCERTIFIED',G3='NOT_EVALUATED',
        G4='NOT_EVALUATED',G5='UNCERTIFIED')
    return dict(scene=scene,verdict='UNDETERMINED' if engineering else 'ENGINEERING_NOT_READY',
        route_a=dict(eligible=a,reason='independent seed quality and relation pass' if a else
            'one or both seed quality, pair relation, or geometry prerequisites failed'),
        route_b=dict(eligible=b,parent_quality_eligible=parent,rgb_qualified_doses=rgb,
            reason='parent and controlled prerequisites pass' if b else
            'parent reconstruction quality, geometry, or all controlled doses ineligible'),
        engineering_ready=bool(engineering),may_run_local_probe=bool(ready),gates=states)


def combined_decision(scenes):
    if len(scenes)!=4: return 'ENGINEERING_NOT_READY'
    if not all(s['engineering_ready'] for s in scenes):return 'ENGINEERING_NOT_READY'
    if not all(s['input_valid'] for s in scenes):return 'UNDETERMINED'
    if all(s['image_only_certified'] for s in scenes) and not all(s['gs_benefit'] for s in scenes):
        return 'PIVOT_IMAGE_ONLY'
    if any(s['negative_evidence'] and not s['machine_pass'] for s in scenes):return 'STOP_B'
    if not all(s['machine_pass'] for s in scenes):return 'UNDETERMINED'
    a=all(s['route_a'] and s['seed_stable'] for s in scenes)
    b=all(s['route_b'] and s['controlled_stable'] for s in scenes)
    if a and not any(s['route_b'] for s in scenes):return 'SEED_ONLY'
    if b and not a:return 'CONTROLLED_ONLY'
    if a and b and all(s['manual_certified'] for s in scenes):return 'FOUNDATION-GO'
    return 'UNDETERMINED'


def _dose_row(r):
    return (f"| {r['scene']} | {r['name']} | {r['dose']:.5f} | "
        f"{r['qualified_pairs']}/{r['total_pairs']} | {r['psnr_min']:.6f} | {r['ssim_min']:.9f} | "
        f"{r['p99_max']:.9f} | {r['selected_mass_min']:.9f} | {r['minor_mass_min']:.9f} | "
        f"{r['passed']} | {r['invariance_eligible']} |")


def render_prerequisite_report(result):
    lines=['# Multiscene foundation results','',f"**Verdict: {result['verdict']}.**",'',
        'Both routes were executed under the frozen protocol. No local scientific conclusion is inferred from an ineligible posterior.',
        '',result['diagnosis'],'','## Totals','']
    lines.extend(f"- {key}: {value}" for key,value in result['totals'].items())
    lines+=['','## Scene gates','',
        '| Scene | Verdict | Route A eligible | Route B eligible | G0 | G1 | G2 machine | G2 manual | G3 | G4 | G5 |',
        '|---|---|---|---|---|---|---|---|---|---|---|']
    for s in result['scenes']:
        g=s['gates']
        lines.append(f"| {s['scene']} | {s['verdict']} | {s['route_a']['eligible']} | {s['route_b']['eligible']} | "
            + ' | '.join(g[k] for k in ['G0','G1','G2_machine','G2_manual','G3','G4','G5'])+' |')
    lines+=['','## Eight fixed training runs','',
        'All rows use final iteration 30,000. 400px quality below is the frozen foreground ROI, white background; black-background results and every view are retained in JSON.',
        '', '| Scene | Seed | Complete | Gaussians | TRAIN mean PSNR | TRAIN SSIM | Validation mean PSNR | Validation SSIM | Eligible |',
        '|---|---:|---|---:|---:|---:|---:|---:|---|']
    for r in result['training_rows']:
        lines.append(f"| {r['scene']} | {r['seed']} | {r['complete']} | {r['gaussians']} | "
            f"{r['train_psnr']:.6f} | {r['train_ssim']:.9f} | {r['val_psnr']:.6f} | {r['val_ssim']:.9f} | {r['eligible']} |")
    lines+=['','## Every controlled dose','',
        'A dose pass means all 32 TRAIN view/background comparisons, coverage and calibration passed. Invariance eligibility additionally requires the preregistered parent reconstruction quality. All doses are retained; none was selected for appearance.',
        '', '| Scene | Dose name | Dose | Passing RGB pairs | Min PSNR | Min SSIM | Max P99 | Min parent mass | Min child mass | Dose pass | Invariance eligible |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|']
    lines.extend(_dose_row(r) for r in result['dose_rows'])
    lines+=['','## Scientific scope and manual status','',
        'G2 manual and G5 are UNCERTIFIED. The implementing assistant recorded 16 coarse TRAIN target candidates and 48 challenge rectangles before local outputs. These are not 12 verified cross-view spans per scene, independent annotations, or blind review. DEV and TEST photographs were not used for training, qualification, fitting or visual review.',
        '', 'Unreached: '+', '.join(result['unreached'])+'.', '',
        'Synthetic unit tests establish software behavior only. They do not establish local observability, posterior invariance, GS benefit, useful glyphs or NPR quality. No UDF, curves, connected linelets, Beziers or final strokes were trained/extracted. No mesh was read.',
        '', 'The source, complete eight-run logs, final PLY paths/hashes, quality renders, every dose, all native arrays and access traces are inventoried in MANIFEST.json. Large files remain server-side. REPRODUCE.md records the exact protocol and commands. VERIFICATION.json records checks; TDD_LEDGER.md preserves observed RED/GREEN failures.',
        '', 'No threshold, parent, dose or image split was changed after results. Any corrected sampling convention or different eligibility resolution requires a new preregistration and separate output directory. This run is retained.', '']
    return '\n'.join(lines)


def check_report(result,text):
    totals={key:int(value) for key,value in re.findall(r'^- (\w+): (\d+)$',text,re.M)}
    assert totals==result['totals'],'JSON/Markdown totals differ'
    assert f"**Verdict: {result['verdict']}.**" in text,'verdict differs'
    for row in result['dose_rows']:
        assert text.count(_dose_row(row))==1,'qualification row differs'
    for scene in result['scenes']:
        line=next(s for s in text.splitlines() if s.startswith('| '+scene['scene']+' | '+scene['verdict']+' |'))
        cells=[s.strip() for s in line.split('|')[1:-1]]
        assert cells[2:4]==[str(scene['route_a']['eligible']),str(scene['route_b']['eligible'])]
        assert cells[4:]==[scene['gates'][k] for k in ['G0','G1','G2_machine','G2_manual','G3','G4','G5']]
    for r in result['training_rows']:
        prefix=f"| {r['scene']} | {r['seed']} | {r['complete']} | {r['gaussians']} | "
        line=next(s for s in text.splitlines() if s.startswith(prefix))
        cells=[s.strip() for s in line.split('|')[1:-1]]
        assert cells[4:8]==[f"{r[k]:.6f}" if 'psnr' in k else f"{r[k]:.9f}" for k in ['train_psnr','train_ssim','val_psnr','val_ssim']]
        assert cells[-1]==str(r['eligible'])
    return True
