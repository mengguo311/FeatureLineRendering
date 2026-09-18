"""Deterministic report rendering and content inventories, outside inference."""
import hashlib
from pathlib import Path


def sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def file_inventory(root,exclude=()):
    root=Path(root);exclude=set(exclude);rows=[]
    for path in sorted(root.rglob('*')):
        name=str(path.relative_to(root))
        if not path.is_file() or name in exclude:continue
        rows.append(dict(path=name,bytes=path.stat().st_size,sha256=sha256(path)))
    return rows


def check_inventory(root,rows):
    for row in rows:
        path=Path(root)/row['path']
        if not path.is_file() or path.stat().st_size!=row['bytes'] or sha256(path)!=row['sha256']:
            raise ValueError('inventory mismatch: '+str(path))
    return True


def render_results(result):
    lines=['# Corrected multiscene foundation results','',
        f"Core synthetic scope: **{result['scope']['core']['verdict']}**. Lego and Chair are evaluated separately; no averaging rescues either.",
        f"Expanded cross-scene scope: **{result['scope']['expanded']['verdict']}**.",'',
        'This is a known post-hoc sampling correction, not a blind experiment. The previous run remains permanently UNDETERMINED. No posterior was retrained.',
        f"Preregistration commit: `{result['protocol']['prereg_commit']}`. Frozen configuration SHA256: `{result['protocol']['config_sha256']}`.",'',
        '## Per-scene outcomes','',
        '| Scene | Eligible | Route A | Route B | Qualified doses | Invariance scope | Machine verdict | Queries | Modes | Accepted |',
        '|---|---|---|---|---:|---|---|---:|---:|---:|']
    for s in result['scenes']:
        lines.append('| '+' | '.join(str(s.get(k,'—')) for k in ['scene','eligible','route_a','route_b','qualified_doses','invariance_scope','verdict','query_count','mode_count','accepted_count'])+' |')
    lines+=['','## Machine gates','',
        '| Scene | G0 | G1 | G2 machine | G3 | G4 machine | G2/G4 benefit/G5 manual |',
        '|---|---|---|---|---|---|---|']
    for s in result['scenes']:
        values=[('PASS' if s['machine'][k] else 'FAIL') if 'machine' in s else 'NOT_ELIGIBLE' for k in ['G0','G1','G2_machine','G3','G4_machine']]
        lines.append('| '+' | '.join([s['scene'],*values,s.get('manual','NOT_REACHED')])+' |')
    lines+=['','G1 requires at least 64 spatially separated accepted positions. Empty outputs cannot pass repeatability or non-null controls through a 0/0 statistic. Manual gates are pending independent review; this does not defer a valid necessary machine-gate failure. No independent reviewer is claimed.','',
        '## Exact totals','', '| Quantity | Count |','|---|---:|']
    lines += [f'| {key} | {value} |' for key,value in result['totals'].items()]
    lines += ['', '## Scope and limitations','']+[f'- {v}' for v in result['limitations']]
    lines += ['', '## Artifacts and verification','',
        'The full per-view quality, dose, calibration and eligibility records are in `quality/`, `controlled/`, and `scenes/`. Every completed local arm retains queries, all depth profiles and modes, accepted records, rejection reasons and coverage denominators under `local/`. Large arrays are server-side and inventoried in MANIFEST.json.',
        'Per-scene `evaluation/SCENE/visual/` contains actual glyph contact sheets, fixed views, rejection/profile diagnostics and the blinded review package. The identity key is outside each package. Video status records whether the frozen per-scene G1/G2 trigger was reached. Empty output is displayed as empty output.',
        f"Native-open access audit: passed={result['access_audit']['passed']}; forbidden successful opens={result['access_audit']['forbidden_successes']}. See ACCESS_AUDIT.json, VERIFICATION.json, TDD_LEDGER.md and REPRODUCE.md. All hash and media checks are machine-generated.",
        'No UDF training, curve extraction, connection/smoothing, Bezier fitting, final strokes, mesh input or old-selector modification was performed.','']
    return '\n'.join(lines)


def check_markdown(result,text):
    if render_results(result)!=text:raise ValueError('JSON/Markdown scene, gate, or total mismatch')
    return True
