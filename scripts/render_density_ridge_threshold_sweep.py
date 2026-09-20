#!/usr/bin/env python3
"""Run the frozen saved-grid mask-budget sweep and render comparison figures."""
import argparse
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import scipy
import skimage
from PIL import Image, ImageDraw, __version__ as pillow_version

from src.density_ridge_lines import CHANNELS, mask_metrics
from src.density_ridge_threshold_sweep import SCENES, BUDGETS, select_sweep, assert_nested
from scripts.render_density_ridge_lines import BG, TITLES, font, scalar_rgb, sha, write_json

ART = Path('artifacts/density_ridge_threshold_sweep')
SOURCE = Path('out/density_ridge_lines')
KEYS = ('support', 'ridge_scores', 'ridge_responses', 'ridge_raw',
        'ridge_cleaned_unmatched', 'ridge_clean', 'color', 'density_factor', 'channel_order')
LEVELS = ('reference', '6', '12', '20', '35')
LABELS = ('Original final', 'Fresh 6%', 'Fresh 12%', 'Fresh 20%', 'Fresh 35%')
CYAN = np.array([.25, .95, 1.])


def load_sources():
    registration = json.loads((ART/'preregistration.json').read_text())
    assert sha(ART/'PROTOCOL.md') == registration['protocol_sha256']
    arrays = []
    for scene in SCENES:
        path = SOURCE/f'{scene}_ridge_grids.npz'
        assert sha(path) == registration['prior_files'][str(path)]
        with np.load(path, allow_pickle=False) as data:
            a = {k: data[k] for k in KEYS}
        assert tuple(a['channel_order']) == CHANNELS
        assert a['support'].dtype == np.bool_
        for key, value in a.items():
            if value.dtype.kind not in 'US':
                assert np.isfinite(value).all(), (scene, key)
        arrays.append(a)
    return arrays, registration


def compute(arrays, registration):
    outputs = [dict(support=a['support'], reference=a['ridge_clean'],
                    raw=np.zeros((4, 7, *a['support'].shape), bool),
                    clean=np.zeros((4, 7, *a['support'].shape), bool),
                    budgets=np.array(BUDGETS), channel_order=np.array(CHANNELS)) for a in arrays]
    old = json.loads((SOURCE/'metrics.json').read_text())
    metrics = {
        'base_head': registration['base_head'], 'protocol_sha256': registration['protocol_sha256'],
        'scope': 'Saved-grid 2D mask-budget sensitivity; no scientific pass defined or selected',
        'environment': {'python': sys.version, 'numpy': np.__version__, 'scipy': scipy.__version__,
                        'skimage': skimage.__version__, 'pillow': pillow_version},
        'parameters': {'scenes': list(SCENES), 'channels': list(CHANNELS), 'budgets': list(BUDGETS),
                       'min_area': 12, 'connectivity': 8, 'long_skeleton_min': 24,
                       'baseline_matching': False, 'second_trim': False,
                       'reference': 'saved ridge_clean from committed 6%-pooled exact-ink protocol',
                       'response_display': 'saved full Hessian response within support, original pooled p99'},
        'source_sha256': {s: sha(SOURCE/f'{s}_ridge_grids.npz') for s in SCENES},
        'source_metrics_sha256': sha(SOURCE/'metrics.json'), 'pooled': {},
        'scenes': {s: {'shape': list(a['support'].shape), 'support_pixels': int(a['support'].sum()),
                       'channels': {}} for s, a in zip(SCENES, arrays)},
    }
    supports = [a['support'] for a in arrays]
    for ch, name in enumerate(CHANNELS):
        print(f'Selecting saved {name} scores', flush=True)
        raw, clean, meta = select_sweep([a['ridge_scores'][ch] for a in arrays], supports)
        metrics['pooled'][name] = {'levels': {}, 'response_display_p99':
                                 old['parameters']['per_channel'][name]['response_display_p99']}
        for b, key in enumerate(LEVELS[1:]):
            pooled = dict(meta[b])
            pooled['raw_ink_support'] = pooled['selected']/pooled['support_pixels']
            pooled['clean_selected'] = sum(int(m[b].sum()) for m in clean)
            pooled['clean_ink_support'] = pooled['clean_selected']/pooled['support_pixels']
            metrics['pooled'][name]['levels'][key] = pooled
        for i, (scene, a, o) in enumerate(zip(SCENES, arrays, outputs)):
            np.testing.assert_array_equal(raw[i][0], a['ridge_raw'][ch])
            np.testing.assert_array_equal(clean[i][0], a['ridge_cleaned_unmatched'][ch])
            o['raw'][:, ch] = raw[i]; o['clean'][:, ch] = clean[i]
            info = {'reference': mask_metrics(o['reference'][ch], a['support']), 'levels': {},
                    'six_percent_reproduction': {'raw': True, 'cleaned_unmatched': True},
                    'reference_to_fresh6_added_pixels': int((clean[i][0] & ~a['ridge_clean'][ch]).sum()),
                    'reference_to_fresh6_removed_pixels': int((a['ridge_clean'][ch] & ~clean[i][0]).sum()),
                    'nesting': {'raw': True, 'clean': True, 'pairs': {}}}
            for b, key in enumerate(LEVELS[1:]):
                info['levels'][key] = {
                    'raw': mask_metrics(raw[i][b], a['support']),
                    'clean': mask_metrics(clean[i][b], a['support']),
                    'pooled_threshold': meta[b]['threshold'],
                    'raw_selected_count': int(raw[i][b].sum()),
                    'clean_selected_count': int(clean[i][b].sum()),
                    'cleanup_retention': float(clean[i][b].sum()/max(raw[i][b].sum(), 1))}
                if b:
                    info['nesting']['pairs'][f'{LEVELS[b]}->{key}'] = {
                        stage: {'removed': int((m[b-1] & ~m[b]).sum()),
                                'added': int((m[b] & ~m[b-1]).sum())}
                        for stage, m in [('raw', raw[i]), ('clean', clean[i])]}
            metrics['scenes'][scene]['channels'][name] = info
    for o in outputs:
        assert_nested(o['raw']); assert_nested(o['clean'])
    return outputs, metrics


def panel(a, masks, ch, level, metrics):
    if level == 'response':
        maximum = metrics['pooled'][CHANNELS[ch]]['response_display_p99']
        rgb = scalar_rgb(a['ridge_responses'][ch]/max(maximum, 1e-15))
    else:
        rgb = .28*a['color'] + .12*a['density_factor'][..., None]
        mask = masks['reference'][ch] if level == 'reference' else masks['clean'][LEVELS.index(level)-1, ch]
        rgb = rgb.copy(); rgb[mask] = CYAN
    rgb = np.where(a['support'][..., None], rgb, np.array(BG)/255)
    return Image.fromarray(np.uint8(np.clip(rgb[::-1], 0, 1)*255))


def caption(metrics, scene, ch, level):
    support = metrics['scenes'][scene]['support_pixels']
    if level == 'response':
        return [f'Ink: n/a (response); support {support:,} px',
                f"0 to {metrics['pooled'][CHANNELS[ch]]['response_display_p99']:.5f} (pooled p99)"]
    info = metrics['scenes'][scene]['channels'][CHANNELS[ch]]
    m = info['reference'] if level == 'reference' else info['levels'][level]['clean']
    return [f"Ink/support {m['ink_pixels']:,}/{support:,} = {100*m['ink_support']:.2f}%",
            f"Long {100*m['long_component_fraction']:.1f}% | components {m['components']} | fragments {m['fragments']}"]


def draw_cell(canvas, a, masks, metrics, scene, ch, level, x, y, w, h, scale=1):
    im = panel(a, masks, ch, level, metrics)
    if scale != 1:
        im = im.resize((im.width*scale, im.height*scale), Image.Resampling.NEAREST)
    canvas.paste(im, (x+(w-im.width)//2, y+(h-im.height)//2))
    draw = ImageDraw.Draw(canvas)
    size = 20 if scale == 1 else 28
    for j, line in enumerate(caption(metrics, scene, ch, level)):
        draw.text((x+8, y+h+5+j*(size+7)), line, font=font(size), fill='#b9c8da')


def make_atlas(scene, a, masks, metrics, out):
    w, h, left, top, gap, cap = 650, a['support'].shape[0], 210, 156, 14, 76
    levels = ('response', *LEVELS)
    labels = ('Hessian\nresponse', 'Original final\n6% + matching', 'Fresh 6%', 'Fresh 12%', 'Fresh 20%', 'Fresh 35%')
    canvas = Image.new('RGB', (left+7*(w+gap)+20, top+6*(h+cap+gap)+70), BG)
    d = ImageDraw.Draw(canvas)
    d.text((left, 14), f'{scene.upper()} | Frozen threshold relaxation | all seven channels', font=font(34), fill='white')
    d.text((left, 61), 'Cyan = selected broad mask; same dim background | budgets pooled across four scenes; actual local ink printed in each cell', font=font(23), fill='#b9c8da')
    for ch, title in enumerate(TITLES):
        x = left+ch*(w+gap)
        d.text((x+8, 112), title, font=font(25), fill='white')
        for row, level in enumerate(levels):
            y = top+row*(h+cap+gap)
            if ch == 0:
                d.text((12, y+h//2-25), labels[row], font=font(24), fill='white')
            draw_cell(canvas, a, masks, metrics, scene, ch, level, x, y, w, h)
    d.text((left, canvas.height-50), 'Full saved response context within support; pooled display p99 clipping only | fresh masks: area >=12, 8-connected; no matching/second trim | 2D projection only', font=font(22), fill='#b9c8da')
    canvas.save(out/f'{scene}_threshold_atlas.png')


def make_focus(ch, arrays, outputs, metrics, out):
    w, h, left, top, gap, cap = 1280, 2*max(a['support'].shape[0] for a in arrays), 235, 164, 24, 95
    levels = ('response', *LEVELS)
    labels = ('Hessian\nresponse', 'Original final\n6% + matching', 'Fresh 6%', 'Fresh 12%', 'Fresh 20%', 'Fresh 35%')
    canvas = Image.new('RGB', (left+4*(w+gap)+20, top+6*(h+cap+gap)+80), BG)
    d = ImageDraw.Draw(canvas)
    d.text((left, 14), f'{TITLES[ch]} | All scenes and frozen thresholds | 2x native pixels', font=font(42), fill='white')
    d.text((left, 73), 'Identical dim background; cyan is the mask | pooled budget is not per-scene coverage | nearest-neighbor enlargement preserves exact pixels', font=font(28), fill='#b9c8da')
    for i, (scene, a, masks) in enumerate(zip(SCENES, arrays, outputs)):
        x = left+i*(w+gap)
        d.text((x+12, 120), scene.upper(), font=font(30), fill='white')
        for row, level in enumerate(levels):
            y = top+row*(h+cap+gap)
            if i == 0:
                d.text((12, y+h//2-35), labels[row], font=font(28), fill='white')
            draw_cell(canvas, a, masks, metrics, scene, ch, level, x, y, w, h, scale=2)
    d.text((left, canvas.height-58), 'Response context: saved full Hessian response, supported region, original pooled p99 | fresh cleanup area >=12 only | 2D; no accuracy or persistence claim', font=font(28), fill='#b9c8da')
    canvas.save(out/f'{CHANNELS[ch]}_all_scenes_focus.png')


def make_summary(arrays, outputs, metrics, out):
    w, left, top, gap, cap = 650, 205, 150, 16, 75
    height = top+2*sum(a['support'].shape[0]+cap+gap for a in arrays)+75
    canvas = Image.new('RGB', (left+5*(w+gap)+20, height), BG)
    d = ImageDraw.Draw(canvas)
    d.text((left, 14), 'All scenes | Opacity and flattening | All frozen mask levels', font=font(32), fill='white')
    d.text((left, 61), 'Native mask pixels; cyan on fixed background | seven-channel detail and response context in scene atlases', font=font(22), fill='#b9c8da')
    for col, label in enumerate(LABELS):
        d.text((left+col*(w+gap)+8, 105), label, font=font(26), fill='white')
    y = top
    for scene, a, masks in zip(SCENES, arrays, outputs):
        h = a['support'].shape[0]
        for ch in (2, 3):
            d.text((12, y+h//2-30), f'{scene.upper()}\n{TITLES[ch]}', font=font(24), fill='white')
            for col, level in enumerate(LEVELS):
                draw_cell(canvas, a, masks, metrics, scene, ch, level, left+col*(w+gap), y, w, h)
            y += h+cap+gap
    d.text((left, canvas.height-48), 'Original final includes historical baseline matching; fresh rows do not | no scientific pass or threshold winner selected', font=font(23), fill='#b9c8da')
    canvas.save(out/'all_scenes_threshold_summary.png')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, default=Path('out/density_ridge_threshold_sweep'))
    ap.add_argument('--artifacts', type=Path, default=ART)
    ap.add_argument('--render-only', action='store_true')
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True); args.artifacts.mkdir(parents=True, exist_ok=True)
    arrays, registration = load_sources()
    if args.render_only:
        metrics = json.loads((args.output/'metrics.json').read_text())
        outputs = []
        for scene in SCENES:
            with np.load(args.output/f'{scene}_threshold_masks.npz', allow_pickle=False) as a:
                outputs.append({k: a[k] for k in a.files})
    else:
        outputs, metrics = compute(arrays, registration)
        write_json(args.output/'metrics.json', metrics)
        for scene, masks in zip(SCENES, outputs):
            np.savez_compressed(args.output/f'{scene}_threshold_masks.npz', **masks)
        write_json(args.output/'science_hashes.json', {p.name: sha(p) for p in
                   [args.output/'metrics.json', *sorted(args.output.glob('*_threshold_masks.npz'))]})
    for scene, a, masks in zip(SCENES, arrays, outputs):
        make_atlas(scene, a, masks, metrics, args.output)
        print(f'Rendered {scene} atlas', flush=True)
    for ch in (2, 3):
        make_focus(ch, arrays, outputs, metrics, args.output)
        print(f'Rendered {CHANNELS[ch]} focus', flush=True)
    make_summary(arrays, outputs, metrics, args.output)
    shutil.copyfile(ART/'PROTOCOL.md', args.output/'PROTOCOL.md')
    for file in [*sorted(args.output.glob('*.png')), args.output/'metrics.json', args.output/'science_hashes.json']:
        if file.resolve() != (args.artifacts/file.name).resolve():
            shutil.copyfile(file, args.artifacts/file.name)
    print('Sweep and figures complete', flush=True)


if __name__ == '__main__':
    main()
