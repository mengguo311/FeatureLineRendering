#!/usr/bin/env python3
"""Render interpretable parameter-field diagnostics for frozen vanilla 3DGS.

The output deliberately calls all geometry quantities proxies: vanilla 3DGS does
not contain calibrated surfaces or ground-truth normals.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from plyfile import PlyData

from src.field_visualization import (
    axial_rgb, covariance_matrices, evaluate_gaussian_slice, flattening_score,
    gaussian_candidate_normals, local_surface_metrics, sigmoid,
)

C0 = 0.28209479177387814
SCENES = ('lego', 'chair', 'drums', 'ficus')
DARK = '#080b12'
CMAP = LinearSegmentedColormap.from_list(
    'field', ['#07111f', '#123c69', '#10a6a6', '#e8d44d', '#ff6138'])


def load_ply(path: Path):
    v = PlyData.read(str(path))['vertex'].data
    def cols(names):
        return np.stack([np.asarray(v[n], dtype=np.float64) for n in names], axis=1)
    return {
        'points': cols(('x', 'y', 'z')),
        'dc': cols(('f_dc_0', 'f_dc_1', 'f_dc_2')),
        'opacity': np.asarray(v['opacity'], dtype=np.float64),
        'log_scales': cols(('scale_0', 'scale_1', 'scale_2')),
        'quat': cols(('rot_0', 'rot_1', 'rot_2', 'rot_3')),
    }


def robust_frame(points, opacity):
    good = opacity >= np.quantile(opacity, 0.25)
    p = points[good]
    center = np.median(p, axis=0)
    q = p - center
    cov = (q.T @ q) / len(q)
    vals, basis = np.linalg.eigh(cov)
    basis = basis[:, np.argsort(vals)[::-1]]
    if np.linalg.det(basis) < 0:
        basis[:, 2] *= -1
    coords = (points - center) @ basis
    return center, basis, coords


def deterministic_sample(n, count, seed):
    rng = np.random.default_rng(seed)
    return np.sort(rng.choice(n, min(n, count), replace=False))


def limits_xy(coords):
    xlo, xhi = np.quantile(coords[:, 0], [0.005, 0.995])
    ylo, yhi = np.quantile(coords[:, 1], [0.005, 0.995])
    padx, pady = .03*(xhi-xlo), .03*(yhi-ylo)
    return (xlo-padx, xhi+padx), (ylo-pady, yhi+pady)


def style_axis(ax, title, xlim, ylim):
    ax.set_facecolor(DARK)
    ax.set_title(title, color='white', fontsize=10, pad=7)
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect('equal')
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)


def scatter_field(ax, xy, values, title, xlim, ylim, cmap=CMAP,
                  vmin=0, vmax=1, rgb=False, size=1.0, alpha=.72):
    if rgb:
        ax.scatter(xy[:, 0], xy[:, 1], s=size, c=np.clip(values, 0, 1),
                   alpha=alpha, linewidths=0, rasterized=True)
    else:
        im = ax.scatter(xy[:, 0], xy[:, 1], s=size, c=values, cmap=cmap,
                        vmin=vmin, vmax=vmax, alpha=alpha, linewidths=0,
                        rasterized=True)
        cb = plt.colorbar(im, ax=ax, fraction=.035, pad=.015)
        cb.ax.tick_params(colors='#cbd5e1', labelsize=7, length=2)
        cb.outline.set_edgecolor('#334155')
    style_axis(ax, title, xlim, ylim)


def orient_axial_2d(v):
    out = v.copy()
    flip = (out[:, 0] < 0) | ((np.abs(out[:, 0]) < 1e-12) & (out[:, 1] < 0))
    out[flip] *= -1
    n = np.linalg.norm(out, axis=1)
    ok = n > 1e-9
    out[ok] /= n[ok, None]
    return out, ok


def process_scene(scene, ply_path, outdir, sample_count=24000, slice_count=1500):
    d = load_ply(ply_path)
    p = d['points']; opacity = sigmoid(d['opacity'])
    cand_n, scales = gaussian_candidate_normals(d['log_scales'], d['quat'])
    flat_all = flattening_score(scales)
    center, basis, coords = robust_frame(p, opacity)
    sample = deterministic_sample(len(p), sample_count, 1701 + sum(map(ord, scene)))
    m = local_surface_metrics(p, cand_n, sample, k=24)
    flat = flat_all[sample]
    agreement = m['axis_agreement']
    planarity = m['planarity']
    surface = np.cbrt(np.clip(flat * planarity * agreement, 0, 1))
    rgb = np.clip(0.5 + C0 * d['dc'][sample], 0, 1)
    axial = axial_rgb(cand_n[sample])
    xy = coords[sample, :2]
    xlim, ylim = limits_xy(coords[sample])

    fig, axes = plt.subplots(3, 3, figsize=(18, 16), facecolor=DARK)
    fig.suptitle(
        f'{scene.upper()} — frozen vanilla 3DGS posterior fields',
        color='white', fontsize=18, y=.985, weight='bold')
    fig.text(.5, .958,
             'All geometry panels are proxies, not calibrated surfaces/normals. Orthographic PCA view; no visibility filtering.',
             ha='center', color='#94a3b8', fontsize=9)

    scatter_field(axes[0,0], xy, rgb, 'SH-DC color at Gaussian means', xlim, ylim,
                  rgb=True, size=.8, alpha=.65)
    scatter_field(axes[0,1], xy, axial,
                  'Covariance smallest-axis orientation |XYZ|', xlim, ylim,
                  rgb=True, size=.9, alpha=.75)
    scatter_field(axes[0,2], xy, opacity[sample],
                  'Opacity sigmoid(logit)', xlim, ylim, size=.9)
    scatter_field(axes[1,0], xy, flat,
                  'Gaussian flattening 1 − s_min/s_mid', xlim, ylim, size=.9)
    scatter_field(axes[1,1], xy, planarity,
                  'Local center-cloud planarity (24-NN)', xlim, ylim, size=.9)
    scatter_field(axes[1,2], xy, agreement,
                  'Axis agreement |n_cov · n_PCA|', xlim, ylim, size=.9)
    scatter_field(axes[2,0], xy, surface,
                  'Surface-likeness proxy (geometric mean)', xlim, ylim, size=.9)

    # Paired axial vector field, sampled uniformly rather than by score.
    qsel = np.linspace(0, len(sample)-1, min(600, len(sample)), dtype=int)
    cov2 = cand_n[sample[qsel]] @ basis[:, :2]
    pca2 = m['local_normal'][qsel] @ basis[:, :2]
    cov2, ok1 = orient_axial_2d(cov2); pca2, ok2 = orient_axial_2d(pca2)
    qq = qsel[ok1 & ok2]
    cov2 = cov2[ok1 & ok2]; pca2 = pca2[ok1 & ok2]
    ax = axes[2,1]
    ax.scatter(xy[:,0], xy[:,1], s=.15, c='#334155', alpha=.28, rasterized=True)
    length = .018 * max(xlim[1]-xlim[0], ylim[1]-ylim[0])
    ax.quiver(xy[qq,0], xy[qq,1], cov2[:,0], cov2[:,1], color='#ff5f56',
              angles='xy', scale_units='xy', scale=1/length, width=.0021,
              headwidth=0, headlength=0, headaxislength=0, alpha=.72)
    ax.quiver(xy[qq,0], xy[qq,1], pca2[:,0], pca2[:,1], color='#41c7ff',
              angles='xy', scale_units='xy', scale=1/length, width=.0015,
              headwidth=0, headlength=0, headaxislength=0, alpha=.58)
    style_axis(ax, 'Axial vector field: covariance (red) / local PCA (cyan)', xlim, ylim)

    # True anisotropic 3D Gaussian mixture evaluated on the global PCA mid-plane.
    cov_all = covariance_matrices(d['log_scales'], d['quat'])
    plane_n = basis[:, 2]
    signed = (p - center) @ plane_n
    sigma_n = np.sqrt(np.maximum(np.einsum('i,nij,j->n', plane_n, cov_all, plane_n), 1e-20))
    relevance = opacity * np.exp(-.5 * np.minimum((signed/sigma_n)**2, 80))
    candidates = np.flatnonzero(np.abs(signed) <= 3.0*sigma_n)
    if len(candidates) > slice_count:
        candidates = candidates[np.argsort(relevance[candidates])[-slice_count:]]
    u = np.linspace(xlim[0], xlim[1], 180)
    v = np.linspace(ylim[0], ylim[1], 180)
    field = evaluate_gaussian_slice(p[candidates], cov_all[candidates], opacity[candidates],
                                    center, basis[:, :2], u, v)
    field_log = np.log1p(field)
    field_norm = field_log / max(float(field_log.max()), 1e-15)
    ax = axes[2,2]
    ax.imshow(field_norm, origin='lower', extent=(*xlim, *ylim), cmap=CMAP,
              vmin=0, vmax=1, interpolation='bilinear', aspect='equal')
    positive = field_norm[field_norm > 1e-5]
    levels = np.unique(np.quantile(positive, [.35,.55,.72,.85,.93])) if len(positive) else []
    if len(levels):
        ax.contour(u, v, field_norm, levels=levels, colors='white', linewidths=.55, alpha=.65)
    style_axis(ax, f'Opacity-weighted Gaussian mixture mid-slice ({len(candidates):,} splats)', xlim, ylim)

    plt.subplots_adjust(left=.025, right=.98, bottom=.03, top=.935, wspace=.12, hspace=.13)
    scene_png = outdir / f'{scene}_field_atlas.png'
    fig.savefig(scene_png, dpi=220, facecolor=fig.get_facecolor())
    plt.close(fig)

    # Distribution summary with robust percentiles.
    stats = {
        'scene': scene, 'gaussian_count': int(len(p)), 'sample_count': int(len(sample)),
        'slice_gaussian_count': int(len(candidates)),
        'opacity': {}, 'scales': {}, 'flattening': {}, 'local_planarity': {},
        'axis_agreement': {}, 'surface_proxy': {},
        'definitions': {
            'candidate_normal': 'smallest covariance axis; signless',
            'flattening': '1 - s_min/s_mid',
            'local_planarity': '(lambda_2-lambda_3)/lambda_1 of 24-NN center covariance',
            'axis_agreement': 'absolute dot product of candidate and local PCA normals',
            'surface_proxy': 'cube root(flattening * local_planarity * axis_agreement)',
            'slice': 'sum alpha_i exp(-0.5 Mahalanobis_i^2), evaluated on PCA mid-plane',
        }
    }
    def quant(name, arr):
        stats[name] = {f'p{q}': float(np.quantile(arr, q/100)) for q in (5,25,50,75,95)}
    quant('opacity', opacity[sample]); quant('flattening', flat)
    quant('local_planarity', planarity); quant('axis_agreement', agreement)
    quant('surface_proxy', surface)
    stats['scales'] = {
        'min_median': float(np.median(np.min(scales[sample], axis=1))),
        'mid_median': float(np.median(np.sort(scales[sample],axis=1)[:,1])),
        'max_median': float(np.median(np.max(scales[sample], axis=1))),
    }
    np.savez_compressed(outdir / f'{scene}_field_samples.npz', indices=sample,
                        points=p[sample], opacity=opacity[sample], scales=scales[sample],
                        candidate_normals=cand_n[sample], local_normals=m['local_normal'],
                        flattening=flat, local_planarity=planarity,
                        axis_agreement=agreement, surface_proxy=surface,
                        slice_u=u, slice_v=v, slice_field=field)
    return stats, scene_png


def make_summary(outdir, scenes):
    from PIL import Image, ImageDraw, ImageFont
    ims = [Image.open(outdir / f'{s}_field_atlas.png').convert('RGB') for s in scenes]
    thumb_w = 1200
    thumbs=[]
    for im in ims:
        h = round(im.height * thumb_w / im.width)
        thumbs.append(im.resize((thumb_w,h), Image.Resampling.LANCZOS))
    gap=24; canvas=Image.new('RGB',(thumb_w*2+gap, thumbs[0].height*2+gap), (8,11,18))
    for i,im in enumerate(thumbs): canvas.paste(im,((i%2)*(thumb_w+gap),(i//2)*(im.height+gap)))
    path=outdir/'all_scenes_field_atlas.png'; canvas.save(path,quality=95)
    return path


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,default=Path('out/multiscene_foundation/training'))
    ap.add_argument('--output',type=Path,default=Path('out/3dgs_field_visualization'))
    ap.add_argument('--scenes',nargs='+',default=list(SCENES))
    ap.add_argument('--sample-count',type=int,default=24000)
    ap.add_argument('--slice-count',type=int,default=1500)
    args=ap.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
    all_stats={}
    for scene in args.scenes:
        ply=args.root/scene/'seed_1729/checkpoints/point_cloud/iteration_30000/point_cloud.ply'
        print(f'[{scene}] {ply}',flush=True)
        stats,path=process_scene(scene,ply,args.output,args.sample_count,args.slice_count)
        all_stats[scene]=stats; print(f'  wrote {path}',flush=True)
    (args.output/'field_statistics.json').write_text(json.dumps(all_stats,indent=2)+'\n')
    print(f'wrote {make_summary(args.output,args.scenes)}')

if __name__=='__main__': main()
