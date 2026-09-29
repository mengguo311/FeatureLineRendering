"""Publish every C panel, both fixed quartiles and both complete videos per scene."""
import argparse, html, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.schedule_direct_curve_probe import atomic_json, sha

ART = Path(__file__).resolve().parent
OUT = ROOT / 'out/direct_curve_global_fit_probe'
cfg = json.loads((ART / 'INPUTS.json').read_text())
review = json.loads((ART / 'VISUAL_REVIEW.json').read_text())
assert set(review['scenes']) == {'lego', 'chair', 'drums', 'ficus'}
parser = argparse.ArgumentParser()
parser.add_argument('--proof', required=True)
args = parser.parse_args()
proof = Path(args.proof)
assert json.loads((proof / 'VERIFICATION.json').read_text())['passed']
target = ART / 'media'
target.mkdir(exist_ok=False)
manifest = {}
keys = {}
proof_target = ART / 'proof'
proof_target.mkdir(exist_ok=False)
for source in sorted(proof.glob('*.json')):
    dest = proof_target / source.name
    with source.open('rb') as incoming, dest.open('xb') as outgoing:
        shutil.copyfileobj(incoming, outgoing)
    assert sha(source) == sha(dest)
    manifest[str(dest.relative_to(ART))] = dict(source=str(source), sha256=sha(source), bytes=dest.stat().st_size)
page = ['<!doctype html><html lang="en"><meta charset="utf-8"><title>Direct curve probe evidence</title>',
        '<style>body{font:16px system-ui;max-width:1500px;margin:30px auto;padding:0 20px}img,video{max-width:100%;height:auto}figure{margin:20px 0}summary{cursor:pointer}a{color:#154f92}</style>',
        '<h1>Complete four-scene evidence</h1><p>All eight C views and both complete 33-frame arcs per scene are included. C uses original TRAIN photographs held out from curve fitting. Arcs use frozen-GS RGB. Figures retain randomized labels; internal observations were recorded before opening their keys. This is not independent human validation.</p>',
        '<p><a href="REPORT.md">Report</a> · <a href="GATES.json">Preregistered gates</a> · <a href="VISUAL_REVIEW.json">Internal review</a> · <a href="proof/VERIFICATION.json">Verification</a></p>']
for scene in ['lego', 'chair', 'drums', 'ficus']:
    base = OUT / 'run' / scene / 'evaluate'
    keys[scene] = json.loads((base / 'REVIEW_KEY.json').read_text())
    mapping = ', '.join(f"{chr(65+i)} = {name}" for i, name in enumerate(keys[scene]['order']))
    page += [f'<h2>{scene}</h2><p>{html.escape(mapping)}</p>']
    names = [f'figures/C_{i}.png' for i in cfg['C']]
    names += [f'figures/arc{arc}_quartiles.png' for arc in range(2)]
    names += [f'videos/arc{arc}_complete.mp4' for arc in range(2)]
    for name in names:
        source = base / name
        dest = target / scene / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with source.open('rb') as incoming, dest.open('xb') as outgoing:
            shutil.copyfileobj(incoming, outgoing)
        digest = sha(source)
        assert sha(dest) == digest
        relative = str(dest.relative_to(ART))
        manifest[relative] = dict(source=str(source), sha256=digest, bytes=dest.stat().st_size)
        caption = html.escape(f'{scene}: {Path(name).stem}')
        element = f'<video controls preload="metadata" src="{relative}"></video>' if dest.suffix == '.mp4' else f'<a href="{relative}"><img loading="lazy" src="{relative}" alt="{caption}"></a>'
        page += [f'<figure><figcaption>{caption}</figcaption>{element}</figure>']
    page += ['<details><summary>Complete source and decoded frame contacts (server paths)</summary>']
    for arc in range(2):
        for source in sorted((base / 'figures').glob(f'arc{arc}_allframes_*.png')):
            relative = '../../' + str(source.relative_to(ROOT))
            page += [f'<p><a href="{relative}">{source.name}</a></p>']
        decoded = OUT / 'review' / scene / f'arc{arc}' / 'DECODE.json'
        page += [f'<p><a href="../../{decoded.relative_to(ROOT)}">Arc {arc} full decode provenance</a></p>']
    page += ['</details>']
page += ['</html>']
atomic_json(ART / 'CURATED_MEDIA_RESUME.json', manifest)
atomic_json(ART / 'REVIEW_KEYS.json', keys)
with (ART / 'index.html').open('x') as f:
    f.write('\n'.join(page) + '\n')
print(json.dumps(dict(files=len(manifest), bytes=sum(v['bytes'] for v in manifest.values()), index=str(ART/'index.html'))))
