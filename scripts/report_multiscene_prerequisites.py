#!/usr/bin/env python3
"""Summarize completed routes without converting failed eligibility into science."""
import argparse
import json
from pathlib import Path
import sys
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.foundation import freeze_json,verified_json
from src.multiscene import independent_eligibility,perturbation_specs
from src.multiscene_training import sha256,utc
from src.multiscene_qualification import save_grid
from src.multiscene_report import (pair_measurements,scene_prerequisites,combined_decision,
    render_prerequisite_report,check_report,summarize_diagnostic)


def load(path):
    return verified_json(path,Path(str(path)+'.sha256').read_text().strip())


def save_plot(path,fig):
    with Path(path).open('xb') as stream:fig.savefig(stream,format='png',dpi=140,bbox_inches='tight')
    plt.close(fig)


def plot_doses(path,controlled):
    fig,axes=plt.subplots(4,2,figsize=(12,13),squeeze=False)
    for col,family in enumerate(['redistribute','moment_split']):
        variants=[v for v in controlled['variants'] if v['family']==family]
        x=np.array([v['dose'] for v in variants])
        for row,(key,label,limit,larger) in enumerate([
                ('psnr_db','ROI PSNR (dB)',40,True),('ssim','ROI SSIM',.995,True),
                ('p99_max_channel_abs','P99 max-channel error',8/255,False)]):
            data=np.array([[r[key] for r in v['rows']] for v in variants])
            axes[row,col].plot(x,data,color='.7',linewidth=.6)
            envelope=data.min(1) if larger else data.max(1)
            axes[row,col].plot(x,envelope,'o-',color='navy',label='worst view/background')
            axes[row,col].axhline(limit,color='red',linestyle='--',label='frozen limit')
            axes[row,col].set_ylabel(label);axes[row,col].set_xlabel(family+' dose');axes[row,col].grid(alpha=.2)
        data=np.array([[r['minor'] for r in v['coverage']] for v in variants])
        axes[3,col].plot(x,data,color='.7',linewidth=.6)
        axes[3,col].plot(x,data.min(1),'o-',color='navy')
        axes[3,col].axhline(.005,color='red',linestyle='--')
        axes[3,col].set_ylabel('Smaller-child contribution / baseline foreground mass')
        axes[3,col].set_xlabel(family+' dose');axes[3,col].grid(alpha=.2)
        axes[0,col].legend(fontsize=7)
    fig.suptitle('Every frozen dose; no dose selected after rendering')
    fig.tight_layout();save_plot(path,fig)


def scene_report(root,cfg,scene):
    quality_dirs=[root/'training'/scene/f'seed_{seed}'/'quality/measurements' for seed in cfg['training']['seeds']]
    quality=[load(p/'quality.json') for p in quality_dirs]
    controlled=load(root/'controlled'/scene/'measurements/qualification.json')
    pairs=pair_measurements([p/'native' for p in quality_dirs],cfg)
    relation=independent_eligibility([q['rows'] for q in quality],pairs,cfg)
    summary=scene_prerequisites(scene,quality,relation,controlled)
    output=root/'scenes'/scene;output.mkdir(parents=True,exist_ok=False)
    freeze_json(output/'independent_relation.json',dict(eligibility=relation,rows=pairs))
    train_rows=[]
    for seed,quality_report in zip(cfg['training']['seeds'],quality):
        d=root/'training'/scene/f'seed_{seed}';completion=load(d/'completion.json')
        # Only read the PLY header, which declares the number of Gaussian vertices.
        count=None
        with Path(completion['path']).open('rb') as stream:
            for line in iter(stream.readline,b''):
                if line.startswith(b'element vertex '):count=int(line.split()[2])
                if line.strip()==b'end_header':break
        groups={r['split']:r for r in quality_report['eligibility']['groups'] if r['background']==1}
        train_rows.append(dict(scene=scene,seed=seed,complete=completion['complete'],gaussians=count,
            train_psnr=groups['train']['mean_psnr'],train_ssim=groups['train']['mean_ssim'],
            val_psnr=groups['val']['mean_psnr'],val_ssim=groups['val']['mean_ssim'],
            eligible=quality_report['eligibility']['passed'],quality=quality_report['eligibility'],
            completion=completion,exit_status=load(d/'exit_status.json')))
    dose_rows=[]
    for v in controlled['variants']:
        dose_rows.append(dict(scene=scene,name=v['name'],family=v['family'],dose=v['dose'],
            qualified_pairs=sum(r['passed'] for r in v['rows']),total_pairs=len(v['rows']),
            psnr_min=min(r['psnr_db'] for r in v['rows']),ssim_min=min(r['ssim'] for r in v['rows']),
            p99_max=max(r['p99_max_channel_abs'] for r in v['rows']),
            selected_mass_min=min(r['selected'] for r in v['coverage']),
            minor_mass_min=min(r['minor'] for r in v['coverage']),passed=v['eligibility']['passed'],
            invariance_eligible=bool(summary['route_b']['eligible'] and v['eligibility']['passed'])))
    panels=[]
    for i in cfg['visuals']['fixed_train']:
        for split in ['train','val']:
            arrays=[np.load(p/f'native/{split}_{i:03d}.npz') for p in quality_dirs]
            gt=arrays[0]['gt_1'];a=arrays[0]['rgb_1'];b=arrays[1]['rgb_1']
            panels.extend([(f'{split} {i} GT',gt),('seed1729',a),('seed2718',b),('seed RGB difference x10',abs(a-b)*10)])
            for archive in arrays:archive.close()
    panels=[(label,cv2.resize(image,(200,200),interpolation=cv2.INTER_AREA)) for label,image in panels]
    save_grid(output/'fixed_seeds.png',panels,4)
    plot_doses(output/'qualification.png',controlled)
    # Numerical dose-response envelope, including departures from monotonicity.
    response=[]
    for family in ['redistribute','moment_split']:
        rows=[r for r in dose_rows if r['family']==family]
        p99=np.array([r['p99_max'] for r in rows]);psnr=np.array([r['psnr_min'] for r in rows])
        response.append(dict(family=family,doses=[r['dose'] for r in rows],p99_max=p99.tolist(),
            psnr_min=psnr.tolist(),p99_nondecreasing=bool(np.all(np.diff(p99)>=0)),
            psnr_nonincreasing=bool(np.all(np.diff(psnr)<=0))))
    summary.update(training_rows=train_rows,dose_rows=dose_rows,dose_response=response,
        calibration=controlled['calibration'],delta=controlled['delta'],box=controlled['box'],
        controlled_seconds=controlled['elapsed_seconds'],source_reports={str(p/'quality.json'):sha256(p/'quality.json') for p in quality_dirs},
        assembled_utc=utc())
    freeze_json(output/'prerequisites.json',summary)
    print(json.dumps(dict(scene=scene,verdict=summary['verdict'],may_run_local_probe=summary['may_run_local_probe'])),flush=True)
    return summary


def final_report(root,cfg):
    scenes=[load(root/'scenes'/scene/'prerequisites.json') for scene in cfg['scene_order']]
    if any(s['may_run_local_probe'] for s in scenes):
        raise RuntimeError('An eligible route exists: complete its full local probe before final reporting')
    training=[r for s in scenes for r in s['training_rows']];doses=[r for s in scenes for r in s['dose_rows']]
    diagnostic_rows=[];diagnostic_reports={};quality_count=pair_count=diagnostic_count=0
    for scene in cfg['scene_order']:
        pair_count+=len(load(root/'scenes'/scene/'independent_relation.json')['rows'])
        for seed in cfg['training']['seeds']:
            quality_count+=len(load(root/'training'/scene/f'seed_{seed}'/'quality/measurements/quality.json')['rows'])
            path=root/'diagnostics/resolution'/scene/f'seed_{seed}'/'measurements/diagnostic.json'
            report=load(path);diagnostic_count+=len(report['rows'])
            diagnostic_rows.extend(summarize_diagnostic(scene,seed,report,cfg['splits']['TRAIN']))
            diagnostic_reports[str(path)]=sha256(path)
    decision_rows=[dict(engineering_ready=s['engineering_ready'],input_valid=s['may_run_local_probe'],
        route_a=s['route_a']['eligible'],route_b=s['route_b']['eligible'],machine_pass=False,
        seed_stable=False,controlled_stable=False,manual_certified=False,negative_evidence=False,
        image_only_certified=False,gs_benefit=False) for s in scenes]
    totals=dict(training_expected=8,training_complete=sum(r['complete'] for r in training),
        seeds_eligible=sum(r['eligible'] for r in training),doses_expected=4*len(perturbation_specs(cfg)),
        doses_measured=len(doses),doses_rgb_qualified=sum(r['passed'] for r in doses),
        doses_invariance_eligible=sum(r['invariance_eligible'] for r in doses),
        quality_view_background_rows=quality_count,controlled_view_background_rows=sum(r['total_pairs'] for r in doses),
        independent_pair_rows=pair_count,posthoc_diagnostic_rows=diagnostic_count,
        local_probe_scenes=0,certified_manual_scenes=0,generated_mp4s=0)
    macro_quality={}
    for split in ['train','val']:
        for bg in [0,1]:
            groups=[g for r in training for g in r['quality']['groups'] if g['split']==split and g['background']==bg]
            macro_quality[f'{split}_background_{bg}']=dict(
                mean_psnr=float(np.mean([g['mean_psnr'] for g in groups])),
                mean_ssim=float(np.mean([g['mean_ssim'] for g in groups])),
                worst_psnr=min(g['worst_psnr'] for g in groups),worst_ssim=min(g['worst_ssim'] for g in groups),
                scope='equal weight per scene and seed; descriptive only, cannot rescue any failed scene')
    result=dict(verdict=combined_decision(decision_rows),totals=totals,scenes=scenes,training_rows=training,dose_rows=doses,
        diagnostic_rows=diagnostic_rows,diagnostic_reports=diagnostic_reports,macro_quality=macro_quality,
        config_sha256=sha256(root/'config.json'),prereg_sha256=sha256(root/'PREREG.md'),created_utc=utc(),
        diagnosis='All eight frozen 400px parent reconstruction quality prerequisites failed. Controlled RGB equivalence is reported independently but cannot override the registered parent-quality requirement. A separate Lego TRAIN1 diagnostic found official 800px rendering downsampled to400 gives33.779945dB/SSIM0.981650; direct official400 gives24.965185dB/0.875092; the frozen K400 convention gives23.451554dB/0.778988. The official and native renderers agree within4.77e-7 when given the same canonical camera. This identifies resolution dependence and a half-pixel convention mismatch as protocol/evaluation limitations, not evidence against hypothesis B. The explicitly post-hoc diagnostic then covered all eight seeds and all frozen views/backgrounds (table below); Drums remains weak even there. No diagnostic metric overrides eligibility. The preregistered validity stop was reached in every scene.',
        unreached=['scene image-evidence ray profiles','H_img/axial scene inference','F/C and LOO scene repeatability',
            'scene no-GS/PCA/shifted/random controls','surface-sample audit','DEV annotations',
            'local glyph comparisons','120-frame videos','independent visual review'],
        implemented_synthetic_core=['full-K projection/Jacobian','fixed Canny/tangents and query hashing','full-box multimodal profiles',
            'bounded image-only Gauss-Newton/H_img axial estimate','native contribution/depth layers','shifted association maps',
            'same-query bidirectional matching','route/gate decisions and report consistency'])
    text=render_prerequisite_report(result);check_report(result,text)
    freeze_json(root/'results.json',result)
    with (root/'RESULTS.md').open('x') as f:f.write(text)
    print(json.dumps(totals),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT/'out/multiscene_foundation')
    parser.add_argument('--scene',choices=['lego','chair','drums','ficus'])
    parser.add_argument('--final',action='store_true');args=parser.parse_args()
    root=args.root.resolve();cfg=load(root/'config.json')
    if args.scene:scene_report(root,cfg,args.scene)
    if args.final:final_report(root,cfg)


if __name__=='__main__':main()
