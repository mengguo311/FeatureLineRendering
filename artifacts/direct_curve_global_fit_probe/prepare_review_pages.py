"""Decode each complete primary video once into uniformly sampled review pages."""
import json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'out/direct_curve_global_fit_probe'
SESSION = OUT / 'scheduler' / sys.argv[1]
pending = {(scene, arc) for scene in ['lego', 'chair', 'drums', 'ficus'] for arc in range(2)}
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
while pending:
    for scene, arc in sorted(pending):
        result = OUT / 'review' / scene / f'arc{arc}' / 'DECODE.json'
        if result.exists():
            pending.remove((scene, arc))
            continue
        marker = OUT / 'run' / scene / 'evaluate' / 'figures' / f'arc{arc}_allframes_5.png'
        if not marker.exists():
            continue
        command = [sys.executable, 'artifacts/direct_curve_global_fit_probe/decode_review_media.py', '--scene', scene, '--arc', str(arc)]
        subprocess.run(command, cwd=ROOT, env=env, check=True)
        pending.remove((scene, arc))
    if pending and (SESSION / 'run/COMPLETE.json').exists():
        raise RuntimeError('Missing complete primary videos: ' + repr(sorted(pending)))
    if pending:
        time.sleep(30)
with (SESSION / 'REVIEW_PAGES_COMPLETE.json').open('x') as f:
    json.dump(dict(arcs=8, frames=264, scope='Decode only; actual visual review remains required'), f)
