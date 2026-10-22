"""Freeze unit013 before implementation/comparison; no historical writes."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import json,shutil,subprocess
unit=OUTPUT_ROOT/'units/unit_013';previous=OUTPUT_ROOT/'units/unit_012';output_guard(unit)
assert not (unit/'PROTOCOL.json').exists()
for d in ('logs','metrics','media'): (unit/d).mkdir(exist_ok=True)
asset=previous/'portable_demo/assets/chair';meta=json.loads((asset/'asset.json').read_text())
assert sha(meta['original']['original_ply'])==meta['original']['sha256']
p=dict(unit='unit_013',frozen_utc=now(),previous_unit=str(previous),scene='chair',asset=str(asset),
 input_files={p.name:sha(p) for p in asset.iterdir() if p.is_file()},original=meta['original'],
 geometry=meta['geometry'],regions=meta['regions'],region_provenance=meta['region_provenance'],styles=meta['styles'],
 changed_variable='Optional saved second world-plane hatch direction in region2, relative cross_angle60deg, independent cross_spacing0.060; base remains angle95/spacing0.045/length0.22/width1.',
 local_edit=dict(region=2,cross_enabled=True,cross_angle=60.,cross_spacing=.060),
 display=dict(contours_visible=True,contour_strength=1.),
 static_camera_values=[dict(azimuth=a,elevation=25,distance=5.2) for a in (47,137,227,317)],
 viewer_camera=dict(azimuth=47,elevation=25,distance=5.2),
 motion=dict(orbit_frames=12,zoom_frames=6,start_azimuth=47,elevation=25,distance=5.2,fps=6,
   rule='unit012 saved-snapshot presentation trajectory, analytic fit if required, all frames retained'),
 layer_contract='layer0 legacy paths unchanged for cross-only edits; layer1 saved anchors/IDs use disjoint region ID subrange; toggle retains all path bytes; width affects both; changing base angle/length changes both directions; explicit target revision.',
 fixed='Original checkpoint, proxy vertices/faces, labels, base paths, other styles, depth tolerance, renderer coverage rules, 512 square/2xAA, contour1.0.',
 evaluation=['real Chair behavior test red then green; toggle exact baseline; non-target bytes/layers exact; base points/bary/face/IDs exact',
 '4 full-object before/after and isolated layer outputs; proxy-label fixed2px locality with residuals retained; visible ink and overlap reported',
 'real original PLY CPU SH3 EWA at first fixed camera; source RGB/proxy/region/base/cross panels',
 'actual Firefox checkbox/angle/spacing/save/undo/reload/export; download snapshot; package relocated cold image/orbit/zoom replay',
 '12orbit/6zoom all frames, full FFV1 exact decode and MP4 full decode/count; no all-path temporal claim'],
 exposure='Known Chair and historically exposed GS images; camera values frozen before this implementation. No blind holdout or independent semantic/geometry truth.',
 scope='Engineering style feature; increased ink is expected, not calibrated shading, geometry improvement, aesthetics certification, or H1/H2 evidence.',
 resource=dict(cpu=2,numeric_threads=1,serial=True,gpu=False,nested_models=False,unit_deadline_jst='2026-10-22T06:50:39+09:00'))
js(unit/'PROTOCOL.json',p);shutil.copy2(unit/'PROTOCOL.json',Path('docs/partwise_sketch_hatching_v04/UNIT013_PROTOCOL.json'))
source=Path(__file__).parent;shutil.copytree(source,unit/'source_before',ignore=shutil.ignore_patterns('__pycache__'))
js(unit/'SOURCE_BEFORE.json',dict(files={p.name:sha(p) for p in source.iterdir() if p.is_file()},git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
(unit/'INHERITED_WORKTREE.diff').write_bytes(subprocess.check_output(['git','diff','--','experiments/partwise_sketch_hatching_v04','docs/partwise_sketch_hatching_v04']))
(unit/'READING_REVIEW_ZH.md').write_text('''# 阅读和决策

完整阅读BRIEF和851行原大纲、P1最后完成unit010的REPORT/NEXT/长度源码及unit011未完成spacing源码、P2 REPORT/NEXT/audit_headroom源码；unit011没有REPORT/NEXT，两条只读cat缺失提示保留在本记录。未执行任何历史写入辅助程序。继承dirty worktree不清理。无适用AGENTS.md。

实际检查unit012 source_proxy_regions_edit整对象图：Chair局部角度编辑可辨、代理轮廓不均；Ficus叶片孔洞和碎线仍明显。unit012导出/cold replay已完成，不能以导出工程当作几何成功。排序：1可保存单区第二方向层；2真实薄结构几何；3继续扩模型。选择1：与原大纲短交叉风格直接相关，可在已有完整对象/可操作界面/冷重开基础上有界交付。保留原GT零交界余量与H2不可辨识，不制造弱基线。

唯一外观候选为Chair region2原角度95度不变，新增60度偏转和0.060世界平面间距。方向角是切割平面法向的偏转，不保证曲面上处处60度。默认四模型均关闭；新层单独记录墨量和重叠。没有改变代理或分部，也不把加墨称作视觉改善。镜头和全部负视角在协议中先冻结，无参数扫选。
''')
js(unit/'STATUS.json',dict(stage='PROTOCOL_FROZEN',execution_state='partial',scientific_verdict='H1_H2_NOT_TESTED',demo_progress=dict(genuinely_ran_old_model=False,reasoning='Implementation and real-model execution pending.'),artifacts=['PROTOCOL.json'],blockers=[]))
print(json.dumps(dict(protocol_sha256=sha(unit/'PROTOCOL.json'),frozen_utc=p['frozen_utc'])))
