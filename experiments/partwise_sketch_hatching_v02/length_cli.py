"""Absolute base length editing on the saved 434-path whole-lamp asset.

Only the selected 75 original base seeds are walked, with both cross layers.
Cold regeneration needs the mesh, the selected-seed recipe and 284 retained
non-target paths. It never reads a saved target curve or generates discarded
curves. All new bundles are restricted to the authorized unit010 directory.
"""
import time

PROCESS_ENTRY = time.perf_counter()

from common import *
import argparse
import copy
import math
import re
import shutil
from PIL import Image
from asset_cli import load_asset, validate_azimuths
from renderer import render

UNIT = OUT.parent / 'unit_010'
VIEWS = [30, 120, 210, 300]
SCHEMA = 'base_length_recipe_v1'
MESH_SHA256 = 'f8de0de7f1b8199dd3a8e3c1045dddaebc1a71a9419d8625665c17ce869a9d08'


def length_value(value):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError('length must be a world-space distance, not bool')
    value = float(value)
    if not math.isfinite(value) or not .06 <= value <= .24:
        raise ValueError('absolute length must be finite in [.06,.24] world units')
    return value


def destination(value):
    path = Path(value).resolve()
    if path == UNIT or not path.is_relative_to(UNIT):
        raise ValueError('output must be a new directory below authorized unit010')
    if path.exists():
        raise FileExistsError(path)
    return path


def revision(strokes):
    h = hashlib.sha256()
    for stroke in sorted(strokes, key=lambda s: s['id']):
        h.update(stroke['id'].encode())
        h.update(np.asarray([stroke['part']], np.int64).tobytes())
        h.update(np.asarray([stroke['ink']], np.float64).tobytes())
        h.update(np.asarray(stroke['faces'], np.int32).tobytes())
        h.update(np.asarray(stroke['bary'], np.float64).tobytes())
    return h.hexdigest()


def generator_hashes():
    here = Path(__file__).resolve().parent
    paths = {name: here / name for name in
             ('length_cli.py', 'common.py', 'asset_cli.py', 'renderer.py')}
    paths.update({'legacy/' + name: LEGACY / name
                  for name in ('core.py', 'core_walk_v2.py')})
    return {name: sha(path) for name, path in paths.items()}


def bound_file(base, item):
    path = Path(item['path'])
    if not path.is_absolute():
        path = base / path
    path = path.resolve(strict=True)
    if not path.is_file() or sha(path) != item['sha256']:
        raise ValueError('recipe dependency SHA mismatch')
    return path


def seed_samples(mesh):
    """Exactly the original sampler sequence; no path integration here."""
    rng = np.random.default_rng(np.random.SeedSequence([1729, 3]))
    candidates = np.flatnonzero(mesh['parts'] == 3)
    probability = mesh['areas'][candidates]
    probability = probability / probability.sum()
    for index in range(150):
        face = int(rng.choice(candidates, p=probability))
        q = rng.random(2)
        square_root = np.sqrt(q[0])
        bary = np.array([1-square_root, square_root*(1-q[1]), square_root*q[1]])
        yield index, face, bary


def selected_domain(strokes):
    target = [s for s in strokes if s['part'] == 3]
    by_id = {s['id']: s for s in target}
    if len(target) != 150 or len(by_id) != 150:
        raise ValueError('exactly 150 unique selected base paths required')
    indices = set()
    for sid in by_id:
        match = re.fullmatch(r'p3:seed(\d{4}):layer([01])', sid)
        if match is None or not 0 <= int(match[1]) < 150:
            raise ValueError('invalid original base seed/layer ID')
        indices.add(int(match[1]))
    expected = {f'p3:seed{index:04d}:layer{layer}'
                for index in indices for layer in (0, 1)}
    if len(indices) != 75 or set(by_id) != expected:
        raise ValueError('selected base must contain 75 complete two-layer seed pairs')
    return sorted(indices), by_id


def validate_recipe(recipe):
    if (recipe.get('schema') != SCHEMA or recipe.get('part') != 3
            or recipe.get('style') != 'mixed'):
        raise ValueError('unsupported base length recipe')
    if recipe.get('generator_sha256') != generator_hashes():
        raise ValueError('generator/dependency SHA mismatch')
    if recipe.get('numpy_version') != np.__version__:
        raise ValueError('NumPy version mismatch')
    length_value(recipe['length_world'])
    if (recipe.get('seed') != 1729 or recipe.get('original_seed_count') != 150
            or recipe.get('selected_count') != 150
            or recipe.get('step_world') != .015 or recipe.get('angle_deg') != 0.):
        raise ValueError('recipe outside original selected base generator domain')
    indices = recipe.get('selected_seed_indices')
    if (not isinstance(indices, list) or len(indices) != 75
            or any(type(i) is not int or not 0 <= i < 150 for i in indices)
            or indices != sorted(set(indices))):
        raise ValueError('recipe requires 75 sorted unique original seed indices')
    inks = recipe.get('selected_stroke_inks')
    expected = {f'p3:seed{index:04d}:layer{layer}'
                for index in indices for layer in (0, 1)}
    if (not isinstance(inks, dict) or set(inks) != expected
            or any(isinstance(v, bool) or not math.isfinite(float(v))
                   or not 0 <= float(v) <= 1 for v in inks.values())):
        raise ValueError('recipe requires finite inks for every selected layer ID')
    return indices


def generate(mesh, recipe):
    """Walk selected paths directly, preserving the original sampler and inks."""
    selected = set(validate_recipe(recipe))
    length = length_value(recipe['length_world'])
    strokes = []
    for index, face, bary in seed_samples(mesh):
        if index not in selected:
            continue
        for layer in (0, 1):
            audits = [{}, {}]
            fa, ba = walker.walk(mesh, face, bary, 3, 'mixed', layer, 0.,
                                 length/2, .015, -1, audits[0])
            fb, bb = walker.walk(mesh, face, bary, 3, 'mixed', layer, 0.,
                                 length/2, .015, 1, audits[1])
            sid = f'p3:seed{index:04d}:layer{layer}'
            strokes.append(dict(id=sid, part=3, style='mixed', angle=0., layer=layer,
                faces=np.asarray(fa[::-1]+fb[1:], np.int32),
                bary=np.asarray(ba[::-1]+bb[1:]),
                ink=float(recipe['selected_stroke_inks'][sid]),
                seed_face=face, seed_bary=bary.copy(), walk_audit=audits))
    return strokes


def detached_manifest(manifest):
    """A recipe belongs to its bundle; never carry a stale inherited pointer."""
    result = copy.deepcopy(manifest)
    result.pop('recipe', None)
    result.pop('path_lineage', None)
    return result


def make_recipe(manifest, files, mesh, strokes, cfg, length, source):
    length = length_value(length)
    if ({p: sum(s['part'] == p for s in strokes) for p in (1, 2, 3)}
            != {1: 260, 2: 24, 3: 150} or len({s['id'] for s in strokes}) != 434
            or sha(files['mesh']) != MESH_SHA256):
        raise ValueError('named 434-path lamp with 260shade/24stem/150base required')
    if (cfg.get('seed') != 1729 or cfg['strokes']['step_world'] != .015
            or cfg.get('density_by_part') != {'2': .5}):
        raise ValueError('frozen seed1729/step.015/stem density.5 configuration required')
    indices, by_id = selected_domain(strokes)
    for index, face, bary in seed_samples(mesh):
        if index not in indices:
            continue
        for layer in (0, 1):
            sid = f'p3:seed{index:04d}:layer{layer}'
            stroke = by_id[sid]
            if not np.any((stroke['faces'] == face)
                          & np.all(np.abs(stroke['bary']-bary) <= 1e-12, axis=1)):
                raise ValueError('source seed/anchor mismatch: ' + sid)
    metadata = detached_manifest(manifest)
    # A cold recipe embeds metadata only: it carries no target-path file pointer.
    for key in ('mesh', 'strokes', 'config'):
        metadata.pop(key, None)
    return dict(schema=SCHEMA, part=3, style='mixed', seed=1729,
        original_seed_count=150, selected_count=150, selected_seed_indices=indices,
        selected_stroke_inks={sid: float(by_id[sid]['ink']) for sid in sorted(by_id)},
        length_world=length, step_world=.015, angle_deg=0.,
        semantics='Absolute requested full path length in world units, centered on original seed; physical/part/field terminations may shorten it',
        generation_scope='150 sampler draws, 75 selected seeds, 150 selected paths, 300 half-walks; no unselected paths generated',
        generator_sha256=generator_hashes(), numpy_version=np.__version__,
        baseline_manifest=metadata,
        lineage=dict(parent_asset_sha256=sha(source),
            parent_strokes_sha256=sha(files['strokes']),
            parent_target_revision=revision(list(by_id.values())),
            non_target_revision=revision([s for s in strokes if s['part'] != 3]),
            target_seed_identity='original per-part area-sampled seed index + layer; paired75 selection retained'))


def read_recipe(path):
    path = Path(path).resolve(strict=True)
    recipe = json.loads(path.read_text())
    validate_recipe(recipe)
    files = {key: bound_file(path.parent, recipe[key])
             for key in ('mesh', 'retained', 'config')}
    if sha(files['mesh']) != MESH_SHA256:
        raise ValueError('recipe mesh is outside frozen lamp domain')
    with np.load(files['mesh'], allow_pickle=False) as data:
        mesh = core.finalize_mesh(data['vertices'], data['faces'], data['parts'])
    kept = load_strokes(files['retained'])
    if (len(kept) != 284 or len({s['id'] for s in kept}) != 284
            or {p: sum(s['part'] == p for s in kept) for p in (1, 2, 3)}
            != {1: 260, 2: 24, 3: 0}):
        raise ValueError('cold retained asset requires only 260shade and 24stem paths')
    if revision(kept) != recipe['lineage']['non_target_revision']:
        raise ValueError('retained revision mismatch')
    cfg = json.loads(files['config'].read_text())
    if (cfg['strokes']['length_by_part']['3'] != recipe['length_world']
            or cfg['strokes']['step_world'] != .015 or cfg.get('seed') != 1729
            or cfg.get('density_by_part') != {'2': .5}):
        raise ValueError('recipe/config base length or generator domain mismatch')
    if any(key in recipe['baseline_manifest']
           for key in ('recipe', 'path_lineage', 'mesh', 'strokes', 'config')):
        raise ValueError('baseline metadata must not contain inherited artifact bindings')
    return recipe, files, mesh, kept, cfg


def execute(args):
    output = destination(args.output)
    views = validate_azimuths(args.azimuths)
    output.mkdir(parents=True, exist_ok=False)
    try:
        return execute_new(args, output, views)
    except Exception as error:
        write_json(output / 'FAILURE.json', dict(operation=args.operation,
            error_type=type(error).__name__, message=str(error),
            elapsed_seconds=time.perf_counter()-PROCESS_ENTRY,
            partial_outputs_retained=True))
        raise


def execute_new(args, output, views):
    recipe = None
    regeneration_seconds = 0.
    regenerated_parts = []
    if args.operation == 'regenerate':
        source = Path(args.recipe).resolve()
        recipe, files, mesh, kept, cfg = read_recipe(source)
        meshfile = files['mesh']
        started = time.perf_counter()
        base = generate(mesh, recipe)
        regeneration_seconds = time.perf_counter()-started
        regenerated_parts = [3]
        if revision(base) != recipe['lineage']['target_path_revision']:
            raise ValueError('regenerated target revision mismatch')
        strokes = sorted(kept+base, key=lambda s: s['id'])
        manifest = detached_manifest(recipe['baseline_manifest'])
    else:
        source = ((Path(args.bundle) / 'asset.json') if args.operation == 'replay'
                  else Path(args.asset)).resolve()
        manifest, files, mesh, strokes, cfg = load_asset(source)
        meshfile = files['mesh']
        kept = [s for s in strokes if s['part'] != 3]
        if args.operation == 'edit':
            if args.part != 'base':
                raise ValueError('this operation supports base only')
            recipe = make_recipe(manifest, files, mesh, strokes, cfg,
                                 args.length_world, source)
            started = time.perf_counter()
            base = generate(mesh, recipe)
            regeneration_seconds = time.perf_counter()-started
            regenerated_parts = [3]
            recipe['lineage']['target_path_revision'] = revision(base)
            strokes = sorted(kept+base, key=lambda s: s['id'])
            cfg = copy.deepcopy(cfg)
            cfg['strokes']['length_by_part']['3'] = recipe['length_world']
        elif args.operation == 'replay' and 'recipe' in manifest:
            recipe_path = bound_file(source.parent, manifest['recipe'])
            candidate = json.loads(recipe_path.read_text())
            if candidate.get('schema') == SCHEMA:
                recipe, recipe_files, _, recipe_kept, _ = read_recipe(recipe_path)
                if (sha(files['mesh']) != sha(recipe_files['mesh'])
                        or sha(files['config']) != sha(recipe_files['config'])
                        or revision(kept) != revision(recipe_kept)
                        or revision([s for s in strokes if s['part'] == 3])
                        != recipe['lineage']['target_path_revision']):
                    raise ValueError('saved asset and recipe bindings disagree')
    record = dict(operation=args.operation, source=str(source), source_sha256=sha(source),
        regenerated_parts=regenerated_parts, regeneration_seconds=regeneration_seconds,
        regenerated_path_count=150 if regenerated_parts else 0,
        saved_path_count=len(strokes),
        counts_by_part={str(p): sum(s['part'] == p for s in strokes) for p in (1, 2, 3)},
        length_world=cfg['strokes']['length_by_part']['3'], per_view_seconds={},
        timing_scope='module entry includes imports, input hashes/loading, regeneration, saving and CPU render; external receipt includes interpreter startup',
        inherited_verdict=manifest['verdict_metadata'],
        promotion='NONE; inherited whole-object visual NO_GO retained')
    shutil.copyfile(meshfile, output / 'mesh.npz')
    core.save_strokes(output / 'strokes.npz', strokes)
    write_json(output / 'config.json', cfg)
    bundled = detached_manifest(manifest)
    bundled['name'] = 'selected434_base_length' + str(record['length_world'])
    for key in ('mesh', 'strokes', 'config'):
        filename = key + ('.json' if key == 'config' else '.npz')
        bundled[key] = dict(path=filename, sha256=sha(output / filename))
    bundled['operation_metadata'] = dict(operation=args.operation,
        scope='base-only absolute length control on complete selected434 GT lamp',
        length_world=record['length_world'], retained_non_target_path_count=len(kept),
        generated_part_ids=regenerated_parts,
        scientific_status='inherited verdict_metadata is historical; no automatic promotion')
    if recipe is not None:
        core.save_strokes(output / 'retained.npz', kept)
        for key, filename in (('mesh', 'mesh.npz'), ('retained', 'retained.npz'),
                              ('config', 'config.json')):
            recipe[key] = dict(path=filename, sha256=sha(output / filename))
        write_json(output / 'recipe.json', recipe)
        bundled['recipe'] = dict(path='recipe.json', sha256=sha(output / 'recipe.json'))
        bundled['path_lineage'] = copy.deepcopy(recipe['lineage'])
        record['lineage'] = copy.deepcopy(recipe['lineage'])
    write_json(output / 'asset.json', bundled)
    folder = output / 'renders'
    folder.mkdir()
    for index, azimuth in enumerate(views):
        started = time.perf_counter()
        result = render(mesh, strokes, cfg, azimuth=azimuth, elevation=20, distance=4.5)
        seconds = time.perf_counter()-started
        prefix = folder / f'{azimuth:03}'
        Image.fromarray(np.uint8(np.rint(result['image']*255))).save(prefix.with_suffix('.png'))
        if index == 0:
            record['command_to_first_preview_seconds'] = time.perf_counter()-PROCESS_ENTRY
        np.savez_compressed(prefix.with_suffix('.npz'),
            **{key: result[key] for key in ('image', 'hatch', 'contours', 'rings', 'depth', 'parts')})
        write_json(prefix.with_suffix('.json'), dict(camera=result['camera'],
            diagnostics=result['diagnostics'], render_seconds=seconds))
        record['per_view_seconds'][str(azimuth)] = seconds
    record['command_to_all_previews_seconds'] = time.perf_counter()-PROCESS_ENTRY
    write_json(output / 'EDIT.json', record)
    return record


def parser():
    ap = argparse.ArgumentParser(description=__doc__)
    commands = ap.add_subparsers(dest='operation', required=True)
    for name in ('preview', 'edit', 'regenerate', 'replay'):
        command = commands.add_parser(name)
        if name == 'regenerate':
            command.add_argument('--recipe', required=True)
        elif name == 'replay':
            command.add_argument('--bundle', required=True)
        else:
            command.add_argument('--asset', required=True)
        command.add_argument('--output', required=True)
        command.add_argument('--azimuths', nargs='+', type=int, default=VIEWS)
        if name == 'edit':
            command.add_argument('--part', choices=['base'], required=True)
            command.add_argument('--length-world', type=float, required=True)
    return ap


def main():
    try:
        record = execute(parser().parse_args())
    except Exception as error:
        print(json.dumps(dict(error_type=type(error).__name__, message=str(error))),
              file=sys.stderr)
        return 1
    print(json.dumps(native(record), allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
