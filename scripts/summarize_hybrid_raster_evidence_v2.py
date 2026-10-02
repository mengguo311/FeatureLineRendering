#!/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python
"""Summarize sealed pixel diagnostics without opening NPZ or image payloads.

This reporting-only entrypoint does not change the frozen renderer/readout and
does not provide a visual quality or scientific GO verdict.
"""
import argparse
import datetime
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.hybrid_raster_io import atomic_json, canonical_hash, hash_file
from src.hybrid_raster_stage import SCENES, frame_specs, read_inputs

OUT = ROOT / 'out/hybrid_raster_evidence_v2'
ART = ROOT / 'artifacts/hybrid_raster_evidence_v2'


def read_json(path):
    def reject(value):
        raise ValueError('nonfinite JSON number: ' + value)
    return json.loads(Path(path).read_text(), parse_constant=reject)


def numeric_summary(values):
    values = [value for value in values if value is not None]
    if not values:
        return dict(count=0, sum=None, mean=None, min=None, max=None)
    if any(not math.isfinite(value) for value in values):
        raise ValueError('nonfinite diagnostic statistic')
    return dict(count=len(values), sum=sum(values), mean=sum(values) / len(values),
                min=min(values), max=max(values))


def aggregate_tree(records):
    """Frame-level sum/mean/range for each numeric leaf; no invented zeros."""
    if not records:
        return None
    result = {}
    for key in sorted(set().union(*(record.keys() for record in records))):
        values = [record[key] for record in records if key in record]
        if values and all(isinstance(value, dict) for value in values):
            result[key] = aggregate_tree(values)
        elif all(value is None or isinstance(value, (int, float)) for value in values):
            result[key] = numeric_summary(values)
        else:
            raise ValueError('nonnumeric diagnostic leaf: ' + key)
    return result


def aggregate_raw(records):
    if not records:
        return None
    result = {}
    for key in ('alpha', 'top4_coverage', 'normal_coherence', 'depth_variance'):
        fields = [record[key] for record in records]
        nonempty = [field for field in fields if field['count'] > 0]
        count = sum(field['count'] for field in nonempty)
        result[key] = dict(
            pixel_count=count,
            pixel_weighted_mean=sum(field['count'] * field['mean'] for field in nonempty) / count if count else None,
            pixel_min=min(field['min'] for field in nonempty) if count else None,
            pixel_max=max(field['max'] for field in nonempty) if count else None,
            frame_means=numeric_summary([field['mean'] for field in nonempty]),
            frame_quantiles={q: numeric_summary([field[q] for field in nonempty]) for q in ('p05', 'p50', 'p95')},
            quantile_qualification='逐帧分位数的汇总；不是跨帧全部像素的 pooled quantile。')
    return result


def seal_metadata(frame):
    """Verify seal envelope and paths; selected JSON payloads are hashed below."""
    if frame.is_symlink() or not frame.is_dir():
        raise ValueError('frame is not a real directory')
    path = frame / 'SEAL.json'
    if hash_file(path) != (frame / 'SEAL.sha256').read_text().strip():
        raise ValueError('SEAL checksum mismatch')
    seal = read_json(path)
    if seal.get('schema') != 'hybrid-raster-frame-v1':
        raise ValueError('unknown frame seal schema')
    if canonical_hash(seal['context']) != seal['context_sha256']:
        raise ValueError('seal context hash mismatch')
    for relative in seal['files']:
        rel = Path(relative)
        if rel.is_absolute() or '..' in rel.parts:
            raise ValueError('unsafe inventory path')
        target = frame / rel
        if target.is_symlink() or not target.is_file():
            raise ValueError('sealed output file missing or symlink: ' + relative)
    return seal


def verified_json_payload(frame, seal, filename):
    if hash_file(frame / filename) != seal['files'].get(filename):
        raise ValueError('sealed JSON checksum mismatch: ' + filename)
    return read_json(frame / filename)


def inspect_frame(spec, inputs, group, parameter_hash):
    frame = OUT / group / spec['scene'] / spec['key']
    record = dict(scene=spec['scene'], split=spec['split'], key=spec['key'], directory=str(frame))
    if not frame.exists():
        return {**record, 'status': 'MISSING', 'reason': '预定义帧尚无已发布目录', 'diagnostics': None}, None
    try:
        seal = seal_metadata(frame)
        context = seal['context']
        if context['scene'] != spec['scene'] or context['key'] != spec['key']:
            raise ValueError('sealed scene/frame identity mismatch')
        if context['camera_hash'] != canonical_hash(spec['camera']) or context['camera'] != spec['camera']:
            raise ValueError('sealed camera differs from exact preregistered pose')
        if context['checkpoint_sha256'] != inputs['scenes'][spec['scene']]['checkpoint']['sha256']:
            raise ValueError('sealed checkpoint differs from frozen input')
        if parameter_hash is not None and context['parameter_hash'] != parameter_hash:
            raise ValueError('sealed parameter hash differs from reporting normalization')
        diagnostics = verified_json_payload(frame, seal, 'diagnostics.json')
        verified_json_payload(frame, seal, 'camera.json')
        for key in ('camera_hash', 'parameter_hash'):
            if diagnostics[key] != context[key]:
                raise ValueError('diagnostic context mismatch: ' + key)
        if diagnostics['scene'] != spec['scene'] or diagnostics['frame'] != spec['key'] or diagnostics['split'] != spec['split']:
            raise ValueError('diagnostic frame identity mismatch')
        if diagnostics['shape'] != [spec['camera']['native_height'], spec['camera']['native_width']]:
            raise ValueError('diagnostic native dimensions mismatch')
        if diagnostics['native_sha256'] != seal['files']['native.npz']:
            raise ValueError('diagnostic native payload hash differs from seal')
        for arm in ('A', 'B', 'C'):
            value = diagnostics['arms'][arm]
            if not math.isclose(sum(s['mass'] for s in value['strata'].values()), value['mass'], rel_tol=1e-9, abs_tol=1e-5):
                raise ValueError('stratum masses do not partition arm: ' + arm)
            if sum(s['support'] for s in value['strata'].values()) != value['support']:
                raise ValueError('stratum support does not partition arm: ' + arm)
        return {**record, 'status': 'SEALED_DIAGNOSTICS_VERIFIED',
                'seal': str(frame / 'SEAL.json'), 'seal_sha256': hash_file(frame / 'SEAL.json'),
                'diagnostics': str(frame / 'diagnostics.json'), 'camera_hash': context['camera_hash'],
                'parameter_hash': context['parameter_hash'],
                'files': {name: dict(path=str(frame / name), sha256=digest) for name, digest in seal['files'].items()}}, diagnostics
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return {**record, 'status': 'INVALID', 'reason': str(exc), 'diagnostics': None}, None


def normalization_record(group):
    if group == 'pilot':
        path = OUT / 'PILOT.json'
        if not path.exists():
            return dict(status='MISSING', path=str(path), reason='pilot record not published'), None
        data = read_json(path)
        hashes = sorted({record['context']['parameter_hash'] for record in data['records']})
        if len(hashes) != 1:
            raise ValueError('pilot parameter hashes disagree')
        return dict(status='PILOT_ONLY', path=str(path), sha256=hash_file(path),
                    normalization=data['normalization'], qualification=data['qualification'], parameter_hash=hashes[0]), hashes[0]
    path = OUT / 'LOCK.json'
    if path.exists():
        lock = read_json(path)
        if lock['lock_hash'] != canonical_hash({key: value for key, value in lock.items() if key != 'lock_hash'}):
            raise ValueError('normalization lock self-hash mismatch')
        parameter_hash = canonical_hash({'config': lock['config'], 'normalization': lock['normalization']})
        if parameter_hash != lock['parameter_hash']:
            raise ValueError('normalization parameter hash mismatch')
        return dict(status='PRIMARY_F_LOCKED', path=str(path), sha256=hash_file(path),
                    parameter_hash=parameter_hash, normalization=lock['normalization'],
                    F_native_sources=lock['F_native_sources'], primary_F_count=len(lock['primary_F'])), parameter_hash
    path = OUT / 'NORMALIZATION.json'
    if path.exists() and (OUT / 'CONFIG.json').exists():
        value, config = read_json(path), read_json(OUT / 'CONFIG.json')
        parameter_hash = canonical_hash({'config': config, 'normalization': value['normalization']})
        return dict(status='F_NORMALIZATION_EXISTS_BUT_C_GATE_NOT_LOCKED', path=str(path),
                    sha256=hash_file(path), parameter_hash=parameter_hash, **value), parameter_hash
    return dict(status='MISSING', path=str(path), reason='尚未发布 primary-F normalization；不能假定单位尺度'), None


def checkpoint_qualifications(scene, inputs):
    records, failures = {}, []
    for path in sorted((OUT / 'raw' / scene).glob('*/checkpoint_qualification.json')):
        try:
            seal = seal_metadata(path.parent)
            value = verified_json_payload(path.parent, seal, path.name)
            records[canonical_hash(value)] = dict(metadata=value, source=str(path), sha256=hash_file(path))
        except (OSError, KeyError, TypeError, ValueError) as exc:
            failures.append(dict(path=str(path), reason=str(exc)))
    return dict(checkpoint=inputs['scenes'][scene]['checkpoint'],
                native_export_metadata=list(records.values()) if records else None,
                metadata_status='AVAILABLE' if records else 'MISSING', invalid_metadata=failures,
                inherited_input_quality_limit=('继承 Drums/Ficus posterior/input qualification 失败，不删除困难帧；不是本阶段重新合格认证。'
                                              if scene in ('drums', 'ficus') else '沿用冻结 vanilla GS；本阶段不宣称几何表面真值。'),
                inherited_report=str(ROOT / 'artifacts/direct_curve_global_fit_probe/REPORT.md'))


def summarize(group='frames'):
    inputs = read_inputs()
    normalization, parameter_hash = normalization_record(group)
    scenes = ('lego', 'chair') if group == 'pilot' else SCENES
    output = dict(schema='hybrid-raster-evidence-summary-v1', group=group,
                  generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  interpretation='仅像素/覆盖诊断；墨量、支持集和新增像素不是真实线质量指标，不给视觉优劣、科学 GO 或时序稳定性结论。',
                  missing_policy='MISSING/INVALID 帧不参与聚合；未完成分组统计为 null，不用零代替。',
                  verification='验证 seal checksum/context、预注册相机、锁参数、JSON payload SHA及库存存在性；不重新读取NPZ/图像、不代替生产runner完整文件hash校验。',
                  normalization=normalization, scenes={}, all_frames=[],
                  qualifications=['A/B/C 完全共享同次原生 SH0 RGB；忽略 full-SH 系数。',
                                  'vanilla checkpoint 缺少训练时 RaDe filter_3D；未补造或重训。',
                                  'top4 是真实 alpha*T 最大四项，仅覆盖部分 alpha；coverage 单列报告。',
                                  '原生法线只是 RaDe splat/raster normals，不是验证过的表面真值；病态 inverse-covariance fallback 数量见checkpoint metadata。',
                                  '作者 Eq.1–5 为 Hao–Mukai 第三方公式的独立重建；OUR dense readout/融合是附加读出，原 proxy rank-max 不是作者方法。',
                                  '主实验纯2D视角相关；旧 fixed-3D NO_GO 未改变，hybrid 本身不作为新颖性。',
                                  'C 为本次 evidence/参数拟合留出，仍属 GS TRAIN 且历史已看过；TEST/DEV 不读。',
                                  '墨量匹配为每帧整图 opacity-mass 缩放，不是等黑像素数；其 gain 可能闪烁。'])
    for scene in scenes:
        scene_data = dict(checkpoint_qualifications=checkpoint_qualifications(scene, inputs), splits={})
        for split in (('F',) if group == 'pilot' else ('F', 'C', 'arc0')):
            specs = frame_specs(inputs, scene, split)
            if group == 'pilot':
                specs = [spec for spec in specs if spec['index'] in (1, 41)]
            records, diagnostics = [], []
            for spec in specs:
                record, diagnostic = inspect_frame(spec, inputs, group, parameter_hash)
                records.append(record)
                if diagnostic is not None:
                    diagnostics.append(diagnostic)
            output['all_frames'].extend(records)
            complete = len(diagnostics)
            scene_data['splits'][split] = dict(
                status='COMPLETE' if complete == len(specs) else 'PARTIAL_OR_MISSING',
                expected_frames=len(specs), complete_frames=complete,
                missing_frames=[record['key'] for record in records if record['status'] == 'MISSING'],
                invalid_frames=[dict(key=record['key'], reason=record['reason']) for record in records if record['status'] == 'INVALID'],
                aggregation_scope='当前已验证seal/diagnostics的帧；count不足expected时不能当作完整split结果。',
                arms={arm: aggregate_tree([diagnostic['arms'][arm] for diagnostic in diagnostics]) for arm in ('A', 'B', 'C')},
                overlap=aggregate_tree([diagnostic['overlap'] for diagnostic in diagnostics]),
                ink_matching=aggregate_tree([diagnostic['ink_matching'] for diagnostic in diagnostics]),
                raw=aggregate_raw([diagnostic['raw'] for diagnostic in diagnostics]),
                frame_directories=[record['directory'] for record in records])
        output['scenes'][scene] = scene_data
    output['expected_frames'] = len(output['all_frames'])
    output['complete_frames'] = sum(record['status'] == 'SEALED_DIAGNOSTICS_VERIFIED' for record in output['all_frames'])
    output['invalid_frames'] = sum(record['status'] == 'INVALID' for record in output['all_frames'])
    output['missing_frames'] = sum(record['status'] == 'MISSING' for record in output['all_frames'])
    output['status'] = 'COMPLETE_DIAGNOSTICS' if output['complete_frames'] == output['expected_frames'] else 'PARTIAL_DIAGNOSTICS'
    calibration = OUT / 'calibration/CALIBRATION.json'
    output['calibration'] = dict(path=str(calibration), sha256=hash_file(calibration),
                                 status=read_json(calibration)['status']) if calibration.exists() else dict(status='MISSING', path=str(calibration))
    return output


def self_test():
    assert aggregate_tree([]) is None
    assert aggregate_tree([{'mass': 0}, {'mass': 2}])['mass'] == dict(count=2, sum=2, mean=1., min=0, max=2)
    sample = {'count': 2, 'mean': 1., 'min': 0., 'max': 2., 'p05': .1, 'p50': 1., 'p95': 1.9}
    other = {'count': 6, 'mean': 3., 'min': 2., 'max': 4., 'p05': 2.1, 'p50': 3., 'p95': 3.9}
    keys = ('alpha', 'top4_coverage', 'normal_coherence', 'depth_variance')
    result = aggregate_raw([{key: sample for key in keys}, {key: other for key in keys}])
    assert result['alpha']['pixel_count'] == 8
    assert result['alpha']['pixel_weighted_mean'] == 2.5
    assert result['alpha']['frame_quantiles']['p50']['mean'] == 2.
    assert numeric_summary([None])['mean'] is None
    try:
        numeric_summary([float('nan')])
    except ValueError:
        pass
    else:
        raise AssertionError('nonfinite data not rejected')
    print('PASS: missing/zero distinction, weighted raw means, frame-quantile qualification, finite diagnostics')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=('frames', 'pilot'), default='frames')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.output is None:
        parser.error('--output is required; snapshots are not silently overwritten')
    destination = args.output.resolve()
    if not destination.is_relative_to(ART) and not destination.is_relative_to(OUT):
        parser.error('--output must remain inside this stage artifact/output directories')
    value = summarize(args.group)
    atomic_json(destination, value)
    print(json.dumps(dict(path=str(destination), status=value['status'], complete=value['complete_frames'],
                          expected=value['expected_frames'], missing=value['missing_frames'], invalid=value['invalid_frames']), ensure_ascii=False))


if __name__ == '__main__':
    main()
