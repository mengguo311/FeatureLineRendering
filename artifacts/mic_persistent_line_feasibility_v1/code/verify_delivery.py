"""Independent delivery checks, deliberately importing no production modules.

The verifier may run only after the accepted-asset seal. It decodes all 49 native
field sets and every frame of both videos, and recomputes projections directly.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ART = HERE.parent
WORKSPACE = ART.parents[1]
OUT = WORKSPACE / 'out/mic_persistent_line_feasibility_v1'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def project_direct(xyz, camera):
    """Homogeneous camera projection independent of production geometry.py."""
    camera = camera.get('camera', camera)
    xyz = np.asarray(xyz, dtype=np.float64).reshape((-1, 3))
    w2c = np.asarray(camera['w2c'], dtype=np.float64)
    k = np.asarray(camera.get('native_K', camera.get('K')), dtype=np.float64)
    camera_xyz = np.c_[xyz, np.ones(len(xyz))] @ w2c.T
    homogeneous = camera_xyz[:, :3] @ k.T
    with np.errstate(divide='ignore', invalid='ignore'):
        xy = homogeneous[:, :2] / homogeneous[:, 2:3]
    return xy, camera_xyz[:, 2]


def verify_frozen_inputs():
    frozen = load(ART / 'PROTOCOL_PUSH.json')
    checks = {}
    for name, digest in frozen['files'].items():
        checks[name] = sha(ART / name) == digest
    if not frozen['verified'] or not all(checks.values()):
        raise ValueError('Frozen protocol/input bytes changed or push unverified')
    return {'protocol_commit': frozen['protocol_commit'], 'frozen_hashes_match': checks}


def verify_fields(inputs):
    headers = inputs['native_cache_npy_headers']
    records = []
    expected = set(sum(inputs['splits'].values(), []))
    rendered = {f['key']: f for f in load(ART/'FRAME_AUDIT.json')['frames']}
    sets = [r for r in inputs['sets'] if r['kind'] == 'frames']
    if not sets:
        sets = [r for r in inputs['sets'] if r['kind'] == 'frame']
    if {r['key'] for r in sets} != expected or len(sets) != 49:
        raise ValueError('Expected exactly 49 sealed frame sets')
    for item in sets:
        arrays = []
        for filename in ('native.npz', 'responses.npz', 'typed.npz', 'provenance.npz'):
            path = Path(item['path']) / filename
            expected_file = next(f for f in item['files'] if Path(f['path']).name == filename)
            if sha(path) != expected_file['sha256']:
                raise ValueError(f'Field seal mismatch {path}')
            with np.load(path, allow_pickle=False) as bundle:
                if set(bundle.files) != {n.removesuffix('.npy') for n in headers[filename]}:
                    raise ValueError(f'Field name mismatch {path}')
                for name in bundle.files:
                    value = bundle[name]
                    expected_field = headers[filename][name + '.npy']
                    if list(value.shape) != expected_field['shape'] or value.dtype.str != expected_field['descr']:
                        raise ValueError(f'Field schema mismatch {path}:{name}')
                    if not np.all(np.isfinite(value)):
                        raise ValueError(f'Nonfinite field {path}:{name}')
                    output_name = ('rgb' if filename == 'native.npz' and name == 'rgb' else
                                   name if filename == 'responses.npz' and name in ('A', 'C') else None)
                    if output_name:
                        expected_pixels = (np.rint(np.clip(value, 0, 1)*255).astype(np.uint8)
                            if output_name == 'rgb' else
                            np.repeat(np.rint(255*(1-np.clip(value, 0, 1))).astype(np.uint8)[..., None], 3, axis=2))
                        with Image.open(resolve_output(rendered[item['key']]['outputs'][output_name])) as im:
                            if not np.array_equal(expected_pixels, np.asarray(im.convert('RGB'))):
                                raise ValueError(f'Rendered native source pixels disagree {item["key"]}/{output_name}')
                    arrays.append({'file': filename, 'field': name, 'shape': list(value.shape),
                                   'dtype': value.dtype.str, 'finite': True})
        records.append({'key': item['key'], 'arrays': arrays})
    return {'camera_count': len(records), 'field_array_count': sum(len(x['arrays']) for x in records),
            'all_finite': True, 'all_field_shapes_and_dtypes_match_frozen_headers': True,
            'all_field_files_match_frozen_byte_hashes': True, 'records': records}


def mp4_atoms(path):
    atoms = []
    with open(path, 'rb') as f:
        end = Path(path).stat().st_size
        while f.tell() < end:
            pos = f.tell()
            header = f.read(8)
            if len(header) != 8:
                raise ValueError('Truncated MP4 atom')
            size, kind = struct.unpack('>I4s', header)
            if size == 1:
                size = struct.unpack('>Q', f.read(8))[0]
            if size == 0:
                size = end - pos
            if size < 8:
                raise ValueError('Invalid MP4 atom length')
            atoms.append((kind.decode('ascii', errors='replace'), pos, size))
            f.seek(pos + size)
    return atoms


def thumb_rgb(image):
    return np.asarray(image.resize((80, 80), Image.Resampling.BILINEAR), dtype=float)


def verify_video(path, expected_width, panel_paths):
    path = Path(path)
    stream = imageio_ffmpeg.read_frames(str(path), pix_fmt='rgb24')
    metadata = next(stream)
    width, height = metadata['size']
    if width != expected_width or height != expected_width * 832 // 3200:
        raise ValueError(f'Unexpected video dimensions {path}: {metadata}')
    if 'h264' not in str(metadata['codec']).lower() or 'yuv420p' not in str(metadata['pix_fmt']).lower():
        raise ValueError(f'Video codec/pixel format mismatch {metadata}')
    expected_thumbs = []
    for panel in panel_paths:
        with Image.open(panel) as im:
            expected_thumbs.append(thumb_rgb(im.crop((0, 32, im.width // 4, im.height)).convert('RGB')))
    expected_thumbs = np.stack(expected_thumbs)
    hashes = []
    order = []
    for index, pixels in enumerate(stream):
        decoded = np.frombuffer(pixels, dtype=np.uint8).reshape((height, width, 3))
        hashes.append(hashlib.sha256(pixels).hexdigest())
        actual = thumb_rgb(Image.fromarray(decoded[expected_width * 32 // 3200:, :width // 4]))
        errors = np.mean(np.abs(expected_thumbs - actual), axis=(1, 2, 3))
        closest = int(np.argmin(errors))
        order.append({'index': index, 'closest_source_index': closest,
                      'source_rgb_mean_abs_error': float(errors[index]) if index < 33 else None})
        if closest != index:
            raise ValueError(f'Video source frame order mismatch {path}: frame{index} closest{closest}')
    atoms = mp4_atoms(path)
    names = [x[0] for x in atoms]
    faststart = 'moov' in names and 'mdat' in names and names.index('moov') < names.index('mdat')
    if len(hashes) != 33 or len(set(hashes)) != 33 or not faststart:
        raise ValueError(f'Video count/distinct/faststart failure {path}')
    if abs(float(metadata['fps']) - 6.) > .001:
        raise ValueError(f'Video fps mismatch {path}')
    return {'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size,
            'metadata': metadata, 'decoded_frames': len(hashes), 'distinct_decoded_frames': len(set(hashes)),
            'frame_sha256': hashes, 'order': order, 'faststart': faststart, 'mp4_atoms': atoms}


def verify_scope(trace_paths, inputs):
    allkeys = set(sum(inputs['splits'].values(), []))
    allowed = {'construction': set(inputs['splits']['construction']),
               'validation': set(inputs['splits']['validation_acceptance_only']), 'render': allkeys,
               'independent': allkeys, 'review_figures': set(), 'regressions': set()}
    rows = []
    violations = []
    keypat = re.compile(r'/transport/(?:raw|frames)/mic/([^/]+)/(?:native|responses|typed|provenance)\.npz')
    for stage, trace in trace_paths.items():
        opened = []
        writes = []
        unresolved_relative = []
        calls = 0
        for line in Path(trace).read_text(errors='replace').splitlines():
            if not re.search(r'\b(?:open|openat|openat2|creat)\(', line):
                continue
            calls += 1
            match = re.search(r'"((?:[^"\\]|\\.)*)"', line)
            if not match:
                continue
            path = match.group(1)
            if not path.startswith('/'):
                if 'openat(' in line or 'openat2(' in line:
                    cwd_relative = bool(re.search(r'\bopenat2?\(AT_FDCWD,', line))
                else:
                    cwd_relative = True
                if cwd_relative:
                    path = str((WORKSPACE/path).resolve())
                else:
                    unresolved_relative.append({'path': path, 'line': line[:500]})
            cache = keypat.search(path)
            if cache:
                key = cache.group(1)
                opened.append(key)
                if key not in allowed[stage]:
                    violations.append({'stage': stage, 'path': path, 'reason': 'wrong_phase_cache_input'})
            if any(flag in line for flag in ['O_WRONLY', 'O_RDWR', 'O_CREAT', 'O_TRUNC']) or 'creat(' in line:
                writes.append(path)
                if not path.startswith('/'):
                    violations.append({'stage': stage, 'path': path, 'reason': 'unresolved_dirfd_relative_write'})
                real_path = str(Path(path).resolve()) if path.startswith('/') else path
                if real_path.startswith('/') and not real_path.startswith(str(WORKSPACE) + '/') and real_path not in ['/dev/null']:
                    violations.append({'stage': stage, 'path': path, 'reason': 'outside_workspace_write'})
            if path.startswith('/mnt/') or path.startswith('/home/'):
                parts = Path(path).parts
                if any(part.upper() == 'TEST' or part.lower() in ('meshes', 'mesh') for part in parts):
                    violations.append({'stage': stage, 'path': path, 'reason': 'forbidden_input_path'})
        rows.append({'stage': stage, 'trace': str(trace), 'sha256': sha(trace), 'open_calls': calls,
                     'launch_cwd': str(WORKSPACE), 'unresolved_dirfd_relative_calls': unresolved_relative,
                     'decoded_cache_candidate_keys': sorted(set(opened)), 'write_paths': sorted(set(writes))})
    return {'scope': 'Actual recorded process trees open/openat/openat2/creat attempts only; not an audit of untraced history or non-open syscalls. Relative AT_FDCWD/open/creat paths resolve against the recorded launch cwd; directory-fd-relative calls are listed unresolved. NPZ member access requires source/event evidence.',
            'passed': not violations, 'violations': violations, 'stages': rows}


def verify_asset(stem):
    record = load(ART / (stem + '.json'))
    seal = load(ART / (stem + '_SEAL.json'))
    for name, digest in seal['files'].items():
        if sha(ART/name) != digest:
            raise ValueError('Independent sealed asset bytes disagree: ' + name)
    paths = record['paths']
    ids = [p.get('persistent_id', p.get('id')) for p in paths]
    if len(ids) != len(set(ids)) or any(x is None for x in ids):
        raise ValueError('Missing/duplicate persistent identity')
    blocks = [np.asarray(p['controls_xyz'], dtype='<f8').reshape((-1, 3)) for p in paths]
    xyz = np.concatenate(blocks) if blocks else np.empty((0, 3), dtype='<f8')
    offsets = np.asarray([0] + list(np.cumsum([len(x) for x in blocks])), dtype='<i8')
    digest = hashlib.sha256(xyz.tobytes() + offsets.tobytes()).hexdigest()
    if not np.isfinite(xyz).all() or digest != record['geometry_sha256'] or digest != seal['geometry_sha256']:
        raise ValueError('Independent world geometry digest/finite check failed')
    with np.load(ART/(stem+'.npz'), allow_pickle=False) as data:
        if set(data.files) != {'controls', 'offsets'}:
            raise ValueError('Unexpected asset NPZ fields')
        if not np.array_equal(data['controls'], xyz) or not np.array_equal(data['offsets'], offsets):
            raise ValueError('Asset NPZ differs from editable JSON')
    for path, points in zip(paths, blocks):
        if not 2 <= len(points) <= 16:
            raise ValueError('Asset control budget/shape violated')
        if path['topology'] != [[i, i+1] for i in range(len(points)-1)]:
            raise ValueError('Asset ordered polyline topology mismatch')
        arc = np.asarray(path['brush_arc'], dtype=float)
        expected_arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
        if arc.shape != expected_arc.shape or not np.allclose(arc, expected_arc, atol=1e-10):
            raise ValueError('Asset arc-length brush coordinates mismatch')
        if path['color_rgb'] != [0, 96, 220] or path['width_px'] != 2:
            raise ValueError('Asset frozen display style mismatch')
    if len(paths) > 32 or len(xyz) > 512:
        raise ValueError('Asset path/control budget violated')
    return record, {'stem': stem, 'paths': len(paths), 'controls': len(xyz),
                    'geometry_sha256': digest, 'seal_utc': seal['utc'],
                    'json_sha256': sha(ART/(stem+'.json')), 'all_world_coordinates_finite': True,
                    'npz_json_exact_agreement': True, 'topology_and_brush_coordinates_valid': True}


def resolve_output(path):
    path = Path(path)
    if path.is_absolute():
        return path
    return WORKSPACE/path


def verify_frames(inputs, accepted, proposed):
    manifest = load(ART/'FRAME_AUDIT.json')
    frames = manifest['frames']
    expected = set(sum(inputs['splits'].values(), []))
    if len(frames) != 49 or {f['key'] for f in frames} != expected:
        raise ValueError('Frame delivery does not contain exactly the original 49 cameras')
    ids = lambda record: {p.get('persistent_id', p.get('id')): p for p in record['paths']}
    assets = [('projections', ids(accepted)), ('proposal_projections', ids(proposed))]
    projection_count = 0
    checks = []
    geometry_digests = set()
    for frame in frames:
        camera_path = Path(frame['camera_path'])
        camera = load(camera_path)
        frozen_camera = next(f for s in inputs['sets'] if s['kind'] == 'raw' and s['key'] == frame['key']
                             for f in s['files'] if Path(f['path']).name == 'camera.json')
        if str(camera_path) != frozen_camera['path'] or sha(camera_path) != frozen_camera['sha256']:
            raise ValueError('Frame camera differs from inherited frozen camera')
        geometry_digests.add(frame['geometry_sha256'])
        if frame['geometry_sha256'] != accepted['geometry_sha256'] or frame['asset_sha256'] != sha(ART/'ASSET.json'):
            raise ValueError('Frame does not use immutable accepted asset')
        for name, paths in assets:
            projected = frame[name]
            if len(projected) != len(paths):
                raise ValueError('Per-camera geometry subset selection detected')
            for line in projected:
                ident = line.get('persistent_id', line.get('id'))
                path = paths[ident]
                uv, z = project_direct(path['controls_xyz'], camera)
                np.testing.assert_allclose(np.asarray(line['uv']), uv, atol=1e-7, rtol=1e-10)
                np.testing.assert_allclose(np.asarray(line['z']), z, atol=1e-9, rtol=1e-10)
                projection_count += len(z)
        outputs = {}
        for name, path in frame['outputs'].items():
            path = resolve_output(path)
            with Image.open(path) as im:
                size = im.size
                if size != ((3200, 832) if name == 'panel' else (800, 800)):
                    raise ValueError(f'Unexpected native frame image size {name}: {size}')
            outputs[name] = {'path': str(path), 'sha256': sha(path), 'size': size}
        if not accepted['paths']:
            with Image.open(resolve_output(frame['outputs']['pure3d'])) as im:
                if not np.all(np.asarray(im.convert('RGB')) == 255):
                    raise ValueError('Empty accepted asset pure3D is not honestly white')
            with Image.open(resolve_output(frame['outputs']['hybrid'])) as a, Image.open(resolve_output(frame['outputs']['residual2d'])) as b:
                if not np.array_equal(np.asarray(a.convert('RGB')), np.asarray(b.convert('RGB'))):
                    raise ValueError('Empty accepted asset hybrid differs from complete residual2D')
        with Image.open(resolve_output(frame['outputs']['panel'])) as panel:
            for index, name in enumerate(['rgb', 'pure3d', 'residual2d', 'hybrid']):
                with Image.open(resolve_output(frame['outputs'][name])) as im:
                    if not np.array_equal(np.asarray(panel.crop((800*index, 32, 800*(index+1), 832)).convert('RGB')),
                                          np.asarray(im.convert('RGB'))):
                        raise ValueError('Panel crops/changes a native 800px tile')
        checks.append({'key': frame['key'], 'camera_path': str(camera_path),
                       'geometry_sha256': frame['geometry_sha256'], 'outputs': outputs})
    arc_frames = sorted((f for f in frames if f['key'].startswith('arc0_')), key=lambda f: f['key'])
    return {'camera_count': len(frames), 'unique_geometry_hashes': sorted(geometry_digests),
            'independently_reprojected_control_instances': projection_count,
            'projection_scope': 'All actual accepted/proposed controls in all49 cameras; empty sets have no actual controls to reproduce',
            'frames': checks}, [resolve_output(f['outputs']['panel']) for f in arc_frames]


def verify_chronology():
    events_path = OUT/'EVENTS.jsonl'
    events = [json.loads(x) for x in events_path.read_text().splitlines() if x.strip()]
    push = load(ART/'PROTOCOL_PUSH.json')
    proposal_seal = load(ART/'PROPOSALS_SEAL.json')
    asset_seal = load(ART/'ASSET_SEAL.json')
    parse = lambda s: datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
    decode = [e for e in events if e.get('action') == 'pixel_decode_start']
    allowed_members = {'A', 'B_delta_D', 'B_delta_A'}
    for event in decode:
        stamp = parse(event['utc'])
        if stamp <= parse(push['utc']):
            raise ValueError('Pixel decode before verified protocol push')
        if event['stage'] == 'validation' and stamp <= parse(proposal_seal['utc']):
            raise ValueError('Validation decode before proposal seal')
        if event['stage'] == 'render' and stamp <= parse(asset_seal['utc']):
            raise ValueError('Render/final evaluation decode before accepted seal')
        if event['stage'] in ('construction', 'validation') and not set(event['response_members']) <= allowed_members:
            raise ValueError('Construction/validation decoded final C evidence')
    source = (HERE/'pipeline_io.py').read_text()
    return {'passed': True, 'event_log_sha256': sha(events_path), 'decode_event_count': len(decode),
            'protocol_remote_verified_utc': push['utc'], 'proposal_sealed_utc': proposal_seal['utc'],
            'accepted_sealed_utc': asset_seal['utc'],
            'member_scope_basis': 'Recorded member names plus reviewed pipeline_io selective np.load member access; strace sees archives, not individual NPZ members',
            'pipeline_io_sha256': hashlib.sha256(source.encode()).hexdigest()}


def verify_counts_and_no_refit(accepted, proposed):
    construction = load(ART/'CONSTRUCTION.json')
    validation = load(ART/'VALIDATION.json')
    proposal_paths = {p['persistent_id']: p for p in proposed['paths']}
    accepted_paths = {p['persistent_id']: p for p in accepted['paths']}
    verdict_ids = {p['persistent_id'] for p in validation['results'] if p['accepted']}
    if verdict_ids != set(accepted_paths):
        raise ValueError('Accepted asset identities differ from validation decisions')
    if construction['proposed'] != len(proposal_paths) or validation['proposed'] != len(proposal_paths):
        raise ValueError('Proposed count not derived consistently')
    if validation['accepted'] != len(accepted_paths) or validation['rejected'] != len(proposal_paths)-len(accepted_paths):
        raise ValueError('Accepted/rejected counters inconsistent')
    for identity, path in accepted_paths.items():
        if not np.array_equal(path['controls_xyz'], proposal_paths[identity]['controls_xyz']):
            raise ValueError('Accepted geometry was refitted after proposal seal')
        if path['topology'] != proposal_paths[identity]['topology']:
            raise ValueError('Accepted topology differs from sealed proposal')
    null = validation['null']
    matching = load(construction['diagnostics_path'])
    if sha(construction['diagnostics_path']) != construction['diagnostics_sha256']:
        raise ValueError('Construction diagnostic bytes changed')
    if not null['sufficient'] and null['status'] == 'PASS_REJECTED':
        raise ValueError('Insufficient null misreported as successful rejection')
    if null['accepted'] and null['scientific_go_valid']:
        raise ValueError('Null survivors ignored by scientific GO status')
    return {'proposed': len(proposal_paths), 'accepted': len(accepted_paths),
            'rejected': len(proposal_paths)-len(accepted_paths), 'accepted_geometry_exactly_proposed': True,
            'triplet_cycle_attempts': len(matching['attempts']),
            'actual_ray_triangulation_attempts': sum('triangulation' in item for item in matching['attempts']),
            'counter_qualification': 'Legacy triangulation_attempts field counts entry to triplet cycle check; actual ray calls require triangulation diagnostics',
            'null': {k: null[k] for k in ['status', 'sufficient', 'proposed', 'accepted', 'scientific_go_valid']}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--native-video', required=True)
    parser.add_argument('--telegram-video', required=True)
    parser.add_argument('--construction-trace', required=True)
    parser.add_argument('--validation-trace', required=True)
    parser.add_argument('--render-trace', required=True)
    parser.add_argument('--output', default=str(ART/'INDEPENDENT_VERIFICATION.json'))
    args = parser.parse_args()
    # Loading seals, before any source array decode, is mandatory.
    accepted, asset_check = verify_asset('ASSET')
    proposed, proposal_check = verify_asset('PROPOSALS')
    inputs = load(ART/'INPUTS.json')
    result = {'schema': 'mic-fixed3d-independent-verification-v1',
              'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'frozen': verify_frozen_inputs(), 'asset': asset_check, 'proposals': proposal_check,
              'chronology': verify_chronology(), 'counts': verify_counts_and_no_refit(accepted, proposed)}
    result['frames'], panels = verify_frames(inputs, accepted, proposed)
    result['fields'] = verify_fields(inputs)
    result['videos'] = [verify_video(args.native_video, 3200, panels), verify_video(args.telegram_video, 1600, panels)]
    result['scope'] = verify_scope({'construction': args.construction_trace,
                                    'validation': args.validation_trace,
                                    'render': args.render_trace}, inputs)
    if not result['scope']['passed']:
        raise ValueError('Scope audit failed: ' + repr(result['scope']['violations']))
    result['completed_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result['passed'] = True
    output = Path(args.output)
    output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: result[k] for k in ['passed', 'completed_utc']}))


if __name__ == '__main__':
    main()
