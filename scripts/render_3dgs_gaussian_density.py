#!/usr/bin/env python3
"""Reproducible plane-sampled density diagnostics for frozen vanilla 3DGS.

Run from the repository root with ``python -m scripts.render_3dgs_gaussian_density``.
Only learned PLY centers, log-scales, quaternions and opacity logits are used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import numpy as np
from plyfile import PlyData

from src.field_visualization import (
    density_pca_frame, evaluate_density_slice, gaussian_density_contributions,
    sigmoid, weighted_quantiles,
)

SCENES = ('lego', 'chair', 'drums', 'ficus')
PLANE_NAMES = ('Lower (q25)', 'Middle (q50)', 'Upper (q75)')
COLORS = ('#0072b2', '#d55e00', '#009e73')
LOG_FLOOR = -6.0


def process_scene(scene, path, output, resolution, radius):
    vertex = PlyData.read(str(path))['vertex'].data
    arrays = {}
    for key, names in {
        'means': ('x', 'y', 'z'), 'logs': ('scale_0', 'scale_1', 'scale_2'),
        'q': ('rot_0', 'rot_1', 'rot_2', 'rot_3'),
    }.items():
        arrays[key] = np.column_stack([vertex[n].astype(np.float64) for n in names])
    means, logs, q = arrays['means'], arrays['logs'], arrays['q']
    alpha = sigmoid(vertex['opacity'].astype(np.float64))
    scales = np.exp(logs); sorted_scales = np.sort(scales, axis=1)
    peak_pdf = alpha * np.exp(-logs.sum(1)) / (2*np.pi)**1.5
    ratio = sorted_scales[:, 2] / sorted_scales[:, 0]
    center, basis, coords = density_pca_frame(means, alpha)
    bounds = np.array([weighted_quantiles(coords[:, i], alpha, [.005, .995]) for i in (0, 1)])
    padding = .05 * np.diff(bounds, axis=1)
    bounds += np.c_[-padding[:, 0], padding[:, 0]]
    u = np.linspace(*bounds[0], resolution); v = np.linspace(*bounds[1], resolution)
    offsets = weighted_quantiles(coords[:, 2], alpha, [.25, .5, .75])
    origins = center + offsets[:, None]*basis[:, 2]
    stat = {
        'source': str(path), 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'gaussian_count': len(alpha), 'sum_opacity': float(alpha.sum()),
        'frame': {'center': center.tolist(), 'basis_columns': basis.tolist(),
                  'definition': 'all-center opacity-weighted global PCA; canonical signs; right handed'},
        'grid': {'shape_per_plane': [resolution, resolution], 'bounds_sample_centers': bounds.tolist(),
                 'spacing_uv': [float(u[1]-u[0]), float(v[1]-v[0])],
                 'bounds_definition': 'opacity-weighted center q0.005..q0.995, plus 5% span on each side',
                 'offset_quantiles': [.25, .5, .75], 'offsets_axis3': offsets.tolist(),
                 'origins': origins.tolist(), 'sampling': 'point values, NOT pixel integrals'},
        'kernel_summaries': {}, 'extreme_counts': {
            'min_scale_below_1e-6': int(np.count_nonzero(sorted_scales[:, 0] < 1e-6)),
            'axis_ratio_above_1e4': int(np.count_nonzero(ratio > 1e4)),
            'opacity_below_0.01': int(np.count_nonzero(alpha < .01)),
            'opacity_above_0.9': int(np.count_nonzero(alpha > .9)),
        }, 'planes': [],
    }
    for name, values in [('opacity', alpha), ('scale_min', sorted_scales[:, 0]),
                         ('scale_mid', sorted_scales[:, 1]), ('scale_max', sorted_scales[:, 2]),
                         ('axis_ratio', ratio), ('kernel_peak_pdf', peak_pdf)]:
        stat['kernel_summaries'][name] = {
            str(p): float(np.quantile(values, p/100)) for p in (0, 1, 5, 25, 50, 75, 95, 99, 100)}
    global_extremes = {}
    record_ids = set()
    for name, values in [('largest_scale', sorted_scales[:, 2]), ('largest_axis_ratio', ratio),
                         ('largest_pdf_peak', peak_pdf)]:
        ids = np.argsort(-values, kind='stable')[:8]
        global_extremes[name] = ids.tolist(); record_ids.update(ids.tolist())
    stat['extreme_kernel_ids'] = global_extremes
    saved = {'u': u, 'v': v, 'center': center, 'basis': basis, 'offsets': offsets, 'origins': origins}
    occupancy = []; pdf = []
    for plane, origin in enumerate(origins):
        result = evaluate_density_slice(means, logs, q, alpha, origin, basis[:, :2], u, v, radius)
        occupancy.append(result['occupancy']); pdf.append(result['pdf'])
        plane_stat = {
            'name': PLANE_NAMES[plane], 'offset': float(offsets[plane]),
            'plane_candidate_count': len(result['plane_indices']),
            'grid_bbox_candidate_count': len(result['grid_indices']),
            'kernels_hitting_any_grid_sample': int(np.count_nonzero(result['hit_counts'])),
            'bbox_candidates_without_sample_hit': int(np.count_nonzero(result['hit_counts'][result['grid_indices']] == 0)),
            'tail_absolute_error_bounds': result['tail_bounds'], 'fields': {},
        }
        for key in ('plane_indices', 'grid_indices', 'hit_counts', 'sample_sums_occupancy', 'sample_sums_pdf'):
            saved[f'plane{plane}_{key}'] = result[key]
        for name in ('occupancy', 'pdf'):
            field = result[name]; positive = field[field > 0]
            peak_rc = np.unravel_index(field.argmax(), field.shape)
            point = origin + u[peak_rc[1]]*basis[:, 0] + v[peak_rc[0]]*basis[:, 1]
            reference_occ, reference_pdf = gaussian_density_contributions([point], means, logs, q, alpha)
            terms = (reference_occ if name == 'occupancy' else reference_pdf)[0]
            top = np.argsort(-terms, kind='stable')[:8]
            sums = result[f'sample_sums_{name}']
            sum_top = np.argsort(-sums, kind='stable')[:8]
            record_ids.update(top.tolist()); record_ids.update(sum_top.tolist())
            field_stats = {
                'min': float(field.min()), 'max': float(field.max()),
                'mean': float(field.mean()), 'zero_fraction': float(np.mean(field == 0)),
                'positive_min': float(positive.min()) if positive.size else None,
                'positive_log10_range': [float(np.log10(positive.min())), float(np.log10(positive.max()))] if positive.size else None,
                'all_sample_quantiles': {str(p): float(np.quantile(field, p/100)) for p in (1, 5, 25, 50, 75, 95, 99, 99.8, 100)},
                'peak_grid_row_col': [int(x) for x in peak_rc], 'peak_world_xyz': point.tolist(),
                'peak_all_kernel_reference': float(terms.sum()),
                'peak_reference_relative_difference': float(abs(terms.sum() - field.max()) / max(terms.sum(), 1e-300)),
                'top_contributors_at_peak': [{'id': int(i), 'value': float(terms[i]),
                                              'fraction': float(terms[i]/terms.sum())} for i in top],
                'top_contributors_by_grid_sum': [{'id': int(i), 'sample_sum': float(sums[i]),
                                                 'fraction': float(sums[i]/sums.sum())} for i in sum_top],
            }
            # Independent all-kernel reference at each field maximum detects
            # missing important kernels and scale-space arithmetic regressions.
            if field_stats['peak_reference_relative_difference'] > 1e-5:
                raise RuntimeError(f'{scene} {plane} {name}: peak reference disagreement')
            plane_stat['fields'][name] = field_stats
        if plane == 1:
            column = int(np.argmax(result['occupancy'].sum(axis=0)))
            rows = weighted_quantiles(np.arange(len(v)), result['occupancy'][:, column],
                                      [.1, .3, .5, .7, .9]).astype(int)
            points = origin + u[column]*basis[:, 0] + v[rows, None]*basis[:, 1]
            ref_occ, ref_pdf = gaussian_density_contributions(points, means, logs, q, alpha)
            samples = []
            for j, row in enumerate(rows):
                top = np.argsort(-ref_occ[j], kind='stable')[:8]
                record_ids.update(top.tolist())
                samples.append({
                    'row_col': [int(row), column], 'world_xyz': points[j].tolist(),
                    'occupancy_grid': float(result['occupancy'][row, column]),
                    'occupancy_reference': float(ref_occ[j].sum()),
                    'pdf_grid': float(result['pdf'][row, column]),
                    'pdf_reference': float(ref_pdf[j].sum()),
                    'top_occupancy_contributors': [{'id': int(i), 'value': float(ref_occ[j, i]),
                                                    'fraction': float(ref_occ[j, i]/ref_occ[j].sum())} for i in top],
                })
            max_relative_error = max(abs(x[f'{f}_grid']-x[f'{f}_reference'])/x[f'{f}_reference']
                                     for x in samples for f in ('occupancy', 'pdf'))
            if max_relative_error > 1e-5:
                raise RuntimeError(f'{scene}: bright-column reference disagreement')
            stat['middle_bright_column_audit'] = {
                'definition': 'column of maximum summed occupancy; rows at occupancy-weighted q10/q30/q50/q70/q90',
                'pca_axis1_coordinate': float(u[column]), 'samples': samples,
                'max_relative_reference_difference': float(max_relative_error)}
        stat['planes'].append(plane_stat)
        print(f'  {PLANE_NAMES[plane]}: {len(result["plane_indices"]):,} plane / '
              f'{len(result["grid_indices"]):,} grid candidates; '
              f'{plane_stat["kernels_hitting_any_grid_sample"]:,} kernels hit samples', flush=True)
    stat['kernel_records'] = {
        str(i): {'mean_xyz': means[i].tolist(), 'mean_pca': coords[i].tolist(),
                 'scales_xyz_local': scales[i].tolist(), 'quaternion_wxyz': q[i].tolist(),
                 'opacity': float(alpha[i]), 'axis_ratio': float(ratio[i]),
                 'peak_pdf': float(peak_pdf[i])} for i in sorted(record_ids)}
    occupancy = np.stack(occupancy); pdf = np.stack(pdf)
    saved.update(occupancy=occupancy, pdf=pdf)
    np.savez_compressed(output / f'{scene}_density_grids.npz', **saved)
    return stat, saved


def slice_panel(ax, grids, plane, field, limits, title, labels=True):
    u, v = grids['u'], grids['v']
    du, dv = u[1]-u[0], v[1]-v[0]
    data = grids[field][plane]
    if field == 'pdf':
        data = np.log10(np.maximum(data, 10.**LOG_FLOOR))
    im = ax.imshow(data, origin='lower', interpolation='nearest', cmap='magma' if field == 'pdf' else 'viridis',
                   norm=Normalize(*limits), extent=[u[0]-du/2, u[-1]+du/2, v[0]-dv/2, v[-1]+dv/2], aspect='equal')
    ax.set_title(title, fontsize=11, pad=8)
    if labels:
        ax.set_xlabel('PCA axis 1 [scene units]', fontsize=9)
        ax.set_ylabel('PCA axis 2 [scene units]', fontsize=9)
        ax.tick_params(labelsize=8)
    else:
        ax.set_xticks([]); ax.set_yticks([])
    return im


def make_atlas(scene, stat, grids, output):
    limits = stat['display']['per_scene']
    fig, axes = plt.subplots(3, 3, figsize=(18, 15), gridspec_kw={'height_ratios': [1, 1, .75]})
    fig.subplots_adjust(left=.065, right=.91, top=.86, bottom=.095, wspace=.32, hspace=.39)
    fig.suptitle(f'{scene.upper()} | Gaussian-kernel posterior density', fontsize=22, weight='bold', y=.975)
    fig.text(.5, .941, r'$\rho_{occ}=\sum_i\alpha_i e^{-d_i^2/2}$  (unnormalized kernels)'
             r'      $\rho_{pdf}=\sum_i\frac{\alpha_i}{(2\pi)^{3/2}\prod_j s_{ij}}e^{-d_i^2/2}$',
             ha='center', fontsize=16)
    fig.text(.5, .911, f'Frozen vanilla 3DGS | seed 1729 / iteration 30000 | {stat["gaussian_count"]:,} kernels | '
             f'{len(grids["u"])} x {len(grids["v"])} samples/plane | per-scene color limits', ha='center', fontsize=11)
    for j in range(3):
        off = stat['grid']['offsets_axis3'][j]
        im_occ = slice_panel(axes[0, j], grids, j, 'occupancy', limits['occupancy'],
                             f'{PLANE_NAMES[j]}: z = {off:+.4f}\nOccupancy proxy (linear)')
        im_pdf = slice_panel(axes[1, j], grids, j, 'pdf', limits['log10_pdf'],
                             f'{PLANE_NAMES[j]}\nPDF proxy (log10)')
    for im, row, label in [(im_occ, 0, 'Occupancy proxy (dimensionless)'),
                            (im_pdf, 1, 'log10 PDF proxy [scene units^-3]')]:
        pos = axes[row, 2].get_position()
        cax = fig.add_axes([.93, pos.y0, .014, pos.height])
        cb = fig.colorbar(im, cax=cax, extend='max' if row == 0 else 'both')
        cb.set_label(label, fontsize=10); cb.ax.tick_params(labelsize=9)
    # Each distribution gives equal weight to grid points in the finite plane ROI.
    for col, name in enumerate(('occupancy', 'pdf')):
        positive = grids[name][grids[name] > 0]
        bins = np.linspace(np.log10(positive.min()), np.log10(positive.max()), 160)
        for j, color in enumerate(COLORS):
            values = grids[name][j].ravel(); pos = values[values > 0]
            logs = np.log10(pos)
            zero = np.mean(values == 0)
            label = f'q{(j+1)*25}: zero {100*zero:.1f}%'
            if name == 'occupancy':
                counts, edges = np.histogram(logs, bins=bins)
                axes[2, col].stairs(counts/len(values), edges, color=color, label=label, linewidth=1.5)
            else:
                # ECDF includes zero samples as an atom at log10(0) = -infinity.
                ordered = np.sort(logs)
                take = np.unique(np.r_[0, np.linspace(0, len(ordered)-1, min(3000, len(ordered)), dtype=int)])
                axes[2, col].plot(ordered[take], (len(values)-len(pos)+take+1)/len(values), color=color, label=label)
        axes[2, col].set_title('Occupancy: log-value histogram' if col == 0 else 'PDF: empirical CDF (zeros included)', fontsize=12)
        axes[2, col].set_xlabel(f'log10 {name} (positive samples; no display floor)', fontsize=10)
        axes[2, col].set_ylabel('Fraction of all grid samples / bin' if col == 0 else 'Fraction of all grid samples <= value', fontsize=10)
        axes[2, col].legend(fontsize=9, loc='best'); axes[2, col].grid(alpha=.2)
        axes[2, col].tick_params(labelsize=9)
        if name == 'pdf':
            axes[2, col].set_ylim(0, 1.02)
    axes[2, 2].axis('off')
    hits = [p['kernels_hitting_any_grid_sample'] for p in stat['planes']]
    planes = [p['plane_candidate_count'] for p in stat['planes']]
    lines = [
        'Sampling / extreme-kernel audit', '',
        'All kernels tested; no top-N selection.',
        '12-sigma Mahalanobis support truncation.',
        'Plane candidates (q25 / q50 / q75):', ' / '.join(f'{x:,}' for x in planes),
        'Kernels hitting samples:', ' / '.join(f'{x:,}' for x in hits), '',
        f'Min learned scale: {stat["kernel_summaries"]["scale_min"]["0"]:.2e}',
        f'Max axis ratio: {stat["kernel_summaries"]["axis_ratio"]["100"]:.2e}',
        f'PDF tail bound: {stat["planes"][0]["tail_absolute_error_bounds"]["pdf"]:.2e}',
        'Thin kernels can fall between grid samples.',
        'Apparent bands can be elongated kernels.',
        'Top kernel IDs / parameters: statistics JSON.',
    ]
    axes[2, 2].text(0, 1, '\n'.join(lines), va='top', fontsize=10.5, linespacing=1.35)
    fig.text(.5, .045, 'POSTERIOR PROXIES: not physical density, occupancy probability, surfaces, or renderer alpha compositing.\n'
             'Point-sampled plane distributions, not 3D volume distributions. Thin peaks may be unresolved; no pixel averaging.\n'
             'Upper colors saturate at pooled per-scene p99.8; PDF display floor 1e-6 includes zeros. Raw grids retain values.',
             ha='center', va='center', fontsize=10, linespacing=1.5)
    fig.savefig(output / f'{scene}_density_atlas.png', dpi=240, facecolor='white')
    plt.close(fig)


def make_comparison(stats, all_grids, output):
    fig, axes = plt.subplots(4, 6, figsize=(24, 17))
    fig.subplots_adjust(left=.055, right=.985, top=.885, bottom=.155, wspace=.12, hspace=.3)
    fig.suptitle('Four frozen vanilla 3DGS scenes | shared density color scales', fontsize=24, weight='bold', y=.976)
    shared = stats['shared_display_limits']
    fig.text(.5, .942, 'Left: unnormalized opacity-kernel sum (linear)     |     Right: determinant-normalized PDF sum (log10)',
             ha='center', fontsize=14)
    fig.text(.5, .915, 'Each row: parallel global-PCA planes at opacity-weighted q25 / q50 / q75 along axis 3. '
             'Axes and spatial extents differ by scene.', ha='center', fontsize=12)
    for row, scene in enumerate(SCENES):
        for j in range(3):
            title = PLANE_NAMES[j] if row == 0 else ''
            im_occ = slice_panel(axes[row, j], all_grids[scene], j, 'occupancy', shared['occupancy'], title, False)
            im_pdf = slice_panel(axes[row, j+3], all_grids[scene], j, 'pdf', shared['log10_pdf'], title, False)
        axes[row, 0].set_ylabel(scene.upper(), fontsize=16, weight='bold', labelpad=16)
    for im, pos, label in [(im_occ, [.1, .12, .34, .013], 'Occupancy proxy | identical limits for all 12 panels'),
                            (im_pdf, [.58, .12, .34, .013], 'log10 PDF proxy | identical limits for all 12 panels')]:
        cb = fig.colorbar(im, cax=fig.add_axes(pos), orientation='horizontal', extend='both')
        cb.set_label(label, fontsize=12); cb.ax.tick_params(labelsize=11)
    fig.text(.5, .042, 'POSTERIOR PROXIES, not physical density or surfaces. Same numerical color limits do not calibrate scene-coordinate units.\n'
             'All kernels considered; 12-sigma support truncation, no top-N cap. 768 x 768 point samples per plane; thin peaks may be missed.\n'
             'Upper limits: pooled p99.8 across all 12 grids. PDF display floor 1e-6 includes zeros. Spatial ROI and saturation are recorded in JSON.',
             ha='center', fontsize=12, linespacing=1.5)
    fig.savefig(output / 'all_scenes_density_comparison.png', dpi=220, facecolor='white')
    plt.close(fig)


def write_report(stats, output):
    shared = stats['shared_display_limits']
    lines = [
        '# Frozen vanilla 3DGS Gaussian-kernel density', '',
        'Lego, chair, drums and ficus use the existing seed_1729 / iteration_30000 PLYs. '
        'Only centers, log-scales, wxyz quaternions and opacity logits are read; no images, mesh, 2DGS, SDF or retraining.', '',
        '## Definitions and interpretation', '',
        '- `rho_occ(x) = sum alpha_i exp(-d_i^2/2)`: renderer-style **unnormalized kernel sum**, '
        'dimensionless and potentially greater than one. It is not renderer transmittance/compositing or occupancy probability.',
        '- `rho_pdf(x) = sum alpha_i exp(-d_i^2/2) / ((2*pi)^(3/2) prod_j s_ij)`: '
        '**determinant-normalized Gaussian PDF mixture**, in inverse scene-coordinate volume. '
        'Weights are not divided by sum(alpha), so its whole-space integral is sum(alpha), not one.',
        '- Both are **posterior proxies, not physical density or surfaces**. '
        'Separate scene coordinate systems are not physically calibrated; shared colors compare numerical proxies only.', '',
        '## Planes, numerical method and truncation', '',
        'An opacity-weighted PCA uses all centers. The first two eigenvector signs are canonicalized by their '
        'largest-magnitude component; axis 3 is their cross product. Offsets are inverse weighted-ECDF '
        'q25/q50/q75 of center coordinates along axis 3. Each axis-1/2 ROI uses weighted q0.005..q0.995 plus 5% span padding. '
        'The same ROI/grid is used for all three planes; tails and centers outside the ROI may still contribute inside it.', '',
        'Every kernel is considered, in source PLY order. A radius-12 Mahalanobis ellipsoid is intersected with each plane. '
        'A conservative conditional bounding rectangle restricts its raster footprint; individual samples beyond radius 12 are zeroed. '
        'There is **no top-N cap**. These are explicitly **tail-truncated point samples**, not exact full infinite-support sums. '
        'The per-point absolute tail bounds are exp(-72) times sum(alpha) for occupancy and sum(PDF peak amplitudes) for PDF. '
        'These mathematical bounds exclude floating-point roundoff. Direct rotation/scale whitening uses all three learned axes, '
        'without covariance pseudoinversion, scale regularization or an exponent floor. All-kernel, untruncated evaluations at '
        'both field maxima independently check each slice (relative differences recorded in JSON). '
        'Values below the absolute tail bound have no guaranteed relative accuracy; the far-left distribution tails describe '
        'the truncated field. The PDF display floor (1e-6) exceeds every reported tail bound.', '',
        'The 768x768 grids do not resolve the smallest learned scales (~1e-8). Kernel hit counts and zero fractions expose this limitation. '
        'Point-sampled histograms/CDFs describe equally weighted locations in these finite 2D ROIs, **not 3D volume distributions**, '
        'pixel-integrated densities or resolution-converged peaks. Zero entries are truncation/numerical zeros, not proven empty space. '
        'No claim of resolution convergence is made; extrema of the continuous field can be much larger.', '',
        '## Figures and display ranges', '',
        'Each 4320x3600 atlas contains three linear-occupancy slices, three log10-PDF slices, an occupancy log-value histogram, '
        'a PDF CDF including the zero atom, and a sampling/extreme-kernel audit. '
        'Atlas color limits pool the three planes of that scene; distribution plots use unfloored raw positive values. '
        'The 5280x3740 comparison uses **one identical occupancy Normalize and one identical log-PDF Normalize** across all scenes/planes.', '',
        f'Shared occupancy limits: {shared["occupancy"]}; shared log10-PDF limits: {shared["log10_pdf"]}. '
        'Upper limits are p99.8 of all 12 grids pooled with equal sample weight. PDF display floor is 1e-6; '
        'zeros and lower positive values share its floor color. Upper saturation and lower-floor fractions are in JSON. '
        'There is no per-panel rescaling in the comparison. Nearest-neighbor display avoids invented smoothness.', '',
        '## Kernel and sampling audit', '',
        '| Scene | Kernels | Opacity median | Min scale | Max scale | Max axis ratio | PDF tail bound |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ]
    for scene in SCENES:
        s = stats['scenes'][scene]; k = s['kernel_summaries']
        lines.append(f'| {scene} | {s["gaussian_count"]:,} | {k["opacity"]["50"]:.4g} | '
                     f'{k["scale_min"]["0"]:.3g} | {k["scale_max"]["100"]:.3g} | '
                     f'{k["axis_ratio"]["100"]:.3g} | {s["planes"][0]["tail_absolute_error_bounds"]["pdf"]:.3g} |')
    lines += ['', '| Scene / plane | Plane / grid-bbox / hit kernels | Occupancy max | Positive PDF log10 range | Zero % |',
              '|---|---:|---:|---:|---:|']
    for scene in SCENES:
        for p in stats['scenes'][scene]['planes']:
            f = p['fields']; r = f['pdf']['positive_log10_range']
            lines.append(f'| {scene} / {p["name"]} | {p["plane_candidate_count"]:,} / '
                         f'{p["grid_bbox_candidate_count"]:,} / {p["kernels_hitting_any_grid_sample"]:,} | '
                         f'{f["occupancy"]["max"]:.4g} | {r[0]:.2f} .. {r[1]:.2f} | {100*f["pdf"]["zero_fraction"]:.2f} |')
    lines += ['', '## Extreme contributors and apparent bands', '',
              'Broad or narrow bands are plausible learned-kernel features: the saved PLYs contain extremely anisotropic kernels. '
              'They are not sufficient evidence of a surface. The following audit identifies the largest middle-plane contributor '
              'by summed occupancy samples (a discrete ROI statistic), and the strongest contributor at the PDF grid maximum. '
        'Full top-eight lists for both definitions at each maximum and by grid sum, plus global scale/anisotropy/PDF-peak extremes, '
              'include source vertex IDs, centers, rotations, scales and opacities in `density_statistics.json`. '
              'The middle-plane maximum-sum occupancy column is also checked at five positions '
              '(row occupancy-weighted q10/q30/q50/q70/q90) using an independent all-kernel sum. '
              'This checks the sampled band against the checkpoint parameters without assuming that a single extreme kernel explains it.', '']
    for scene in SCENES:
        s = stats['scenes'][scene]; mid = s['planes'][1]['fields']
        top = mid['occupancy']['top_contributors_by_grid_sum'][0]
        rec = s['kernel_records'][str(top['id'])]
        peak = mid['pdf']['top_contributors_at_peak'][0]
        peak_rec = s['kernel_records'][str(peak['id'])]
        band = s['middle_bright_column_audit']
        lines.append(f'- **{scene}**: middle-plane occupancy-sum leader ID {top["id"]}, '
                     f'{100*top["fraction"]:.2f}% of sampled sum, alpha={rec["opacity"]:.4g}, '
                     f'local scales={rec["scales_xyz_local"]}, axis ratio={rec["axis_ratio"]:.3g}. '
                     f'PDF-maximum leader ID {peak["id"]} supplies {100*peak["fraction"]:.4f}% of that sample '
                     f'(alpha={peak_rec["opacity"]:.4g}, scales={peak_rec["scales_xyz_local"]}, '
                     f'axis ratio={peak_rec["axis_ratio"]:.3g}). '
                     f'The five-point band check at PCA x={band["pca_axis1_coordinate"]:.4f} has maximum relative '
                     f'reference difference {band["max_relative_reference_difference"]:.3g} across both fields. '
                     f'{s["extreme_counts"]["min_scale_below_1e-6"]:,} kernels have minimum scale below 1e-6; '
                     f'{s["extreme_counts"]["axis_ratio_above_1e4"]:,} have axis ratio above 10,000.')
    lines += ['', '## Reproduction and files', '',
              '```bash',
              'OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/u00134/bin/miniconda3/envs/scgs/bin/python -m scripts.render_3dgs_gaussian_density',
              'OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/u00134/bin/miniconda3/envs/scgs/bin/python -m scripts.verify_3dgs_gaussian_density',
              '```', '',
              '`*_density_grids.npz` stores the raw float64 occupancy/PDF arrays, u/v, frame, offsets/origins, '
              'candidate IDs, per-kernel hit counts and grid sums. `density_statistics.json` stores source hashes, '
              'software versions, definitions, numerical parameters, summaries, display limits and extreme contributors. '
              'Raw NPZs stay in ignored `out/3dgs_gaussian_density/`; curated PNGs, statistics and this report are copied to '
              '`artifacts/3dgs_gaussian_density/`. `verification.json` records test/decode/rerun checks after generation. '
              'No commit or push is performed.', '']
    (output / 'REPORT.md').write_text('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('out/multiscene_foundation/training'))
    parser.add_argument('--output', type=Path, default=Path('out/3dgs_gaussian_density'))
    parser.add_argument('--artifacts', type=Path, default=Path('artifacts/3dgs_gaussian_density'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    stats = {'schema_version': 1, 'scenes': {},
             'software': {'python': platform.python_version(), 'numpy': np.__version__, 'matplotlib': matplotlib.__version__},
             'definitions': {'occupancy': 'sum alpha_i exp(-0.5 d_i^2)',
                             'pdf': 'sum alpha_i exp(-0.5 d_i^2) / ((2*pi)^1.5 prod(scales_i))',
                             'interpretation': 'posterior proxies, not physical density or surfaces; weights not sum-normalized'},
             'numerics': {'dtype': 'float64', 'mahalanobis_radius': 12., 'top_n_cap': None,
                          'grid_resolution': 768, 'pdf_display_floor': 10.**LOG_FLOOR}}
    all_grids = {}
    for scene in SCENES:
        print(f'[{scene}] frozen PLY -> density grids', flush=True)
        path = args.root / scene / 'seed_1729/checkpoints/point_cloud/iteration_30000/point_cloud.ply'
        stats['scenes'][scene], all_grids[scene] = process_scene(scene, path, args.output, 768, 12.)
    shared = {'occupancy': [0., float(np.quantile(np.concatenate([all_grids[s]['occupancy'].ravel() for s in SCENES]), .998))],
              'log10_pdf': [LOG_FLOOR, float(np.log10(np.quantile(np.concatenate([all_grids[s]['pdf'].ravel() for s in SCENES]), .998)))]}
    stats['shared_display_limits'] = shared
    for scene in SCENES:
        grids = all_grids[scene]; s = stats['scenes'][scene]
        own = {'occupancy': [0., float(np.quantile(grids['occupancy'], .998))],
               'log10_pdf': [LOG_FLOOR, float(np.log10(np.quantile(grids['pdf'], .998)))]}
        s['display'] = {'per_scene': own, 'shared': shared, 'fractions': {}}
        for kind, limits in [('per_scene', own), ('shared', shared)]:
            s['display']['fractions'][kind] = {
                'occupancy_saturated_per_plane': np.mean(grids['occupancy'] > limits['occupancy'][1], axis=(1, 2)).tolist(),
                'pdf_saturated_per_plane': np.mean(grids['pdf'] > 10**limits['log10_pdf'][1], axis=(1, 2)).tolist(),
                'pdf_at_or_below_display_floor_per_plane': np.mean(grids['pdf'] <= 10**LOG_FLOOR, axis=(1, 2)).tolist()}
        make_atlas(scene, s, grids, args.output)
        print(f'[{scene}] atlas written', flush=True)
    make_comparison(stats, all_grids, args.output)
    (args.output / 'density_statistics.json').write_text(json.dumps(stats, indent=2, allow_nan=False) + '\n')
    write_report(stats, args.output)
    args.artifacts.mkdir(parents=True, exist_ok=True)
    for path in sorted(args.output.iterdir()):
        if path.suffix in ('.png', '.json', '.md') and path.name != 'verification.json':
            shutil.copyfile(path, args.artifacts / path.name)
    print(f'Curated outputs: {args.artifacts}', flush=True)


if __name__ == '__main__':
    main()
