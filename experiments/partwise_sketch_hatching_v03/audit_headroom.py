"""Read-only baseline/topology audit; no candidate image is rendered."""
from runtime import *
from diagnostic import topology, headroom_status, curve_evidence
from experiments.partwise_sketch_hatching_v02 import renderer

def main():
    resources()
    seal = json.loads((BASE/'SEAL.json').read_text())
    manifest = json.loads((BASE/'SHA256_MANIFEST.json').read_text())
    assert sha(BASE/'SHA256_MANIFEST.json') == seal['manifest_sha256']
    for entry in manifest['files']:
        path = Path(manifest['roots'][entry['root']]) / entry['path']
        assert sha(path) == entry['sha256'], str(path)
    mesh, strokes, cfg = load_asset()
    report = topology(mesh)
    report['sealed_baseline_files_verified'] = len(manifest['files'])
    report['counts'] = {str(p): sum(s['part']==p for s in strokes) for p in (1,2,3)}
    assert report['counts'] == {'1':260, '2':24, '3':150}
    report['vertices'] = len(mesh['vertices']); report['faces'] = len(mesh['faces'])
    report['bbox_diagonal_world'] = float(np.linalg.norm(np.ptp(mesh['vertices'],axis=0)))
    lengths, wrong_length, wrong_anchors = {}, 0., 0
    for s in strokes:
        pts = core.anchor_points(mesh, s)
        lengths[s['id']] = float(np.linalg.norm(np.diff(pts,axis=0),axis=1).sum())
        wrong = mesh['parts'][s['faces']] != s['part']
        wrong_anchors += int(wrong.sum())
        wrong_length += float(np.linalg.norm(np.diff(pts,axis=0),axis=1)[wrong[:-1]].sum())
    report['stroke_length_by_part_world'] = {str(p): sum(lengths[s['id']] for s in strokes if s['part']==p) for p in (1,2,3)}
    report['gt_wrong_part_anchors'] = wrong_anchors
    report['gt_wrong_part_length_world'] = wrong_length
    report['physical_boundary_eligible_surface_area_world2'] = 0. if not report['shared_part_boundary_edges'] else None
    report['physical_boundary_eligible_length_fraction'] = report['shared_part_boundary_length_world']/sum(lengths.values())
    report['headroom_verdict'] = headroom_status(report['shared_part_boundary_length_world'],wrong_length,report['nonmanifold_edges']==0)
    report['scientific_verdict'] = 'UNIDENTIFIABLE_FOR_H2' if report['headroom_verdict']=='ZERO_HEADROOM' else 'PENDING'
    _, rings = renderer._structure_edges(mesh,cfg,core.camera(30,20,4.5,512,600))
    curves = []
    for index,(edge,owners) in enumerate(rings):
        points=mesh['vertices'][list(edge)]
        evidence=dict(source='unit010 authored lathe profiles and indexed mesh edges',confirmed=True,kind='physical_profile_ring')
        curves.append(dict(curve_id=f'profile_edge_{index:04}',edge=list(edge),owners=owners,
                           part_ids=np.unique(mesh['parts'][owners]),points=points,
                           length_world=float(np.linalg.norm(points[1]-points[0])),
                           provenance=evidence,evidence_status=curve_evidence(points,evidence)))
    write_json(ROOT/'audit/AUTHORED_CURVES.json',dict(curves=curves,scope='Physical profile edges, NOT shared part or authored edit boundaries; no image-edge recovery'))
    report['authored_structure_edges'] = len(curves)
    report['authored_structure_length_world'] = sum(c['length_world'] for c in curves)
    report['source_audit'] = dict(
        generation='core_walk_v2.generate_strokes samples mesh.parts == part, then walk stops at differing neighbor GT part. All compared saved paths identical; no coarse-label claim.',
        rendering='renderer.render surface_part == mesh.parts[owner] AND same-ray owner-plane depth. GT masks baseline fragments. This is shared and explicit, not disabled in one arm.',
        structure='renderer already draws authored profile rings. structure=False retains view-dependent contours and suppresses only non-contour rings.',
        scoring='Independent analytic lathe ray intersections for GT scoring only; same authored geometry definition, not independent real-world truth.',
        config='Saved434 paths authoritative. config counts still260/48/150 and are NOT a complete regeneration recipe.',
        exclusion='Do not import v02.common: it changes TMPDIR to the old tree. No old producer or sealer executed.')
    report['decision'] = 'One B1-like vs existing B2-like authored fixed-structure DISPLAY diagnostic; H2 untested. No synthetic label corruption or fabricated cross-component paths.'
    report['geometry_limit'] = 'Components may intersect spatially (stem/base) without shared mesh adjacency. Spatial contact is not walkable adjacency.'
    write_json(ROOT/'audit/HEADROOM.json',report)
    source_paths = [WORK/'experiments/partwise_sketch_hatching/core.py', WORK/'experiments/partwise_sketch_hatching/core_walk_v2.py',WORK/'experiments/partwise_sketch_hatching_v02/renderer.py']
    hashes = {str(p):sha(p) for p in source_paths + [ASSET/f for f in ('asset.json','mesh.npz','strokes.npz','config.json','recipe.json')] + [BASE/'SEAL.json',BASE/'SHA256_MANIFEST.json']}
    write_json(ROOT/'audit/BASELINE_HASHES.json',hashes)
    doc = '# P2 基线接受与范围\n\n用户原话：**“感觉目前的质量以及足够，直接开始下一步实验”**。\n\n记录：`USER_ACCEPTED_GT_VISUAL_BASELINE_FOR_P2`。接受 unit010 完整封存 outputs/edited named434：260 灯罩0°、24支杆、150缩短底座路径。unit011 未封存工作不使用、不改写、不续跑。旧 NO_GO、旧 NEXT 和历史状态原样保留；本决定只允许进入 P2，不代表重建完成、全时序认证或 H1/H2 成功。\n\n完整原大纲851行、P1_ROADMAP_ZH、REPORT_unit010、实际 renderer/walker/asset 已读取。unit010 的601个清单文件重新校验。原始生成与可见性已用 GT 部件，不能冒称粗分部基线。\n\n基线哈希：\n\n' + ''.join(f'- `{p}`：`{h}`\n' for p,h in hashes.items())
    output_path(DOC/'BASELINE_ACCEPTANCE_ZH.md').write_text(doc)
    update_status('HEADROOM_AUDIT_COMPLETE',scientific_verdict=report['scientific_verdict'],artifacts={'headroom':str(ROOT/'audit/HEADROOM.json')},tests={'tdd_red':'expected assertion failure, rc1 preserved'},blockers=['No connected physical part boundary support; H2 cannot be identified on this accepted GT asset.'])
    print(json.dumps(native(report),ensure_ascii=False,allow_nan=False))

if __name__=='__main__': main()
