"""Explicit saved-asset width editing and CPU previews for the unit005 slice.

The saved paths are authoritative. This CLI never regenerates them from the
inherited generator configuration, whose counts can describe older assets.
All output is restricted to new directories within the authorized unit005.
"""
import time

PROCESS_ENTRY = time.perf_counter()

import os

os.environ['CUDA_VISIBLE_DEVICES'] = ''
for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
             'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.sched_setaffinity(0, [0, 1])

import argparse
import copy
import json
import math
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True

import numpy as np
from PIL import Image

from common import core, load_strokes, native, sha, write_json
from renderer import render


UNIT = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_005')
SCHEMA = 'partwise_asset_v1'
PARTS = {'shade': 1, 'stem': 2, 'base': 3}
DEFAULT_AZIMUTHS = (30, 120, 210, 300)


def positive_width(value):
    """Validate against the bounded renderer before any output is created."""
    width = float(value)
    if not math.isfinite(width) or not 0 < width <= 64:
        raise ValueError('width must be a finite pixel diameter in (0, 64]')
    return width


def output_path(path):
    output = Path(path).resolve()
    if not output.is_relative_to(UNIT.resolve()) or output == UNIT.resolve():
        raise ValueError('output must be a new directory below authorized unit005')
    if output.exists():
        raise FileExistsError(f'output already exists: {output}')
    return output


def validate_azimuths(values):
    values = list(values)
    if not values or any(not math.isfinite(float(v)) or float(v) != int(v)
                         or not 0 <= int(v) < 360 for v in values):
        raise ValueError('azimuths must be integer degrees in [0, 360)')
    result = [int(v) for v in values]
    if len(set(result)) != len(result):
        raise ValueError('azimuths must be unique')
    return result


def read_asset(manifest_path):
    """Resolve only explicitly named, hash-bound inputs; never use legacy OUT."""
    manifest_path = Path(manifest_path).resolve(strict=True)
    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, dict) or manifest.get('schema') != SCHEMA:
        raise ValueError(f'asset manifest schema must be {SCHEMA}')
    if not isinstance(manifest.get('name'), str) or not manifest['name'].strip():
        raise ValueError('asset manifest requires a nonempty name')
    if not isinstance(manifest.get('provenance'), dict):
        raise ValueError('asset manifest requires provenance metadata')
    verdict = manifest.get('verdict_metadata')
    required = ('source_unit', 'scientific_verdict', 'claim_status', 'blockers')
    if not isinstance(verdict, dict) or any(key not in verdict for key in required):
        raise ValueError('asset manifest requires complete inherited verdict metadata')
    if (not isinstance(verdict['source_unit'], str)
            or not isinstance(verdict['scientific_verdict'], str)
            or not isinstance(verdict['claim_status'], dict)
            or not isinstance(verdict['blockers'], list)):
        raise ValueError('invalid inherited verdict metadata types')
    paths = {}
    for name in ('mesh', 'strokes', 'config'):
        item = manifest.get(name)
        if not isinstance(item, dict) or not isinstance(item.get('path'), str):
            raise ValueError(f'asset manifest requires explicit {name} path')
        digest = item.get('sha256')
        if (not isinstance(digest, str) or len(digest) != 64
                or any(c not in '0123456789abcdef' for c in digest)):
            raise ValueError(f'asset manifest requires valid {name} SHA256')
        path = Path(item['path'])
        if not path.is_absolute():
            path = manifest_path.parent / path
        path = path.resolve(strict=True)
        if not path.is_file() or sha(path) != digest:
            raise ValueError(f'{name} input does not match manifest SHA256: {path}')
        paths[name] = path
    return manifest, paths


def load_asset(manifest_path):
    manifest, paths = read_asset(manifest_path)
    config = json.loads(paths['config'].read_text())
    if not isinstance(config, dict):
        raise ValueError('config must be a JSON object')
    widths = config.get('widths_by_part', {})
    for part in PARTS.values():
        positive_width(widths.get(str(part), widths.get(part, 1.)))
    with np.load(paths['mesh'], allow_pickle=False) as data:
        mesh = core.finalize_mesh(data['vertices'], data['faces'], data['parts'])
    strokes = load_strokes(paths['strokes'])
    if not strokes or len({s['id'] for s in strokes}) != len(strokes):
        raise ValueError('saved asset requires nonempty, unique stroke IDs')
    if any(s['part'] not in PARTS.values() for s in strokes):
        raise ValueError('saved asset contains an unsupported part ID')
    return manifest, paths, mesh, strokes, config


def apply_width_edit(config, part, width):
    if part not in PARTS.values():
        raise ValueError('part must be shade, stem or base')
    width = positive_width(width)
    changed = copy.deepcopy(config)
    changed.setdefault('widths_by_part', {})[str(part)] = width
    return changed


def parser():
    argument_parser = argparse.ArgumentParser(description=__doc__)
    commands = argument_parser.add_subparsers(dest='operation', required=True)
    for name in ('preview', 'edit', 'replay'):
        command = commands.add_parser(name)
        if name == 'replay':
            command.add_argument('--bundle', type=Path, required=True,
                                 help='saved bundle directory containing asset.json')
        else:
            command.add_argument('--asset', type=Path, required=True,
                                 help='explicit hash-bound asset manifest')
        command.add_argument('--output', type=Path, required=True)
        command.add_argument('--azimuths', nargs='+', type=int,
                             default=list(DEFAULT_AZIMUTHS))
        if name == 'edit':
            command.add_argument('--part', choices=list(PARTS), required=True)
            command.add_argument('--width', type=float, required=True)
    return argument_parser


def preflight(args):
    output = output_path(args.output)
    azimuths = validate_azimuths(args.azimuths)
    part = PARTS[args.part] if args.operation == 'edit' else None
    width = positive_width(args.width) if args.operation == 'edit' else None
    asset_path = (args.bundle / 'asset.json' if args.operation == 'replay'
                  else args.asset)
    loaded = load_asset(asset_path)
    if args.operation == 'edit' and not any(s['part'] == part for s in loaded[3]):
        raise ValueError('edited part has no saved strokes')
    return output, azimuths, part, width, asset_path.resolve(), loaded


def execute(args):
    output, azimuths, part, width, source, loaded = preflight(args)
    manifest, paths, mesh, strokes, config = loaded
    changed = (apply_width_edit(config, part, width) if args.operation == 'edit'
               else copy.deepcopy(config))
    before_widths = {str(p): float(config.get('widths_by_part', {}).get(str(p), 1.))
                     for p in PARTS.values()}
    after_widths = {str(p): float(changed.get('widths_by_part', {}).get(str(p), 1.))
                    for p in PARTS.values()}
    record = dict(operation=args.operation, part=part,
                  part_name=args.part if args.operation == 'edit' else None,
                  width=width, before=before_widths, after=after_widths,
                  regenerated_parts=[], asset_name=manifest['name'],
                  source_manifest=str(source), source_manifest_sha256=sha(source),
                  source_input_sha256={key: manifest[key]['sha256']
                                       for key in ('mesh', 'strokes', 'config')},
                  source_verdict_metadata=copy.deepcopy(manifest['verdict_metadata']),
                  verdict_metadata=copy.deepcopy(manifest['verdict_metadata']),
                  promotion='NONE; inherited scientific verdict is unchanged',
                  saved_path_count=len(strokes),
                  saved_path_counts_by_part={str(p): sum(s['part'] == p for s in strokes)
                                             for p in PARTS.values()},
                  azimuths=azimuths, elevation=20, distance=4.5,
                  timing_scope='Python module entry through actual loading, saving and CPU previews; interpreter startup excluded',
                  per_view_seconds={})
    output.mkdir(parents=True, exist_ok=False)
    try:
        shutil.copyfile(paths['mesh'], output / 'mesh.npz')
        shutil.copyfile(paths['strokes'], output / 'strokes.npz')
        write_json(output / 'config.json', changed)
        bundled = copy.deepcopy(manifest)
        for key, filename in (('mesh', 'mesh.npz'), ('strokes', 'strokes.npz'),
                              ('config', 'config.json')):
            bundled[key] = dict(path=filename, sha256=sha(output / filename))
        write_json(output / 'asset.json', bundled)
        render_folder = output / 'renders'
        render_folder.mkdir()
        for index, azimuth in enumerate(azimuths):
            start = time.perf_counter()
            result = render(mesh, strokes, changed, azimuth=azimuth,
                            elevation=20, distance=4.5)
            render_seconds = time.perf_counter() - start
            prefix = render_folder / f'{azimuth:03}'
            Image.fromarray(np.uint8(np.rint(result['image'] * 255))).save(prefix.with_suffix('.png'))
            if index == 0:
                record['command_to_first_preview_seconds'] = time.perf_counter() - PROCESS_ENTRY
            np.savez_compressed(prefix.with_suffix('.npz'),
                                **{key: result[key] for key in
                                   ('image', 'hatch', 'contours', 'rings', 'depth', 'parts')})
            write_json(prefix.with_suffix('.json'), dict(camera=result['camera'],
                        diagnostics=result['diagnostics'], render_seconds=render_seconds))
            record['per_view_seconds'][str(azimuth)] = dict(render=render_seconds,
                        render_and_save=time.perf_counter() - start)
        record['command_to_all_previews_seconds'] = time.perf_counter() - PROCESS_ENTRY
        record['output_asset_sha256'] = sha(output / 'asset.json')
        record['process_entry_to_receipt_seconds'] = time.perf_counter() - PROCESS_ENTRY
        write_json(output / 'EDIT.json', record)
        return record
    except Exception as error:
        write_json(output / 'FAILURE.json', dict(operation=args.operation,
                   error_type=type(error).__name__, message=str(error),
                   elapsed_seconds=time.perf_counter() - PROCESS_ENTRY,
                   partial_outputs_retained=True,
                   verdict_metadata=manifest['verdict_metadata']))
        raise


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        record = execute(args)
    except Exception as error:
        print(json.dumps(dict(error_type=type(error).__name__, message=str(error)),
                         allow_nan=False), file=sys.stderr)
        return 1
    print(json.dumps(native(record), allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
