"""Exposed-fixture repair verification; immutable round013 evaluator reused."""
import round014_common as c
import argparse
import importlib.metadata
import importlib.util
import json
import subprocess
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import planar_fragments_exact as candidate
import run_round013 as old

P = json.loads((c.D / 'PROTOCOL.json').read_text())
S = c.W / 'experiments/partwise_sketch_hatching'
NEW = ['round014_common.py', 'round014_receipt.py', 'planar_fragments_exact.py',
       'test_exact_triangle_set.py', 'run_round014.py', 'seal_round014.py']
TESTS = ['INHERITED_ATTACHMENT', 'INHERITED_PATCH', 'INHERITED_CANDIDATE',
         'INHERITED_ORACLE', 'INHERITED_TEMPORAL', 'INHERITED_STAGE',
         'INHERITED_CENTERED', 'INHERITED_AREA', 'INHERITED_REFERENCE',
         'INHERITED_FRAGMENTS', 'CANDIDATE_FRAGMENTS', 'GREEN_EXACT_SET']
# Independent module namespace: no rebinding of the original evaluator or its
# historical dependencies. Reuse unchanged numerical/reference gate functions.
spec = importlib.util.spec_from_file_location('_round014_repair_checks', S / 'run_round013.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
checks.c, checks.P, checks.candidate = c, P, candidate

def prepare():
    assert not (c.D / 'ASSET_LOCK.json').exists()
    previous = json.loads((c.W / 'docs/partwise_sketch_hatching/round_013/ASSET_LOCK.json').read_text())
    for name, digest in previous['sources'].items():
        assert c.sha(c.W / name) == digest, name
    assert c.sha(S / 'planar_fragments.py') == P['repair']['source_sha256']
    paths = {c.W / p for p in previous['sources']} | {S / n for n in NEW}
    paths |= {p for p in c.D.iterdir() if p.is_file()}
    paths |= {p for p in (c.W / 'docs/partwise_sketch_hatching/round_013').iterdir() if p.is_file()}
    inputs = [p for p in c.P.rglob('*') if p.is_file() and 'runtime' not in p.relative_to(c.P).parts]
    c.write(c.D / 'ASSET_LOCK.json', {
        'protocol_commit': 'aed26a66',
        'implementation_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=c.W, text=True).strip(),
        'sources': {str(p.relative_to(c.W)): c.sha(p) for p in sorted(paths)},
        'inputs': {str(p): c.sha(p) for p in sorted(inputs)},
        'prior_seal': c.verify_prior(), 'resources': c.resources(),
        'dependencies': {n: importlib.metadata.version(n) for n in ['numpy', 'scipy', 'Pillow']}})
    c.status('sources_locked_awaiting_evaluation')
    print(json.dumps({'cases': len(P['cases']), 'prior': c.verify_prior()}))

def evaluate_case(case):
    metrics, arrays = checks.evaluate_case(case)
    with np.load(c.P / 'raw' / (case['id'] + '.npz')) as saved:
        base = {k: bool(np.array_equal(arrays[k], saved[k]))
                for k in saved.files if k.startswith('candidate_')}
        # Every unchanged ordering variant is also exact against prior outputs.
        unchanged = {k: bool(np.array_equal(arrays[k], saved[k])) for k in saved.files
                     if k.startswith('variant_') and not k.startswith('variant_duplicate_occluders_')}
    exact_raw = {k: bool(np.array_equal(arrays['candidate_raw_' + k],
                arrays['variant_duplicate_occluders_raw_' + k])) for k in checks.NAMES
                if 'variant_duplicate_occluders_raw_' + k in arrays}
    metrics['repair_gates'] = {'base_all_arrays_exact': bool(base) and all(base.values()),
                               'unchanged_variants_exact': all(unchanged.values()),
                               'duplicate_raw_exact': all(exact_raw.values())}
    metrics['base_array_equalities'] = base
    metrics['unchanged_variant_equalities'] = unchanged
    metrics['duplicate_raw_equalities'] = exact_raw
    metrics['original_candidate_go'] = metrics['candidate_go']
    metrics['candidate_go'] = metrics['candidate_go'] and all(metrics['repair_gates'].values())
    metrics['study_type'] = 'exposed engineering repair'
    return metrics, arrays

def historical_replay():
    # Run the actual old renderer, retaining its nine strict failures exactly.
    assert old.candidate.__name__ == 'planar_fragments'
    count = 0
    records = []
    for case in old.P['cases']:
        m, a = old.evaluate_case(case)
        assert m == json.loads((c.P / 'raw' / (case['id'] + '.json')).read_text())
        with np.load(c.P / 'raw' / (case['id'] + '.npz')) as saved:
            assert set(a) == set(saved.files)
            for key in a:
                np.testing.assert_array_equal(a[key], saved[key], err_msg=case['id'] + '/' + key)
                count += 1
        records.append({'case_id': case['id'], 'arrays_exact': len(a),
                        'original_candidate_go': m['candidate_go']})
    older = old.historical_replay()
    return {'round013_cases': records, 'round013_arrays_exact': count,
            'round013_NO_GO_retained': sum(not r['original_candidate_go'] for r in records) == 3,
            'older': older, 'all_exact': count == 1045 and older['all_exact']}

def repair_sites(arrays_by_id):
    prior = json.loads((c.P / 'FAILURE_LOCALIZATION.json').read_text())
    cells = []
    for failed in prior['failures']:
        a = arrays_by_id[failed['case_id']]
        for cell in failed['cells']:
            x, y = cell['x'], cell['y']
            base = float(a['candidate_occluded'][y, x])
            duplicate = float(a['variant_duplicate_occluders_occluded'][y, x])
            cells.append({'case_id': failed['case_id'], 'x': x, 'y': y,
                          'old_base': cell['base'], 'old_duplicate': cell['variant'],
                          'new_base': base, 'new_duplicate': duplicate,
                          'base_preserved_exactly': base == cell['base'],
                          'duplicate_fixed_exactly': base == duplicate})
    return {'source_sha256': c.sha(c.P / 'FAILURE_LOCALIZATION.json'),
            'prior_failure_count': len(cells), 'cells': cells,
            'all_fixed_base_preserved': len(cells) == 9 and all(
                r['base_preserved_exactly'] and r['duplicate_fixed_exactly'] for r in cells)}

def contact(records, arrays):
    font = lambda n: ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', n)
    sheet = Image.new('RGB', (1160, 85 + len(records) * 290), 'white')
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 8), 'Exact triangle-set repair | All exposed full views | Analytic GT', font=font(22), fill='black')
    draw.text((12, 40), '64x64 output, 2x area grid. Duplicate difference: black means any exact mismatch.', font=font(16), fill='black')
    for i, (m, a) in enumerate(zip(records, arrays)):
        top = 80 + i * 290
        draw.text((12, top), f"{m['case_id']} | repair GO {m['candidate_go']}", font=font(15), fill='black')
        with np.load(c.P / 'raw' / (m['case_id'] + '.npz')) as saved:
            old_image = saved['candidate_final_uint8'].copy()
        duplicate = a.get('variant_duplicate_occluders_occluded', a['candidate_occluded'])
        mismatch = np.uint8(duplicate != a['candidate_occluded']) * 255
        panels = [old_image, a['candidate_final_uint8'], a['reference_final_uint8'], mismatch]
        titles = ['Preserved round013 base', 'Exact-set candidate', 'Independent reference', 'Duplicate occluded difference']
        for j, (pixels, title) in enumerate(zip(panels, titles)):
            x = 12 + j * 290
            draw.text((x, top + 22), title, font=font(14), fill='black')
            image = Image.fromarray(255 - pixels).resize((240, 240), Image.Resampling.NEAREST)
            sheet.paste(image.convert('RGB'), (x, top + 44))
    sheet.save(c.R / 'figures/full_view_contact_sheet.png')

def summary(records, regression, reject, sensitivity, sites):
    red = json.loads((c.R / 'RED_EXACT_SET.json').read_text())
    gates = {'ten_original_cases': len(records) == 10,
             'reference_controls': all(r['measurement_valid'] for r in records),
             'historical_exact': regression['all_exact'],
             'original_round013_failure_retained': regression['round013_NO_GO_retained'],
             'rejections_unchanged': reject == json.loads((c.P / 'REJECTIONS.json').read_text()),
             'rejections_passed': reject['all_rejected'],
             'sensitivity_unchanged': sensitivity == json.loads((c.P / 'SENSITIVITY.json').read_text()),
             'sensitivity_passed': sensitivity['all_detected'],
             'actual_old_RED': red['returncode'] == 1}
    for name in TESTS:
        gates[name.lower()] = json.loads((c.R / (name + '.json')).read_text())['returncode'] == 0
    valid = all(gates.values())
    go = valid and all(r['candidate_go'] for r in records) and sites['all_fixed_base_preserved']
    return {'complete': True, 'measurement_valid': valid, 'candidate_go': go,
            'verdict': 'REPAIR_QUALIFIED_FINITE_PLANAR_P0_GO' if go else (
                'MEASUREMENT_VALID_REPAIR_NO_GO' if valid else 'ENGINEERING_INVALID'),
            'study_type': P['study_type'], 'gates': gates, 'cases': records,
            'regression': regression, 'rejections': reject, 'sensitivity': sensitivity,
            'repair_sites': sites, 'limits': P['limits']}

def evaluate():
    c.verify_lock(); c.verify_prior(); c.resources()
    assert not (c.R / 'metrics.json').exists()
    for name in ['raw', 'figures']:
        (c.R / name).mkdir(exist_ok=True)
    c.status('evaluating_frozen_exact_set_repair')
    start = time.monotonic()
    records, arrays = [], []
    for case in P['cases']:
        c.resources()
        m, a = evaluate_case(case)
        records.append(m); arrays.append(a)
        c.write(c.R / 'raw' / (case['id'] + '.json'), m)
        np.savez_compressed(c.R / 'raw' / (case['id'] + '.npz'), **a)
        c.write(c.R / 'PARTIAL_METRICS.json', {'completed_cases': len(records), 'cases': records})
        print(json.dumps({'case': case['id'], 'valid': m['measurement_valid'],
                          'go': m['candidate_go'], 'repair': m['repair_gates']}), flush=True)
    reject = checks.rejections(); sensitivity = checks.sensitivity(arrays[0])
    regression = historical_replay()
    sites = repair_sites({m['case_id']: a for m, a in zip(records, arrays)})
    for name, obj in [('REJECTIONS', reject), ('SENSITIVITY', sensitivity),
                      ('REGRESSION', regression), ('REPAIR_SITES', sites)]:
        c.write(c.R / (name + '.json'), obj)
    contact(records, arrays)
    out = summary(records, regression, reject, sensitivity, sites)
    out['wall_seconds'] = time.monotonic() - start
    out['resources'] = c.resources()
    c.write(c.R / 'metrics.json', out)
    c.status('evaluated_awaiting_replay', scientific_verdict=out['verdict'])
    print(json.dumps({'verdict': out['verdict'], 'gates': out['gates']}))

def validate():
    c.verify_lock(); c.verify_prior(); c.resources()
    saved = json.loads((c.R / 'metrics.json').read_text())
    records, arrays, count = [], [], 0
    for case in P['cases']:
        m, a = evaluate_case(case)
        assert m == json.loads((c.R / 'raw' / (case['id'] + '.json')).read_text())
        with np.load(c.R / 'raw' / (case['id'] + '.npz')) as previous:
            assert set(a) == set(previous.files)
            for key in a:
                np.testing.assert_array_equal(a[key], previous[key])
                count += 1
        records.append(m); arrays.append(a)
    regression = historical_replay()
    sites = repair_sites({m['case_id']: a for m, a in zip(records, arrays)})
    out = summary(records, regression, checks.rejections(), checks.sensitivity(arrays[0]), sites)
    for key in out:
        assert out[key] == saved[key], key
    result = {'complete': True, 'cases_exact': len(records), 'arrays_exact': count,
              'all_metrics_exact': True, 'regression': regression,
              'measurement_valid': out['measurement_valid'], 'candidate_go': out['candidate_go'],
              'prior_seal': c.verify_prior(), 'resources': c.resources()}
    c.write(c.R / 'VALIDATION.json', result)
    c.status('validated_awaiting_report')
    print(json.dumps({'cases_exact': len(records), 'arrays_exact': count, 'verdict': out['verdict']}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['prepare', 'evaluate', 'validate'])
    args = parser.parse_args()
    try:
        globals()[args.command]()
    except Exception as exc:
        c.status('interrupted_or_engineering_failure', execution_state='incomplete',
                 scientific_verdict='ENGINEERING_INVALID', blockers=[type(exc).__name__ + ': ' + str(exc)])
        raise
