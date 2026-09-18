#!/usr/bin/env python3
"""Report measured prerequisite results without inventing downstream experiments."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO))
import numpy as np
import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.foundation import freeze_json,verified_json

p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,required=True)
a=p.parse_args(); root=a.root.resolve()
run=root/'lego/prerequisites.json'
r=verified_json(run,Path(str(run)+'.sha256').read_text().strip())
audit=json.loads((root/'access_audit.json').read_text())
if audit['forbidden_successful_input_reads'] or audit['unresolved_paths']:
    r['gates']['G0']=dict(state='INVALID',reason='input audit has forbidden or unresolved successful accesses')
    r['experiment_valid']=False; r['may_run_local_probe']=False
r['access_audit']=audit
r['scene_gates']={r['scene']:r['gates'],'chair':{g:dict(state='NOT_RUN',reason='Lego prerequisite gate did not permit transfer') for g in r['gates']}}
r['per_region']=[]
r['per_region_state']='NOT_EVALUATED: no local method output or independently annotated image regions'
r['manual_review']=dict(G2='UNCERTIFIED',G5='UNCERTIFIED',independent_annotators=0,independent_evaluators=0,
    TRAIN_annotation_package='NOT_CREATED: prerequisite stop before local/photo stage',
    DEV_annotations='NOT_CREATED: DEV photos remain sealed',blind_glyph_package='NOT_REACHED')
r['implementation_scope']=dict(
    implemented=['canonical protocol/hash verification','native IO isolation and audit','full K projection/Jacobian',
                 'native anisotropic stock state and contribution/depth replay','fixed clone/split and coverage qualification',
                 'prerequisite gate state computation','deterministic result figures and reports'],
    not_reached=['Canny/tangent/query extraction','full-box image profile and refinements','H_img and axial acceptance',
                 'GS support/visibility and no-GS image probe','local surface-sample diagnostic',
                 'PCA/shifted/random axial controls','F/C/LOO/perturbation geometry matching',
                 'scientific G1-G5 evaluation','glyph/ink matching/120-frame video'])
r['scientific_budget_conservative_seconds']=sum(r['timing'][k] for k in ['setup_seconds','scientific_prerequisite_seconds','local_scientific_probe_seconds'])
r['generated_utc']=datetime.now(timezone.utc).isoformat()
freeze_json(root/'results.json',r)

# Every plotted series comes directly from recorded stock-render measurements.
fig,axes=plt.subplots(2,2,figsize=(14,9),constrained_layout=True)
for mode,color in [('clone','#1769aa'),('split','#cf6717')]:
    for background,style in [('white','-'),('black','--')]:
        rows=[x for x in r['qualification'][mode] if x['background']==background]
        xs=[x['view'] for x in rows]
        for ax,key in zip(axes.flat,['psnr_db','ssim','p99_max_channel_abs']):
            ys=[x[key] if x[key] is not None else np.nan for x in rows]
            ax.plot(xs,ys,style+'o',color=color,markersize=4,label=f'{mode} / {background}')
for ax,title,threshold in zip(axes.flat,['Foreground PSNR (dB): >=40','Foreground SSIM: >=0.995','P99 max-channel error: <=8/255'],[40,.995,8/255]):
    ax.axhline(threshold,color='black',linestyle=':',label='frozen threshold'); ax.set_title(title)
    ax.set_xlabel('TRAIN camera index'); ax.grid(alpha=.25)
axes[0,0].legend(fontsize=8)
ax=axes[1,1]; rows=r['per_view']
ax.plot([x['view'] for x in rows],[x['coverage'] for x in rows],'o-',label='selected-parent contribution')
ax.axhline(.2,color='black',linestyle=':',label='minimum 20%'); ax.set_ylim(0,1)
ax.set_title('Nontrivial intervention coverage'); ax.set_xlabel('TRAIN camera index'); ax.legend(fontsize=8); ax.grid(alpha=.25)
fig.suptitle('Lego prerequisite measurements — no qualifying intervention' if not r['valid_interventions'] else 'Prerequisite measurements')
fig.savefig(root/'qualification_metrics.png',dpi=140,metadata={'Software':'FeatureLineRendering foundation'}); plt.close(fig)

views=[x['view'] for x in r['per_view']]
for kind in ['white','black','calibration']:
    available=[(i,root/f'lego/{kind}_{i:03d}.png') for i in views if (root/f'lego/{kind}_{i:03d}.png').exists()]
    for page,start in enumerate(range(0,len(available),4)):
        images=[cv2.imread(str(path)) for _,path in available[start:start+4]]
        if any(im is None for im in images): raise ValueError('undecodable source PNG')
        sheet=np.vstack([cv2.resize(im,(im.shape[1]//2,im.shape[0]//2),interpolation=cv2.INTER_AREA) for im in images])
        assert cv2.imwrite(str(root/f'contact_{kind}_{page:02d}.png'),sheet,[cv2.IMWRITE_PNG_COMPRESSION,6])
    fixed=[cv2.imread(str(path)) for i,path in available if i in [1,27,53,79]]
    if fixed: assert cv2.imwrite(str(root/f'fixed_{kind}.png'),np.vstack(fixed),[cv2.IMWRITE_PNG_COMPRESSION,6])

lines=['# Foundation prerequisite result', '',f"**Verdict: {r['verdict']}. Hypothesis B was not scientifically tested.**",'',
       'The stock renderer calibrated, but neither preregistered intervention qualified as RGB-near-equivalent. '
       'G0 therefore prevents a valid invariance experiment. The run stopped before local edge-band inference, all image controls, glyphs, DEV, and Chair. '
       'This is neither a scientific rejection of B nor evidence for a pivot.', '',
       '| Gate | State | Evidence / limitation |','|---|---|---|']
for g,v in r['gates'].items(): lines.append(f"| {g} | {v['state']} | {v['reason']} |")
lines+=['','Chair: G0–G5 **NOT_RUN**; Lego did not permit transfer. No FOUNDATION-GO claim.','',
        '## Renderer and intervention evidence','',
        f"Original Gaussians: {r['original_count']:,}; selected parents: {r['selected_parent_count']:,}; each perturbed asset: {r['perturbed_count']:,}. "
        'Original PLY bytes were preserved. No defloat or center pruning was used.','',
        '| Check | Measurement | Required |','|---|---|---|']
cal=r['calibration']
for name,key in [('White RGB max absolute error','rgb_max_abs'),('Black RGB max absolute error','black_rgb_max_abs'),('Alpha max absolute error','alpha_max_abs')]:
    lines.append(f"| {name} | {max(x[key] for x in cal):.9g} | ≤1/255 = {1/255:.9g} |")
lines.append(f"| Selected-parent contribution, per-view range | {min(x['coverage'] for x in rows):.6%}–{max(x['coverage'] for x in rows):.6%} | ≥20% in every view |")
lines.append(f"| Maximum outside-box contribution | {max(x['outside_contribution'] for x in rows):.6%} | ≤1% |")
lines+=['','| Intervention | Qualifying view/background pairs | PSNR range (dB) | SSIM range | P99 error range |','|---|---:|---:|---:|---:|']
for mode,qs in r['qualification'].items():
    if qs:
        ps=[x['psnr_db'] for x in qs if x['psnr_db'] is not None]
        lines.append(f"| {mode} | {sum(x['passed'] for x in qs)}/{len(qs)} | {min(ps):.5f}–{max(ps):.5f} | {min(x['ssim'] for x in qs):.7f}–{max(x['ssim'] for x in qs):.7f} | {min(x['p99_max_channel_abs'] for x in qs):.7f}–{max(x['p99_max_channel_abs'] for x in qs):.7f} |")
lines+=['','All three limits must pass in every TRAIN view on both backgrounds: PSNR ≥40 dB, SSIM ≥0.995, P99 ≤8/255. '
        'The P99 criterion alone fails every measured pair for both interventions. No amplitude, parent, threshold, view, ROI, or detector was changed.', '',
        f"Baseline delta = {r['delta']:.10g}, from {r['delta_foreground_rays']:,} conditional-median foreground depths. "
        'It is a pixel-scale unit, not certified surface accuracy. Full native conics, ordering, weights-derived maps, ROIs and depth quantiles are retained in lego/native/.', '',
        '## Access and review boundaries','',
        f"Forbidden successful input reads: {len(audit['forbidden_successful_input_reads'])}; unresolved accesses: {len(audit['unresolved_paths'])}. "
        'No TRAIN/C/DEV/TEST photograph, mesh, mesh-derived cache, or historical experiment array entered this prerequisite run. '
        'All 16 TRAIN camera matrices were allowed. Landlock was installed before opening the GS; strace covers process startup and native IO. '
        'See access_audit.json for bootstrap directory/runtime-code exceptions and the raw strace location. '
        'The original GS training split is unverified; this is only a postprocessing access claim.','',
        'No independent annotators or reviewers were available. No target spans, challenge regions, or DEV labels were invented. '
        'G2 manual precision and G5 remain UNCERTIFIED. No local method result exists to review anonymously. '
        'The fixed 120-frame video and foundation glyph comparisons were not reached, so no substitute video or schematic output is supplied.','',
        '## Timing and completed implementation','',
        f"Setup/input preparation: {r['timing']['setup_seconds']:.3f} s; native calibration: {r['timing']['calibration_seconds']:.3f} s; "
        f"scientific perturbation qualification: {r['timing']['scientific_prerequisite_seconds']:.3f} s; local scientific probe: 0 s. "
        f"Even charging all setup to science gives {r['scientific_budget_conservative_seconds']:.3f} s, below 1800 s. "
        'Software development/testing and the reused stock renderer build are separate from these run timers.','',
        'Implemented and observed RED→GREEN: protocol hashing, kernel input restrictions, full-K camera Jacobian, native stock projection/state replay, '
        'unfiltered SH3 asset loading, fixed interventions, numerical qualification, prerequisite verdict states, IO audit, deterministic sheets, '
        'end-to-end runner, and reporting. The additional native shuffle/rotation test is a regression check of existing behavior, not a fabricated RED. '
        'See TDD_LEDGER.md and tests/ for exact commands and evidence.','',
        'The Canny/image-profile/H_img, surface-sample audit, PCA/shifted/random/no-GS controls, geometric matching, and scientific G1–G5 implementations '
        'were deliberately not reached after the necessary validity prerequisite failed. They are not claimed complete or tested. '
        'No field, network, tracer, curve, selector, or chainer was built.','',
        '## Artifacts and permitted next action','',
        '[Qualification plot](qualification_metrics.png), [fixed white-background comparisons](fixed_white.png), '
        '[fixed black-background comparisons](fixed_black.png), [fixed calibration](fixed_calibration.png). '
        'contact_white_00–03.png and contact_black_00–03.png cover all 16 views; contact_calibration_00–03.png covers every calibration view. '
        'Per-view full-resolution sheets and immutable prerequisite JSON are in lego/. Native arrays, binary, and strace remain on the server; '
        'MANIFEST.json inventories their exact paths, sizes and SHA256 hashes. Reproduction: REPRODUCE.md.','',
        '**Next permitted action:** retain this invalid-intervention result and pause investment in B. '
        'Only complete the original execution prerequisites; any changed perturbation recipe, threshold, algorithm meaning or evidence needs a new preregistration. '
        'Do not reduce the split amplitude, loosen RGB limits, run Chair, train a UDF, or develop a curve extractor under this run.','',
        '## All recorded qualification pairs','',
        '| Intervention | View | Background | PSNR dB | SSIM | P99 | Qualified |','|---|---:|---|---:|---:|---:|---|']
for mode,qs in r['qualification'].items():
    for x in qs:
        ps='∞' if x['psnr_db'] is None else f"{x['psnr_db']:.6f}"
        lines.append(f"| {mode} | {x['view']} | {x['background']} | {ps} | {x['ssim']:.8f} | {x['p99_max_channel_abs']:.8f} | {x['passed']} |")
with (root/'RESULTS.md').open('x') as f: f.write('\n'.join(lines)+'\n')
print(json.dumps(dict(verdict=r['verdict'],generated_root=str(root))))
