"""Audit completed units and write delivery documentation. No model mutation."""
from common import *

def main():
 guard();state('FINAL_READONLY_REPLAY')
 excluded={'stdout.log','stderr.log','ASTRA_RUNTIME_FINAL.md'}
 def frozen_tree():return {str(p.relative_to(ROOT)):sha(p) for p in ROOT.rglob('*') if p.is_file() and p.name not in excluded}
 before=frozen_tree();t=time.monotonic()
 cmd=[sys.executable,'-B',str(CODE/'verify.py'),'--readonly','--replay']
 run=subprocess.run(cmd,capture_output=True,text=True)
 after=frozen_tree();assert before==after,'Readonly verification modified task files'
 (ROOT/'logs/VERIFY_REPLAY.log').write_text(run.stdout+run.stderr)
 assert run.returncode==0,run.stderr
 verification=json.loads(run.stdout);verification.update(command=cmd,exit_code=run.returncode,task_file_tree_unchanged=True,tree_file_count=len(before),seconds=time.monotonic()-t)
 js(ROOT/'VERIFY_REPLAY.json',verification)
 sources=json.loads((ROOT/'SOURCE_MANIFEST.json').read_text())['files'];after_sources={p:sha(p) for p in sources};assert after_sources==sources
 js(ROOT/'SOURCE_BEFOREAFTER.json',dict(unchanged=True,files_checked=len(sources),files={p:dict(before=h,after=after_sources[p]) for p,h in sources.items()},old_worktree=rollback(),utc=now()))
 log=(ROOT/'logs/TESTS_FINAL.log').read_text();assert 'Ran 17 tests' in log and log.rstrip().endswith('OK')
 js(ROOT/'TEST_RESULTS.json',dict(status='PASS',tests_run=17,failures=0,command=[sys.executable,'-B',str(CODE/'test_runner.py')],log_sha256=sha(ROOT/'logs/TESTS_FINAL.log'),red_logs=['logs/FORMAT_RED.log','logs/RENDER_RED.log'],green_logs=['logs/FORMAT_GREEN_ATTEMPT1.log','logs/RENDER_GREEN_ATTEMPT1.log','logs/TESTS_FINAL.log'],production_readback=verification,not_historical_tests=True))
 observations={
 'scan24':'实际查看0000/0036四格和全景/轨迹contact。房屋、屋顶和窗户保留；joint中窗线与部分边缘变黑，很多后层线被源表面遮住。line-only的屋顶重线/杂线并未被修复。0036源相机原本截到建筑一侧，保持原native framing；转动轨迹包含完整主体，源背景浮片仍存在。',
 'scan65':'实际查看0036四格、全景/轨迹contact。颅骨、眼眶、牙齿与下颌保留；joint表面细碎纹理明显增多，局部像裂纹，不能称为干净特征线。背面线被遮挡是联合合成结果，没有人为将线前移。',
 'ficus':'实际查看test_r_14四格、全景/轨迹contact。叶片、枝干和花盆保留；原C线资产在顶端向右上/右方伸出的长毛刺在joint和运动中仍明显，未删核、未夹断、未提高opacity或偏置深度。叶片重叠区域仍有杂线。'}
 inspected=[ROOT/'delivery/OVERVIEW.jpg']
 for s in SCENES:inspected.append(ROOT/'scenes'/s/'media/CONTACT_FIRST_EXTREMES_MIDDLE_RETURN.jpg')
 for s,v in [('scan24','0000'),('scan24','0036'),('scan65','0036'),('ficus','test_r_14')]:inspected.append(ROOT/'scenes'/s/'views'/v/'COMPARISON.jpg')
 js(ROOT/'VISUAL_REVIEW.json',dict(tool='view_image',qualitative_executor_review=True,not_blind_or_independent_human_evaluation=True,images={str(p):sha(p) for p in inspected},observations=observations,verdict='MERGE_DELIVERED_WITH_INHERITED_VISUAL_LIMITATIONS'))
 stats={};models={};movies=json.loads((ROOT/'VIDEO_PROGRESS.json').read_text());assert len(movies['completed'])==3 and not movies['failures']
 for s in SCENES:
  models[s]=json.loads((ROOT/'scenes'/s/'model/AUDIT.json').read_text())
  rows=[json.loads(p.read_text()) for p in (ROOT/'scenes'/s/'views').glob('*/AUDIT.json')];assert len(rows)==5
  stats[s]=dict(views=rows,RGB_MAE_range=[min(r['RGB_MAE_vs_frozen'] for r in rows),max(r['RGB_MAE_vs_frozen'] for r in rows)],reference='official native RaDe' if s!='ficus' else 'earlier vanilla-GS CPU render, not native RaDe',mean_source_seconds=float(np.mean([r['source_seconds'] for r in rows])),mean_joint_seconds=float(np.mean([r['joint_seconds'] for r in rows])))
 audit=dict(renderer='CPU EWA, approximate, full SH3, single combined projected list and center-depth sort',official_code_anchors={'scene/gaussian_model.py':'115-120 scaling, 141-165 opacity compensation, 513-555 loader','gaussian_renderer/__init__.py':'get_scaling_n_opacity_with_3D_filter','submodules/diff-gaussian-rasterization/cuda_rasterizer/forward.cu':'perspective Jacobian/clamp and filtering; CPU not CUDA-equivalent','utils/sh_utils.py':'full degree-3 eval_sh read-only'},source_code_hashes={p:h for p,h in sources.items() if '/official_code_fix_v01/source/' in p},scene_diagnostics=stats,config=json.loads((ROOT/'CONFIG.json').read_text()),limitations=['Mean-depth ordering, local perspective covariance and finite footprint approximate source surface visibility.','CPU center-depth diagnostic is not native affine camera-z.','Ficus source floor variance .3, ink floor .0144; DTU both .0144. One joint sort, no layer overlay. Generic viewers may impose another pixel floor.','No GPU official rendering/loading was run.','Equal center-depth ties may depend on input order; permutation control uses distinct depths.','Near plane .2 and 3-sigma footprint clipping are rendering conventions, not world asset pruning.'])
 js(ROOT/'RENDERER_AUDIT.json',audit)
 table='\n'.join(f"| {s} | {a['source_count']:,} | {a['ink_count']:,} | {a['merged_count']:,} | {a['source_raw_opacity_positive_inf']} |" for s,a in models.items())
 rgb='\n'.join(f"- {s} source-only RGB MAE：{v['RGB_MAE_range'][0]:.6f}–{v['RGB_MAE_range'][1]:.6f}（{v['reference']}）；平均 source/joint {v['mean_source_seconds']:.2f}/{v['mean_joint_seconds']:.2f} 秒/帧。" for s,v in stats.items())
 text=f'''# C2L50 8BUILD C 与原3DGS联合模型交付

已实际导出、重载并渲染三个独立合并模型。采用的唯一线基线是 `c2l50_multiview05_v01/arms/C`，不含A/B、分类资产或去刺修复。源和线保存在同一个PLY中；渲染将两者一起投影、排序、合成。本次完成的是参数合并交付，不宣称线重建质量改善。旧成果全部保留。

## 真实资产与输入条件

| 场景 | 原source核 | C线核 | 合并总核 | source raw opacity +Inf |
|---|---:|---:|---:|---:|
{table}

DTU scan24/scan65 使用 REGISTRY 指定的官方配置修复 C24 30k 源模型，保留3D filter和完整SH3。Ficus是原vanilla3DGS，不称RaDe训练模型。全部坐标沿用原scene单位；不平移、缩放、中心化或声称单位为米。源 checkpoint 与线PLY/NPZ/parent/control等共 {len(sources)} 个输入文件SHA已前后核验。

## 两类真实合并文件

每场景 `scenes/<scene>/model/merged_native.ply` 原source为prefix，原有每字段值和位模式保持exact，包括SH、scale、rotation、filter与+Inf opacity。后缀是原C线PLY，原字段同样exact；高阶SH补0，`filter_3D=0`，避免源3D filter再次扩展线核。source+line并非两层viewer临时显示。源与线区间、原ID、primitive/internal_piece/arc以及完整length/control映射在RANGES/GROUP_MAPPING及sidecars，可拆分回原序列。

官方激活语义为 s_eff²=s²+f²，alpha_eff=sigmoid(raw_alpha)*sqrt(prod(s²)/prod(s²+f²))。+Inf经sigmoid得到1，不是损坏值，不删源核。native文件保留这些原raw参数。

`merged_portable.ply` 单独导出标准3DGS字段，将上述filter烘焙到log scale/logit opacity，完整SH不变。有限logit策略epsilon=1e-7，本批三个模型实际clip数量均0：DTU原+Inf在filter补偿后低于1，已转成有限logit；Ficus没有+Inf。native和portable raw参数不是bitexact同一格式。实际最大effective covariance相对Frobenius误差 <7.60e-7、opacity绝对误差 <1.25e-8，means误差0；Ficus烘焙前后effective量exact。

线PLY原float32与原canonical NPZ的float64有限精度差单独核验：所有scene坐标最大差<2.39e-7、covariance相对差<4.63e-7、opacity差<1.26e-8、黑色颜色差0。不是重新拟合或调整线。模型中没有人为把线移动到表面前方。

## 真实联合渲染及可视化

CPU EWA读取合并PLY，激活完整covariance/full SH3。source+line一次全局中心深度排序，alpha前到后合成：C=Σ(T_i alpha_i color_i)+T_end background。没有先渲染RGB再乘ink，也没有用2D overlay冒充联合模型。测试显示前线/后线正确受source transmittance影响，完全透明线等于source，无source等于line，非同深度的输入顺序置换结果一致。

DTU五相机0000/0012/0024/0036/0048，native777×581，完整fx/fy/cx/cy、COLMAP W2C/整数pixel center不变。Ficus五相机test_r_1/79/14/99/7，800×800，沿用已验证转换后的W2C。没有新拟合；这些相机历史已看过，不是新blind验证。

每相机四格为冻结reference / 同renderer source / line-only白底 / true joint；曝光gain固定1。DTU source/joint用原黑背景，Ficus白背景。line-only不加source遮挡，因此用于揭示原始线几何，不代表那些线在joint中都应该可见。总计15张native尺寸四格图、每scene5视图总板以及英文OVERVIEW。

{rgb}

这些误差只是CPU近似与既有reference差异，不是官方CUDA等价证明；Ficus更是CPU-to-CPU对照。CPU投影用C24 Jacobian clamp，中心不clamp，near=.2，3σ footprint，中心深度排序。源和线world covariance未改，Ficus源与线各自保留既有pixel floor（.3与.0144）；通用viewer统一floor时可能显示更粗/不同。native RaDe affine surface depth与CPU中心median depth不是同一量，深度差诊断不作为质量准确率。

三个33帧视频均实际从固定合并模型逐帧渲染，共99帧；每段17个不同姿态的往返轨迹，非33个独立姿态。原始source与joint两列同步，源本身参与每帧遮挡。H264/yuv420p/faststart完整解码均33帧；独立首尾重渲染数组bitexact。没有旧视频、图像warp或逐帧检线。三段实际耗时约216/149/95秒。已通过图像工具查看首/极值/中/返程contact和弱相机静态图。

## 实际视觉判断与保留缺陷

'''+'\n\n'.join(f'**{s}**：{o}' for s,o in observations.items())+f'''

因此本次状态为 DONE_WITH_LIMITATIONS：完成合并及可复现交付，不声称去掉毛刺、所有轮廓显现或3D线科学重建成功。源表面遮住线是预期联合合成；若希望线始终显在前方，需要另一种艺术化策略，本次未执行。

## 测试、保护与可恢复过程

本轮新增17项测试全部通过：字段/SH/prefix、filter/+Inf/portable、ID、PLY往返/full covariance、解析单Gaussian、前后遮挡、非RGB相乘、顺序置换、透明/空source、完整相机、near/offscreen、fullSH与SPD。FORMAT/RENDER两组真实RED日志和第一GREEN日志保留。没有挪用旧31项测试；没有调宽fixture容差。独立 `verify.py --readonly --replay` 对三个merged PLY重载/逐字段审计，再重渲染一个指定相机与保存数组bitexact；验证前后输出文件树不变。

三场景批次最初在写ROLLBACK_AFTER文件名时发生Path+str异常；错误发生在模型及5相机已经封存之后。保留原失败代码/日志/计数，修复新任务记账代码后从封存单元恢复，实际exit0，没有重复计算或修改模型。源码改动仅新worktree专属目录；旧worktreeHEAD/branch/index/status和1727文件快照、893个Python文件均核验不变。每stage资源检查，全部CPU最多2线程，无GPU/网络/训练/环境安装。

## 文件入口

输出绝对根：`{ROOT}`。

- `delivery/OVERVIEW.jpg`；`delivery/<scene>_FIVE_VIEWS.jpg`。
- `scenes/<scene>/views/<view>/COMPARISON.jpg`，另有原尺寸独立PNG及渲染数组。
- `scenes/<scene>/media/<scene>_SOURCE_JOINT.mp4` 和full decode/return验证。
- `downloads/<scene>_C2L50_8BUILD_JOINT_MODELS.zip`：两种实际合并PLY、映射、parent/control。大包提供40MiB分块与SPLIT清单；保留原完整包。
- `downloads/PREVIEWS.tar.gz`、`DELIVERABLE_CODE.tar.gz`，配SHA和统一MEMBERS清单。
- `FORMAT_ZH.md`、`RUN_COMMANDS.md`、`SOURCE_MANIFEST.json`、`RENDERER_AUDIT.json`、`TEST_RESULTS.json`、`VERIFY_REPLAY.json`。

所有压缩成员采用相对安全路径，不含links/../absolute项。重组脚本实际构建一次完整文件并对SHA，再仅删除本任务可重建重组临时副本。未删除历史失败证据。封存报告为ASTRA_FINAL.md；外部runner的ASTRA_RUNTIME_FINAL.md不进入seal。
'''
 (ROOT/'REPORT_ZH.md').write_text(text)
 (ROOT/'RUN_COMMANDS.md').write_text(f'''# 本轮实际执行与复跑

工作目录 `{CODE}`。Python `{sys.executable}`（只读环境），每次带 `-B`；common限制2CPU/线程，禁用GPU可见设备但未启动GPU。

1. C++构建实际argv/exit/源SHA见BUILD_RECEIPT.json：`g++ -O3 -std=c++17 -shared -fPIC ewa.cpp -o {ROOT}/build/libjoint.so`。
2. RED：`python -B -m unittest test_format -v`；实现后相同命令GREEN。renderer同理 `test_render`。保留四个相应日志，最终 `python -B test_runner.py` 实际17/17。
3. 首个完整单元：`python -B produce.py --scene scan24 --view 0000`。三场景静态 `python -B batch.py`，记账异常后修复恢复同一命令（sealed units只验证不重算），日志STATIC_BATCH/STATIC_BATCH_RESUME。
4. 视频：`python -B movie.py`。实际ffmpeg参数、全解码输出与每帧耗时见scenes各media/VALIDATION及logs/MOVIES.log。`python -B figures.py` 生成overview/native contacts。
5. 独立校验：`python -B verify.py --readonly --replay`；全过程只读，由外层捕获stdout再写验证receipt。
6. 文档/来源复核：`python -B finalize.py`；只重放合并模型、不做训练或模型修改。封存后不要重复写报告。
7. 本地提交仅本源码目录；实际commit见LOCAL_CHECKPOINT.json。`python -B package.py` 拒绝覆盖已有下载包，逐成员哈希和分块真实重组校验。
8. 收到大包分块：`python3 reassemble.py path/to/<scene>_C2L50_8BUILD_JOINT_MODELS.zip.SPLIT.json --output rebuilt.zip`。输出不得存在。省略--output只stream验证。

独立verify无需重建模型或重渲染全视频；--replay只在内存逐场景渲染一相机。已有build/libjoint.so来自本轮源码。新机器可用相同g++命令编译，需按README配置源码/输出根和只读源依赖；没有共享env安装步骤。
''')
 (ROOT/'ASTRA_FINAL.md').write_text(f'''# 合并交付完成：C2L50 8BUILD arms/C

三个实际合并Gaussian模型已导出和重载验证，原source完整SH3/prefix字段exact，原C线geometry/opacity/colors不改。

| 场景 | source | C线核 | 合并核 | raw +Inf |
|---|---:|---:|---:|---:|
{table}

17项本轮测试通过；逐场景重载重渲染bitexact；15张静态四格、3段33帧真实joint往返视频全部完整解码（总99帧，各17不同姿态），首尾独立渲染一致。GPU官方CUDA未执行，CPU EWA近似限制明确。

源和线在同一PLY并共同排序合成；源遮住后方线是预期结果。Ficus原长毛刺、头骨细碎表面纹理和建筑重线未修。没有自动去刺、重拟合或训练。原模型/线资产SHA及旧worktreeHEAD/index/源码均保持不变。

完整目录：`{ROOT}`
预览：`{ROOT}/delivery/OVERVIEW.jpg`
报告：`{ROOT}/REPORT_ZH.md`
模型：`{ROOT}/downloads/<scene>_C2L50_8BUILD_JOINT_MODELS.zip`（每包native+portable+mapping）。大于45MiB提供40MiB分块、SPLIT清单和真实重组SHA验证。
视频：`{ROOT}/scenes/<scene>/media/<scene>_SOURCE_JOINT.mp4`
预览包/代码包：`{ROOT}/downloads/PREVIEWS.tar.gz`、`DELIVERABLE_CODE.tar.gz`。

native source字段exact；portable烘焙filter，epsilon1e-7实际clip0，effective covariance最大相对误差<7.60e-7，opacity<1.25e-8。不能称portable raw bitexact或CUDA等价。

状态DONE_WITH_LIMITATIONS；独立branch本地commit详情见LOCAL_CHECKPOINT.json；不push/merge。停止，不自动继续分类/mesh/去刺。
''')
 review('05_DELIVERY_REVIEW_GO_LOCAL_COMMIT_PACKAGE','GO：3场景model逐字段/重载验证、15静态、99新帧和首尾一致均通过；实际view_image审查overview与3contact。格式交付成立，未修视觉毛刺须明确保留。下一步仅secret-pattern检查本任务源码、本地专属目录commit、安全打包/分块/真实重组和只读最终校验，不允许模型修改或后续研究。若任一包hash/资源失败，停止该包并记录失败。预算检查见STATUS。', [ROOT/'VERIFY_REPLAY.json',ROOT/'TEST_RESULTS.json',ROOT/'VISUAL_REVIEW.json',ROOT/'VIDEO_PROGRESS.json',ROOT/'SOURCE_BEFOREAFTER.json'])
 state('READY_FOR_LOCAL_COMMIT_AND_PACKAGE',completed_scenes=3,static_views=15,video_frames=99,tests_passed=17,children=[])
 print(json.dumps(dict(verification=verification['status'],resources=guard())),flush=True)
if __name__=='__main__':main()
