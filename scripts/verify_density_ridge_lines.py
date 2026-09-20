#!/usr/bin/env python3
"""Verify tests, provenance, NPZ semantics, PNG decoding, and full PLY rerun."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
from PIL import Image

from src.density_ridge_lines import CHANNELS, mask_metrics

OUT = Path('out/density_ridge_lines')
ART = Path('artifacts/density_ridge_lines')
SCENES = ('lego', 'chair', 'drums', 'ficus')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reuse-full-log', type=Path)
    args = parser.parse_args()
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
    evidence = {'tests': {}, 'npz': {}, 'png_decode': {}, 'preservation': {}}
    for label, pattern in [('targeted', 'test_density_ridge_lines.py'), ('field', 'test_field_visualization.py'),
                           ('density', 'test_gaussian_density.py'), ('full', 'test*.py')]:
        cmd = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', pattern, '-v']
        print(f'Running {label} tests', flush=True)
        if label == 'full' and args.reuse_full_log:
            log = args.reuse_full_log.read_text()
            if not re.search(r'\nOK\s*$', log):
                raise RuntimeError('Cannot reuse an incomplete or failing full-suite log')
            returncode = 0
            (OUT/'unittest_full.log').write_text(log)
        else:
            with (OUT/f'unittest_{label}.log').open('w') as f:
                proc = subprocess.run(cmd, env=env, stdout=f, stderr=subprocess.STDOUT)
            log = (OUT/f'unittest_{label}.log').read_text()
            returncode = proc.returncode
        count = re.search(r'Ran (\d+) tests?', log)
        evidence['tests'][label] = {'command': cmd, 'exit_code': returncode,
                                    'count': int(count.group(1)) if count else None}
        if returncode:
            (ART/'verification_partial.json').write_text(json.dumps(evidence, indent=2)+'\n')
            raise RuntimeError(f'{label} tests failed; see log')
    metrics = json.loads((OUT/'metrics.json').read_text())
    names = (['metrics.json', 'PROTOCOL.md', 'all_scenes_ridge_summary.png']
             + [f'{s}_{suffix}' for s in SCENES for suffix in ('ridge_grids.npz', 'ridge_atlas.png', 'raw_audit.png')])
    baseline = {name: sha(OUT/name) for name in names}
    cmd = [sys.executable, '-m', 'scripts.render_density_ridge_lines',
           '--output', str(OUT/'determinism_rerun'), '--artifacts', str(OUT/'determinism_rerun/curated')]
    print('Full rerun from all four PLYs', flush=True)
    with (OUT/'determinism_rerun.log').open('w') as f:
        subprocess.run(cmd, env=env, stdout=f, stderr=subprocess.STDOUT, check=True)
    for name in names:
        assert sha(OUT/'determinism_rerun'/name) == baseline[name], name
        if not name.endswith('.npz'):
            assert sha(ART/name) == baseline[name], name
    evidence['determinism'] = {'command': cmd, 'all_match': True, 'file_count': len(names), 'sha256': baseline,
                               'scope': 'bytewise, same CPU/interpreter/dependencies; PLY reload, all-center PCA/KDE, selection and rendering'}
    totals = {key: np.zeros(7, dtype=np.int64) for key in ('ridge_raw','baseline_raw','ridge_clean','baseline_clean')}
    for scene in SCENES:
        s = metrics['scenes'][scene]
        assert sha(s['source']) == s['source_sha256']
        with np.load(OUT/f'{scene}_ridge_grids.npz', allow_pickle=False) as a:
            checked = {}
            for key in a.files:
                x = a[key]
                if x.dtype.kind not in 'US':
                    assert np.isfinite(x).all(), (scene, key)
                checked[key] = {'shape': list(x.shape), 'dtype': str(x.dtype)}
            assert list(a['channel_order']) == list(CHANNELS)
            assert list(a['density'].shape) == s['grid_shape']
            assert a['density'].dtype == np.float64
            assert (a['density'] >= 0).all()
            np.testing.assert_allclose(a['numerator']/np.maximum(a['density'][..., None],1e-15), a['normalized'], atol=0, rtol=0)
            np.testing.assert_allclose(a['basis'].T@a['basis'], np.eye(3), atol=1e-12)
            np.testing.assert_allclose(a['confidence'], a['density']/(a['density']+.25), atol=0, rtol=0)
            assert np.all(np.diff(a['kde_indices']) > 0)
            with np.load(Path('out/3dgs_field_visualization')/f'{scene}_field_samples.npz') as prior:
                np.testing.assert_array_equal(a['crop_sample_indices'], prior['indices'])
            for ch, name in enumerate(CHANNELS):
                for method in ('ridge', 'baseline'):
                    raw = a[method+'_raw'][ch]
                    mid = a[method+'_cleaned_unmatched'][ch]
                    final = a[method+'_clean'][ch]
                    assert raw.dtype == np.bool_ and mid.dtype == np.bool_ and final.dtype == np.bool_
                    assert np.all(~final | mid) and np.all(~mid | raw)
                    assert np.all(~raw | a['support'])
                    for stage in ('raw','cleaned_unmatched','clean'):
                        key = method+'_'+stage
                        mm = mask_metrics(a[key][ch], a['support'])
                        assert mm == s['channels'][name][key], (scene, name, key)
                    totals[method+'_raw'][ch] += raw.sum()
                    totals[method+'_clean'][ch] += final.sum()
                assert np.isin(a['winning_scales'][ch], [0,1.5,2.5,4]).all()
            evidence['npz'][scene] = {'source_sha256': s['source_sha256'], 'arrays': checked,
                                     'checks': 'finite, shape, float64, normalized KDE denominator, orthogonal frame, prior crop sample, masks subset/support, all recomputed mask metrics'}
    np.testing.assert_array_equal(totals['ridge_raw'], totals['baseline_raw'])
    np.testing.assert_array_equal(totals['ridge_clean'], totals['baseline_clean'])
    for ch, name in enumerate(CHANNELS):
        p = metrics['parameters']['per_channel'][name]
        assert totals['ridge_raw'][ch] == p['raw_ridge_selection']['selected']
        assert totals['ridge_clean'][ch] == p['clean_ridge_selection']['selected']
    evidence['pooled_ink'] = {k: v.tolist() for k,v in totals.items()}
    for folder in (OUT, ART, OUT/'determinism_rerun', OUT/'determinism_rerun/curated'):
        for path in sorted(folder.glob('*.png')):
            with Image.open(path) as im:
                im.verify()
            with Image.open(path) as im:
                im.load()
                evidence['png_decode'][str(path)] = {'size': list(im.size), 'mode': im.mode}
    registration = json.loads((ART/'preregistration.json').read_text())
    assert sha(ART/'PROTOCOL.md') == registration['protocol_sha256'] == metrics['protocol_sha256']
    assert sha('tests/test_density_ridge_lines.py') == registration['preimplementation_tests_sha256']
    for path, digest in registration['prior_artifacts'].items():
        assert sha(path) == digest, path
    evidence['preservation'] = {'prior_files_unchanged': len(registration['prior_artifacts']),
                                'protocol_unchanged': True, 'preregistered_tests_unchanged': True}
    layout_hashes = json.loads((OUT/'pre_layout_science_hashes.json').read_text())
    for name, digest in layout_hashes.items():
        assert sha(OUT/name) == digest
    evidence['preservation']['layout_only_scientific_files_unchanged'] = len(layout_hashes)
    evidence['code_sha256'] = {p: sha(p) for p in ('src/density_ridge_lines.py','scripts/render_density_ridge_lines.py',
                                                 'scripts/verify_density_ridge_lines.py','tests/test_density_ridge_lines.py')}
    evidence['visual_inspection'] = 'Separately recorded in visual_review.json and REPORT.md; PNG decoding alone is not visual verification.'
    for folder in (OUT, ART):
        (folder/'verification.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print(f'PASS: {len(names)} byte-identical outputs; {len(evidence["png_decode"])} PNG decodes; '
          f'{evidence["tests"]["full"]["count"]} full tests; prior artifacts preserved', flush=True)


if __name__ == '__main__':
    main()
