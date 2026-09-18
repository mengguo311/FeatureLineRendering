"""Frozen multiscene qualification and controlled posterior interventions."""
import hashlib
import numpy as np
from .common import quat_to_rotmat


def perturbation_specs(cfg):
    p=cfg['perturbations']
    return ([dict(name=f'redistribute_{i:02d}',family='redistribute',q=q,dose=q)
             for i,q in enumerate(p['redistribute_q'])] +
            [dict(name=f'moment_split_{i:02d}',family='moment_split',q=p['moment_split_q'],dose=d)
             for i,d in enumerate(p['moment_split_d'])])


def controlled_asset(asset, spec, cfg):
    """Radial-L2 opacity redistribution, optionally with preserved mixture moments."""
    if spec not in perturbation_specs(cfg):
        raise ValueError('unregistered intervention')
    n=len(asset['mu']); p=cfg['perturbations']
    hashes=[hashlib.sha256(f"{p['parent_hash_seed']}:parent:{i}".encode()).digest() for i in range(n)]
    selected=np.zeros(n,bool)
    selected[sorted(range(n),key=lambda i:hashes[i])[:int(n*p['parent_fraction'])]]=True
    parents=np.repeat(np.arange(n),1+selected.astype(int))
    child={key:value[parents].copy() for key,value in asset.items()}
    affected=np.flatnonzero(selected[parents]); first,second=affected[::2],affected[1::2]
    a=asset['opacity'][selected,0].astype(float); b=spec['q']*a
    c=(a-b)*(.5-b/3)/(.5-2*b/3+b*b/4)
    if not np.all((b>0)&(b<1)&(c>0)&(c<1)):
        raise ValueError('invalid child opacity')
    child['opacity'][first,0]=c;child['opacity'][second,0]=b
    if spec['family']=='moment_split':
        scale=asset['scale'][selected].astype(float); axis=scale.argmax(1)
        R=quat_to_rotmat(asset['quat'][selected].astype(float)); rows=np.arange(len(scale))
        v=R[rows,:,axis]*scale[rows,axis,None]*spec['dose']
        w1=c/(b+c);w2=b/(b+c)
        child['mu'][first]-=(np.sqrt(w2/w1)[:,None]*v).astype(child['mu'].dtype)
        child['mu'][second]+=(np.sqrt(w1/w2)[:,None]*v).astype(child['mu'].dtype)
        scale[rows,axis]*=np.sqrt(1-spec['dose']**2)
        child['scale'][first]=scale;child['scale'][second]=scale
    minor=np.zeros(len(parents),bool);minor[second]=True
    return child,parents,selected,minor


def _quality_keys(cfg):
    return {(split,i,bg) for split in ['train','val']
            for i in cfg['splits']['TRAIN'] for bg in [0,1]}


def _keys(rows, fields):
    return [tuple(row[k] for k in fields) for row in rows]


def _complete(rows, fields, expected):
    keys=_keys(rows,fields)
    return len(keys)==len(expected) and set(keys)==expected


def seed_eligibility(rows,cfg):
    limits=cfg['eligibility']['independent']
    complete=_complete(rows,['split','view','background'],_quality_keys(cfg))
    groups=[]
    for split in ['train','val']:
        for bg in [0,1]:
            values=[r for r in rows if (r['split'],r['background'])==(split,bg)]
            psnr=np.array([r['psnr_db'] if r['psnr_db'] is not None else np.inf for r in values])
            ssim=np.array([r['ssim'] for r in values])
            valid=bool(values) and all(r['valid'] for r in values)
            valid=valid and not np.isnan(psnr).any() and bool(np.isfinite(ssim).all())
            summary=dict(split=split,background=bg,n=len(values),passed=False)
            if valid:
                mp,wp,ms,ws=psnr.mean(),psnr.min(),ssim.mean(),ssim.min()
                summary.update(mean_psnr=None if np.isinf(mp) else float(mp),
                    worst_psnr=None if np.isinf(wp) else float(wp),mean_ssim=float(ms),worst_ssim=float(ws),
                    passed=bool(mp>=limits['mean_psnr_min'] and wp>=limits['worst_psnr_min']
                                and ms>=limits['mean_ssim_min'] and ws>=limits['worst_ssim_min']))
            groups.append(summary)
    return dict(passed=complete and all(g['passed'] for g in groups),complete=complete,groups=groups)


def independent_eligibility(seed_rows,pair_rows,cfg):
    if len(seed_rows)!=2:
        raise ValueError('exactly two preregistered seeds required')
    quality=[seed_eligibility(rows,cfg) for rows in seed_rows]
    complete=_complete(pair_rows,['split','view','background'],_quality_keys(cfg))
    limits=cfg['eligibility']['independent']; groups=[]
    for a,b in zip(quality[0]['groups'],quality[1]['groups']):
        pair=[r for r in pair_rows if (r['split'],r['background'])==(a['split'],a['background'])]
        passed=a['passed'] and b['passed'] and bool(pair)
        psnr_gap=ssim_gap=None
        if passed:
            pa,pb=a['mean_psnr'],b['mean_psnr']
            psnr_gap=0. if pa is None and pb is None else (None if pa is None or pb is None else abs(pa-pb))
            ssim_gap=abs(a['mean_ssim']-b['mean_ssim'])
            passed=(psnr_gap is not None and psnr_gap<=limits['mean_psnr_gap_max']
                and ssim_gap<=limits['mean_ssim_gap_max']
                and np.mean([r['ssim'] for r in pair])>=limits['pair_mean_ssim_min'])
            for r in pair:
                errors=np.array([r['rmse_seed0'],r['rmse_seed1'],r['rmse_pair']])
                passed=passed and r['valid'] and bool(np.isfinite(errors).all()) and bool(
                    r['rmse_pair']<=limits['pair_rmse_factor_max']*max(r['rmse_seed0'],r['rmse_seed1'])+limits['pair_rmse_epsilon'])
        groups.append(dict(split=a['split'],background=a['background'],passed=bool(passed),
                           mean_psnr_gap=psnr_gap,mean_ssim_gap=ssim_gap))
    return dict(passed=bool(complete and all(q['passed'] for q in quality) and all(g['passed'] for g in groups)),
                complete=complete,seeds=quality,relation=groups)


def controlled_eligibility(rows,coverage,cfg):
    expected={(i,bg) for i in cfg['splits']['TRAIN'] for bg in [0,1]}
    complete=_complete(rows,['view','background'],expected)
    complete=complete and _complete(coverage,['view'],{(i,) for i in cfg['splits']['TRAIN']})
    limits=cfg['eligibility']['controlled']
    coverage_pass=bool(coverage) and all(np.isfinite([r['selected'],r['minor']]).all()
        and r['selected']>=limits['selected_mass_min'] and r['minor']>=limits['child_mass_min'] for r in coverage)
    rgb_pass=bool(rows) and all(r['valid'] and r['passed'] for r in rows)
    return dict(passed=bool(complete and coverage_pass and rgb_pass),complete=complete,
                coverage_pass=bool(coverage_pass),rgb_pass=bool(rgb_pass))
