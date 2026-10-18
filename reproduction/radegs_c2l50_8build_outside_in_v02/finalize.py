"""Delivery only; never runs scientific fitting or changes sealed evidence."""
from env import *
from io_checks import safe_member,check_members,verify_frozen
import tarfile,io

def newtext(name,text):
 p=ROOT/name;assert not p.exists(),p;p.write_text(text.strip()+'\n')

REPORT=r'''
# Outside-in v02：确实生成多块，但尚未获得可靠的大部件结构

本轮完成一次三场景有界 pilot。Ficus 已实际运行共享三块及五块模型，不再把一个二值主体换名字作为“分区”。然而，主方案仍把一部分主干与盆合并、另一部分枝干与叶片混合，不能认证为完整的“盆—主干—叶冠”。建筑、头骨先在主体/地台分离处失败，因此按预冻门槛停止后续正式分区。结论是**诊断执行 PARTIAL；作为结构分区方案 NO_GO**。原 C2L50+8BUILD 线资产和真实 joint 模型完整保留。

## 为什么 v01 只有一个主体，本轮改变了什么

v01 把每幅图独立的颜色/深度分区拿来事后配对，前置主体也不可靠：建筑亮屋顶和头骨暗骨/牙齿漏掉，而地台/桌面会混入。一个主体块只是范围候选，不能回答部件问题。Ficus 虽然范围较好，RGB-depth 大区在 DEV/AUX 没有合格配对；其 RGB-only 是必须认真比较的强对照，已有盆附近配对。

本轮在生成阶段联合 DEV+AUX：先回投**原 source-only 深度可见像素**到同一世界坐标，而非取 source GS 中心或依靠不稳定的核身份。建筑/头骨从两视角共同可见深度尝试支撑平面分离；Ficus 在主体范围合格后，以同一个世界位置、Lab 外观及局部覆盖宽度特征模型生成全部相机的粗区域。没有 graph-cut、watershed、统一网格种子，也没有用 C8 细线或人工像素标签构造主体。

这使“不同相机共用生成模型”成立，但不使“同色块就是同一物理部件”自动成立。模型没有强制连通性或语义知识；它仍可能将空间相近或外观相似的枝叶混在一起。这正是本轮的可证伪限制。

## 研究依据与适配边界

[Papon 等，VCCS，CVPR 2013](https://openaccess.thecvf.com/content_cvpr_2013/papers/Papon_Voxel_Cloud_Connectivity_2013_CVPR_paper.pdf) 的 §3.1–3.4 使用校准多视角 RGB-D、体素邻接及空间/颜色/几何描述子组织 supervoxels，支持先统一空间再组织局部区域的思路。本文没有复制其体素连通、FPFH 或原算法；采用更便宜的共享特征模型作证伪，也不把 supervoxel 当语义部件。

[Felzenszwalb 与 Huttenlocher，IJCV 2004](https://www.cs.cornell.edu/~dph/papers/seg-ijcv.pdf) 的 §2–4 讨论区域内部变化和边界证据，说明紧致特征簇未必对应视觉区域。本轮把 RGB-only、XYZ-only 作为同预算控制，检验主方案是否只按颜色或位置切块。未复现该论文算法。两份全文及文本 SHA 在 SOURCES.json；v01 原文献/方法只读。未声称读到不可访问的分享页正文。

## 冻结输入、相机与公平范围

科学输入是原 `c2l50_multiview05_v01/arms/C`：scan24/scan65/ficus 分别 458490/279616/285956 个 ink 核；source 分别 596467/317817/284835 个。全部保留，没有源核编辑、线筛选、重采样或训练。DTU 为封存 native RaDe RGB/alpha/camera-z；Ficus 为 vanilla GS 的原 CPU 条件平面深度代理，两者不是同一种真值。

| 场景 | 联合拟合 DEV+AUX | 冻结 reserved-analysis |
|---|---|---|
| scan24 | 0000、0024 | 0012、0036 |
| scan65 | 0000、0024 | 0012、0036 |
| Ficus | train_r_80、train_r_7 | test_r_14、test_r_79 |

共12个完整原尺寸画面，DTU 777×581，Ficus 800×800。所有视角历史曝光，DTU 也是源 GS 训练视角；没有新的 blind/GS-heldout 实验声明。reserved 不参与参数、中心或阈值拟合，只查询冻结模型并作固定对照；目标视图自身 RGB/depth 用于该视图推断，这不是仅由 DEV 标签作无图像信息的预测。实际只做一次冻结方案，无保留视角后调参。输入审计中 `source` 展示字段曾误指最后 raw 文件，INPUT_AUDIT_CLARIFICATION 明确纠正出处；模型路径/hash始终以 `model`/`model_sha256` 和封存清单为准，原审计未被悄悄覆盖。

## A：上游首先失效的位置

统一像素世界尺度 `p=z/sqrt(fx*fy)`，完整内参/W2C与整数像素中心。两构建相机等预算取有效深度。若画边覆盖低且总 alpha 覆盖稀疏，则只称 isolated-coverage proxy；否则由下方外围深度提议共享支撑平面，检验双视角支持、中心分离及同侧，平面附近保留 UNKNOWN。没有 p20/1.15 相机深度截断、孔洞填充或删小组件。

**scan24：A NO_GO。** 白屋顶比 v01 保留，但支撑平面实际落在左侧建筑立面。结果把大块白地台卷进主体，将该立面变成 UNKNOWN。`delivery/scan24_PLANE_SUPPORT.jpg` 与四视图图板直接显示这个错误；0012 候选覆盖全画面92.3%仍不能证明主体完整。最先失效的是“外围且两视角一致的平面就是地台”的身份假设，而非缺少更强局部检线。B/C/D 均 NOT_RUN。

**scan65：A NO_GO，局部完整性有改善。** 暗骨/牙齿较少因颜色被排除，但桌面残余仍成为候选，头骨周边及桌面出现很大的 UNKNOWN 带。0036 同样失败。共享平面只是近似几何分离，不能稳定区分对象与桌面；不能用新增保留骨片掩盖背景误入。B/C/D 均 NOT_RUN。

**Ficus：A GO_PROXY。** 原 isolated alpha 支撑保留盆、枝叶和叶间空隙，未新增语义前景能力。DEV→AUX及两个保留视角可比较可见比例约57.7%、63.6%、53.0%；相应可见样本都落在目标候选范围。遮挡、前方不一致、深度未知单列，不作负票；这不是全主体准确率。

## B：真实多块尝试和强对照

从 Ficus 两构建图各取4459个样本，共8918。主特征为归一世界 XYZ、Lab 和投影 coverage 距离变换得到的宽度代理。后者不是物理枝干半径。冻结 K=3 主方案、K=5 诊断；RGB-only 与 XYZ-only 用完全相同样本及 K，运行6个共享模型、24幅区域结果。soft assignment 未达最大值/边际门槛，或离原可见样本邻域过远者保留 UNKNOWN。邻域查询仅限定已观察范围，不把最近点证明为表面。

主 K3 不是一个主体块：DEV 的三个已分配区域分别23320、21100、26346像素，另4642主体像素 UNKNOWN；AUX 也是三个非空块。只是这些块的**身份不合格**。蓝色盆基本连贯，却吞入下部主干；绿色/橙色同时混合叶片、枝干与明暗外观。K5 能分出一部分细干，但也混入叶片，UNKNOWN显著增多，不能事后改为主结果。

| 同预算模型 | DEV↔AUX 合格互配 | DEV↔test14 | DEV↔test79 |
|---|---:|---:|---:|
| XYZ+Lab+width，K3主方案 | 1 | 2 | 1 |
| RGB-only，K3 | 0 | 1 | 1 |
| XYZ-only，K3 | 3 | 3 | 3 |
| XYZ+Lab+width，K5诊断 | 2 | 2 | 1 |

这些互配使用实际深度重投影、双向区域占比和可比较可见分母，不靠颜色编号相同。**XYZ-only 配对最多却仍不合格**：它把冠层切成空间左右块，主干有大段 UNKNOWN；所以配对数不能认证盆/干/叶身份。主方案 K3 在四图的主体 UNKNOWN 约6.2%、5.5%、9.8%、10.6%，也不是准确率。test14 盆底未在构建样本邻域出现，明确 UNKNOWN；没有为好看补标签。

v01 RGB-only 的区域预算更大，原图板予以保留，不能冒充同预算实验。它已有盆相关配对，并非一个完全失败的弱基线；目前证据不能声称 v02 总体优于该强基线。本轮同预算 RGB-only 是额外必要控制。未保证二维/三维区域连通，且使用代理深度的重投影检查存在相关误差；没有物理部件 GT，不报告 precision/accuracy。

## 最终门槛与实际图

Ficus B **NO_GO**：虽然真实多块与部分跨视角对应存在，未同时实现至少两块在各目标视角稳定且盆/干/叶形态完整、互不吞并。因此 C 的原 C8/no-line/shifted-line 边界消融与 D source 软归属均 **NOT_RUN**，不是执行失败、更不是成功。没有新 primitive、GS 模型或视频；静态全图足以呈现当前失败，未以视频掩盖。

建议先看 `delivery/OVERVIEW.jpg`、三个 `*_A_FOUR_VIEWS.jpg`、`ficus_B_FOUR_VIEWS.jpg`；每个 `stageA/<scene>/<view>/COMPARISON.jpg` 保留原RGB、原C8纯线及真正 joint 的只读参考，`stageB/ficus/<view>/PAIRED_ARMS.jpg` 是同预算全部模型。配对图 `ficus_MATCH_*.jpg` 和 `FAILURE_DETAIL_*.jpg` 解释负例；放大框仅后验说明，没有进入算法。总览仅等比例缩放，原尺寸子图全在单相机图板，未裁掉弱视角主体。已实际逐图核读，英文图题/图例。

## 工程证据、保留成果和限制

本轮22项测试通过（A8、regions8、integrity6）；三个真实 RED 日志是缺失实现 API/module 后的失败，再实现 GREEN，**不是每一条22个断言均单独记录RED**。旧测试和旧all-N验证未冒充本轮新增测试。只读 replay 精确重算12个A结果、6共享模型（中心固定1e-12容差）、24个B标签/概率、18组匹配；三个DEV source/line/joint的RGB数组与封存CPU参考逐项相同。source原prefix、线原字段、full SH/filter/+Inf语义保持。这个一致性只证明同一CPU近似实现可重放，不等于官方CUDA；继承v01源渲染校准的边界和Ficus深度代理限制仍在。

148个来源文件hash、旧main893个Python及11个受保护工作树HEAD/branch/index/status核验不变。41个科学单元封存；CPU最多2线程，无GPU、源模型训练或新网络下载模型。整个pilot只写本任务路径。结果报告、源码与数据包提供独立成员SHA与只读verify，不含旧模型或环境。实际提交号见COMMIT.json，包大小/总SHA见PACKAGE_INDEX.json。

当前应继续保留 C2L50+8BUILD/joint 作为可用基线，本轮彩色区域只作诊断，不建议直接驱动大范围NPR编辑。下一步若另行授权，需要先解决“支持平面属于谁”和“哪些连接构成盆/干/冠的部件拓扑”这两种身份约束；继续调 K 或要求更多相同颜色票不能替代这些证据。本轮已按门槛停止，不启动v03。
'''

FORMAT=r'''
# 数据格式与证据边界

- `stageA/<scene>/model/MODEL.json`：两构建视角拟合的支撑平面代理，或isolated-coverage模式；不是source GS几何改动。`FIT_SAMPLES.npz`含真实depth回投world/UV/视角等原始样本。
- `stageA/<scene>/<view>/SUBJECT.npz`：native H×W `candidate`、`unknown`，均bool。假设背景是剩余部分；UNKNOWN从未自动视为主体/真实背景。
- `stageB/ficus/models/TRAIN_OBSERVATIONS.npz`：两个fit视角各4459个可见深度样本，含`view_id`；不是Gaussian中心，非人工标注。
- `models/<arm>_kK.npz`：共享feature centers、归一参考量、observed anchor坐标、模型类型及训练统计。centers是特征簇中心，不是source或ink核，不是物理部件。
- `<view>/<arm>_kK.npz`：`labels` 0=未分配（需联合A mask区分背景与UNKNOWN），1..K=冻结模型ID；`probability`为启发soft assignment而非校准概率，`unknown`、`observed_neighborhood`单列。颜色ID不可充当对应证明。
- `matches/*/FORWARD.npz,REVERSE.npz`：真实重投影/可见性/region对应取样；`COUNTS.json`保留遮挡、前方不一致、未知、可见和互配。没有source_index→region正式映射，Stage D未运行。
- 每个`SEAL.json`封存所在unit，`RESULTS_MANIFEST.json`封存稳定报告、数据与代码。*.MEMBERS.json统一 `{members:{relative_path:{sha256:...}}}`，归档不允许absolute、`..`、links。

旧source与ink的完整SH/filter/+Inf原始参数未改；没有导出新的PLY或高斯资产。所有世界坐标沿原始场景、非米。静态原RGB/depth为封存输入，原joint参考是统一source+ink深度排序的CPUfullSH/EWA，非RGB乘线，也非官方CUDA等价。DTU nativeRaDe与Ficus vanilla+CPUdepth条件分开。参考复制为可视对照，不伪称新重建。

`AGENT_LAUNCH.json`、`ASTRA_RUNTIME_FINAL.md`、外部stdout/stderr及launcher属于可变runtime，排除静态seal；agent终稿是`ASTRA_FINAL.md`。manifest不自包含自身，归档/成员表/sidecar由PACKAGE_INDEX显式列出。
'''

COMMANDS=r'''
# 实际运行顺序与只读复现

工作目录：`/home/u00134/3dgs_line/gaer_c2l50_8build_outside_in_v02/reproduction/radegs_c2l50_8build_outside_in_v02`。
所有Python命令使用只读 `/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B`。env.py只为本进程设CPU线程/affinity≤2与禁用CUDA，未改共享env。

已执行顺序（首次写入用，不要对sealed结果重复执行写入命令）：

1. `preflight.py` → `PREFLIGHT.log`，读取实际v01代码/全图和输入、核验资源与旧状态。
2. `freeze.py` → HYPOTHESIS_FREEZE_ZH/CONFIG/METHOD；reviews00/01先于科学运行。
3. `-m unittest discover -p 'test_stage_a.py' -v`：实现前RED_STAGE_A，实施后GREEN_STAGE_A。
4. `run_a.py --phase fit` → RUN_A_FIT.log；DEV/AUX审查后 `run_a.py --phase reserved` → RUN_A_RESERVED.log。两个DTU停止于A，Ficus允许B。
5. `-m unittest discover -p 'test_regions.py' -v`：RED_REGIONS后GREEN_REGIONS；`run_b.py --phase fit` → RUN_B_FIT.log，冻结诊断后`run_b.py --phase reserved` → RUN_B_RESERVED.log。
6. `diagnose.py` → DIAGNOSE.log；`test_integrity.py`先RED_INTEGRITY，再总回归。测试为3个vertical-slice API RED，不是每个断言单独RED。
7. `-m unittest discover -p 'test_*.py' -v` → TEST_RESULTS.log（22通过）。
8. `verify.py --readonly --replay` → VERIFY_REPLAY.json及独立stderr；重算数据、三DEV source/line/joint渲染、核验来源和保护树，不保存新科学结果。
9. `finalize.py prepare`写终稿和交付评估；新branch仅此代码目录本地commit；`finalize.py package`封存包并全成员核查；最终`verify.py --readonly`复核manifest/旧状态。

独立父级建议直接运行第7、8步，stdout写到自己的临时目录，不覆盖本任务封存日志。读写root在env.py明确定义；依赖绝对旧目录及已有jointCPU库需可读。无GPU/native重编译，没有外部模型。
'''

def prepare():
 verify_frozen();v=json.loads((ROOT/'VERIFY_REPLAY.json').read_text());assert v['stageA_replays']==12 and v['stageB_replays']==24 and v['match_replays']==18
 review('08_DELIVERY_GO', 'GO仅限整理与封存已经完成的负结果。已核读Ficus四视图与scan24四视图，真实多块不等于盆/干/冠。22测试及只读全重放通过；C/D仍NOT_RUN，不再科学调参。允许本任务源码本地commit及安全包。', [ROOT/'VERIFY_REPLAY.json',ROOT/'STAGE_A_GATE.json',ROOT/'STAGE_B_GATE.json',ROOT/'delivery/ficus_B_FOUR_VIEWS.jpg'])
 newtext('REPORT_ZH.md',REPORT);newtext('FORMAT_ZH.md',FORMAT);newtext('RUN_COMMANDS.md',COMMANDS)
 newtext('ASTRA_FINAL.md', '''# 本轮完成：有真实多块，尚不可升级为结构分区

scan24与scan65完成4视图主体实验，A NO_GO：建筑支撑平面误认立面、地台误入；头骨暗骨/牙齿保留改善但桌面与UNKNOWN仍未分离。两者B/C/D均NOT_RUN。

Ficus完成共享K3/K5及同预算RGB/XYZ控制，4视图24幅区域结果。确实分出多个块，主K3花盆大体连贯，但主干与盆/叶互相混入；DEV/AUX仅1对合格区域，B NO_GO。test14盆底保留UNKNOWN。不能声称优于v01强RGB-only，更不能称已恢复物理部件。C/D未执行。

22本轮测试通过；12A、24B、6模型、18配对精确重放，3DEV source/line/joint数组同既有CPU参考bitexact。148源文件、893旧主Python、11受保护worktree核验不变。没有新GS/PLY/视频/源标签。

查看 delivery/OVERVIEW.jpg、ficus_B_FOUR_VIEWS.jpg、scan24_A_FOUR_VIEWS.jpg、scan65_A_FOUR_VIEWS.jpg；详见REPORT_ZH.md与VERIFY_REPLAY.json。下载PREVIEWS.tar.gz、DELIVERABLE.tar.gz及SHA/MEMBERS。实际本地commit见COMMIT.json。保留C8/joint基线，不自动启动v03。''')
 js(ROOT/'TEST_RESULTS.json',dict(new_tests=22,stageA=8,regions=8,integrity=6,passed=22,inherited_tests_counted_as_new=0,red_logs=['RED_STAGE_A.log','RED_REGIONS.log','RED_INTEGRITY.log'],red_scope='three missing-API/module slices; not a separate RED for each of 22 assertions',tolerances_relaxed=False,log_sha256=sha(ROOT/'TEST_RESULTS.log')))
 js(ROOT/'SOURCE_AFTER.json',dict(files=v['source_files'],unchanged=True,verification=sha(ROOT/'VERIFY_REPLAY.json')))
 js(ROOT/'ROLLBACK_AFTER.json',v['rollback'])
 src=json.loads((ROOT/'SOURCES_ACCESS.json').read_text());titles=['Voxel Cloud Connectivity Segmentation — Supervoxels for Point Clouds','Efficient Graph-Based Image Segmentation'];sections=['3.1–3.4','2–4']
 for s,t,sec in zip(src,titles,sections):s.update(title=t,sections_read=sec,local_pdf='literature/'+s['name']+'.pdf',local_text='literature/'+s['name']+'.txt',text_sha256=sha(ROOT/'literature'/(s['name']+'.txt')),role='primary method evidence; scoped inspiration, not reproduction')
 js(ROOT/'SOURCES.json',dict(primary_sources=src,prior_sources_readonly='v01 SOURCES and reports; see SOURCE_MANIFEST',share_page_body_claimed_read=False))
 js(ROOT/'CODE_FREEZE.json',dict(files={p.name:sha(p) for p in sorted(CODE.iterdir()) if p.is_file()}))
 state('COMPLETE',scientific_status='PARTIAL_DIAGNOSTIC_NO_GO_STRUCTURAL_PARTS',completed_scenes=3,stageA_views=12,stageB_scenes=1,stageB_arm_view_maps=24,stageB_fit_models=6,stageC='NOT_RUN',stageD='NOT_RUN',new_Gaussian_models=0,videos=0,tests_passed=22,source_files_verified=148,children=[],no_automatic_continuation=True)

def bundle(name,paths):
 archive=ROOT/(name+'.tar.gz');assert not archive.exists();members={}
 for p in paths:
  n=safe_member(str(p.relative_to(ROOT)));assert p.is_file() and not p.is_symlink();members[n]=dict(sha256=sha(p))
 with tarfile.open(archive,'w:gz') as t:
  for p in paths:t.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
 man=dict(members=members);js(ROOT/(name+'.MEMBERS.json'),man)
 with tarfile.open(archive,'r:gz') as t:
  got=[]
  for m in t.getmembers():
   safe_member(m.name);assert m.isfile() and not m.issym() and not m.islnk();got.append(m.name);f=t.extractfile(m);h=hashlib.sha256()
   while True:
    b=f.read(1024*1024)
    if not b:break
    h.update(b)
   assert h.hexdigest()==members[m.name]['sha256']
  assert set(got)==set(members) and len(got)==len(members)
 h=sha(archive);(ROOT/(name+'.tar.gz.sha256')).write_text(h+'  '+archive.name+'\n')
 return dict(path=archive.name,bytes=archive.stat().st_size,sha256=h,members=len(members),members_file=name+'.MEMBERS.json',safe_members_verified=True)

def package():
 assert json.loads((ROOT/'STATUS.json').read_text())['phase']=='COMPLETE'
 verify_frozen();rollback();guard()
 p=ROOT/'code';assert not p.exists();p.mkdir()
 for f in sorted(CODE.iterdir()):
  if f.is_file():shutil.copyfile(f,p/f.name)
 head=git(CODE,'rev-parse','HEAD');assert head!='935c52e6a04f8d55e8468c932a4cf0cf4778d7d8'
 js(ROOT/'COMMIT.json',dict(head=head,branch=git(CODE,'branch','--show-current'),local_only=True,pushed=False,merged=False))
 excluded={'AGENT_LAUNCH.json','ASTRA_RUNTIME_FINAL.md','stdout.log','stderr.log','launch.py','setup_remote.py','PROMPT.txt','RESULTS_MANIFEST.json','PACKAGE_INDEX.json'}
 files=[f for f in sorted(ROOT.rglob('*')) if f.is_file() and not f.is_symlink() and f.relative_to(ROOT).parts[0] not in excluded|{'mplconfig'} and not f.name.endswith(('.tar.gz','.tar.gz.sha256','.MEMBERS.json'))]
 man=dict(members={str(f.relative_to(ROOT)):dict(sha256=sha(f)) for f in files});js(ROOT/'RESULTS_MANIFEST.json',man);check_members(ROOT,man)
 preview=[f for f in files if f.relative_to(ROOT).parts[0]=='delivery' and f.suffix=='.jpg']+[ROOT/f for f in ['REPORT_ZH.md','ASTRA_FINAL.md','HYPOTHESIS_FREEZE_ZH.md','COMMIT.json']]
 result=[bundle('PREVIEWS',preview),bundle('DELIVERABLE',files+[ROOT/'RESULTS_MANIFEST.json'])]
 js(ROOT/'PACKAGE_INDEX.json',dict(archives=result,resources=guard(),mutable_runtime_excluded=sorted(excluded-{'RESULTS_MANIFEST.json','PACKAGE_INDEX.json'}),this_receipt_outside_results_manifest=True))
 check_members(ROOT,man);print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','package']);a=p.parse_args();prepare() if a.phase=='prepare' else package()
