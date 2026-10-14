import json,shutil,time,html
import numpy as np
from common import *
from selection_boards import CHOICES
from render_boards import board

counts=json.loads((T/'COUNTS.json').read_text());registry=json.loads((T/'REGISTRY.json').read_text())['views'];presets=json.loads((T/'PRESETS.json').read_text())['presets']
# Keep the source RGB values (and only RGB) in the deliverable for exact replay.
portable=[]
for e in registry:
    with np.load(e['path']) as z:rgb=z['rgb']
    p=T/'scenes'/e['scene']/e['view']/'input_rgb_float32.npz'
    np.savez_compressed(p,rgb=rgb)
    with np.load(p) as z:np.testing.assert_array_equal(z['rgb'],rgb)
    portable.append(dict(scene=e['scene'],view=e['view'],path=str(p),sha256=sha(p),source_path=e['path'],source_sha256=e['sha256'],rgb_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(),no_depth_or_alpha=True))
write(T/'PORTABLE_RGB_MANIFEST.json',portable)
# Verify the separately exercised one-preset CLI.
a=T/'cli_replay'/'scan24_0000_C2U20'/'maps.npz';b=T/'scenes'/'scan24'/'0000'/'presets'/'C2U20'/'maps.npz'
with np.load(a) as za,np.load(b) as zb:
    for k in za.files:np.testing.assert_array_equal(za[k],zb[k])
write(T/'CLI_REPLAY.json',dict(command='apply_preset.py --input <native scan24/0000 input> --preset C2U20 --output <task>/cli_replay/scan24_0000_C2U20',bitexact=True,all_five_arrays=True))
pilot=sum(json.loads(p.read_text())['total_seconds'] for p in (T/'scenes').glob('*/*/COMPLETE.json'))
peak=max(json.loads(p.read_text())['peak_rss_MiB'] for p in (T/'scenes').glob('*/*/COMPLETE.json'))
write(T/'RESOURCE_REPORT.json',dict(all_view_processing_seconds=pilot,peak_child_rss_MiB=peak,cpu_affinity_first_two_allowed_cpus=True,max_math_threads=2,gpu_used=False,new_models=0))
rows=json.loads((T/'METRICS.json').read_text())['rows']
def row(s,v,id):return next(x for x in rows if x['scene']==s and x['view']==v and x['preset']==id)
table='| 图 | 预设 | 候选像素 | 骨架像素 |\n|---|---|---:|---:|\n'
for s,v,ids in [('scan24','0000',['A20','A40','C2U20','B00']),('scan65','0000',['A20','A40','C1L50','B00']),('ficus','train_r_80',['A20','A30','C1U20','B00'])]:
    for id in ids:
        r=row(s,v,id);table+=f'| {s}/{v} | {id} | {r["marked_pixels"]} | {r["skeleton_pixels"]} |\n'

report=f'''# Spatial RGB 检线强度与纹理抑制实验

已完成 **16个预设×11张原生视角=176组** 检线结果。当前建议先比较建筑 **C2U20 / A40 / C1L50**、头骨 **A40 / C1L50 / C2U20**。Ficus参考图可先比较 **A30 / C1U20 / M75T30**。这是供用户选图的暂定范围，不是已选定的生产参数；没有自动重跑05、融合、训练或生成新3D模型。

实际看图后，建筑的较粗尺度比单纯提高阈值更有针对性地减少屋瓦密纹；头骨提高候选阈值能大幅减少桌面纹理，同时保留主要轮廓。不过仍有明暗引起的内部线、断点和重复轮廓，没有证据证明已得到真实信噪比最高的图。纯结构分支B00是明确过度抑制负例，不能作为“干净即最好”的答案。

## 输入与可比条件

scan24建筑、scan65头骨来自刚完成的native RaDe 05任务：官方修正C24配置30k原生渲染RGB，777×581，scan65使用其原有eigen-fallback来源。每个场景固定0000/0024/0048为BUILD，0012/0036为历史已见的构建保留视角，仍属于原GS训练视角，不是盲测或GS泛化实验。输入NPZ字节与旧输出清单核验，同时与更早原始CHW RGB逐元素相同。

Ficus仅使用固定train_r_80，800×800，来源是原有vanilla3DGS渲染缓存；它与DTU的GS条件不同，不能据此直接做跨场景数值排名。RGB均保持原float32值，包括少数大于1的渲染值；只在RGB图片显示时截断到屏幕范围。算法没有读取深度、alpha、相机参数或语义掩码，没有把旧CPU头骨RGB替换成官方输入，也没有艺术着色。

所有预设在查看本轮EVAL结果前冻结；先运行建筑0000、头骨0000与Ficus参考图，再把完全相同的参数用于剩余8张图。候选名单来自先行参考图，并保留冻结记录。之后查阅全5视角只是透明诊断，不改变预设。若用户根据这些图选参数，后续这些视角也不能再称盲测。

## 为什么原算法会留下杂线

原boundary.py SHA256保持11bbb41a762f252d9eeb4ea3f0a8399ed026139d9490bb8cf161bc815e05dd30。原尺度[0.7,1.4,2.8]上的彩色结构张量提供方向、响应与相干性；detail分支保留脊线并乘(.55+.45×confidence)，随后沿切向补充支持。structural分支在法线方向±9像素拟合单调颜色过渡，并检查两侧平台、残差、反向变化、对比度与相干性，再做weak=.075/strong=.22的连通滞后筛选。

最后取 **union=max(detail,structural)**。因此某条细纹即使不符合结构分支的单次过渡模型，仍能经detail进入union。weak/strong并不是整个union的全局门槛。建筑0000的68445个被分析profile中只有2813个通过结构有效性条件，头骨0000为94533中5983个；这说明结构分支严格，**不说明其余全是噪声**。多窗格、相邻叶片、牙齿等有效结构同样可能不符合这个局部平台假设。原代码还在profile拟合时排除11像素边框；本轮没有偷偷更改。

## 实际运行的16个预设

| 家族 | IDs | 改变内容 |
|---|---|---|
| A | A10/A15/A20/A30/A40/A50 | 原union不变，严格darkness>T，T=.10/.15/.20/.30/.40/.50；A20为原05候选基线 |
| B | B75/B50/B25/B00 | 原尺度，max(structural,lambda×detail)，lambda=.75/.5/.25/0，T=.20 |
| M | M75T30/M50T30 | 同时用lambda=.75/.5与T=.30，两个因素同时变化 |
| C1 | C1U20/C1L50 | 尺度[1,2,4]，lambda=1/.5，T=.20 |
| C2 | C2U20/C2L50 | 尺度[1.4,2.8,5.6]，lambda=1/.5，T=.20 |

所有gain=1、ink_sigma=.5。先计算soft，再得到原ink函数的darkness，marked=(darkness>T)，最后skeletonize(marked)。候选软图显示1-darkness×marked，没有门槛后再模糊或逐图归一化。原未截断soft图、真正黑白候选、骨架分别保存。

降低detail占比既改变候选集合，也降低部分保留线的灰度。因此“看起来更淡”不是信噪比提高的充分证据。本轮另给全黑二值候选对照；A系列也只改变集合，不提高保留线亮度。C系列会改变方向、脊线位置、尺度响应及profile，而不只是原图删线，不能称DEFAULT的同义名字。

## 图像审查及暂定选择

**建筑scan24：优先打开C2U20。** 在0000/0012可见屋瓦和砖墙细纹减少，阶梯山墙、窗列、主要檐口保留。0036/0048的屋瓦仍有成片残留，说明强纹理没有被语义识别。放大窗格可见C2U20把一些细内框合并成较少轮廓，也有短缺口；它更简洁，但不是无损。A40保留更细的窗格和旧脊线位置，然而在0036仍保留较密屋瓦，不是干扰最小的选择。C1L50是偏淡的折中，须对照二值图，不能把灰度降低全算作删掉干扰。

**头骨scan65：优先比较A40与C1L50。** A40在0000/0012/0036明显削弱桌面碎纹，颅顶、眼窝、鼻腔和下颌仍可辨认。0036侧后颅骨轮廓保留，但颞部、颧骨附近内部杂线仍多；提高阈值不能知道哪些明暗线具有结构意义。C1L50再减少部分细线，同时减淡牙齿和鼻腔细节，二值图仍显示局部碎片。C2U20保持较黑、较少的内轮廓，适合偏简洁的表达，但某些齿间细线会合并，并且背景残点可能多于A40。B00虽然白，头部轮廓与面部结构变得断续，不推荐。

**Ficus：保守先比较A30与C1U20，M75T30作为更淡档。** 原图背景已较干净，密线中相当一部分来自真实重叠叶片和枝条；这与头骨桌面不一样。A30比A20去掉一些弱纹而仍保留细叶和主干；C1U20减少局部双重细轮廓，但一些相邻叶缘会简化。M75T30减少部分盆纹与弱细线，叶柄也会变弱。C2尺度更容易把小叶相邻轮廓混在一起，不能据“更少线”就选它。B00几乎只剩花盆边缘和稀疏叶片碎段，是主体删除负例。这里只有一个Ficus视角，不能宣称跨视角结论。

完整原生画面是主结果；原输入建筑本来就有部分建筑延伸到画面边界，实验不额外裁切或补全。六个手选局部框仅用于放大说明屋瓦/窗格、颅顶/眼鼻牙、叶柄/花盆的代价，框的位置保存，**从未作为检测掩码**。

## 数值只用于核对，不能冒充SNR

{table}

全部176行见METRICS.csv/json。候选像素是darkness>T的数量；骨架像素不是3D长度；分量是8邻域连通域；端点/结点统计是骨架像素的8邻域度数，斜向相邻会导致结点数量偏大，不能当成有意义笔画数。表中大量减少既包含纹理减少，也可能包含主体细节损失。

另保留两组真实执行的合成机制控制。第一组对比度.04的单台阶通过structural拟合，各阈值都保留150个弱边候选；它没有证明弱边会被删，不能强行解读。新增固定对比度梯度.01/.02/.03/.04后，.01/.02台阶从A10的150个候选变成A20及以上的0，而同图强重复纹理仍有4050个候选。这直接说明阈值排序不等于重要性排序，但不提供真实场景GT或信噪比分数。原控制与负例都保存。

## 验证与交付边界

16项单元测试经过RED缺模块失败、实现后GREEN；没有放宽阈值或删除失败控制。176组NPZ与图片逐项回读，重新从字段计算的所有数组一致；3张参考图重新执行分析位级一致；10张DTU图的A20 union/darkness/marked与旧05缓存位级一致。单预设CLI也真实重算C2U20并逐数组一致。29个冻结来源文件重哈希不变，另确认旧boundary原文件哈希不变。全部视角处理时间合计{pilot:.1f}秒，峰值子进程RSS约{peak:.1f}MiB，CPU限制在2个核，无GPU。

每组保存soft/darkness/marked/skeleton/candidate_darkness及recipe。RGB原float32仅RGB的便携副本也提供，PNG不能替代它作位级重算输入。PREVIEWS是选图入口，NATIVE_IMAGES包含176张未裁切候选PNG，DELIVERABLE包含全部软字段/二值/骨架、代码、配置、测试及来源。没有选择一个预设自动传入05，当前3D模型数为0。图像更干净不等于多视角几何已更可靠，后续需用户选定后另行检验。
'''
(T/'REPORT_ZH.md').write_text(report)
(T/'SELECTION_GUIDE_ZH.md').write_text('''# 先看这些图

已交付16档×11视角。A20是现有检线基线；没有自动替换05。

| 场景 | 建议先比较 | 主要取舍 |
|---|---|---|
| scan24建筑 | C2U20、A40、C1L50 | C2U20屋瓦干扰更少，细窗格有简化；A40细节更多但屋瓦仍密；C1L50更淡 |
| scan65头骨 | A40、C1L50、C2U20 | A40轮廓较明确；C1L50更简淡但部分牙齿变弱；C2U20简化小内部边界 |
| Ficus参考 | A30、C1U20、M75T30 | 保住细叶和枝干优先，不能照搬头骨的强抑制 |

先看selection/*_CHOICES.jpg，再看*_BINARY.jpg排除“只是变淡”的错觉。全5视角在*_ALL5.jpg。原生单图在scenes/<scene>/<view>/presets/<ID>/candidate.png；marked.png为全黑候选，skeleton.png为骨架。

更完整系列：THRESHOLD.jpg为6档阈值，MIX.jpg为分支占比，SCALE.jpg为尺度对照，DIAGNOSTICS.jpg包含原RGB及S/D分支。B00是删除过多的负例，请勿按白色面积选最好。没有GT，不能给出真实SNR第一名。候选ID只是暂定建议，最终由用户根据图选择；本轮到此停止。
''')
(T/'ASSET_FORMAT_ZH.md').write_text('''# 检线资产格式

scenes/<scene>/<view>/input_rgb_float32.npz：rgb，H×W×3 float32，原渲染值逐元素保留（可略大于1）。无深度/alpha，出处与SHA见PORTABLE_RGB_MANIFEST。RGB.png仅屏幕展示。

fields_native/medium/coarse.npz：detail、structural、union、normal、confidence、magnitude、profile_confidence、width_map、classmap。field只按三套尺度计算一次，所有预设引用它们。未保存庞大profile采样数组，可用原RGB精确重算。

presets/<ID>/maps.npz：soft为max(structural,lambda*detail)；darkness为1-boundary.ink(soft,gain=1,sigma=.5)的第一通道；marked bool=darkness>T（严格大于）；skeleton bool=skimage.skeletonize(marked)；candidate_darkness=darkness*marked。浮点地图float32，均为原生H×W。

candidate.png是1-candidate_darkness的8bit显示；marked.png/skeleton.png为黑色有效像素、白底。没有二次模糊，没有按图调亮度。recipe.json包含完整分析参数、阈值、分支系数、输入hash。不得拿candidate.png重新阈值代替float32地图用于精确复现。

后续05若获用户选择，需显式读取该recipe的soft/darkness/marked，然后使用既定骨架过程；不能只改变展示gain便声称用了该预设。本轮不修改05，不导出3D Gaussian或直接曲线。
''')
cmd=f'''# 实际运行与重放

工作目录：{C.parent.parent}
只读解释器：{B}/official_code_fix_v01/env/bin/python
代码目录：{C}
cpu_entry.py固定2核亲和性/数学线程并禁写旧pycache。

以下命令均已真实执行（RED测试第一次因detector尚未实现返回1，GREEN及最终测试返回0）：
```
PY={B}/official_code_fix_v01/env/bin/python
CODE={C}
"$PY" -B "$CODE/cpu_entry.py" "$CODE/freeze.py"
"$PY" -B "$CODE/cpu_entry.py" "$CODE/test_detector.py"
"$PY" -B "$CODE/cpu_entry.py" "$CODE/run.py" --stage pilot
"$PY" -B "$CODE/cpu_entry.py" "$CODE/selection_boards.py"
"$PY" -B "$CODE/cpu_entry.py" "$CODE/run.py" --stage rest
"$PY" -B "$CODE/cpu_entry.py" "$CODE/analytic_controls.py"
"$PY" -B "$CODE/cpu_entry.py" "$CODE/contrast_control.py"
"$PY" -B "$CODE/cpu_entry.py" "$CODE/restyle_analytic.py"
"$PY" -B "$CODE/cpu_entry.py" "$CODE/selection_boards.py"
"$PY" -B "$CODE/cpu_entry.py" "$CODE/verify.py"
"$PY" -B "$CODE/cpu_entry.py" "$CODE/test_detector.py"
"$PY" -B "$CODE/cpu_entry.py" "$CODE/apply_preset.py" --input {B}/depth_guided_native_dtu_v01/scenes/scan24/inputs/0000.npz --preset C2U20 --output {T}/cli_replay/scan24_0000_C2U20
```
freeze与run会拒绝覆盖已有冻结/完成单元。要单图复算，用apply_preset并指定本任务内新的、尚不存在输出目录；可把input换成便携input_rgb_float32.npz。run只生产检测图，不存在3D调用。代码的common.py为当前任务路径适配；异机需指向解包目录/输入路径，不要修改旧实验。
'''
(T/'RUN_COMMANDS.md').write_text(cmd)
# Actual image-tool inspections recorded as qualitative evidence, not all-image blind scoring.
review=[]
for scene in ['scan24','scan65','ficus']:
    v='train_r_80' if scene=='ficus' else '0000'
    for name in ['MIX','SCALE']+(['THRESHOLD'] if scene in ['scan24','scan65'] else ['DIAGNOSTICS']):review.append(str(T/'scenes'/scene/v/f'{name}.jpg'))
for scene in ['scan24','scan65']:
    for v in ['0012','0036']:review.append(str(T/'selection'/f'{scene}_{v}_CHOICES.jpg'))
for name in ['scan24_C2U20_ALL5.jpg','scan65_A40_ALL5.jpg','scan65_C1L50_ALL5.jpg','scan65_0036_BINARY.jpg','scan24_ROI_windows.jpg','scan65_ROI_eyes_nose_teeth.jpg','ficus_ROI_leaves_stems.jpg']:review.append(str(T/'selection'/name))
write(T/'VISUAL_REVIEW.json',dict(utc=utc(),tool='view_image',actually_inspected_files=[dict(path=p,sha256=sha(p)) for p in review],judgement='Qualitative assistant inspection; not blinded user preference or GT SNR',per_scene=dict(scan24='C2U20 reduces dense roof texture; window small inner frames simplify and some gaps remain; 0036 roof still has texture',scan65='A40 and C1L50 remove much table texture; eye/nose/jaw remain; internal fragments and detail tradeoffs visible, including 0036',ficus='Pure structural destroys plant detail; moderate A30/C1U20 are safer options, only one reference view'),selection_is_provisional=True))
# Browser index with native candidate links, all 16 presets; no hidden subset.
parts=['<!doctype html><meta charset="utf-8"><title>Spatial RGB preset gallery</title><style>body{font:16px sans-serif;margin:24px;background:#f2f4f6}section{margin:30px 0}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}img{width:100%;background:white}a{color:#164268}article{background:white;padding:12px}</style><h1>Spatial RGB preset gallery</h1><p>RGB only. 16 presets × 11 native views. Click images for native size. No 3D model created. See SELECTION_GUIDE_ZH.md.</p>']
for e in registry:
    rel=f'scenes/{e["scene"]}/{e["view"]}';parts.append(f'<section><h2>{e["scene"]} / {e["view"]}</h2><p>{html.escape(e["condition"])} | {html.escape(e["split"])}</p><p>'+ ' | '.join(f'<a href="{rel}/{name}.jpg">{name}</a>' for name in ['DIAGNOSTICS','THRESHOLD','MIX','SCALE'])+'</p><div class="grid">')
    for p in presets:
        path=f'{rel}/presets/{p["id"]}';parts.append(f'<article><strong>{p["id"]}</strong> — T={p["threshold"]}, detail={p["detail_lambda"]}, {p["analysis"]}<a href="{path}/candidate.png"><img loading="lazy" src="{path}/candidate.png"></a><a href="{path}/marked.png">Binary candidates</a> | <a href="{path}/skeleton.png">Skeleton</a> | <a href="{path}/recipe.json">Recipe</a></article>')
    parts.append('</div></section>')
(T/'GALLERY.html').write_text('\n'.join(parts))
test=json.loads((T/'TESTRESULTS.json').read_text());test.update(cli_replay_bitexact=True,portable_rgb_bitexact=11,final_test_log='logs/TEST_FINAL.log');write(T/'TESTRESULTS.json',test)
status('REPORTS_WRITTEN',children=[],next_action='Package and independent archive member/hash verification')
print('Reports, portable RGB and gallery written')
