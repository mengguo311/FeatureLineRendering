"""One frozen recipe: construction, acceptance-only validation, then rendering."""
import argparse
from collections import Counter
import json
from pathlib import Path
import time
import numpy as np

import fields
import geometry
from paths import extract_paths, Evidence, resample
from pipeline_io import ART, OUT, CFG, check_freeze, event, load_asset, load_view, sha, save_geometry_asset, write_json


def code_hashes():
    return {p.name: sha(p) for p in sorted((ART/'code').iterdir()) if p.suffix in ['.py', '.cpp']}


def decorate(proposals):
    for p in proposals:
        xyz = np.asarray(p.get('controls_xyz', p['xyz']), dtype=float)
        p['controls_xyz'] = xyz
        p['topology'] = [[i, i+1] for i in range(len(xyz)-1)]
        p['brush_arc'] = np.r_[0., np.cumsum(np.linalg.norm(np.diff(xyz, axis=0), axis=1))]
        p['color_rgb'] = CFG['render']['fixed_color_rgb']
        p['width_px'] = CFG['render']['fixed_width_px']
        p['style_source'] = CFG['render']['width_source']
    return proposals


def construction():
    start = time.monotonic()
    check_freeze()
    event('construction', 'begin', code_sha256=code_hashes())
    cameras, native, paths, stats = {}, {}, {}, {}
    for key in CFG['construction']:
        camera, raw, response = load_view('construction', key)
        cameras[key] = camera; native[key] = raw
        paths[key], stats[key] = extract_paths(response, raw, CFG, key)
        print(key, stats[key], flush=True)
    write_json(OUT/'CONSTRUCTION_PATHS.json', dict(paths=paths, statistics=stats))
    event('construction', 'matching_begin', path_counts={key: len(value) for key, value in paths.items()})
    proposals, diagnostics = geometry.build_proposals(paths, cameras, CFG,
        lambda view, uv, z: fields.depth_support(native[view], uv, z, CFG))
    null = diagnostics.pop('null_proposals')
    proposals, null = decorate(proposals), decorate(null)
    write_json(OUT/'MATCH_DIAGNOSTICS.json', diagnostics)
    reason_counts = Counter(reason for p in proposals for reason in p['construction_reasons'])
    summary = dict(stage='construction', path_statistics=stats,
                   construction_paths=sum(len(p) for p in paths.values()),
                   proposed=len(proposals), construction_pass=sum(p['construction_ok'] for p in proposals),
                   rejected_construction=sum(not p['construction_ok'] for p in proposals),
                   construction_reason_counts=dict(reason_counts),
                   matching={k: diagnostics[k] for k in ['triplet_hypotheses', 'triangulation_attempts', 'total_controls']},
                   pairs=diagnostics['pairs'], null=diagnostics['null'],
                   diagnostics_path=str(OUT/'MATCH_DIAGNOSTICS.json'), diagnostics_sha256=sha(OUT/'MATCH_DIAGNOSTICS.json'),
                   paths_path=str(OUT/'CONSTRUCTION_PATHS.json'), paths_sha256=sha(OUT/'CONSTRUCTION_PATHS.json'),
                   elapsed_seconds=time.monotonic()-start, code_sha256=code_hashes())
    write_json(ART/'CONSTRUCTION.json', summary)
    metadata = dict(config_sha256=sha(ART/'CONFIG.json'), protocol_sha256=sha(ART/'PROTOCOL.md'),
                    source_qualification='Mic vanilla30000 seed1729; GS TRAIN; four LINE construction views only',
                    construction_cameras=CFG['construction'], geometry_refit_after_seal=False)
    _, seal = save_geometry_asset('PROPOSALS', proposals, metadata)
    save_geometry_asset('NULL_PROPOSALS', null, dict(metadata, null_control=diagnostics['null']))
    event('construction', 'proposals_sealed', proposed=len(proposals),
          construction_pass=summary['construction_pass'], seal_sha256=sha(ART/'PROPOSALS_SEAL.json'),
          geometry_sha256=seal['geometry_sha256'])
    print('CONSTRUCTION COMPLETE', len(proposals), 'formed;', summary['construction_pass'], 'pass', flush=True)


def validate_candidates(proposals, views):
    results, accepted = [], []
    for proposal in proposals:
        record = dict(persistent_id=proposal['persistent_id'], construction_ok=proposal['construction_ok'], views={})
        if not proposal['construction_ok']:
            record.update(accepted=False, rejection_reasons=['construction:'+x for x in proposal['construction_reasons']], eligible_views=0)
            results.append(record)
            continue
        points = resample(proposal['controls_xyz'], CFG['validation_rules']['samples_per_path'])
        for key, (cam, native, evidence) in views.items():
            uv, z = geometry.project(points, cam)
            tangents = np.gradient(uv, axis=0)
            record['views'][key] = fields.validate_view(native, uv, z, tangents, evidence.candidates, CFG)
        eligible = sum(v['eligible'] for v in record['views'].values())
        reasons = []
        if eligible < CFG['validation_rules']['min_eligible_views']:
            reasons.append('insufficient_validation')
        for key, v in record['views'].items():
            reasons.extend(key+':'+failure for failure in v['failures'])
        record.update(accepted=not reasons, rejection_reasons=reasons, eligible_views=eligible)
        results.append(record)
        if not reasons:
            p = dict(proposal); p['validation'] = record; accepted.append(p)
    return results, accepted


def validation():
    start = time.monotonic()
    check_freeze()
    proposed = load_asset(ART/'PROPOSALS.json')
    null_proposed = load_asset(ART/'NULL_PROPOSALS.json')
    proposal_sha = sha(ART/'PROPOSALS.json')
    event('validation', 'begin', proposed_asset_sha256=proposal_sha, code_sha256=code_hashes())
    views = {}
    for key in CFG['validation']:
        camera, native, responses = load_view('validation', key)
        evidence = Evidence(responses, native, CFG)
        views[key] = camera, native, evidence
        print('validation evidence', key, len(evidence.xy), flush=True)
    real_results, accepted = validate_candidates(proposed['paths'], views)
    null_results, null_accepted = validate_candidates(null_proposed['paths'], views)
    assert sha(ART/'PROPOSALS.json') == proposal_sha
    null_info = null_proposed['null_control']
    null_status = ('FAIL_SURVIVORS' if null_accepted else 'PASS_REJECTED' if null_info['sufficient'] else 'INSUFFICIENT')
    summary = dict(proposed=len(proposed['paths']), accepted=len(accepted), rejected=len(proposed['paths'])-len(accepted),
                   results=real_results, rejection_reason_counts=dict(Counter(r for p in real_results for r in p['rejection_reasons'])),
                   null=dict(status=null_status, sufficient=null_info['sufficient'], proposed=len(null_proposed['paths']),
                             construction_pass=sum(p['construction_ok'] for p in null_proposed['paths']), accepted=len(null_accepted), results=null_results,
                             scientific_go_valid=bool(null_info['sufficient'] and not null_accepted), repetition=1, seed=1730),
                   elapsed_seconds=time.monotonic()-start, geometry_refit=False, code_sha256=code_hashes())
    write_json(ART/'VALIDATION.json', summary)
    metadata = dict(config_sha256=sha(ART/'CONFIG.json'), protocol_sha256=sha(ART/'PROTOCOL.md'),
                    proposed_asset_sha256=proposal_sha, validation_sha256=sha(ART/'VALIDATION.json'),
                    validation_cameras=CFG['validation'], source_qualification='historical GS TRAIN; unused only in LINE construction',
                    human_review='PENDING', parent_review='PENDING', fixed_geometry_does_not_prove_temporal_superiority=True)
    asset, seal = save_geometry_asset('ASSET', accepted, metadata)
    event('validation', 'accepted_asset_sealed', accepted=len(accepted), proposed=len(proposed['paths']),
          asset_sha256=sha(ART/'ASSET.json'), geometry_sha256=asset['geometry_sha256'], seal_sha256=sha(ART/'ASSET_SEAL.json'))
    print('VALIDATION COMPLETE', len(accepted), '/', len(proposed['paths']), 'null', null_status, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['construction', 'validation', 'render'])
    args = parser.parse_args()
    np.random.seed(CFG['seed'])
    if args.stage == 'construction': construction()
    elif args.stage == 'validation': validation()
    else:
        from render_result import render_all
        render_all()


if __name__ == '__main__':
    main()
