"""Frozen round_003 diagnostic driver; each trajectory runs independently."""
import temporal_audit as ta  # Resource controls before scientific imports.
import argparse
import datetime
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

W = Path(__file__).resolve().parents[2]
R = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_003')
P = R.parent/'round_002'
D = W/'docs/partwise_sketch_hatching/round_003'
CFG = json.loads((W/'docs/partwise_sketch_hatching/round_001/PROTOCOL.json').read_text())
PROTO = json.loads((D/'PROTOCOL.json').read_text())
START = time.monotonic()


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def write_json(p, obj):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    temp = p.with_suffix('.tmp')
    temp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False,
                               default=lambda v: v.item() if isinstance(v, np.generic) else str(v))+'\n')
    temp.replace(p)


def status(stage, state='in_progress', verdict='UNMEASURED', **extra):
    obj = json.loads((R/'STATUS.json').read_text())
    obj.update(stage=stage, execution_state=state, scientific_verdict=verdict,
               updated_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), **extra)
    write_json(R/'STATUS.json', obj)


def resource_check():
    root = shutil.disk_usage('/').free; hdd = shutil.disk_usage('/mnt/hdd1').free
    used = sum(p.stat().st_size for p in R.parent.parent.rglob('*') if p.is_file())
    deps = sum(p.stat().st_size for p in (W/'.runtime_p0').rglob('*') if p.is_file())
    assert root >= 1073741824 and hdd >= 10737418240, 'Disk floor'
    assert used+deps < 12884901888, 'Output cap'
    assert time.monotonic()-START < 570, 'Invocation budget'
    assert datetime.datetime.now(datetime.timezone.utc) < datetime.datetime.fromisoformat('2026-10-21T05:01:46.241909+09:00'), 'Round deadline'
    return {'root_free_bytes': root, 'hdd_free_bytes': hdd, 'task_bytes': used,
            'isolated_dependency_bytes': deps, 'affinity': sorted(ta.os.sched_getaffinity(0)),
            'threads_max': 2, 'GPU': False}


def verify_prior():
    manifest = json.loads((P/'SHA256_MANIFEST.json').read_text())
    seal = json.loads((P/'SEAL.json').read_text())
    assert sha(P/'SHA256_MANIFEST.json') == seal['manifest_sha256']
    for f in manifest['files']:
        path = (W if f['root'] == 'worktree' else P)/f['path']
        assert sha(path) == f['sha256'] and path.stat().st_size == f['bytes'], str(path)
    return {'verified_files': len(manifest['files']), 'prior_seal_sha256': sha(P/'SEAL.json')}


def prepare():
    assert not (D/'ASSET_LOCK.json').exists(), 'Never replace frozen lock'
    resource_check(); verified = verify_prior()
    write_json(R/'PRIOR_SEAL_VERIFY.json', verified)
    src = [W/'experiments/partwise_sketch_hatching'/n for n in
           ['core.py', 'temporal_audit.py', 'test_temporal_audit.py', 'run_round003.py', 'round003_receipt.py']]
    src += [D/'PROTOCOL.json', W/'docs/partwise_sketch_hatching/round_001/PROTOCOL.json',
            W/'docs/partwise_sketch_hatching/experiment_outline_v1.md']
    assets = [P/'assets/lamp_mesh.npz', P/'camera_trajectories.json', P/'SEAL.json', P/'NEXT.json']
    assets += list((P/'strokes').glob('*.npz'))
    for kind in ('orbit', 'zoom'): assets += sorted((P/'frames'/kind).glob('*.png'))
    lock = {'implementation_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=W, text=True).strip(),
            'protocol_commit': '9e13c76a', 'source': {str(p.relative_to(W)): sha(p) for p in src},
            'prior_assets': {str(p.relative_to(P)): sha(p) for p in assets},
            'prior_verification': verified, 'resources': resource_check(),
            'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    write_json(D/'ASSET_LOCK.json', lock); status('prepared_waiting_for_lock_commit')
    print(json.dumps({'prepared': True, 'source_files': len(src), 'prior_assets': len(assets)}))


def verify_lock():
    assert subprocess.check_output(['git', 'branch', '--show-current'], cwd=W, text=True).strip() == 'partwise-sketch-hatching-p0p1-v01'
    lock = json.loads((D/'ASSET_LOCK.json').read_text())
    for relative, digest in lock['source'].items(): assert sha(W/relative) == digest, relative
    for relative, digest in lock['prior_assets'].items(): assert sha(P/relative) == digest, relative
    relative = str((D/'ASSET_LOCK.json').relative_to(W))
    subprocess.run(['git', 'ls-files', '--error-unmatch', relative], cwd=W, capture_output=True, check=True)
    assert not subprocess.check_output(['git', 'diff', 'HEAD', '--', relative], cwd=W)
    return lock


def contact_sheet(entries, target, columns=6, width=170):
    height = width+34; sheet = Image.new('RGB', (columns*width, ((len(entries)+columns-1)//columns)*height), 'white')
    draw = ImageDraw.Draw(sheet)
    for i, (title, path) in enumerate(entries):
        x = i % columns * width; y = i // columns * height
        with Image.open(path) as im: sheet.paste(im.convert('RGB').resize((width, width)), (x, y+34))
        draw.text((x+3, y+3), title, fill='black')
    target.parent.mkdir(exist_ok=True, parents=True); sheet.save(target)


def frame_overlay(full, expected, ambiguity, observation):
    im = Image.fromarray(full).convert('RGB'); draw = ImageDraw.Draw(im)
    eligible = expected['eligible_geometry'] & ~ambiguity
    # Every failing eligible sample is shown; no chosen sample subsampling.
    missing = eligible & (observation['distance'][0] > 1.5)
    for x, y in expected['uv'][missing]: draw.ellipse((x-1, y-1, x+1, y+1), fill=(215, 25, 30))
    return im


def run(kind):
    verify_lock(); resource_check()
    assert not (R/(kind+'_metrics.json')).exists(), 'Never overwrite completed trajectory'
    z = np.load(P/'assets/lamp_mesh.npz'); mesh = ta.core.finalize_mesh(z['vertices'], z['faces'], z['parts'])
    strokes = ta.load_strokes(P/'strokes/mixed.npz')
    samples = ta.sample_paths(mesh, strokes, PROTO['sampling']['spacing_world_max'])
    if not (R/'samples.npz').exists():
        np.savez_compressed(R/'samples.npz', **samples, stroke_ids=np.array([s['id'] for s in strokes]),
                            selected_drop=np.array([ta.drop_id(s['id']) for s in strokes]))
    else:
        previous_samples = np.load(R/'samples.npz')
        for key in samples: np.testing.assert_array_equal(samples[key], previous_samples[key])
    trajectories = json.loads((P/'camera_trajectories.json').read_text())[kind]
    records, pairs, timings, image_matches, entries, overlay_entries = [], [], [], [], [], []
    previous = None; fault_totals = {'drift_baseline_sum': 0., 'drift_fault_sum': 0., 'drift_baseline_weight': 0.,
                                    'drift_fault_weight': 0., 'drop_target_count': 0, 'drop_target_weight': 0.,
                                    'drop_baseline_missing_weight': 0., 'drop_fault_missing_weight': 0.}
    for folder in ('raw', 'frames', 'overlays', 'faults'):
        (R/folder/kind).mkdir(parents=True, exist_ok=True)
    for p in trajectories:
        resource_check(); t = time.monotonic(); i = p['index']
        assert p['stroke_digest'] == ta.core.stroke_digest(strokes), 'Original saved path digest'
        c = ta.core.camera(p['azimuth_deg'], p['elevation_deg'], p['distance'], 512, 600)
        expected = ta.expected_samples(samples, CFG['asset'], c)
        render = ta.instrumented_render(mesh, strokes, CFG, p, drop_active=i % 3 == 1)
        original = np.asarray(Image.open(P/'frames'/kind/f'{i:04d}.png'))
        matches = bool(np.array_equal(render['full'], original)); image_matches.append(matches)
        assert matches, f'Instrumented full image differs: {kind} {i}'
        ambiguity = ta.ambiguous_samples(expected['uv'], render['count'])
        observation = ta.observe(samples, expected['uv'], render, strokes, i % 2 == 1, i % 3 == 1)
        frame = ta.frame_summary(samples, expected, ambiguity, observation)
        frame.update(index=i, camera=p, full_image_byte_match=matches,
                     parts={str(k): ta.frame_summary(samples, expected, ambiguity, observation, samples['parts'] == k)
                            for k in (1, 2, 3)})
        current = {key: expected[key] for key in ('visible', 'eligible_geometry')}
        current.update(ambiguity=ambiguity, distance=observation['distance'], offset=observation['offset'])
        if previous is not None:
            pair = ta.pair_summary(samples, previous, current)
            pair.update(from_index=i-1, to_index=i,
                        parts={str(k): ta.pair_summary(samples, previous, current, samples['parts'] == k)
                               for k in (1, 2, 3)})
            pairs.append(pair)
        previous = current
        eligible = expected['eligible_geometry'] & ~ambiguity
        w = samples['weight']; d = observation['distance']
        if i % 2 == 1:
            for v, name in ((0, 'baseline'), (1, 'fault')):
                selected = eligible & np.isfinite(d[v])
                fault_totals[f'drift_{name}_sum'] += float((w[selected]*d[v, selected]).sum())
                fault_totals[f'drift_{name}_weight'] += float(w[selected].sum())
        if i % 3 == 1:
            selected = eligible & np.array([ta.drop_id(s['id']) for s in strokes])[samples['owner']]
            fault_totals['drop_target_count'] += int(selected.sum())
            fault_totals['drop_target_weight'] += float(w[selected].sum())
            fault_totals['drop_baseline_missing_weight'] += float(w[selected & (d[0] > 1.5)].sum())
            fault_totals['drop_fault_missing_weight'] += float(w[selected & (d[2] > 1.5)].sum())
        np.savez_compressed(R/'raw'/kind/f'{i:04d}.npz',
                            uv=expected['uv'], expected_depth=expected['expected_depth'], sample_depth=expected['sample_depth'],
                            exclusion_code=expected['code'], visible=expected['visible'],
                            eligible_geometry=expected['eligible_geometry'], ambiguity=ambiguity,
                            distance=d, offset=observation['offset'], overlap_count=render['count'],
                            identified_xy=observation['provenance_xy'], identified_owner=observation['provenance_owner'],
                            hatch=render['hatch'], drift_hatch=observation['drift'], drop_hatch=render['drop'])
        path = R/'frames'/kind/f'{i:04d}.png'; Image.fromarray(render['full']).save(path)
        overlay = R/'overlays'/kind/f'{i:04d}.png'; frame_overlay(render['full'], expected, ambiguity, observation).save(overlay)
        entries.append((f'{kind} {i:02d} | fixed strokes', path))
        overlay_entries.append((f'{kind} {i:02d} | missing in red', overlay))
        if i in (0, 1, 2):
            for key, a in [('baseline', render['hatch']), ('drift', observation['drift']), ('drop', render['drop'])]:
                Image.fromarray(255-a).save(R/'faults'/kind/f'{i:04d}_{key}.png')
        timings.append(time.monotonic()-t); frame['seconds'] = timings[-1]; records.append(frame)
        write_json(R/(kind+'_partial.json'), {'frames_complete': len(records), 'frames': records, 'pairs': pairs,
                                             'fault_totals': fault_totals, 'image_matches': image_matches})
        status(f'{kind}_frame_{i+1}_of_{len(trajectories)}', artifacts=['samples.npz', kind+'_partial.json', 'raw/'+kind])
        print(json.dumps({'trajectory': kind, 'frame': i, 'seconds': timings[-1],
                          'eligible': frame['eligible_samples'], 'missing_fraction': frame['variants']['baseline']['missing_fraction']}), flush=True)
    contact_sheet(entries, R/'figures'/(kind+'_all_frames.png'))
    contact_sheet(overlay_entries, R/'figures'/(kind+'_all_missing.png'))
    result = {'complete': True, 'kind': kind, 'frames': records, 'pairs': pairs,
              'frame_seconds': timings, 'full_image_matches': image_matches, 'fault_totals': fault_totals,
              'resources': resource_check(), 'stroke_count': len(strokes), 'sample_count': len(samples['xyz']),
              'length_world': float(samples['weight'].sum())}
    write_json(R/(kind+'_metrics.json'), result)
    status(kind+'_complete', artifacts=[kind+'_metrics.json', 'raw/'+kind, 'figures/'+kind+'_all_frames.png'])


def aggregate(kind):
    m = json.loads((R/(kind+'_metrics.json')).read_text()); frames = m['frames']; pairs = m['pairs']
    den = sum(f['eligible_length_world'] for f in frames)
    pairden = sum(p['common_length_world'] for p in pairs)
    output = {'frames': len(frames), 'pairs': len(pairs), 'sample_count_per_frame': m['sample_count'],
              'full_image_matches': sum(m['full_image_matches']),
              'total_length_frame_world': sum(f['total_length_world'] for f in frames),
              'visible_length_frame_world': sum(f['visible_length_world'] for f in frames),
              'eligible_length_frame_world': den,
              'eligible_fraction_of_visible': den/sum(f['visible_length_world'] for f in frames),
              'eligible_fraction_of_total': den/sum(f['total_length_world'] for f in frames),
              'common_length_pair_world': pairden,
              'common_fraction_of_jointly_visible': pairden/sum(p['jointly_visible_length_world'] for p in pairs),
              'frame_time_seconds': ta.weighted_stats(np.array(m['frame_seconds']), np.ones(len(frames))),
              'variants': {}, 'fault_totals': m['fault_totals']}
    for name in ('baseline', 'drift', 'drop'):
        output['variants'][name] = {'missing_fraction': sum(f['variants'][name]['missing_fraction']*f['eligible_length_world'] for f in frames)/den,
                                   'pair_events': {event: sum(p['variants'][name][event]['length_world'] for p in pairs)/pairden
                                                   for event in ('both_detected', 'disappearance', 'reappearance', 'both_missing')}}
    return output


def summarize():
    verify_lock(); resource_check(); assert not (R/'metrics.json').exists()
    summaries = {k: aggregate(k) for k in ('orbit', 'zoom')}
    totals = {key: sum(m['fault_totals'][key] for m in summaries.values()) for key in summaries['orbit']['fault_totals']}
    baseline_drift = totals['drift_baseline_sum']/totals['drift_baseline_weight']
    injected_drift = totals['drift_fault_sum']/totals['drift_fault_weight']
    baseline_drop = totals['drop_baseline_missing_weight']/totals['drop_target_weight']
    injected_drop = totals['drop_fault_missing_weight']/totals['drop_target_weight']
    green = json.loads((R/'TESTS_GREEN.json').read_text())
    gates = {'regression_green': green['returncode'] == 0,
             'all_60_full_images_byte_match': sum(m['full_image_matches'] for m in summaries.values()) == 60,
             'drift_mean_increase_above_1px': injected_drift-baseline_drift > 1,
             'drop_target_count_at_least_100': totals['drop_target_count'] >= 100,
             'drop_target_missing_exactly_one': injected_drop == 1.,
             'drop_missing_increase_above_half': injected_drop-baseline_drop > .5,
             'drop_has_disappearance_and_reappearance': all(sum(m['variants']['drop']['pair_events'][key] for m in summaries.values()) > 0
                                                          for key in ('disappearance', 'reappearance'))}
    result = {'evaluation_complete': True, 'diagnostic_go': all(gates.values()), 'gates': gates,
              'trajectories': summaries,
              'fault_sensitivity': {'drift_baseline_finite_mean_px': baseline_drift,
                                    'drift_injected_finite_mean_px': injected_drift,
                                    'drop_target_samples': totals['drop_target_count'],
                                    'drop_target_baseline_missing_fraction': baseline_drop,
                                    'drop_target_injected_missing_fraction': injected_drop},
              'metric_scope': 'Hatch-layer identified raster SUPPORT, not subpixel centerline, final composite visibility, or perceptual flicker.',
              'identity_caveat': 'One nonzero separately downsampled layer is an operational conservative filter, not exact causal decomposition under signed LANCZOS.',
              'exclusion_codes': {'1': 'out_of_frame_or_nonpositive_z', '2': 'no_analytic_hit',
                                  '3': 'different_frontmost_part', '4': 'same_part_depth_disagreement_over_0.006',
                                  '5': 'visible_but_within_fixed_2px_boundary_band'},
              'resources': resource_check(), 'nonclaims': PROTO['not_measured']}
    write_json(R/'metrics.json', result)
    # All 60 complete-object views remain represented; fault examples fixed before evaluation.
    contact_sheet([(f'{k} {i:02d}', R/'frames'/k/f'{i:04d}.png') for k, count in [('orbit',36), ('zoom',24)] for i in range(count)],
                  R/'figures/full_view_contact_sheet.png')
    contact_sheet([(f'{k} {i:02d} | {variant}', R/'faults'/k/f'{i:04d}_{variant}.png')
                   for k in ('orbit', 'zoom') for i in (0, 1, 2) for variant in ('baseline', 'drift', 'drop')],
                  R/'figures/fault_examples.png', columns=3, width=256)
    status('evaluated_pending_validation_report', verdict='DIAGNOSTIC_GO' if result['diagnostic_go'] else 'DIAGNOSTIC_NO_GO',
           tests={'gates': gates}, artifacts=['metrics.json', 'orbit_metrics.json', 'zoom_metrics.json', 'raw/', 'figures/'])
    print(json.dumps({'diagnostic_go': result['diagnostic_go'], 'gates': gates, 'fault_sensitivity': result['fault_sensitivity']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=('prepare', 'orbit', 'zoom', 'summarize'))
    action = parser.parse_args().action
    try:
        if action == 'prepare': prepare()
        elif action == 'summarize': summarize()
        else: run(action)
    except Exception as exc:
        status('interrupted_or_failed', state='engineering_invalid', verdict='INCOMPLETE', error=f'{type(exc).__name__}: {exc}')
        raise
