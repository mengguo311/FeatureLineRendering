import runtime
from runtime import OUTPUT_ROOT,js,sha,now
from pathlib import Path
import json,shutil,subprocess

unit=OUTPUT_ROOT/'units/unit_012';previous=OUTPUT_ROOT/'units/unit_011'
assert not (unit/'PROTOCOL.json').exists()
for d in ('logs','metrics','media'): (unit/d).mkdir(parents=True,exist_ok=True)
scenes={}
for scene in ('chair','ficus'):
    asset=previous/'portable_demo/assets'/scene;meta=json.loads((asset/'asset.json').read_text())
    assert sha(meta['original']['original_ply'])==meta['original']['sha256']
    scenes[scene]=dict(asset=str(asset),files={p.name:sha(p) for p in asset.iterdir() if p.is_file()},original=meta['original'],
        region_provenance=meta['region_provenance'],styles=meta['styles'],local_edit=dict(region=2,angle=45),
        display=dict(contours_visible=True,contour_strength=.35),camera=dict(azimuth=97,elevation=28,distance=5.2))
p=dict(unit='unit_012',frozen_utc=now(),previous_unit=str(previous),scenes=scenes,
    scope='Engineering presentation export from saved real-model assets. No geometry/appearance optimization or H1/H2 comparison.',
    changed_variable='Add snapshot PNG / short orbit / short zoom export and exact offline replay; renderer and asset geometry unchanged.',
    fixed='512 square, 2x AA, current saved styles and contour display, fixed 3D paths/IDs; no per-frame path generation.',
    camera_policy=dict(image='Exact currently rendered camera; report bounds honestly.',orbit='12 equally spaced azimuths starting at current camera, same elevation; one shared distance enlarged only as needed for 16px whole-proxy margin.',
        zoom='6 distances, far to near from 1.15x current distance down to current distance; clamp near to analytic whole-proxy fit with 16px margin; fixed azimuth/elevation.',
        fitting='Use all saved proxy vertices only; analytic perspective inequalities, no image tuning.',fps=6),
    tests=['Real HTTP endpoint red before implementation; invalid/stale/unknown request does not create export.',
        'Image export pixel-exact to current display; snapshot includes display/camera/paths; no source mutation.',
        'Chair and Ficus edit plus both trajectories; all frames inspected and bounded.',
        'FFV1 every frame decoded exact; MP4 every frame decoded and counted (lossy).',
        'Actual Firefox buttons download PNG/ZIP; scene switching cannot mix old export links.',
        'Relocated exported asset/cameras replay every PNG exactly in a fresh process; final portable package cold run.'],
    exposure='These are known models and historically exposed viewpoints; not blind held-out geometry or human preference data.',
    resource=dict(cpu=2,affinity=[0,1],numeric_threads=1,serial=True,gpu=False,nested_models=False,unit_deadline_jst='2026-10-22T06:34:30+09:00'))
js(unit/'PROTOCOL.json',p);shutil.copy2(unit/'PROTOCOL.json',Path('docs/partwise_sketch_hatching_v04/UNIT012_PROTOCOL.json'))
here=Path(__file__).parent
js(unit/'SOURCE_BEFORE.json',dict(files={p.name:sha(p) for p in here.iterdir() if p.is_file()},git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
shutil.copytree(here,unit/'source_before',ignore=shutil.ignore_patterns('__pycache__'))
(unit/'INHERITED_WORKTREE.diff').write_bytes(subprocess.check_output(['git','diff','--','experiments/partwise_sketch_hatching_v04','docs/partwise_sketch_hatching_v04']))
(unit/'READING_REVIEW_ZH.md').write_text('''# 阅读与选择

完整阅读BRIEF及851行原大纲，P1 unit010 REPORT/NEXT/length_cli，P2 REPORT/NEXT/audit_headroom，unit011 REPORT/STATUS/NEXT及viewer/demo/render/catalog/media源码。旧GT三不连通部件与精确GT裁剪令H2零余量，原NO_GO不改写。单单元旧限制由当前用户授权替代；本单元仍≤55分钟。

实际审阅unit011 Ficus comparison、Chair local edit、Ficus orbit全帧：完整模型可辨且Chair编辑清晰，Ficus叶片缺损/杂线明显，35%显示会发白。优先级：1当前资产图片/动画导出；2处理可见几何缺陷；3扩大模型数。选择1，因为已有四模型，完整对象/局部编辑/冷重开已完成，而浏览器分享仍依赖手写脚本。保留默认外观，不追求更密网格、玩具证明或H2新科学。

读取时两次只读路径探测返回非零：猜测旧v03 NEXT路径不存在，后从runtime找到正确p2_v03路径并完整读取；若干AGENTS.md路径不存在，rg未找到适用文件。未运行旧写入辅助程序。无嵌套代理/模型；只在授权worktree及unit012/新交付根写入。
''')
print(json.dumps({'protocol_sha256':sha(unit/'PROTOCOL.json'),'frozen_utc':p['frozen_utc']}))
