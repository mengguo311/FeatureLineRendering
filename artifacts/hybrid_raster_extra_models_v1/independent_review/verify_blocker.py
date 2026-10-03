#!/usr/bin/env python3
"""Independent CPU-only zero-scene audit; success never means scientific success.

Read only declared TRAIN metadata, candidate checkpoint headers/hashes, the prior
LOCK and its scientific sources. No renderer, image decoder or GPU import.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

F = [1, 14, 27, 41, 53, 67, 79, 93]
C = [7, 21, 33, 47, 59, 73, 86, 99]
SCENES = ['hotdog', 'materials', 'mic', 'ship']
LOCK_SHA256 = 'd5ec038e8ebc8a7160bc9e31ebb6ac8ce755fdbf1677a32ad55102a48c6a0926'
PRIOR = Path('/home/u00134/3dgs_line/hybrid_raster_evidence_v2')
EXTENSION = 'hybrid_raster_extra_models_v1'
VANILLA = {'x', 'y', 'z', 'opacity', 'scale_0', 'scale_1', 'scale_2',
           'rot_0', 'rot_1', 'rot_2', 'rot_3', 'f_dc_0', 'f_dc_1', 'f_dc_2'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for b in iter(lambda: stream.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def assess(inventory, manifest, production_files, source_checks):
    require(inventory.get('status') == 'BLOCKED_NO_USABLE_NEW_SCENES', 'not a zero-scene inventory blocker')
    require(inventory.get('requested_scene_order') == SCENES, 'inventory scene order differs')
    require(set(inventory.get('scenes', {})) == set(SCENES), 'inventory scene coverage differs')
    require(inventory.get('selected_scenes') == [] and manifest.get('selected_scenes') == [], 'selected scenes must be empty')
    require(manifest.get('scenes') == {}, 'camera manifest has selected scene cameras')
    require(manifest.get('F') == F and manifest.get('C') == C, 'deterministic camera splits differ')
    require(manifest.get('expected_production_frames') == 0, 'expected production frames must be zero')
    require(set(manifest.get('blocked_missing_scenes', [])) == set(SCENES), 'manifest missing-scene coverage differs')
    for scene, record in inventory['scenes'].items():
        require(not any(c.get('eligible') for c in record.get('checkpoint_candidates', [])),
                'eligible checkpoint contradicts zero inventory: ' + scene)
        require(bool(record.get('missing')), 'inventory lacks concrete missing input: ' + scene)
    require(not production_files, 'production artifacts contradict zero-scene blocker: ' + repr(production_files))
    for key in ['scientific_sources_unchanged', 'locked_recipe_hash_valid',
                'locked_parameter_hash_valid', 'locked_lock_hash_valid']:
        require(source_checks.get(key) is True, 'source/lock verification failed: ' + key)
    return {'status': 'BLOCKER_CONFIRMED', 'science_executed': False,
            'scientific_verdict': None, 'completed_frames': 0,
            'scope': 'bounded inventory and unchanged inheritance only; rendering/media/field validation not executed',
            'human_review': 'PENDING_NO_NEW_OUTPUTS'}


def audit_sources(root):
    lock_path = PRIOR / 'out/hybrid_raster_evidence_v2/LOCK.json'
    require(sha(lock_path) == LOCK_SHA256, 'prior LOCK byte hash differs')
    lock = json.loads(lock_path.read_text())
    sources = []
    for relative, expected in lock['config']['sources'].items():
        old, new = sha(PRIOR / relative), sha(root / relative)
        sources.append({'path': relative, 'locked_sha256': expected,
                        'prior_sha256': old, 'current_sha256': new, 'unchanged': old == new == expected})
    result = {
        'scientific_sources_unchanged': all(s['unchanged'] for s in sources),
        'locked_recipe_hash_valid': canonical(lock['normalization']['recipe']) == lock['normalization']['recipe_hash'],
        'locked_parameter_hash_valid': canonical({'config': lock['config'], 'normalization': lock['normalization']}) == lock['parameter_hash'],
        'locked_lock_hash_valid': canonical({k: v for k, v in lock.items() if k != 'lock_hash'}) == lock['lock_hash'],
        'lock_path': str(lock_path), 'lock_sha256': sha(lock_path), 'sources': sources,
        'inherited_normalization': lock['normalization'], 'parameter_hash': lock['parameter_hash'],
    }
    return result


def audit_inventory(inventory):
    rows = {}
    for scene in SCENES:
        record = inventory['scenes'][scene]
        meta_record = record['train_metadata']
        path = Path(meta_record['path'])
        require(path.name == 'transforms_train.json' and path.parent.name == scene,
                'metadata is not explicit TRAIN: ' + str(path))
        require(sha(path) == meta_record['sha256'], 'TRAIN metadata hash mismatch: ' + scene)
        meta = json.loads(path.read_text())
        require(math.isfinite(meta['camera_angle_x']) and 0 < meta['camera_angle_x'] < math.pi,
                'invalid TRAIN field of view: ' + scene)
        by_index = {}
        for fr in meta['frames']:
            p = Path(fr['file_path'])
            require(p.parent.name == 'train' and p.stem.startswith('r_'), 'non-TRAIN frame path')
            index = int(p.stem[2:])
            require(index not in by_index, 'duplicate TRAIN index')
            matrix = fr['transform_matrix']
            require(len(matrix) == 4 and all(len(row) == 4 for row in matrix), 'invalid camera matrix shape')
            require(all(math.isfinite(v) for row in matrix for v in row), 'nonfinite camera matrix')
            by_index[index] = fr
        require(len(by_index) == meta_record['frame_count'], 'TRAIN frame count mismatch')
        require(set(F + C) <= set(by_index), 'required TRAIN camera absent')
        candidates = []
        for item in record.get('checkpoint_candidates', []):
            checkpoint = Path(item['path'])
            require(checkpoint.name == 'point_cloud.ply', 'candidate is not a Gaussian checkpoint')
            require(sha(checkpoint) == item['sha256'], 'checkpoint hash mismatch')
            properties = []
            with checkpoint.open('rb') as stream:
                for _ in range(1024):
                    line = stream.readline(4096).decode('ascii').strip()
                    if line.startswith('property '):
                        properties.append(line.split()[-1])
                    if line == 'end_header':
                        break
                else:
                    raise ValueError('checkpoint header not bounded')
            missing = sorted(VANILLA - set(properties))
            require(bool(missing), 'candidate is vanilla-compatible; inventory blocker must be revisited')
            require(not item['eligible'] and bool(item['rejection_reason']), 'candidate rejection not explicit')
            candidates.append({'path': str(checkpoint), 'sha256': item['sha256'],
                               'missing_vanilla_properties_independent': missing})
        rows[scene] = {'train_sha256_verified': meta_record['sha256'], 'frame_count': len(by_index),
                       'F_C_indices_available': True, 'images_decoded': 0,
                       'candidate_checkpoint_rejections': candidates}
    return rows


def production_inventory(root):
    result = []
    suffixes = {'.png', '.jpg', '.jpeg', '.mp4', '.mov', '.mkv', '.npz', '.npy', '.exr', '.ply'}
    for branch in ['out', 'artifacts']:
        base = root / branch / EXTENSION
        if not base.exists():
            continue
        for directory, subdirs, files in os.walk(base, followlinks=False):
            for name in subdirs + files:
                require(not (Path(directory) / name).is_symlink(), 'extension output symlink is not allowed')
            for name in files:
                p = Path(directory) / name
                relative = p.relative_to(base)
                if p.suffix.lower() in suffixes or name in {'SEAL.json', 'SEAL.sha256'} or relative.parts[0] in {'frames', 'raw', 'media', 'calibration'}:
                    result.append(str(p.relative_to(root)))
    return sorted(result)


def audit_manifest_links(manifest, inventory_path, original_lock, expected_lock_sha):
    linked_inventory = manifest['inventory']
    require(Path(linked_inventory['path']).resolve() == Path(inventory_path).resolve(),
            'inventory path link differs from actual input')
    actual_inventory_sha = sha(inventory_path)
    require(linked_inventory['sha256'] == actual_inventory_sha, 'inventory manifest hash mismatch')
    inherited = manifest['inherited_lock']
    inherited_path = Path(inherited['path'])
    require(not inherited_path.is_symlink(), 'inherited lock must be a real frozen copy')
    inherited_sha = sha(inherited_path)
    original_sha = sha(original_lock)
    require(inherited['sha256'] == inherited_sha == original_sha == expected_lock_sha,
            'inherited lock copy or hash differs from original LOCK')
    return {'inventory_link_verified': True, 'inventory_sha256': actual_inventory_sha,
            'inherited_lock_copy_verified': True, 'inherited_lock_sha256': inherited_sha}


def audit_search_snapshot(search):
    """Replay only declared bounded filename enumeration, never candidate content."""
    root = Path(search['root'])
    require(not root.is_symlink(), 'UNDETERMINED: search root is a symlink')
    require(search['follow_symlinks'] is False, 'UNDETERMINED: unexpected symlink search policy')
    exists = root.is_dir()
    require(exists == search['exists'], 'UNDETERMINED: search root existence changed')
    names = set(search['pruned_directory_names'])
    prefixes = tuple(search['pruned_directory_prefixes'])
    maximum = search['max_directory_depth']
    require(isinstance(maximum, int) and 0 <= maximum <= 7, 'UNDETERMINED: unbounded search depth')
    pending = [(root, 0)] if exists else []
    actual, visited = [], 0
    while pending:
        directory, depth = pending.pop()
        visited += 1
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.is_symlink():
                    continue
                name = entry.name
                if entry.is_dir(follow_symlinks=False):
                    if depth < maximum and name not in names and not name.startswith(prefixes):
                        pending.append((Path(entry.path), depth + 1))
                elif entry.is_file(follow_symlinks=False):
                    lower = name.lower()
                    if 'test' in lower or 'mesh' in lower:
                        continue
                    if name in ('point_cloud.ply', 'cfg_args') or lower.endswith(('.pth', '.ckpt')) or 'asset' in lower:
                        actual.append(str(Path(entry.path)))
    actual = sorted(actual)
    expected = sorted(search['matched_files'])
    require(len(expected) == len(set(expected)), 'UNDETERMINED: duplicate inventory candidates')
    new = sorted(set(actual) - set(expected))
    absent = sorted(set(expected) - set(actual))
    require(not new and not absent,
            'UNDETERMINED: filename snapshot differs; unregistered=' + repr(new) + '; disappeared=' + repr(absent))
    return {'root': str(root), 'max_directory_depth': maximum,
            'matched_files_identical': True, 'matched_file_count': len(actual),
            'visited_directory_count': visited,
            'frozen_visited_directory_count': search.get('visited_directory_count'),
            'matched_files': actual, 'candidate_contents_opened': 0}


def audit_canonical_missing(scenes):
    result = {}
    for scene, record in scenes.items():
        path = Path(record['canonical_expected_checkpoint_path'])
        require(record['canonical_expected_checkpoint_exists'] is False,
                'canonical checkpoint is not registered missing: ' + scene)
        require(not path.exists() and not path.is_symlink(),
                'canonical checkpoint appeared; inventory must be revised: ' + str(path))
        result[scene] = {'path': str(path), 'exists': False, 'content_opened': False}
    return result


def audit_searches(inventory):
    expected_roots = {
        '/home/u00134/cglib/outputs': 6,
        '/home/u00134/cglib/logs': 5,
        '/home/u00134/cglib/data/full': 2,
        '/home/u00134/3dgs_line/tier1/out': 7,
        '/home/u00134/3dgs_line/FeatureLineRendering/real_3dgs/outputs': 6,
        '/home/u00134/3dgs_line/FeatureLineRendering/tier1/out': 6,
    }
    searches = inventory['searches']
    require(len(searches) == len(expected_roots), 'UNDETERMINED: bounded search root count differs')
    require({s['root']: s['max_directory_depth'] for s in searches} == expected_roots,
            'UNDETERMINED: bounded search roots/depths differ')
    for search in searches:
        require({'test', 'TEST', 'mesh', 'meshes'} <= set(search['pruned_directory_names']),
                'UNDETERMINED: forbidden directory pruning missing')
    return [audit_search_snapshot(search) for search in searches]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    allowed = root / 'artifacts' / EXTENSION / 'independent_review'
    require(args.output.resolve().is_relative_to(allowed), 'output must remain in independent_review')
    inventory = json.loads(args.inventory.read_text())
    manifest = json.loads(args.manifest.read_text())
    links = audit_manifest_links(manifest, args.inventory, PRIOR / 'out/hybrid_raster_evidence_v2/LOCK.json', LOCK_SHA256)
    search_checks = audit_searches(inventory)
    canonical_missing = audit_canonical_missing(inventory['scenes'])
    sources = audit_sources(root)
    production = production_inventory(root)
    result = assess(inventory, manifest, production, sources)
    result.update({'inventory_path': str(args.inventory), 'inventory_sha256': sha(args.inventory),
                   'manifest_path': str(args.manifest), 'manifest_sha256': sha(args.manifest),
                   'source_checks': sources, 'independent_inventory_checks': audit_inventory(inventory),
                   'manifest_link_checks': links, 'bounded_filename_rechecks': search_checks,
                   'canonical_checkpoint_absence_checks': canonical_missing,
                   'production_artifacts': production,
                   'counts': {'frames': 0, 'frame_seals': 0, 'raw_fields': 0, 'images': 0, 'videos': 0,
                              'native_calibrations': 0, 'unique_arc_poses_rendered': 0},
                   'not_applicable': ['same-state A/B/C', 'finite contributor exports', 'raw alpha*T original IDs',
                                      'camera/render calibration', 'video full decode and distinct frames'],
                   'access_scope': 'This verifier independently re-enumerates the six frozen roots at identical depth/pruning/matching, stats canonical missing checkpoint paths, and reads TRAIN metadata, declared Gaussian checkpoints and source/lock JSON only. Unregistered filename matches reject before candidate content is read.'})
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    print(json.dumps({'status': result['status'], 'science_executed': False, 'output': str(args.output)}))


if __name__ == '__main__':
    main()
