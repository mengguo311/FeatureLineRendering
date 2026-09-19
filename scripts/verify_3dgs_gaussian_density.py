#!/usr/bin/env python3
"""Test, regenerate, decode and byte-compare the Gaussian-density deliverables."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image


def main():
    output = Path('out/3dgs_gaussian_density')
    artifacts = Path('artifacts/3dgs_gaussian_density')
    rerun = output / 'determinism_rerun'
    scenes = ('lego', 'chair', 'drums', 'ficus')
    names = (['REPORT.md', 'density_statistics.json', 'all_scenes_density_comparison.png']
             + [f'{s}_density_atlas.png' for s in scenes]
             + [f'{s}_density_grids.npz' for s in scenes])
    baseline = {name: hashlib.sha256((output/name).read_bytes()).hexdigest() for name in names}
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
    evidence = {'tests': {}, 'determinism': {}, 'png_decode': {}, 'grid_checks': {}, 'source_hash_checks': {}}
    for label, pattern in [('targeted_new', 'test_gaussian_density.py'),
                           ('targeted_legacy', 'test_field_visualization.py'), ('full', 'test*.py')]:
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', pattern, '-v']
        print(f'Running {label} tests', flush=True)
        with (output/f'unittest_{label}.log').open('w') as log:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        log_text = (output/f'unittest_{label}.log').read_text()
        count = int(re.search(r'Ran (\d+) tests?', log_text).group(1))
        evidence['tests'][label] = {'command': command, 'count': count, 'result': 'OK'}
    command = [sys.executable, '-m', 'scripts.render_3dgs_gaussian_density',
               '--output', str(rerun), '--artifacts', str(rerun/'curated')]
    print('Regenerating all four scenes for bytewise comparison', flush=True)
    with (output/'determinism_rerun.log').open('w') as log:
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    for name in names:
        actual = hashlib.sha256((rerun/name).read_bytes()).hexdigest()
        if actual != baseline[name]:
            raise RuntimeError(f'Non-deterministic output: {name}')
    evidence['determinism'] = {'command': command, 'all_match': True, 'sha256': baseline,
                               'scope': 'same interpreter, dependencies and CPU environment; all 11 generated files'}
    # Decode every generated and curated PNG, not just its header.
    for folder in (output, artifacts, rerun, rerun/'curated'):
        for path in sorted(folder.glob('*.png')):
            with Image.open(path) as im:
                im.verify()
            with Image.open(path) as im:
                im.load()
                evidence['png_decode'][str(path)] = {'size': list(im.size), 'mode': im.mode, 'decoded': True}
    stats = json.loads((output/'density_statistics.json').read_text())
    for scene in scenes:
        s = stats['scenes'][scene]
        digest = hashlib.sha256(Path(s['source']).read_bytes()).hexdigest()
        assert digest == s['source_sha256'], f'{scene}: source modified'
        evidence['source_hash_checks'][scene] = digest
        with np.load(output/f'{scene}_density_grids.npz', allow_pickle=False) as grids:
            for field in ('occupancy', 'pdf'):
                values = grids[field]
                assert values.shape == (3, 768, 768)
                assert values.dtype == np.float64
                assert np.all(np.isfinite(values)) and np.all(values >= 0)
                for j in range(3):
                    np.testing.assert_allclose(values[j].sum(), grids[f'plane{j}_sample_sums_{field}'].sum(), rtol=1e-12)
                    assert float(values[j].max()) == s['planes'][j]['fields'][field]['max']
                    ids = grids[f'plane{j}_grid_indices']
                    assert np.all(np.diff(ids) > 0)
                    assert np.isin(ids, grids[f'plane{j}_plane_indices']).all()
            np.testing.assert_allclose(grids['basis'].T @ grids['basis'], np.eye(3), atol=1e-12)
            assert s['display']['shared'] == stats['shared_display_limits']
        evidence['grid_checks'][scene] = 'finite nonnegative float64; shape, maxima, kernel sums, sorted candidate IDs, frame, shared limits verified'
    for name in names:
        if not name.endswith('.npz'):
            assert hashlib.sha256((artifacts/name).read_bytes()).hexdigest() == baseline[name]
            assert hashlib.sha256((rerun/'curated'/name).read_bytes()).hexdigest() == baseline[name]
    evidence['curated_copies_match'] = True
    evidence['visual_review'] = 'PNG decoding is automated; human/model layout inspection is documented in the completion report.'
    (output/'verification.json').write_text(json.dumps(evidence, indent=2) + '\n')
    shutil.copyfile(output/'verification.json', artifacts/'verification.json')
    print(f'PASS: {len(names)} byte-identical outputs; {len(evidence["png_decode"])} PNGs decoded; '
          f'{evidence["tests"]["full"]["count"]} full-suite tests', flush=True)


if __name__ == '__main__':
    main()
