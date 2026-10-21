"""Independent saved-output audit and actual raster fault controls for unit007.

No producer/renderer imports. Anchor positions are reconstructed from serialized
triangles and barycentric weights. This validator independently sums coverage and
temporal presence; centroid extraction deliberately exercises the frozen metric
implementation. Software validity and observed temporal quality stay separate.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.sched_setaffinity(0, [0, 1])

import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np
from PIL import Image, ImageDraw
from temporal_audit_unit007 import evaluate_frame, reference_maps, summarize

WORK = Path(__file__).resolve().parents[2]
U = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_007')
FFMPEG = '/home/u00134/3dgs_line/partwise_sketch_hatching_p0p1_v01/.runtime_p0/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
CLASSES = ('visible', 'hidden', 'ambiguous', 'boundary', 'outside', 'unmeasured')


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def save(path, value):
    path = Path(path)
    require(not path.exists(), f'preserve existing output: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def close(a, b, name):
    require((a is None and b is None) or
            (a is not None and b is not None and abs(a - b) <= 1e-9),
            f'{name}: independent={a}, producer={b}')


def key(row):
    return row['sequence'], row['stroke_id'], row['frame']


def order(row):
    return ('orbit', 'zoom').index(row['sequence']), row['frame'], row['stroke_id']


def frozen_hashes():
    protocol = read(U / 'PROTOCOL.json')
    entries = dict(read(U / 'SOURCE_LOCK.json')['files'])
    entries.update(protocol['inputs'])
    for path, expected in entries.items():
        require(sha(path) == expected, f'changed frozen source/input: {path}')
    require(sha(U / 'inputs/selected.npz') == protocol['asset']['sha256'], 'wrong selected asset')
    return dict(checked_files=len(entries), protocol_sha256=sha(U / 'PROTOCOL.json'),
                selected_asset_sha256=sha(U / 'inputs/selected.npz'))


def historical_manifest(unit_name):
    """Validate immutable unit files and source bytes at each historical commit."""
    unit = U.parent / unit_name
    seal = read(unit / 'SEAL.json')
    manifest_path = Path(seal['manifest_path'])
    require(manifest_path.resolve() == (unit / 'SHA256_MANIFEST.json').resolve(), 'historical manifest escapes unit')
    require(sha(manifest_path) == seal['manifest_sha256'], 'historical seal hash mismatch')
    manifest = read(manifest_path)
    counts = {'unit': 0, 'worktree': 0}
    for entry in manifest['files']:
        root, relative = entry['root'], entry['path']
        require(root in counts and not Path(relative).is_absolute() and '..' not in Path(relative).parts,
                'historical manifest entry is invalid')
        if root == 'unit':
            path = unit / relative
            actual, length = sha(path), path.stat().st_size
        else:
            result = subprocess.run(['git', 'show', f"{manifest['source_commit']}:{relative}"],
                                    cwd=WORK, capture_output=True, timeout=30)
            require(result.returncode == 0, f'historical committed source missing: {relative}')
            actual, length = hashlib.sha256(result.stdout).hexdigest(), len(result.stdout)
        require(actual == entry['sha256'] and length == entry['bytes'], f'historical bytes changed: {root}/{relative}')
        counts[root] += 1
    return dict(unit=unit_name, manifest_sha256=seal['manifest_sha256'], files=counts,
                source_commit=manifest['source_commit'],
                source_method='git show at manifest source_commit; current source is separately locked')


def coverage(rows):
    """Independent sums, including all excluded observations and missing ink."""
    counts = dict.fromkeys(CLASSES, 0)
    lengths = dict.fromkeys(CLASSES, 0.)
    projected = dict.fromkeys(CLASSES, 0.)
    raw_visible = missing = 0.
    missing_count = 0
    identities = set()
    for row in rows:
        sample = row['samples']
        n = row['sample_count']
        require(all(len(sample[field]) == n for field in
                    ('class', 'world_weight', 'projected_length_weight', 'raw_visible', 'profile_present', 'normal_centroid_px')),
                f'sample lengths differ: {key(row)}')
        require(sum(sample['world_weight']) > 0, 'nonpositive path weight')
        close(sum(sample['world_weight']), row['path_length_world'], 'world quadrature conserves path length')
        for i, label in enumerate(sample['class']):
            require(label in CLASSES, 'unknown observation class')
            ww, sw = sample['world_weight'][i], sample['projected_length_weight'][i]
            require(np.isfinite(ww) and np.isfinite(sw) and ww > 0 and sw >= 0, 'invalid sample weight')
            counts[label] += 1
            lengths[label] += ww
            projected[label] += sw
            raw_visible += ww if sample['raw_visible'][i] else 0.
            if label == 'visible':
                identities.add((row['stroke_id'], i))
                require(sample['raw_visible'][i], 'eligible observation not independently raw-visible')
                if not sample['profile_present'][i]:
                    missing += ww
                    missing_count += 1
                else:
                    require(sample['normal_centroid_px'][i] is not None, 'present eligible ink lacks centroid')
    return dict(records=len(rows), class_counts=counts, class_world_length=lengths,
                class_projected_length=projected, raw_visible_world_length=raw_visible,
                missing_world_length=missing, missing_visible_samples=missing_count,
                missing_world_fraction=missing / lengths['visible'] if lengths['visible'] else None,
                eligible_over_raw_visible_world=lengths['visible'] / raw_visible if raw_visible else None,
                unique_visible_material_samples=len(identities))


def temporal_presence(rows):
    by_key = {key(row): row for row in rows}
    common = dropout = appear = missing = 0.
    pairs = 0
    for row in rows:
        after = by_key.get((row['sequence'], row['stroke_id'], row['frame'] + 1))
        if after is None:
            continue
        pairs += 1
        a, b = row['samples'], after['samples']
        require(len(a['class']) == len(b['class']), 'material sample count changes over time')
        require(a['world'] == b['world'] and a['world_weight'] == b['world_weight'],
                'fixed material sample correspondence changes')
        for i, (left, right) in enumerate(zip(a['class'], b['class'])):
            if left != 'visible' or right != 'visible':
                continue
            weight = a['world_weight'][i]
            x, y = a['profile_present'][i], b['profile_present'][i]
            common += weight
            dropout += weight if x and not y else 0.
            appear += weight if not x and y else 0.
            missing += weight if not (x and y) else 0.
    return dict(adjacent_pairs=pairs, common_visible_world_length=common,
                missing_either_world_fraction=missing / common if common else None,
                dropout_world_fraction=dropout / common if common else None,
                reappearance_world_fraction=appear / common if common else None)


def aggregate_checks(rows, summary):
    trajectories = read(U / 'TRAJECTORIES.json')
    selection = read(U / 'SAMPLE_SELECTION.json')['selected']
    expected = {(seq, item['id'], cam['frame']) for seq, cameras in trajectories.items()
                for cam in cameras for item in selection}
    require(len(rows) == len(expected) and {key(row) for row in rows} == expected,
            'missing, duplicate or extra metric observations')
    for seq, cameras in trajectories.items():
        for camera in cameras:
            raw = read(U / 'raw' / f'{seq}_{camera["frame"]:04}.json')
            require(raw == [r for r in rows if r['sequence'] == seq and r['frame'] == camera['frame']],
                    'per-frame raw metrics disagree with collected rows')
    output = {}
    for seq in ('orbit', 'zoom'):
        for part in (1, 2, 3):
            selected = [r for r in rows if r['sequence'] == seq and r['part'] == part]
            independent = coverage(selected)
            producer = summary['per_sequence'][seq]['per_part'][str(part)]
            for name, value in independent.items():
                if isinstance(value, dict):
                    for label, number in value.items():
                        close(number, producer[name][label], f'{seq}/{part}/{name}/{label}')
                else:
                    close(value, producer[name], f'{seq}/{part}/{name}')
            temporal = temporal_presence(selected)
            for name, value in temporal.items():
                close(value, producer['temporal'][name], f'{seq}/{part}/temporal/{name}')
            independent['temporal'] = temporal
            output[f'{seq}/part{part}'] = independent
    return dict(expected_rows=len(expected), checked_rows=len(rows), groups=output)


def video_checks():
    trajectories, producer = read(U / 'TRAJECTORIES.json'), read(U / 'VIDEO_VALIDATION.json')
    result = {}
    for seq in ('orbit', 'zoom'):
        n = len(trajectories[seq])
        command = [FFMPEG, '-v', 'error', '-threads', '1', '-i', str(U / 'videos' / f'{seq}.mkv'),
                   '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-threads', '1', '-']
        decode = subprocess.run(command, capture_output=True, timeout=90)
        require(decode.returncode == 0, f'{seq}: independent decode failed')
        require(len(decode.stdout) == n * 512 * 512 * 3, f'{seq}: incomplete or excess decoded frames')
        frames = np.frombuffer(decode.stdout, np.uint8).reshape(n, 512, 512, 3)
        comparisons = []
        for i, frame in enumerate(frames):
            path = U / 'frames' / seq / f'{i:04}.png'
            with Image.open(path) as original:
                original.load()
                require(original.size == (512, 512) and original.mode in ('L', 'RGB'), 'full frame shape/encoding differs')
                equal = bool(np.array_equal(frame, np.asarray(original.convert('RGB'))))
            comparisons.append(dict(frame=i, exact=equal, png_sha256=sha(path)))
        require(all(row['exact'] for row in comparisons), f'{seq}: FFV1 pixels differ')
        require(producer[seq]['frames'] == n and producer[seq]['all_frames_exact'], 'producer video receipt disagrees')
        require(len({frame.tobytes() for frame in frames}) >= 2, f'{seq}: static video')
        result[seq] = dict(command=command, returncode=decode.returncode, decoded_frames=n,
                           all_frames_exact=True, frames=comparisons, video_sha256=sha(U / 'videos' / f'{seq}.mkv'))
    require(sum(r['decoded_frames'] for r in result.values()) == 36, 'not all 36 frames decoded')
    return result


def anchor_paths():
    with np.load(U / 'inputs/lamp_mesh.npz', allow_pickle=False) as mesh:
        triangles = mesh['vertices'][mesh['faces']]
    output = {}
    with np.load(U / 'inputs/selected.npz', allow_pickle=False) as strokes:
        for i, name in enumerate(strokes['ids']):
            lo, hi = strokes['offsets'][i:i + 2]
            output[str(name)] = np.einsum('ni,nij->nj', strokes['bary'][lo:hi], triangles[strokes['faces'][lo:hi]])
    return output


def shifted(ink, dx=0, dy=0):
    out = np.zeros_like(ink)
    out[dy:, dx:] = ink[:ink.shape[0] - dy or None, :ink.shape[1] - dx or None]
    return out


def comparison_figure(part, variants, records, destination):
    uv = np.asarray(records['before']['samples']['uv'])
    finite = uv[np.isfinite(uv).all(axis=1)]
    low = np.maximum(np.floor(finite.min(axis=0) - 12).astype(int), 0)
    high = np.minimum(np.ceil(finite.max(axis=0) + 12).astype(int), 512)
    bounds = tuple(int(v) for v in (low[0], low[1], high[0], high[1]))
    width, height = 330, 400
    canvas = Image.new('RGB', (4 * width, height), 'white')
    draw = ImageDraw.Draw(canvas)
    for col, name in enumerate(('before', 'shift_x3', 'shift_y3', 'drop')):
        rgb = Image.fromarray(255 - variants[name]).convert('RGB')
        crop = rgb.crop(bounds)
        crop.thumbnail((width - 20, 290), Image.Resampling.NEAREST)
        canvas.paste(crop, (col * width + 10, 70))
        metric = records[name]['summary']
        missing = metric['missing_world_fraction']
        centroid = metric['centroid_abs_px']['p95']
        draw.text((col * width + 10, 10), f'Part {part}: {name}', fill='black')
        draw.text((col * width + 10, 28), f'Missing fraction: {missing:.4f}', fill='black')
        draw.text((col * width + 10, 46), f'Normal centroid P95: {centroid if centroid is not None else "absent"}', fill='black')
    draw.text((10, 374), 'Actual saved isolated hatch pixels; same crop and scale. White means no ink.', fill='black')
    require(not destination.exists(), 'comparison figure exists')
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination)
    return dict(path=str(destination), crop_xyxy=bounds)


def directional_dropout(part, candidates, paths, asset, destination):
    """First adjacent pair with common-visible ink; suppress its later raster."""
    index = {key(row): row for row in candidates}
    selected = None
    for after in sorted(candidates, key=order):
        before = index.get((after['sequence'], after['stroke_id'], after['frame'] - 1))
        if before is None:
            continue
        a, b = before['samples'], after['samples']
        both = [i for i, (x, y) in enumerate(zip(a['class'], b['class']))
                if x == y == 'visible' and a['profile_present'][i] and b['profile_present'][i]]
        if both:
            selected = before, after, both
            break
    require(selected is not None, f'part {part}: no common-visible present adjacent pair for dropout control')
    before, after, both = selected
    seq, sid, frame = key(after)
    camera = read(U / 'frames' / seq / f'{frame:04}.json')['camera']
    original = U / 'isolated' / seq / sid / f'{frame:04}.png'
    with Image.open(original) as image:
        ink = np.array(image)
    for name, array in (('temporal_before', ink), ('temporal_drop', np.zeros_like(ink))):
        path = destination / f'{name}.png'
        require(not path.exists(), f'existing temporal control: {path}')
        Image.fromarray(array).save(path)
    with Image.open(destination / 'temporal_drop.png') as image:
        dropped = evaluate_frame(np.array(image), paths[sid], part, camera, asset, sid, seq, frame)
    baseline = [r for r in candidates if r['sequence'] == seq]
    replacement = [dropped if key(r) == key(after) else r for r in baseline]
    a, b = temporal_presence(baseline), temporal_presence(replacement)
    reported = summarize(replacement)['per_part'][str(part)]['temporal']
    for name, value in b.items():
        close(value, reported[name], 'directional dropout ' + name)
    pair_baseline = temporal_presence([before, after])
    pair_fault = temporal_presence([before, dropped])
    reported_pair = summarize([before, dropped])['per_part'][str(part)]['temporal']
    for name, value in pair_fault.items():
        close(value, reported_pair[name], 'directional selected pair ' + name)
    # An existing dropout in the following pair can move one transition earlier
    # without increasing the sequence aggregate. Assert the injected pair itself.
    responsive = pair_fault['dropout_world_fraction'] > pair_baseline['dropout_world_fraction'] + 1e-12
    result = dict(rule='First orbit then zoom, later frame ascending, stroke lexical adjacent pair with >=1 common-visible sample present in both; zero later actual raster',
                  sequence=seq, stroke_id=sid, frames=[before['frame'], frame],
                  both_present_sample_indices=both, baseline=a, fault=b,
                  selected_pair_baseline=pair_baseline, selected_pair_fault=pair_fault,
                  directional_dropout_response=responsive,
                  source_png=str(original), source_sha256=sha(original),
                  temporal_before_png_sha256=sha(destination / 'temporal_before.png'),
                  temporal_drop_png_sha256=sha(destination / 'temporal_drop.png'), dropped_row=dropped)
    save(destination / 'TEMPORAL_DROPOUT.json', result)
    require(dropped['summary']['missing_world_fraction'] == 1., 'temporal dropped row not fully missing')
    require(responsive, f'part {part}: directional dropout control unresponsive')
    return result


def control_part(part, rows, paths, asset):
    candidates = sorted((r for r in rows if r['part'] == part), key=order)
    chosen = next((r for r in candidates if sum(c == 'visible' for c in r['samples']['class']) >= 10
                   and any(c == 'visible' and p for c, p in zip(r['samples']['class'], r['samples']['profile_present']))), None)
    require(chosen is not None, f'part {part}: no eligible control row')
    sequence, sid, frame = key(chosen)
    camera = read(U / 'frames' / sequence / f'{frame:04}.json')['camera']
    reference = reference_maps(asset, camera)
    original = U / 'isolated' / sequence / sid / f'{frame:04}.png'
    with Image.open(original) as image:
        ink = np.array(image)
    destination = U / 'controls' / 'independent' / f'part{part}'
    destination.mkdir(parents=True, exist_ok=True)
    variants = dict(before=ink, repeat=ink.copy(), shift_x3=shifted(ink, dx=3),
                    shift_y3=shifted(ink, dy=3), drop=np.zeros_like(ink))
    metrics, hashes = {}, {}
    for name, array in variants.items():
        path = destination / f'{name}.png'
        require(not path.exists(), f'control output already exists: {path}')
        Image.fromarray(array).save(path)
        with Image.open(path) as actual:
            saved = np.array(actual)
        metrics[name] = evaluate_frame(saved, paths[sid], part, camera, asset, sid, sequence, frame, reference)
        hashes[name] = sha(path)
    require(metrics['before'] == metrics['repeat'], 'no-edit metric repeat differs')
    require(metrics['before'] == chosen, 'independent actual PNG replay differs from stored row')
    base = metrics['before']['summary']
    responses = {}
    for name in ('shift_x3', 'shift_y3'):
        changed = metrics[name]['summary']
        responses[name] = bool(changed['missing_world_fraction'] > base['missing_world_fraction'] + 1e-12
            or (changed['centroid_abs_px']['p95'] is not None and base['centroid_abs_px']['p95'] is not None
                and changed['centroid_abs_px']['p95'] > base['centroid_abs_px']['p95'] + 1e-12))
    # Preserve metrics and figures before assertions so failed controls remain inspectable.
    figure = comparison_figure(part, variants, metrics, U / 'figures' / f'controls_part{part}.png')
    part_rows = [r for r in rows if r['part'] == part and r['sequence'] == sequence]
    replaced = [metrics['drop'] if key(r) == key(chosen) else r for r in part_rows]
    normal_temporal = temporal_presence(part_rows)
    fault_temporal = temporal_presence(replaced)
    normal_metric = summarize(part_rows)['per_part'][str(part)]['temporal']
    fault_metric = summarize(replaced)['per_part'][str(part)]['temporal']
    for name in normal_temporal:
        close(normal_temporal[name], normal_metric[name], 'control baseline ' + name)
        close(fault_temporal[name], fault_metric[name], 'control replacement ' + name)
    transition_response = (fault_temporal['missing_either_world_fraction'] is not None
        and fault_temporal['missing_either_world_fraction'] > normal_temporal['missing_either_world_fraction'] + 1e-12)
    result = dict(part=part, selection=dict(sequence=sequence, frame=frame, stroke_id=sid),
                  rule='First orbit then zoom, frame ascending, stroke lexical; >=10 eligible observations and some present ink',
                  source_png=str(original), source_sha256=sha(original), control_png_sha256=hashes,
                  no_edit_exact=True, drift_responses=responses, dropped_missing_fraction=metrics['drop']['summary']['missing_world_fraction'],
                  temporal_baseline=normal_temporal, temporal_suppressed=fault_temporal,
                  temporal_missing_transition_response=transition_response, comparison_figure=figure,
                  note='Dropping an initial frame can register reappearance rather than directional dropout; both are reported.',
                  metric_rows=metrics)
    save(destination / 'METRICS.json', result)
    require(any(responses.values()), f'part {part}: drift control unresponsive')
    require(result['dropped_missing_fraction'] == 1., f'part {part}: complete disappearance not detected')
    result['directional_dropout'] = directional_dropout(part, candidates, paths, asset, destination)
    return result


def validate():
    start = time.monotonic()
    checks, evidence = {}, {}

    def check(name, action):
        try:
            evidence[name] = action()
            checks[name] = dict(passed=True)
        except Exception as error:
            checks[name] = dict(passed=False, error_type=type(error).__name__, message=str(error))

    check('frozen_input_source_hashes', frozen_hashes)
    for unit in ('unit_003', 'unit_006'):
        check(f'historical_{unit}_seal', lambda unit=unit: historical_manifest(unit))
    rows, summary = read(U / 'METRIC_ROWS.json'), read(U / 'TEMPORAL_SUMMARY.json')
    check('independent_raw_coverage_and_temporal_sums', lambda: aggregate_checks(rows, summary))
    check('independent_complete_video_decode', video_checks)
    paths, asset = anchor_paths(), read(U / 'CONFIG.json')['asset']
    for part in (1, 2, 3):
        check(f'actual_raster_controls_part{part}', lambda part=part: control_part(part, rows, paths, asset))
    valid = all(item['passed'] for item in checks.values())
    result = dict(verdict='VALID' if valid else 'INVALID', checks=checks, evidence=evidence,
                  seconds=time.monotonic() - start,
                  scientific_gates=dict(software_contract='GO' if valid else 'NO_GO',
                      actual_rendered_temporal_quality=summary['status'], visual_review='SEPARATE_REQUIRED',
                      reconstructed_input='NOT_TESTED', full_P1='NOT_CLAIMED', H1_H2='NOT_TESTED'),
                  scope='Saved actual per-ID raster controls, independent raw presence sums, all-frame FFV1 decode and provenance audit; no renderer import.',
                  limitations=['Centroid extraction shares the frozen temporal metric implementation; independent sums verify coverage and disappearance accounting.',
                               'Analytic references share authored lamp geometry and manual labels. No reconstructed or blind scientific data.',
                               'No-edit checks repeat saved-output evaluation; renderer instrumentation regression is recorded separately.',
                               'Inherited density, rim and hidden-profile failures remain unchanged.'])
    save(U / 'INDEPENDENT_VALIDATION.json', result)
    return result


if __name__ == '__main__':
    result = validate()
    print(json.dumps(dict(verdict=result['verdict'], scientific_gates=result['scientific_gates'],
                          seconds=result['seconds'], failures={k: v for k, v in result['checks'].items() if not v['passed']})))
    raise SystemExit(0 if result['verdict'] == 'VALID' else 1)
