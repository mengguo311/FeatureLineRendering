#!/usr/bin/env python3
"""Summarize completed runs and check frozen artifacts; never changes a method input."""
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'out/stroke_organization'
ARMS = ['A', 'B', 'C', 'C-no-global', 'C-no-corner', 'N']
MODES = ['native', 'length_matched', 'area_matched']


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip()
    assert branch == 'stroke-organization', 'STOP: wrong branch'
    m, r, ga = [read(OUT / f) for f in ['MANIFEST.json', 'render.json', 'graph/audit.json']]
    path_index = read(OUT / 'PATH_INDEX.json')
    g = np.load(OUT / 'graph/graph.npz')
    inputs = {}
    for name, item in m['inputs'].items():
        inputs[name] = sha(item['path'])
        assert inputs[name] == item['sha256'], name
    for path, expected in r['freeze']['files'].items():
        assert sha(ROOT / path) == expected, path
    assert sha(OUT / 'graph/graph.npz') == ga['graph_sha256']
    arms, checks = {}, {}
    for a in ARMS:
        for suffix, item in path_index['arms'][a].items():
            assert sha(OUT / f'paths/{a}{suffix}') == item['sha256']
        meta = read(OUT / f'paths/{a}.json')
        rows = [json.loads(s) for s in (OUT / f'paths/{a}_paths.jsonl').read_text().splitlines()]
        z = np.load(OUT / f'paths/{a}.npz')
        seen = set()
        for i, row in enumerate(rows):
            nodes = np.array(row['nodes'], dtype=int)
            assert len(nodes) == len(set(nodes)) and not seen.intersection(nodes)
            seen.update(nodes)
            lo, hi = z['offsets'][i:i + 2]
            expected = g['p'][nodes][row['retained_vertices']]
            assert np.array_equal(z['vertices'][lo:hi], expected)
            assert row['original_node_ids'] == g['original_ids'][nodes].tolist()
        assert len(rows) == meta['paths'] and len(seen) == meta['used_nodes']
        checks[a] = dict(paths=len(rows), used_nodes=len(seen), exact_frozen_vertices=True,
                         node_disjoint=True, simple_paths=True)
        witness = [row['terms'] for row in rows if 'witness_score' in row['terms']]
        arms[a] = dict(**meta, new_D_nodes_in_paths=meta['used_nodes'] - meta['source_used_nodes']['M1a'],
                       display={mode: r['means'][mode][a] for mode in MODES},
                       matching=r['calibration'][a])
        if witness and a != 'B':
            arms[a]['witness_audit'] = dict(
                mean_score=float(np.mean([x['witness_score'] for x in witness])),
                fewer_than_three_views=sum(len(x['witness_views']) < 3 for x in witness),
                zero_views=sum(not x['witness_views'] for x in witness))
    access = {}
    train = set(m['train_indices'])
    for path in sorted(OUT.glob('access_*.json')):
        d = read(path)
        assert set(d['allowed_indices']) == train
        photo_ids = [int(Path(p).stem.split('_')[-1]) for p in d['rgb_reads']]
        assert set(photo_ids) <= train, path
        access[path.name] = dict(photo_indices=photo_ids, data_reads=len(d['data_reads']))
        for name in d['data_reads']:
            assert not any(t in name.lower() for t in ['/meshes/', '/mesh/', 'mesh_oracle', 'gt_crease', '/dd3', '/2dgs_'])
    assert not read(OUT / 'access_render.json')['rgb_reads']
    assert sha(OUT / 'paths/A.npz') == sha(ROOT / 'out/raster_state_candidates/lego/step4/paths_D.npz')
    for data in r['videos'].values():
        assert data['frames'] == 120 and sha(ROOT / data['path']) == data['sha256']
    aa, cc = [r['means']['area_matched'][a] for a in ['A', 'C']]
    reduction = 1 - cc['short_fragment_fraction_lt12px'] / aa['short_fragment_fraction_lt12px']
    ratio = cc['median_visible_fragment_px'] / aa['median_visible_fragment_px']
    review = dict(internal_only=True, blind_participants=0, realtime_playback=False,
                  complete_decoded_frame_review=True, frames_per_mode=120,
                  contact_sheets=[str(p.relative_to(OUT)) for pattern in ['all_contact_*.png', 'video_contact_*.png']
                                  for p in sorted((OUT / 'render').glob(pattern))],
                  regions=[dict(id='R1', pass_g2=False, observation='cab frame remains broken/noisy; roof edge can be lost'),
                           dict(id='R2', pass_g2=False, observation='local diagonal continuity; no clear mechanical-turn organization'),
                           dict(id='R3', pass_g2=False, observation='longer border portions retain loops and zigzags')])
    assert len(review['contact_sheets']) == 54
    summary = dict(
        decision='NO-GO', method='Witnessed-View Prize-Collecting Path Cover (WV-PC)', scene='lego',
        scope='bounded beam proposals plus whole-path greedy packing; not all global path-cover methods',
        base_commit=m['base_commit'], freeze_commit=r['freeze']['commit'], input_sha256=inputs,
        candidate_generation_provenance=read(ROOT / 'out/raster_state_candidates/lego/step4.json')['provenance'],
        manifest_sha256=sha(OUT / 'MANIFEST.json'), graph=ga, arms=arms,
        gates=dict(G1=dict(status='FAIL', short_relative_reduction=reduction, required_reduction=.4,
                           visible_fragment_median_ratio=ratio, required_ratio=1.8),
                   G2=dict(status='FAIL', clearly_improved_regions=0, required=2),
                   G3=dict(status='NOT_CERTIFIED', reason='no obvious large shortcut seen; small persistent contour errors cannot be ruled out'),
                   G4=dict(status='FAIL', reason='full not clearly better visually than geometry-only and local organization; null comparable'),
                   G5=dict(status='FAIL', A_C_area_matching_pass=True, reason='matched ink does not yield clear readability gain'),
                   G6=dict(status='PASS_CARRIER_CONSTRAINT', temporal_advantage_claim=False)),
        integrity=dict(input_hashes_pass=True, freeze_sources_unchanged=True, paths=checks,
                       original_A_identical=True, access=access, final_test_images_opened=False,
                       original_GS_training_split_verified=False),
        official_rgb=r['official_rgb'], depth='common vanilla Gaussian disc proxy, not official anisotropic raster depth',
        runtimes_seconds=dict(audit=read(OUT / 'audit/audit.json')['seconds'], graph=ga['seconds'],
                              smoke=read(OUT / 'smoke.json')['seconds'],
                              solve={a: arms[a]['seconds'] for a in ARMS}, render=r['seconds']),
        videos=r['videos'], fixed_frames=r['fixed_frames'], visual_review=review,
        tests=dict(command='python -m unittest discover -s tests -v', passed=45, failed=0, seconds=.497,
                   evidence='TESTS.md; actual execution before final report commit'),
        stopped=dict(chair_not_run=True, no_post_DEV_weight_tuning=True, no_new_candidates=True))
    with open(OUT / 'RESULTS.json', 'x') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write('\n')
    lines = ['# 真实运行数值（由 summarize_stroke_organization.py 汇总）', '',
             '长度/面积都是120帧的均值；短片段<12px；长度中位数是每帧连续可见片段中位数的均值。', '',
             '| arm | 图节点 | 允许边 | 使用节点 | 新D节点 | 原生paths | world长度P10/P50/P90 | 求解秒 |',
             '|---|---:|---:|---:|---:|---:|---|---:|']
    for a, d in arms.items():
        q = d['world_length_quantiles']
        edges = '未记录原chainer图' if d['edges'] is None else str(d['edges'])
        lines.append(f"|{a}|{d['nodes']}|{edges}|{d['used_nodes']}|{d['new_D_nodes_in_paths']}|{d['paths']}|{q[1]:.5f}/{q[2]:.5f}/{q[3]:.5f}|{d['seconds']:.3f}|")
    for mode in MODES:
        lines += ['', f'## {mode}', '', '| arm | 固定路径数 | 可见长度px | AA墨面积px² | 短片段率 | 可见片段median px | overlap | 匹配有效 |', '|---|---:|---:|---:|---:|---:|---:|---|']
        for a, d in arms.items():
            s = d['display'][mode]
            match = mode == 'native' or d['matching'][mode]['matched']
            count = d['paths'] if mode == 'native' else d['matching'][mode]['selected_paths']
            state = '原生' if mode == 'native' else ('是' if match else '**否；全量仍不足**')
            lines.append(f"|{a}|{count}|{s['visible_length_px']:.4f}|{s['ink_area_px']:.4f}|{100*s['short_fragment_fraction_lt12px']:.2f}%|{s['median_visible_fragment_px']:.4f}|{s['overlap_rate']:.4f}|{state}|")
    lines += ['', 'B 明确等同 C-no-image。source标签可重叠，不能把各source计数相加作为新增节点数。', '',
              f'G1：短片段相对降低 {100*reduction:.4f}%；median比 {ratio:.6f}。两个门槛均失败。', '',
              '逐帧原始值见 render.json，路径与各项分数见 paths/*_paths.jsonl，source计数与见证统计见 RESULTS.json。']
    (OUT / 'NUMBERS.md').write_text('\n'.join(lines) + '\n')
    gallery = ['# 完整产物索引', '',
               '**注意：C-no-corner 在 matched 六臂图中墨量不足，该列不构成公平匹配。完整视频只含 RGB/A/C，A/C 匹配成功。**', '']
    for mode in MODES:
        gallery += [f'## {mode}', '', f'[完整120帧视频](render/official_A_C_{mode}.mp4) · [固定四帧](render/fixed_{mode}.png) · [六臂四帧](render/all_fixed_{mode}.png) · [三个区域](render/regions_{mode}.png)', '',
                    '六臂全部帧：' + ' · '.join(f'[{10*i:03d}–{10*i+9:03d}](render/all_contact_{mode}_{i:02d}.png)' for i in range(12)), '',
                    '视频全部解码帧：' + ' · '.join(f'[{20*i:03d}–{20*i+19:03d}](render/video_contact_{mode}_{i:02d}.png)' for i in range(6)), '']
    gallery += ['[候选图诊断](graph/graph_debug.png) · [raw无可见性投影](render/raw_organized_train053.png) · [冻结前TRAIN审计](audit/train_contact.png) · [预标区域](graph/premarked_regions.png)', '',
                'MP4、NPZ和较大junction日志保留服务器，按.gitignore不提交；哈希见 PATH_INDEX.json、render.json。']
    (OUT / 'GALLERY.md').write_text('\n'.join(gallery) + '\n')
    print(json.dumps(dict(decision=summary['decision'], integrity='PASS', G1=summary['gates']['G1'], arms=len(arms), reviewed_sheets=54), indent=2))


if __name__ == '__main__':
    main()
