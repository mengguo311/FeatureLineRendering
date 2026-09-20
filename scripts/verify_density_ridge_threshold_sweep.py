#!/usr/bin/env python3
"""Audit saved-grid sweep independently, then byte-compare a complete rerun."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
from scipy import ndimage as ndi
from PIL import Image

from src.density_ridge_lines import CHANNELS, mask_metrics
from src.density_ridge_threshold_sweep import SCENES, BUDGETS
from scripts.render_density_ridge_lines import sha, write_json

OUT = Path('out/density_ridge_threshold_sweep')
ART = Path('artifacts/density_ridge_threshold_sweep')
SOURCE = Path('out/density_ridge_lines')


def main():
    evidence = {'tests': {}, 'npz': {}, 'png_decode': {}, 'selection': {}}
    for label, name in [('targeted', 'tdd_green.log'), ('full', 'unittest_full.log')]:
        path = OUT/name
        log = path.read_text()
        assert re.search(r'\nOK\s*$', log), path
        evidence['tests'][label] = {'count': int(re.search(r'Ran (\d+) tests?', log).group(1)),
                                    'log': str(path), 'sha256': sha(path), 'passed': True}
    reg = json.loads((ART/'preregistration.json').read_text())
    assert sha(ART/'PROTOCOL.md') == reg['protocol_sha256']
    assert sha('tests/test_density_ridge_threshold_sweep.py') == reg['preimplementation_tests_sha256']
    assert sha(OUT/'tdd_red.log') == reg['red_log_sha256']
    for path, digest in reg['prior_files'].items():
        assert sha(path) == digest, path
    metrics = json.loads((OUT/'metrics.json').read_text())
    assert metrics['protocol_sha256'] == reg['protocol_sha256']
    assert metrics['source_metrics_sha256'] == sha(SOURCE/'metrics.json')
    sources = []; masks = []
    for scene in SCENES:
        path = SOURCE/f'{scene}_ridge_grids.npz'
        assert sha(path) == metrics['source_sha256'][scene]
        # Inspect all source arrays, including unchanged fields not used by the sweep.
        with np.load(path, allow_pickle=False) as data:
            source_description = {}
            for key in data.files:
                value = data[key]
                if value.dtype.kind not in 'US':
                    assert np.isfinite(value).all(), (scene, key)
                source_description[key] = {'shape': list(value.shape), 'dtype': str(value.dtype)}
            a = {k: data[k] for k in ('support', 'ridge_scores', 'ridge_responses', 'ridge_clean',
                                      'ridge_raw', 'ridge_cleaned_unmatched', 'channel_order')}
        with np.load(OUT/f'{scene}_threshold_masks.npz', allow_pickle=False) as data:
            o = {k: data[k] for k in data.files}
        shape = a['support'].shape
        assert list(shape) == metrics['scenes'][scene]['shape']
        assert int(a['support'].sum()) == metrics['scenes'][scene]['support_pixels']
        for key in ('ridge_scores', 'ridge_responses', 'ridge_clean', 'ridge_raw', 'ridge_cleaned_unmatched'):
            assert a[key].shape == (7, *shape)
        assert tuple(a['channel_order']) == tuple(o['channel_order']) == CHANNELS
        np.testing.assert_array_equal(o['budgets'], BUDGETS)
        np.testing.assert_array_equal(o['reference'], a['ridge_clean'])
        np.testing.assert_array_equal(o['support'], a['support'])
        for key in ('support', 'reference', 'raw', 'clean'):
            assert o[key].dtype == np.bool_ and np.isfinite(o[key]).all()
        assert o['reference'].shape == (7, *shape)
        assert o['raw'].shape == o['clean'].shape == (4, 7, *shape)
        assert not np.any(o['raw'] & ~o['support'])
        assert not np.any(o['clean'] & ~o['raw'])
        for stage in ('raw', 'clean'):
            assert not np.any(o[stage][:-1] & ~o[stage][1:])
        np.testing.assert_array_equal(o['raw'][0], a['ridge_raw'])
        np.testing.assert_array_equal(o['clean'][0], a['ridge_cleaned_unmatched'])
        for ch, channel in enumerate(CHANNELS):
            info = metrics['scenes'][scene]['channels'][channel]
            assert mask_metrics(o['reference'][ch], o['support']) == info['reference']
            assert info['six_percent_reproduction'] == {'raw': True, 'cleaned_unmatched': True}
            assert info['reference_to_fresh6_added_pixels'] == int((o['clean'][0, ch] & ~o['reference'][ch]).sum())
            assert info['reference_to_fresh6_removed_pixels'] == int((o['reference'][ch] & ~o['clean'][0, ch]).sum())
            assert info['nesting']['raw'] and info['nesting']['clean']
            for b, budget in enumerate(BUDGETS):
                key = str(round(budget*100))
                level = info['levels'][key]
                for stage in ('raw', 'clean'):
                    m = o[stage][b, ch]
                    assert mask_metrics(m, o['support']) == level[stage], (scene, channel, key, stage)
                    assert int(m.sum()) == level[f'{stage}_selected_count']
                    if b:
                        before = o[stage][b-1, ch]
                        pair = info['nesting']['pairs'][f'{round(BUDGETS[b-1]*100)}->{key}'][stage]
                        assert pair == {'removed': int((before & ~m).sum()), 'added': int((m & ~before).sum())}
                assert level['cleanup_retention'] == float(o['clean'][b, ch].sum()/max(o['raw'][b, ch].sum(), 1))
                # Independent 8-connected area filter: no call to clean_mask.
                labels, _ = ndi.label(o['raw'][b, ch], np.ones((3, 3), bool))
                areas = np.bincount(labels.ravel())
                expected = (labels > 0) & (areas[labels] >= 12)
                np.testing.assert_array_equal(expected, o['clean'][b, ch])
        sources.append(a); masks.append(o)
        evidence['npz'][scene] = {'source_sha256': sha(path), 'source_arrays': source_description,
                                  'output_arrays': {k: {'shape': list(v.shape), 'dtype': str(v.dtype)} for k, v in o.items()},
                                  'metrics_recomputed': True, 'cleanup_recomputed': True,
                                  'raw_and_clean_nested': True, 'six_percent_reproduced': True}
    total = sum(int(a['support'].sum()) for a in sources)
    support = np.concatenate([a['support'].ravel() for a in sources])
    for ch, channel in enumerate(CHANNELS):
        scores = np.concatenate([a['ridge_scores'][ch].ravel() for a in sources])
        candidates = np.flatnonzero(support & (scores > 0))
        # Independent lexicographic ranking: descending value, ascending global index.
        ranked = candidates[np.lexsort((candidates, -scores[candidates]))]
        evidence['selection'][channel] = {}
        for b, budget in enumerate(BUDGETS):
            key = str(round(100*budget))
            meta = metrics['pooled'][channel]['levels'][key]
            requested = int(budget*total); selected = min(requested, len(ranked))
            expected = np.zeros(len(scores), bool); expected[ranked[:selected]] = True
            actual = np.concatenate([o['raw'][b, ch].ravel() for o in masks])
            np.testing.assert_array_equal(actual, expected)
            threshold = float(scores[ranked[selected-1]]) if selected else None
            assert meta['requested'] == requested and meta['selected'] == selected
            assert meta['positive_candidates'] == len(ranked) and meta['threshold'] == threshold
            assert meta['candidate_exhausted'] == (selected < requested)
            assert meta['budget'] == budget and meta['support_pixels'] == total
            clean_count = sum(int(o['clean'][b, ch].sum()) for o in masks)
            assert meta['clean_selected'] == clean_count
            assert meta['raw_ink_support'] == selected/total
            assert meta['clean_ink_support'] == clean_count/total
            for scene in SCENES:
                assert metrics['scenes'][scene]['channels'][channel]['levels'][key]['pooled_threshold'] == threshold
            evidence['selection'][channel][key] = {'requested': requested, 'selected': selected,
                                                   'clean': clean_count, 'threshold': threshold}
    for name, digest in json.loads((OUT/'science_hashes.json').read_text()).items():
        assert sha(OUT/name) == digest, name
    names = ['metrics.json', 'science_hashes.json', 'PROTOCOL.md']
    names += [p.name for p in sorted(OUT.glob('*_threshold_masks.npz'))]
    names += [p.name for p in sorted(OUT.glob('*.png'))]
    hashes = {name: sha(OUT/name) for name in names}
    cmd = [sys.executable, '-m', 'scripts.render_density_ridge_threshold_sweep',
           '--output', str(OUT/'determinism_rerun'), '--artifacts', str(OUT/'determinism_rerun/curated')]
    print('Complete saved-grid selection/metrics/render rerun', flush=True)
    with (OUT/'determinism_rerun.log').open('w') as log:
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True,
                       env=dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1'))
    for name, digest in hashes.items():
        assert sha(OUT/'determinism_rerun'/name) == digest, name
        if not name.endswith('.npz'):
            assert sha(ART/name) == digest, name
        if name.endswith('.png') or name in ('metrics.json', 'science_hashes.json'):
            assert sha(OUT/'determinism_rerun/curated'/name) == digest, name
    for folder in (OUT, ART, OUT/'determinism_rerun', OUT/'determinism_rerun/curated', OUT/'inspection'):
        for path in sorted(folder.glob('*.png')):
            with Image.open(path) as im:
                im.verify()
            with Image.open(path) as im:
                im.load()
                evidence['png_decode'][str(path)] = {'size': list(im.size), 'mode': im.mode}
    for path, digest in reg['prior_files'].items():
        assert sha(path) == digest, path
    evidence['preservation'] = {'prior_files_unchanged': len(reg['prior_files']), 'tests_and_protocol_unchanged': True,
                                'science_hashes_before_visual_inspection_unchanged': True}
    evidence['determinism'] = {'command': cmd, 'file_count': len(names), 'all_match': True, 'sha256': hashes,
                               'scope': 'Complete saved-grid sweep, same CPU/interpreter/dependencies; no field construction rerun'}
    evidence['code_sha256'] = {str(p): sha(p) for p in [Path('src/density_ridge_threshold_sweep.py'),
                              Path('scripts/render_density_ridge_threshold_sweep.py'), Path(__file__).relative_to(Path.cwd()),
                              Path('tests/test_density_ridge_threshold_sweep.py')]}
    evidence['visual_inspection'] = 'Separate unblinded model review in visual_review.json and REPORT.md'
    for folder in (OUT, ART):
        write_json(folder/'verification.json', evidence)
    print(f"PASS: {len(names)} byte-identical outputs; {len(evidence['png_decode'])} PNG decodes; "
          f"{evidence['tests']['full']['count']} full tests; all masks/counts/metrics/nesting verified", flush=True)


if __name__ == '__main__':
    main()
