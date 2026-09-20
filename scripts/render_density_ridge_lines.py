#!/usr/bin/env python3
"""Execute the frozen 2D density-ridge protocol; no scene-specific tuning."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import matplotlib
import numpy as np
import scipy
from scipy import ndimage as ndi
import skimage
from PIL import Image, ImageDraw, ImageFont

from scripts.render_3dgs_fields import (
    load_ply, robust_frame, deterministic_sample, limits_xy, SCENES, C0, CMAP,
)
from src.field_visualization import (
    sigmoid, gaussian_candidate_normals, flattening_score, local_surface_metrics,
)
from src.density_ridge_lines import (
    CHANNELS, BANDWIDTHS, SCALES, axial_tensor, adaptive_kde, disk,
    gradient_energy, ridge_response, broad_score, pooled_select, clean_mask, mask_metrics,
)

PROTOCOL = Path('artifacts/density_ridge_lines/PROTOCOL.md')
TITLES = ('SH-DC color', 'Axial orientation', 'Opacity', 'Flattening', '24-NN planarity',
          'Axis/PCA agreement', 'Surface proxy')
PARAMETERS = {
    'scenes': list(SCENES), 'seed': 1729, 'iteration': 30000, 'grid_long_side': 640,
    'crop_sample': 24000, 'crop_seed': '1701 + sum(map(ord,scene))', 'padding_px': 40,
    'pilot_sigma': 4., 'bandwidths': BANDWIDTHS.tolist(), 'kde_truncate': 4.,
    'adaptive_base_sigma': 2., 'adaptive_exponent': -.5, 'knn': 24, 'pca_batch': 16384,
    'support_min_density': .05, 'support_erosion_radius': 3, 'confidence_denominator': .25,
    'density_pooled_quantile': .99, 'energy_pooled_quantile': .99,
    'derivative_sigma': 1., 'hessian_sigmas': list(SCALES), 'hessian_ratio_cutoff': .5,
    'hessian_ratio_beta': .5, 'nms_offset': 1., 'broad_disk_radius': 1,
    'raw_ink_support_budget': .06, 'cleanup_min_area': 12, 'connectivity': 8,
    'long_component_skeleton_min': 24, 'channel_order': list(CHANNELS),
    'classes': {'color': 'normalized RGB discontinuity', 'axis': 'axial tensor/coherence discontinuity',
                'scalar': 'positive density-confidence-weighted normalized attribute'},
    'baseline': 'Gaussian gradient energy; same energy before Hessian for color/axis',
    'boundary_modes': {'kde': 'constant zero', 'derivatives': 'nearest', 'nms': 'constant zero'},
    'selection': 'pooled stable descending score; scene then row-major ties',
    'cleanup_matching': 'symmetric component removal then pooled trim to smaller area, no re-clean',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')


def prepare(scene):
    source = Path('out/multiscene_foundation/training')/scene/'seed_1729/checkpoints/point_cloud/iteration_30000/point_cloud.ply'
    d = load_ply(source)
    if not all(np.isfinite(a).all() for a in d.values()):
        raise ValueError(f'{scene}: nonfinite PLY input')
    if np.any(np.linalg.norm(d['quat'], axis=1) <= 1e-15):
        raise ValueError(f'{scene}: invalid quaternion')
    p = d['points']; alpha = sigmoid(d['opacity'])
    n, scales = gaussian_candidate_normals(d['log_scales'], d['quat'])
    if not np.isfinite(scales).all() or np.any(scales <= 0):
        raise ValueError(f'{scene}: invalid scales')
    flat = flattening_score(scales)
    center, basis, coords = robust_frame(p, alpha)
    sample = deterministic_sample(len(p), 24000, 1701+sum(map(ord, scene)))
    xlim, ylim = limits_xy(coords[sample])
    spans = np.array([np.ptp(xlim), np.ptp(ylim)])
    width, height = np.ceil(640*spans/spans.max()).astype(int)
    pitch = spans / [width, height]
    print(f'[{scene}] {len(p):,} centers; grid {width}x{height}; all-center local PCA', flush=True)
    planarity = np.zeros(len(p)); agreement = np.zeros(len(p))
    for start in range(0, len(p), 16384):
        ids = np.arange(start, min(start+16384, len(p)))
        local = local_surface_metrics(p, n, ids, k=24)
        planarity[ids] = local['planarity']; agreement[ids] = local['axis_agreement']
    surface = np.cbrt(np.clip(flat*planarity*agreement, 0, 1))
    attrs = np.c_[np.clip(.5+C0*d['dc'], 0, 1), axial_tensor(n).reshape(-1, 9),
                  alpha, flat, planarity, agreement, surface]
    xy = (coords[:, :2]-[xlim[0], ylim[0]])/pitch - .5 + 40
    inside = ((xy[:, 0] >= 0) & (xy[:, 0] <= width+79) &
              (xy[:, 1] >= 0) & (xy[:, 1] <= height+79))
    ids = np.flatnonzero(inside)
    print(f'[{scene}] KDE {len(ids):,} centers within padded crop', flush=True)
    kde = adaptive_kde(xy[ids], attrs[ids], (height+80, width+80))
    crop = np.s_[40:-40, 40:-40]
    arrays = {key: kde[key][crop] for key in ('density', 'numerator', 'normalized', 'pilot')}
    arrays.update(center=center, basis=basis, crop=np.array([xlim, ylim]),
                  pixel_pitch=pitch, crop_sample_indices=sample, kde_indices=ids,
                  kde_bandwidths=kde['bandwidth'], all_center_count=np.array(len(p)),
                  x=xlim[0]+(np.arange(width)+.5)*pitch[0],
                  y=ylim[0]+(np.arange(height)+.5)*pitch[1])
    D = arrays['density']; A = arrays['normalized']
    arrays['confidence'] = D/(D+.25)
    arrays['support'] = ndi.binary_erosion(D >= .05, structure=disk(3), border_value=0)
    tensor = A[..., 3:12].reshape(height, width, 3, 3)
    arrays['tensor'] = tensor
    arrays['coherence'] = np.clip((3*np.linalg.eigvalsh(tensor)[..., -1]-1)/2, 0, 1)
    arrays['color'] = A[..., :3]
    arrays['axis_rgb'] = np.sqrt(np.maximum(np.diagonal(tensor, axis1=-2, axis2=-1), 0))
    arrays['scalar_attributes'] = A[..., 12:17]
    stats = {'source': str(source), 'source_sha256': sha(source), 'gaussians': len(p),
             'kde_centers': len(ids), 'omitted_outside_padded_crop': int((~inside).sum()),
             'grid_shape': [int(height), int(width)], 'pixel_pitch': pitch.tolist(),
             'pixel_anisotropy_ratio': float(pitch.max()/pitch.min()),
             'pilot_geomean': kde['pilot_geomean'], 'support_pixels': int(arrays['support'].sum()),
             'density_mass_in_crop': float(D.sum()),
             'bandwidth_counts': {str(h): int((kde['bandwidth'] == h).sum()) for h in BANDWIDTHS},
             'channels': {}}
    return arrays, stats


def pooled_quantile(values, q=.99):
    joined = np.concatenate([x.ravel() for x in values])
    return float(np.quantile(joined, q)) if joined.size else 1.


def machine_pass(ridge, baseline, raw):
    return bool(.015 <= ridge['ink_support'] <= .12 and ridge['support_overlap'] >= .98
                and ridge['long_component_fraction'] >= .60
                and ridge['fragments_per_10000_support'] <= 80
                and ridge['ink_pixels']/max(raw['ink_pixels'], 1) >= .65
                and ridge['long_component_fraction'] >= baseline['long_component_fraction']-.05)


def correlate(a, b, support):
    a = a[support]; b = b[support]
    if len(a) < 2 or min(np.std(a), np.std(b)) < 1e-15:
        return 0.
    return float(np.corrcoef(a, b)[0, 1])


def compute(all_arrays, stats):
    d99 = pooled_quantile([a['density'][a['density'] > 0] for a in all_arrays])
    params = dict(PARAMETERS, pooled_density_p99=d99, per_channel={})
    for a in all_arrays:
        a['density_factor'] = np.clip(np.log1p(a['density'])/np.log1p(d99), 0, 1)
        a['coupling'] = a['confidence']*np.sqrt(a['density_factor'])
        a['color_energy'] = a['coupling']*gradient_energy(a['color'])
        a['axis_energy'] = a['coupling']*np.sqrt(gradient_energy(a['tensor'].reshape(*a['density'].shape, 9))**2
                                                  + .25*gradient_energy(a['coherence'])**2)
        for key in ('detector_fields', 'ridge_responses', 'ridge_seeds', 'ridge_scores',
                    'winning_scales', 'baseline_scores'):
            a[key] = np.zeros((7, *a['density'].shape))
        for key in ('ridge_raw', 'baseline_raw', 'ridge_cleaned_unmatched', 'baseline_cleaned_unmatched',
                    'ridge_clean', 'baseline_clean'):
            a[key] = np.zeros((7, *a['density'].shape), dtype=bool)
    machine = {}
    for ch, name in enumerate(CHANNELS):
        print(f'[pooled] detecting {name}', flush=True)
        energy99 = None
        if ch < 2:
            key = f'{name}_energy'
            energy99 = pooled_quantile([a[key][a['support'] & (a[key] > 0)] for a in all_arrays])
        for a in all_arrays:
            F = (np.clip(a[f'{name}_energy']/max(energy99, 1e-15), 0, 1) if ch < 2 else
                 a['coupling']*a['scalar_attributes'][..., ch-2])
            a['detector_fields'][ch] = F
            r = ridge_response(F)
            a['ridge_responses'][ch] = r['response']
            a['ridge_seeds'][ch] = r['seed_score']
            a['winning_scales'][ch] = r['winning_scale']
            a['ridge_scores'][ch] = broad_score(r['seed_score'], a['support'])
            a['baseline_scores'][ch] = broad_score(F if ch < 2 else gradient_energy(F), a['support'])
        supports = [a['support'] for a in all_arrays]
        scores_r = [a['ridge_scores'][ch] for a in all_arrays]
        scores_b = [a['baseline_scores'][ch] for a in all_arrays]
        requested = int(.06*sum(s.sum() for s in supports))
        budget = min(requested, sum((r > 0).sum() for r in scores_r), sum((b > 0).sum() for b in scores_b))
        raw_r, select_r = pooled_select(scores_r, supports, budget)
        raw_b, select_b = pooled_select(scores_b, supports, budget)
        clean_r = [clean_mask(m) for m in raw_r]; clean_b = [clean_mask(m) for m in raw_b]
        clean_budget = min(sum(m.sum() for m in clean_r), sum(m.sum() for m in clean_b))
        final_r, match_r = pooled_select(scores_r, clean_r, clean_budget)
        final_b, match_b = pooled_select(scores_b, clean_b, clean_budget)
        response99 = pooled_quantile([a['ridge_responses'][ch][a['support'] & (a['ridge_responses'][ch] > 0)]
                                      for a in all_arrays])
        params['per_channel'][name] = {'class': 'discontinuity' if ch < 2 else 'scalar_positive_ridge',
                                      'energy_p99': energy99, 'response_display_p99': response99,
                                      'requested_raw_ink': requested, 'raw_ridge_selection': select_r,
                                      'raw_baseline_selection': select_b,
                                      'clean_ridge_selection': match_r, 'clean_baseline_selection': match_b,
                                      'pooled_raw_ink_equal': bool(sum(m.sum() for m in raw_r) == sum(m.sum() for m in raw_b)),
                                      'pooled_clean_ink_equal': bool(sum(m.sum() for m in final_r) == sum(m.sum() for m in final_b))}
        passes = []; gains = []
        for i, (scene, a) in enumerate(zip(SCENES, all_arrays)):
            pairs = {'ridge_raw': raw_r[i], 'baseline_raw': raw_b[i],
                     'ridge_cleaned_unmatched': clean_r[i], 'baseline_cleaned_unmatched': clean_b[i],
                     'ridge_clean': final_r[i], 'baseline_clean': final_b[i]}
            mm = {}
            for key, mask in pairs.items():
                a[key][ch] = mask
                mm[key] = mask_metrics(mask, a['support'])
            mm['ridge_raw_retention'] = float(final_r[i].sum()/max(raw_r[i].sum(), 1))
            mm['baseline_raw_retention'] = float(final_b[i].sum()/max(raw_b[i].sum(), 1))
            mm['per_scene_ink_difference'] = int(final_r[i].sum())-int(final_b[i].sum())
            mm['machine_pass'] = machine_pass(mm['ridge_clean'], mm['baseline_clean'], mm['ridge_raw'])
            mm['density_detector_correlation'] = correlate(a['density_factor'], a['detector_fields'][ch], a['support'])
            mm['density_response_correlation'] = correlate(a['density_factor'], a['ridge_responses'][ch], a['support'])
            stats[scene]['channels'][name] = mm
            passes.append(mm['machine_pass'])
            gains.append(mm['ridge_clean']['long_component_fraction']-mm['baseline_clean']['long_component_fraction'])
        decision = 'GO' if sum(passes) >= 3 and np.median(gains) >= .05 else ('PIVOT' if sum(passes) >= 2 else 'STOP')
        machine[name] = {'scene_passes': int(sum(passes)), 'median_long_fraction_gain': float(np.median(gains)), 'decision': decision}
    decisions = [m['decision'] for m in machine.values()]
    global_decision = ('GO' if decisions.count('GO') >= 2 else
                       'PIVOT' if decisions.count('GO') >= 1 or decisions.count('PIVOT') >= 2 else 'STOP')
    return params, {'channels': machine, 'global': global_decision}


# Raster figures use native grid pixels, explicit labels and identical color scales.
BG = (8, 11, 18)
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def font(size):
    return ImageFont.truetype(FONT, size)


def scalar_rgb(a):
    return CMAP(np.clip(a, 0, 1))[..., :3]


def panel(a, ch, kind, parameters):
    support = a['support']
    if kind == 'source':
        rgb = (a['color'] if ch == 0 else a['axis_rgb'] if ch == 1 else scalar_rgb(a['scalar_attributes'][..., ch-2]))
    elif kind == 'input':
        rgb = scalar_rgb(a['detector_fields'][ch])
    elif kind == 'response':
        maximum = parameters['per_channel'][CHANNELS[ch]]['response_display_p99']
        rgb = scalar_rgb(a['ridge_responses'][ch]/max(maximum, 1e-15))
    else:
        rgb = .28*a['color'] + .12*a['density_factor'][..., None]
        mask = a[kind][ch]
        rgb = rgb.copy(); rgb[mask] = [1., .77, .27] if kind.startswith('baseline') else [.25, .95, 1.]
    rgb = np.where(support[..., None], rgb, np.array(BG)/255)
    return Image.fromarray(np.uint8(np.clip(rgb[::-1], 0, 1)*255))


def paste_center(canvas, im, x, y, w, h):
    canvas.paste(im, (x+(w-im.width)//2, y+(h-im.height)//2))


def make_atlas(scene, a, stats, params, out, raw=False):
    tile_w, tile_h, left, top, gap, caption = 650, a['density'].shape[0], 180, 135, 14, 64
    kinds = ('ridge_raw', 'baseline_raw') if raw else ('source', 'input', 'response', 'ridge_clean', 'baseline_clean')
    labels = ('Raw ridge', 'Raw gradient') if raw else ('Source field', 'Detector input', 'Ridge response', 'Broad ridge', 'Gradient baseline')
    step = tile_h+caption+gap
    canvas = Image.new('RGB', (left+7*(tile_w+gap)+20, top+len(kinds)*step+60), BG)
    draw = ImageDraw.Draw(canvas)
    draw.text((left, 15), f'{scene.upper()} | '+('Raw masks before cleanup' if raw else 'Density-aware broad ridge bands'), font=font(34), fill='white')
    draw.text((left, 61), '2D orthographic PCA projection | frozen vanilla 3DGS | no visibility filtering | 3D / multi-view persistence NOT established', font=font(21), fill='#bac7d8')
    for ch, title in enumerate(TITLES):
        x = left+ch*(tile_w+gap)
        draw.text((x+8, 100), title, font=font(26), fill='white')
        for row, kind in enumerate(kinds):
            y = top+row*step
            paste_center(canvas, panel(a, ch, kind, params), x, y, tile_w, tile_h)
            if ch == 0:
                draw.text((14, y+tile_h//2-22), labels[row].replace(' ', '\n', 1), font=font(24), fill='#d1deeb')
            if kind in ('source', 'input', 'response'):
                text = ('RGB; XYZ tensor diagonal' if ch == 1 and kind == 'source' else
                        'Normalized SH-DC RGB' if ch == 0 and kind == 'source' else
                        'Scalar 0 to 1' if kind in ('source', 'input') else
                        f"0 to {params['per_channel'][CHANNELS[ch]]['response_display_p99']:.4f} (pooled p99)")
            else:
                m = stats['channels'][CHANNELS[ch]][kind]
                text = f"Ink/support {100*m['ink_support']:.1f}% | long {100*m['long_component_fraction']:.0f}% | fragments {m['fragments']}"
            draw.text((x+8, y+tile_h+6), text, font=font(19), fill='#aebdd0')
            if kind in ('input', 'response') or (kind == 'source' and ch >= 2):
                ramp = np.linspace(0, 1, 260)[None, :].repeat(10, axis=0)
                canvas.paste(Image.fromarray(np.uint8(scalar_rgb(ramp)*255)), (x+8, y+tile_h+34))
    draw.text((left, canvas.height-44), 'Cyan: ridge | amber: gradient | shared crop and channel scales | ink matched across all four scenes per channel, not separately per scene', font=font(21), fill='#bac7d8')
    canvas.save(out/f"{scene}_{'raw_audit' if raw else 'ridge_atlas'}.png")


def make_summary(all_arrays, stats, params, out):
    tile_w, left, top, gap, caption = 650, 135, 135, 14, 55
    heights = [a['density'].shape[0] for a in all_arrays]
    offsets = np.cumsum([0]+[h+caption+gap for h in heights[:-1]])
    canvas = Image.new('RGB', (left+7*(tile_w+gap)+20, top+sum(heights)+4*(caption+gap)+60), BG)
    draw = ImageDraw.Draw(canvas)
    draw.text((left, 15), 'Across scenes | final density-ridge overlays', font=font(34), fill='white')
    draw.text((left, 62), '2D orthographic PCA diagnostic | same recipe across scenes | no demonstrated multi-view / 3D persistence', font=font(23), fill='#bac7d8')
    for ch, title in enumerate(TITLES):
        x = left+ch*(tile_w+gap)
        draw.text((x+8, 103), title, font=font(26), fill='white')
        for row, (scene, a) in enumerate(zip(SCENES, all_arrays)):
            tile_h = heights[row]
            y = int(top+offsets[row])
            paste_center(canvas, panel(a, ch, 'ridge_clean', params), x, y, tile_w, tile_h)
            if ch == 0:
                draw.text((12, y+tile_h//2), scene.upper(), font=font(25), fill='white')
            m = stats[scene]['channels'][CHANNELS[ch]]['ridge_clean']
            draw.text((x+8, y+tile_h+6), f"Ink {100*m['ink_support']:.1f}% | long {100*m['long_component_fraction']:.0f}% | fragments {m['fragments']}", font=font(20), fill='#aebdd0')
    draw.text((left, canvas.height-44), 'All centers; unit-count adaptive KDE | cyan = selected 3 px nominal bands | dark RGB background = normalized SH-DC field', font=font(22), fill='#bac7d8')
    canvas.save(out/'all_scenes_ridge_summary.png')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, default=Path('out/density_ridge_lines'))
    ap.add_argument('--artifacts', type=Path, default=Path('artifacts/density_ridge_lines'))
    ap.add_argument('--render-only', action='store_true', help='Layout-only render of existing frozen arrays/metrics')
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True); args.artifacts.mkdir(parents=True, exist_ok=True)
    expected = PROTOCOL.with_suffix('.sha256').read_text().split()[0]
    if sha(PROTOCOL) != expected:
        raise RuntimeError('Frozen protocol hash mismatch')
    if args.render_only:
        summary = json.loads((args.output/'metrics.json').read_text())
        all_arrays = []
        for scene in SCENES:
            with np.load(args.output/f'{scene}_ridge_grids.npz', allow_pickle=False) as grids:
                a = {key: grids[key] for key in grids.files}
            all_arrays.append(a)
            make_atlas(scene, a, summary['scenes'][scene], summary['parameters'], args.output)
            make_atlas(scene, a, summary['scenes'][scene], summary['parameters'], args.output, raw=True)
        make_summary(all_arrays, summary['scenes'], summary['parameters'], args.output)
        for file in args.output.glob('*.png'):
            if file.resolve() != (args.artifacts/file.name).resolve():
                shutil.copyfile(file, args.artifacts/file.name)
        return
    stats = {}; all_arrays = []
    for scene in SCENES:
        a, s = prepare(scene); all_arrays.append(a); stats[scene] = s
    params, decision = compute(all_arrays, stats)
    summary = {'scope': '2D orthographic PCA projection diagnostic; cannot establish multi-view/3D persistence',
               'protocol_sha256': expected, 'base_head': 'bcf8260ac194191a9d9c1b28e21d3c82a5c3f0a0',
               'environment': {'python': sys.version, 'numpy': np.__version__, 'scipy': scipy.__version__,
                               'matplotlib': matplotlib.__version__, 'skimage': skimage.__version__},
               'parameters': params, 'scenes': stats, 'machine_decision': decision}
    write_json(args.output/'metrics.json', summary)
    for scene, a in zip(SCENES, all_arrays):
        a['channel_order'] = np.array(CHANNELS)
        np.savez_compressed(args.output/f'{scene}_ridge_grids.npz', **a)
        make_atlas(scene, a, stats[scene], params, args.output)
        make_atlas(scene, a, stats[scene], params, args.output, raw=True)
        print(f'[{scene}] saved grids, atlas and raw audit', flush=True)
    make_summary(all_arrays, stats, params, args.output)
    shutil.copyfile(PROTOCOL, args.output/'PROTOCOL.md')
    for file in sorted(args.output.glob('*.png')) + [args.output/'metrics.json']:
        if file.resolve() != (args.artifacts/file.name).resolve():
            shutil.copyfile(file, args.artifacts/file.name)
    print(json.dumps(decision, indent=2), flush=True)


if __name__ == '__main__':
    main()
