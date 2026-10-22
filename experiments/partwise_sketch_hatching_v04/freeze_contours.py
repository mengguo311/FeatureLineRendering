"""Freeze one display-only comparison before implementation and rendering."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now
from pathlib import Path
import json,shutil,subprocess
from geometry import orbit_camera

def main():
    unit=OUTPUT_ROOT/'units/unit_011';previous=OUTPUT_ROOT/'units/unit_010'
    assert not (unit/'PROTOCOL.json').exists()
    scenes={}
    for scene in ('ficus','chair'):
        asset=previous/'portable_demo/assets'/scene
        meta=json.loads((asset/'asset.json').read_text())
        assert sha(meta['original']['original_ply'])==meta['original']['sha256']
        scenes[scene]=dict(asset=str(asset),files={p.name:sha(p) for p in asset.iterdir() if p.is_file()},
            original=meta['original'],region_provenance=meta['region_provenance'],styles=meta['styles'],
            cameras=[meta['cameras'][0],meta['cameras'][2]]+[orbit_camera(a,28,5.2) for a in (91,271)],
            local_edit=dict(region=2,angle=45))
    protocol=dict(unit=unit.name,frozen_utc=now(),previous_unit=str(previous),
        question='Can independently saved contour visibility/strength improve readability without changing any hatch evidence?',
        scope='Engineering display control on actual saved model-derived proxies; not geometry repair, curve recovery, H1 or H2.',
        scenes=scenes,arms={'baseline':{'contours_visible':True,'contour_strength':1.0},
            'reduced':{'contours_visible':True,'contour_strength':0.35}},
        changed_variable='Global view-contour multiplier only; original .85 mask ink remains baseline. Zero and hidden are functional tests, not tuned candidates.',
        fixed='Mesh, labels, paths, IDs, hatch styles, visibility, contour mask detection, 512px/2xAA and cameras unchanged across display arms.',
        exposure='First two cameras per model historically exposed; new 91/271 deg at elevation28/distance5.2 chosen before output. Not blind holdouts of GS training or independent geometry truth.',
        orbit=[orbit_camera(97+30*k,24,5.4) for k in range(12)],
        zoom=[orbit_camera(127,28,5.8-k*.2) for k in range(6)],
        evaluation=['Full-object original-GS RGB/proxy/regions/baseline/reduced images, including weak views',
            'Exact same hatch/depth/regions/layers and all saved mesh/path hashes across display arms',
            'Per-camera total ink, hatch ink and contour ink; lower contour ink is intentional, not an accuracy gain',
            'Middle angle95->45 at both strengths: unchanged other paths/layers, target change, fixed 2px AA-band locality',
            'Old assets without display metadata reproduce baseline; finite numeric [0,1] plus bool visibility validation',
            'Actual browser control, undo/model persistence, exported-asset process restart and relocated CLI/viewer reload',
            'Real orbit12/zoom6 with every video frame decoded and inspected; no full temporal correspondence claim'],
        decision='Ship control with legacy defaults preserved. Visual judgment is nonblind descriptive; no parameter sweep.',
        resource=dict(cpu_affinity=list(__import__('os').sched_getaffinity(0)),numeric_threads=1,serial=True,gpu=False,
            nested_models=False,deadline_jst='2026-10-22T06:12:47+09:00'))
    js(unit/'PROTOCOL.json',protocol)
    shutil.copy2(unit/'PROTOCOL.json',Path('docs/partwise_sketch_hatching_v04/UNIT011_PROTOCOL.json'))
    (unit/'logs').mkdir();(unit/'metrics').mkdir();(unit/'media').mkdir()
    here=Path(__file__).parent
    files={str(p):sha(p) for p in here.iterdir() if p.is_file()}
    js(unit/'SOURCE_BEFORE.json',dict(files=files,git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
    (unit/'INHERITED_WORKTREE.diff').write_bytes(subprocess.check_output(['git','diff','--','experiments/partwise_sketch_hatching_v04','docs/partwise_sketch_hatching_v04']))
    (unit/'READING_REVIEW_ZH.md').write_text('''# Unit011 阅读与方向选择

完整读取 BRIEF 与851行原大纲，P1 unit010 REPORT/NEXT及length_cli种子/生成逻辑，P2 experiment001 REPORT/NEXT及audit_headroom。保留原P1完整视觉NO_GO/PARTIAL；三不连通GT部件和既有GT裁剪导致P2 ZERO_HEADROOM，不是H2否证。旧单单元限制由新用户授权覆盖，但本轮仍≤55分钟。

读取unit010 REPORT/STATUS/NEXT及真实render/demo/viewer/catalog/runtime/package源码。实际查看simplification_new_views与local_edit_all_views：完整Ficus可辨，137k叶片拓扑依然破碎，轮廓密集且局部角度变化不突出。更多面不等于更好，保留30k目录资产。排序：1独立轮廓显示控制；2更换薄叶几何表示；3继续扩模型。选择1，因为成本有界、直接帮助观察已有局部编辑，并且符合大纲分层显示要求。四模型已可用，暂不新增模型。

本轮只比较默认轮廓与0.35倍一个候选，保存开关/强度；网格、区域、排线路径不变。原始资产中区已95度，局部编辑明确改回45度。两个历史视图与两个新虚拟视图/模型在输出前冻结。显示控制不作几何修复、结构恢复或H1/H2结论；降低总墨量须公开。不开嵌套模型/代理，不读凭据，不修改orchestration或历史单元。
''')
    print(json.dumps({'protocol_sha256':sha(unit/'PROTOCOL.json'),'scenes':list(scenes)}))

if __name__=='__main__':main()
