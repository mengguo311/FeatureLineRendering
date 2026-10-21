"""Posthoc read-only artifact verification; this does not set scientific gates.

Writes only unit_001/INDEPENDENT_VALIDATION.json. Invoke through receipt.py for
runtime records. No producer entry point is imported or run. --skip-probes is
an explicit budget option and is recorded as a coverage omission.
"""
from common import *
import argparse
import subprocess
import time
import traceback
from datetime import datetime, timezone
from PIL import Image
from scipy import ndimage
from renderer import render
from temporal_probe import evaluate_probe, summarize_probes


def read_json(name):
    return json.loads((OUT / name).read_text())


def pixels(path):
    with Image.open(path) as im:
        return np.asarray(im).copy()


def compare(actual, expected, path="value", errors=None):
    """Compare complete JSON trees; floats permit only serialization-level noise."""
    errors = [] if errors is None else errors
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            errors.append(f"{path}: keys/type differ")
        else:
            for key in expected:
                compare(actual[key], expected[key], f"{path}.{key}", errors)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            errors.append(f"{path}: length/type differ")
        else:
            for i, (a, b) in enumerate(zip(actual, expected)):
                compare(a, b, f"{path}[{i}]", errors)
    elif isinstance(expected, float):
        if not isinstance(actual, (int, float)) or not np.isclose(actual, expected, rtol=1e-10, atol=1e-12):
            errors.append(f"{path}: numeric mismatch {actual!r} != {expected!r}")
    elif actual != expected:
        errors.append(f"{path}: mismatch {actual!r} != {expected!r}")
    return errors


def source_checks():
    lock, protocol = read_json('SOURCE_LOCK.json'), read_json('PROTOCOL.json')
    errors, files, snapshots = [], [], []
    for name, expected in lock['files'].items():
        path = Path(name)
        digest = sha(path)
        files.append(dict(path=name, sha256=digest, matches=digest == expected))
        if digest != expected:
            errors.append(f'source hash mismatch: {name}')
        if WORK in path.parents and path.suffix in ('.py', '.md'):
            snap = OUT / 'source_snapshot' / path.relative_to(WORK)
            good = snap.is_file() and sha(snap) == expected
            snapshots.append(dict(path=str(snap), matches=good))
            if not good:
                errors.append(f'snapshot mismatch: {snap}')
    for name, expected in protocol['inputs'].items():
        if sha(name) != expected:
            errors.append(f'original input mismatch: {name}')
    return dict(files=files, source_snapshots=snapshots, original_inputs_checked=len(protocol['inputs'])), errors


def edit_metric(before, after, parts, target=1, band=2):
    delta = np.abs(after.astype(float) / 255. - before.astype(float) / 255.)
    if delta.ndim == 3:
        delta = delta.sum(axis=2)
    target_mask = parts == target
    outside = ~target_mask
    distance = ndimage.distance_transform_edt(outside)
    total = float(delta.sum())
    fraction = lambda mask: float(delta[mask].sum()) / max(total, 1e-15)
    inside_delta = float(delta[target_mask].sum())
    return dict(total_delta=total, inside_delta=inside_delta, nonzero_edit=inside_delta > 10,
                outside_fraction=fraction(outside), boundary_band_fraction=fraction(outside & (distance <= band)),
                far_other_parts_fraction=fraction(outside & (distance > band) & (parts > 0)),
                far_background_fraction=fraction(outside & (distance > band) & (parts == 0)),
                inside_mean_delta=float(delta[target_mask].mean()) if target_mask.any() else 0.,
                mask_pixels=int(target_mask.sum()), band_px=band)


def still_checks():
    mesh, strokes, cfg = load_inputs()
    saved = read_json('EDIT_METRICS.json')
    errors, views = [], []
    compare([v['azimuth'] for v in saved['views']], [30, 120, 210, 300], 'still_views', errors)
    for row in saved['views']:
        az = row['azimuth']
        camera = core.camera(az, 20, 4.5, 512, 600)
        refdepth, refparts = core.analytic_reference(cfg['asset'], camera)
        with np.load(OUT / f'stills/reference_{az:03}.npz', allow_pickle=False) as ref:
            same_depth = np.array_equal(refdepth, ref['depth'])
            same_parts = np.array_equal(refparts, ref['parts'])
        if not same_depth or not same_parts:
            errors.append(f'analytic reference mismatch: {az}')
        before = pixels(OUT / f'stills/base_{az:03}.png')
        angle = pixels(OUT / f'stills/angle_{az:03}.png')
        width = pixels(OUT / f'stills/width_{az:03}.png')
        injected = angle.copy()
        yy, xx = np.where(refparts == 2)
        cy, cx = int(yy[len(yy)//2]), int(xx[len(xx)//2])
        injected[max(0, cy-4):cy+4, max(0, cx-4):cx+4] = 0
        metrics = dict(angle=edit_metric(before, angle, refparts), width=edit_metric(before, width, refparts),
                       no_edit=edit_metric(before, before, refparts), injected_leakage=edit_metric(before, injected, refparts))
        for name, metric in metrics.items():
            compare(metric, row[name], f'view{az}.{name}', errors)
        gates = {name: m['inside_delta'] > 10 and m['far_other_parts_fraction'] <= .02 and m['far_background_fraction'] <= .02
                 for name, m in metrics.items() if name in ('angle', 'width')}
        gates['no_edit_control'] = metrics['no_edit']['total_delta'] == 0 and not metrics['no_edit']['nonzero_edit']
        gates['leakage_control'] = metrics['injected_leakage']['far_other_parts_fraction'] > metrics['angle']['far_other_parts_fraction']
        compare(gates, row['gates'], f'view{az}.recorded_gates', errors)
        with np.load(OUT / f'stills/base_{az:03}.npz', allow_pickle=False) as base:
            interior = ndimage.binary_erosion(refparts > 0, iterations=2) & np.isfinite(refdepth) & np.isfinite(base['depth'])
            dz = abs(refdepth[interior] - base['depth'][interior])
            compare(dict(samples=len(dz), p95=float(np.percentile(dz, 95)), max=float(dz.max())), row['independent_depth'], f'view{az}.depth_stats', errors)
            compare({str(p): float(base['hatch'][refparts == p].sum()) for p in (1, 2, 3)}, row['per_part_ink'], f'view{az}.part_ink', errors)
        views.append(dict(azimuth=az, analytic_depth_exact=same_depth, analytic_parts_exact=same_parts, metrics=metrics))
    compare(saved['all_gates'], all(all(v['gates'].values()) for v in saved['views']), 'recorded_all_edit_gates', errors)
    return dict(views=views, metric_float_rtol=1e-10, metric_float_atol=1e-12), errors


def asset_checks():
    mesh, baseline, cfg = load_inputs()
    original = {s['id']: s for s in baseline}
    errors, rows = [], []
    for name, target_only in [('cold_regenerated.npz', False), ('angle_edited.npz', True)]:
        derived = load_strokes(OUT / 'inputs' / name)
        index = {s['id']: s for s in derived}
        if len(index) != len(derived) or set(index) != set(original):
            errors.append(f'{name}: ID set/uniqueness mismatch')
        checked, equal = 0, True
        for sid in set(index) & set(original):
            a, b = original[sid], index[sid]
            if target_only and a['part'] == 1:
                continue
            checked += 1
            same = a['part'] == b['part'] and a['ink'] == b['ink'] and np.array_equal(a['faces'], b['faces']) and np.array_equal(a['bary'], b['bary'])
            equal &= same
            if not same:
                errors.append(f'{name}: unexpected changed path {sid}')
        rows.append(dict(file=name, unique_ids=len(index), checked_paths=checked, exact=equal))
    report = read_json('ASSET_VALIDATION.json')
    compare(core.stroke_digest(baseline), report['baseline_digest'], 'baseline_digest', errors)
    compare(core.stroke_digest(load_strokes(OUT / 'inputs/angle_edited.npz')), report['edited_digest'], 'edited_digest', errors)
    return dict(stroke_files=rows, part_stroke_counts={str(p): sum(s['part'] == p for s in baseline) for p in (1, 2, 3)}), errors


def cold_render_check():
    mesh, _, cfg = load_inputs()
    cold = load_strokes(OUT / 'inputs/cold_regenerated.npz')
    result = render(mesh, cold, cfg, azimuth=30, elevation=20, distance=4.5)
    quantized = np.uint8(np.rint(np.clip(result['image'], 0, 1) * 255))
    errors, exact = [], dict(image=np.array_equal(quantized, pixels(OUT / 'stills/base_030.png')))
    with np.load(OUT / 'stills/base_030.npz', allow_pickle=False) as saved:
        for name in ('hatch', 'depth', 'parts'):
            exact[name] = np.array_equal(result[name], saved[name])
    errors.extend(f'cold render mismatch: {name}' for name, value in exact.items() if not value)
    return dict(camera=dict(azimuth=30, elevation=20, distance=4.5), exact_arrays=exact,
                cold_rgb_sha256=hashlib.sha256(quantized.tobytes()).hexdigest(),
                scope='Fresh renderer invocation using separately regenerated saved paths; no producer import.'), errors


def media_checks():
    errors, videos = [], []
    for name, expected_frames in [('orbit', 36), ('zoom', 24), ('edit', 24)]:
        folder = OUT / 'frames' / name
        compare(sorted(p.name for p in folder.glob('*.png')), [f'{i:04d}.png' for i in range(expected_frames)], f'{name}.source_frame_set', errors)
        trajectory = read_json(f'TRAJECTORY_{name}.json')
        if len(trajectory) != expected_frames:
            errors.append(f'{name}: trajectory frame count differs')
        for i, row in enumerate(trajectory):
            expected = dict(frame=i, azimuth=10*i if name == 'orbit' else 30, elevation=20,
                            distance=float(4.8-.8*np.cos(2*np.pi*i/23)) if name == 'zoom' else 4.5,
                            shade_edit=name == 'edit' and i >= 12)
            compare({key: row[key] for key in expected}, expected, f'{name}.trajectory[{i}]', errors)
        command = [FFMPEG, '-v', 'error', '-threads', '1', '-i', str(OUT / 'videos' / f'{name}.mkv'),
                   '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-threads', '1', '-']
        run = subprocess.run(command, capture_output=True, timeout=180)
        expected_bytes = expected_frames * 512 * 512 * 3
        hashes, exact = [], []
        if run.returncode != 0 or len(run.stdout) != expected_bytes:
            errors.append(f'{name}: full decode failed or byte count differs')
        else:
            frames = np.frombuffer(run.stdout, np.uint8).reshape(expected_frames, 512, 512, 3)
            for i, frame in enumerate(frames):
                with Image.open(folder / f'{i:04d}.png') as im:
                    source = np.asarray(im.convert('RGB'))
                same = np.array_equal(source, frame)
                exact.append(same)
                hashes.append(hashlib.sha256(frame.tobytes()).hexdigest())
                if not same:
                    errors.append(f'{name}: decoded RGB mismatch frame {i}')
        saved = read_json(f'VIDEO_{name}.json')
        observed = dict(decoded_bytes=len(run.stdout), expected_frames=expected_frames, decoded_frames=len(exact),
                        all_rgb_exact=len(exact) == expected_frames and all(exact), distinct_frames=len(set(hashes)), frame_sha256=hashes)
        compare(observed, {key: saved[key] for key in observed}, f'{name}.saved_decode_summary', errors)
        videos.append(dict(name=name, command=command, returncode=run.returncode,
                           stderr=run.stderr.decode('utf8', errors='replace'), **observed))
    return dict(videos=videos, expected_frames_total=84, decoded_frames_total=sum(v['decoded_frames'] for v in videos)), errors


def array_inventory():
    inventory = []
    for path in sorted(OUT.rglob('*.npz')):
        arrays = {}
        with np.load(path, allow_pickle=False) as archive:
            for key in archive.files:
                value = archive[key]
                entry = dict(shape=list(value.shape), dtype=str(value.dtype), elements=int(value.size))
                if np.issubdtype(value.dtype, np.floating):
                    entry.update(nan=int(np.isnan(value).sum()), positive_inf=int(np.isposinf(value).sum()), negative_inf=int(np.isneginf(value).sum()))
                arrays[key] = entry
        inventory.append(dict(path=str(path.relative_to(OUT)), sha256=sha(path), arrays=arrays))
    return dict(npz_files=len(inventory), arrays=sum(len(x['arrays']) for x in inventory), files=inventory), []


def probe_checks():
    mesh, strokes, cfg = load_inputs()
    protocol, saved = read_json('PROTOCOL.json'), read_json('TEMPORAL_PROBES.json')
    index = {s['id']: s for s in strokes}
    expected_keys = {(fi, sid) for fi in range(len(protocol['metrics']['probe_cameras'])) for sid in protocol['metrics']['probe_ids']}
    actual_keys = [(r['frame'], r['stroke_id']) for r in saved['rows']]
    errors, rows, faults = [], [], []
    if len(actual_keys) != len(expected_keys) or set(actual_keys) != expected_keys:
        errors.append('probe ID/frame coverage differs from protocol')
    references = {}
    for fi, cam in enumerate(protocol['metrics']['probe_cameras']):
        camera = core.camera(cam['azimuth'], cam['elevation'], cam['distance'], 512, 600)
        with np.load(OUT / f'probes/reference_{fi:02}.npz', allow_pickle=False) as ref:
            references[fi] = (camera, ref['depth'].copy(), ref['parts'].copy())
    for stored in saved['rows']:
        fi, sid = stored['frame'], stored['stroke_id']
        s = index[sid]
        camera, depth, parts = references[fi]
        ink = pixels(OUT / 'probes' / f'{fi:02}_{sid.replace(":", "_")}.png')
        points = core.anchor_points(mesh, s)
        baseline = evaluate_probe(ink, points, s['part'], camera, depth, parts, sid, fi)
        compare(baseline, {key: value for key, value in stored.items() if key != 'render_seconds'}, f'probe[{fi},{sid}]', errors)
        rows.append(baseline)
        shifted = np.zeros_like(ink)
        shifted[:, 3:] = ink[:, :-3]
        drift = evaluate_probe(shifted, points, s['part'], camera, depth, parts, sid, fi)
        dropout = evaluate_probe(np.zeros_like(ink), points, s['part'], camera, depth, parts, sid, fi)
        faults.append(dict(stroke_id=sid, frame=fi, part=s['part'], baseline=baseline['summary'], drift=drift['summary'], dropout=dropout['summary']))
    compare(summarize_probes(rows), saved['summary'], 'probe_aggregate', errors)
    compare(faults, saved['faults'], 'probe_faults', errors)
    drifts, drops = [], []
    for fault in faults:
        n = fault['baseline']['class_counts']['visible']
        if n:
            drops.append(fault['dropout']['missing_visible'] == n)
            a, b = fault['baseline']['support_distance_px']['mean'], fault['drift']['support_distance_px']['mean']
            if a is not None and b is not None:
                drifts.append(b-a)
    controls = dict(dropout_all_eligible_missing=bool(drops) and all(drops),
                    drift_max_mean_support_increase_px=max(drifts) if drifts else None,
                    drift_sensitive=bool(drifts) and max(drifts) > .5)
    compare(controls, saved['controls'], 'probe_controls', errors)
    return dict(records=len(rows), expected_records=len(expected_keys), samples=sum(r['summary']['samples'] for r in rows),
                stored_reference_maps_used=len(references), controls_recomputed=controls,
                scope='Artifact replay through locked metric implementation; not an independent second temporal estimator.'), errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-probes', action='store_true')
    args = parser.parse_args()
    destination = OUT / 'INDEPENDENT_VALIDATION.json'
    if destination.exists():
        raise FileExistsError(f'refusing to overwrite {destination}')
    started = time.monotonic()
    report = dict(purpose='Posthoc independent execution and artifact verification; no science verdict or threshold changes.',
                  validator_sha256=sha(__file__), source_lock_sha256=sha(OUT / 'SOURCE_LOCK.json'),
                  started_utc=datetime.now(timezone.utc).isoformat(), probe_replay_skipped=args.skip_probes, checks=[])
    stages = [('source_and_snapshot_hashes', source_checks), ('array_inventory', array_inventory),
              ('saved_path_identity', asset_checks), ('four_view_edit_and_reference', still_checks),
              ('full_media_decode', media_checks), ('cold_baseline_render', cold_render_check)]
    if not args.skip_probes:
        stages.append(('isolated_probe_png_replay', probe_checks))
    for name, function in stages:
        t = time.monotonic()
        try:
            details, errors = function()
            result = dict(name=name, passed=not errors, details=details, error_count=len(errors), errors=errors[:50])
        except Exception as exc:
            result = dict(name=name, passed=False, exception_type=type(exc).__name__, exception=str(exc), traceback=traceback.format_exc())
        result['seconds'] = time.monotonic()-t
        report['checks'].append(result)
        print(json.dumps(dict(check=name, passed=result['passed'], seconds=result['seconds'])), flush=True)
    report.update(verdict='PASS' if all(x['passed'] for x in report['checks']) else 'FAIL',
                  wall_seconds=time.monotonic()-started, resources=check_resources())
    write_json(destination, report)
    print(json.dumps(dict(validation=report['verdict'], report=str(destination), probe_replay_skipped=args.skip_probes)))
    return 0 if report['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
