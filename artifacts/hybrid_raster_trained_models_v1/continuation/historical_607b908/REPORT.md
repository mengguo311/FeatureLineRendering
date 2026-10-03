# 四场景 TRAIN → FREEZE → NPR 实验

**部分完成，因授权工作区容量不足停止后续NPR。** 四个 vanilla3DGS 模型均已实际完成唯一一次 seed1729、30000步训练并冻结；Hotdog完成49帧及全部媒体，总计 **49/196帧**。Materials、Mic、Ship的147帧未运行，不能视为科学负结果。Hotdog首次运行的syscall trace因异常终止而不完整，此限制没有被后续恢复掩盖。最终独立核验确认Hotdog全部49帧、6视频、15联系表和9首中末图完整；总体因另三场景缺失而退出1。结论见 `FINAL.json` 和 `independent_review/PRODUCTION.json`。

全部新代码/报告位于本工作区 `artifacts/hybrid_raster_trained_models_v1`，大产物位于 `out/hybrid_raster_trained_models_v1`。大模型、原始字段和视频保留本地并由哈希清单绑定；Git提交保存代码、报告及来源证据，不代表这些大文件已上传。

## 实际完成范围

| 场景 | vanilla采集 | 最终Gaussian数 | 训练秒数 | NPR帧 | patched/unpatched资格 |
|---|---|---:|---:|---:|---|
| hotdog | 30000 / seed1729，PASS | 148610 | 474.685 | 49/49 | 全部8F独立PASS |
| materials | 30000 / seed1729，PASS | 282537 | 486.267 | 0/49 | 未启动，空间阻塞 |
| mic | 30000 / seed1729，PASS | 311562 | 496.476 | 0/49 | 未启动 |
| ship | 30000 / seed1729，PASS | 320284 | 657.632 | 0/49 | 未启动 |

总训练进程墙钟2115.060秒；保留8个7000/30000 PLY、8个完整恢复snapshot、120000条有限loss和24张TRAIN诊断图。没有真实场景重训或训练resume。`acquisition/results/`记录精确CLI/config、source/input hash、GPU/资源/timestamps、checkpoint lineage及大文件索引；`independent_review/ACQUISITION_FINAL.json`独立重新核验四场景并PASS。

## 训练设置与实际可见缺陷

沿用旧Lego实际设置中适用的部分：原生800、白背景、SH3、seed1729、30000步、随机100000点初始化、原始0.8 L1 + 0.2(1−SSIM)损失和默认增密/optimizer schedule。无normal/depth/mesh/NPR监督、人工标签或结果驱动调参。所有初始化/cache写本工作区，既有解释器及official vanilla二进制只读，没有环境安装或全局设置修改。

必要差异：旧Lego流程使用86个TRAIN及16个VAL诊断，本轮使用原始全部100个TRAIN，严格不读TEST/VAL元数据或像素，并增加TRAIN-only loader、隔离、日志和可核验恢复。**C相机参与GS训练，只对NPR参数拟合留出，不是盲测或泛化评估；本轮NPR完全没有重新拟合。** 以下仅为预声明F1/F41的TRAIN in-sample RGB诊断，不作为质量门槛：

- **Hotdog：** 盘沿、面包和芥末带基本对齐，未见黑屏、整体错位或主要对象缺失；面包细纹和盘面反射略平滑。
- **Materials：** 球体、切口和底座基本对齐；镜面环境反射变软、局部高光略糊，粗糙金属颗粒被平滑。反光/折射外观的视角相关近似不能证明几何正确。
- **Mic：** 主体、支架和电缆基本对齐，网罩孔格大体保留；局部灰度、细高光及表面过渡仍与源图有差别。
- **Ship：** 船体、桅杆和容器整体对齐；水面高频波纹明显变软，船侧木纹、炮口及部分细索模糊，反光仍有差别。保留这些缺陷，没有追加训练。

诊断原图路径/hash见 `TRAIN_RGB_VISUAL_REVIEW.json`。全SH训练外观与下面SH0 NPR原生RGB不同，不能混为同一个质量检查。

## Hotdog冻结NPR的经验结果

固定检查F1/F41、C7/C47、arc首/中/末，另审阅全部C和完整33帧arc联系表；具体实际查看文件及hash见 `NPR_VISUAL_REVIEW.json`、`SECOND_VISUAL_REVIEW.json`。观察来自实现代理，人类科学评审仍pending。

A保留盘沿和食物边界，但面包/香肠内部有拥挤碎线，盘面可见由明暗变化引出的长弯线或折线。B在食物内部形成大面积灰色密纹，盘面出现颗粒/片状杂纹；C保留A边线并叠加B覆盖，画面更拥挤。等墨量后B/C整体变浅，空间杂纹仍在，部分边界对比变弱。弧线中段（包括arc016）的盘子下沿超出画面下边界，各臂共同可见；保持冻结相机，没有事后重构图。AUTHOR固定增益列主要呈很细的外轮廓与稀疏内部斑点；它是独立Eq.1–5重建，**NOT official**。

49帧平均连续墨量A=38992.69、B=94992.00、C=112476.05；这不是准确率或有用线增益。按前景alpha>0.05像素加权的top4贡献覆盖均值约0.51923，反映截断贡献统计，不是几何质量。B-only argmax以delta_G（10000863像素）及visibility_raw（1245094像素）为主；不能把通道占比直接解释为正确表面线。完整分组统计见 `transport/DIAGNOSTIC_SUMMARY.json`，该汇总明确49/196并以退出2标记总体不完整。

**当前观察不支持“额外墨量就是更好的线条”。** 不作fixed3D或时序收益声明，也不从Hotdog外推未运行的三个场景。

## 产物入口

Hotdog每帧原生800×800，五列panel为4000×832，顺序RGB | A | B | C | AUTHOR。49帧均有raw、typed、responses、provenance、diagnostics、单臂图、line/overlay/matched panel及seal。matched仅匹配A/B/C墨量，AUTHOR仍用固定增益，标签明确。

| 内容 | 路径 |
|---|---|
| 原生五列示例 | [F1 line](../../out/hybrid_raster_trained_models_v1/transport/frames/hotdog/F_001/line_panel.png)、[matched](../../out/hybrid_raster_trained_models_v1/transport/frames/hotdog/F_001/matched_panel.png)、[overlay](../../out/hybrid_raster_trained_models_v1/transport/frames/hotdog/F_001/overlay_panel.png) |
| 全33帧原生视频 | [comparison](../../out/hybrid_raster_trained_models_v1/transport/media/hotdog/arc0_comparison.mp4)、[overlay](../../out/hybrid_raster_trained_models_v1/transport/media/hotdog/arc0_overlay.mp4)、[matched](../../out/hybrid_raster_trained_models_v1/transport/media/hotdog/arc0_matched.mp4) |
| Telegram全33帧 | [comparison](../../out/hybrid_raster_trained_models_v1/transport/media/hotdog/arc0_comparison_telegram1600.mp4)、[overlay](../../out/hybrid_raster_trained_models_v1/transport/media/hotdog/arc0_overlay_telegram1600.mp4)、[matched](../../out/hybrid_raster_trained_models_v1/transport/media/hotdog/arc0_matched_telegram1600.mp4) |
| 全C/arc联系表及首中末 | [媒体目录](../../out/hybrid_raster_trained_models_v1/transport/media/hotdog/)，完整清单见 `transport/hotdog/MEDIA.json` |
| 原始字段/逐帧seal | `out/hybrid_raster_trained_models_v1/transport/{raw,frames}/hotdog/` |
| 四个模型 | `out/hybrid_raster_trained_models_v1/training/{hotdog,materials,mic,ship}/seed_1729/checkpoints/` |

实际有6视频（3原生、3Telegram）、15联系表、9首中末面板；四场景原期望分别为24、60、36。原生视频4000×832；Telegram为1600×368、H264/yuv420p/faststart，重画可读标签，保留全部33帧。独立产物checker已完整核验decode/distinct/尺寸/hash，6视频各33帧且全部distinct；首帧标签检查不替代全视频核验。

## 冻结、来源与核验边界

GPU前协议冻结提交 `8b3915b5e3211530beefd8606dbdcdd5cdf25e2d`；支持修正 `9fb46557958e5ec4b3e13df0894b9be747c43e6b`；真实采集最终源码冻结 `206b9ebf3e90d4766fb1b3e32ebfba491e390f4e`。实际源为上游 `472689c0dc70417448fb451bf529ae532d32c095` 的17个git blob，保留许可证。外部只读工作目录的未提交renderer改动曾使合成夹具失败；最后允许的修复轮次改为immutable blob提取后，才开始四场景训练。三轮修复和原失败证据全部保留，没有第四次producer修复。

全部checkpoint的哈希/lineage/lock及49×4精确相机清单在 `26636535ab39c1996493d0088a7a53bb358dbb9a` 提交推送，10:06:08 UTC核对远端后才释放NPR。训练前已冻结F/C精确矩阵和唯一arc算法；旧arc中心依赖最终checkpoint，因此模型封存后才解析并推送全部33 poses。F=[1,14,27,41,53,67,79,93]，C=[7,21,33,47,59,73,86,99]，arc固定C7→C33；800×800、主点399.5，Materials用其独立FoV。`independent_review/FREEZE_ORDER.json`核对实际先后顺序。

六个旧科学源码、patched/unpatched隔离二进制均只读且hash一致；parameter hash固定为 `6c4ef4afa648f54794d7094a7b21368a89e14cdbc792766441aa3d3639d487c9`。A=灰度RGB/depth/alpha dense edges，B=OUR dense六通道，C=自动互补；原尺度、作者增益全部继承，无新F拟合。各臂同一次native traversal、白底SH0、原Gaussian行ID、raw alpha*T。缺filter3D；raster/splat/ray-plane normals不是GT表面法线。

92项最终选定的新/相关旧测试全部通过，另有真实两步CUDA训练集成通过；RED、失败夹具、重跑不增加通过数。`independent_review/TEST_INDEX.json`保存命令/日志hash和计数。四场景训练实际trace均PASS；严格loader不会读取transforms_test，即使标准Scene仍无条件打印“Loading Test Cameras”，该列表也为空。审计仅覆盖记录进程的open/openat/openat2/creat和退出，不声称覆盖整个会话。

Hotdog第一次NPR在27帧后工具返回143，原因/发信者未知，无正常EXIT及trace退出尾标，故该审计保持INVALID/不完整。27完整frame、28raw及中断arc011 staging保留；独立核验后按原清单续跑，首段保守计入622秒预算，并非伪造实测墙钟。第二次实际执行目录名为`hotdog_render_003`（logger的glob计入outer文件，并非四次启动）。续跑trace和媒体trace完整PASS；原帧hash保持不变。一次独立CPU核验也遇到143，原失败log/trace保留，再用不改源码的独立会话完成核验。数据完整性与原执行审计缺口分别报告。

## 真实阻塞与剩余事项

Materials原启动守卫于10:34:34 UTC实际退出3，GPU未启动：空闲1266896896字节，低于该阶段保守门槛2147483648字节。硬保留1073741824字节后只余193155072字节，少于Hotdog实测16个校准NPZ的206130333字节，尚未考虑新帧。`transport/STORAGE_BLOCKER.json`明确区分硬余量和阶段估算，不伪称磁盘已物理写满。

Hotdog媒体依据实际输入体积将操作层阶段估算从512MiB调整到256MiB，未改producer、参数或硬1GiB余量；实际约131MB，完整交付后再尝试下一场景预检。没有删旧资产、损失性压缩字段、减帧、降分辨率或写外部磁盘。曾请求仅授权新外部目录 `/mnt/hdd1/u00134/hybrid_raster_trained_models_v1`，尚未收到许可，故未使用。

继续剩余147帧需要足够的授权存储；三个模型及精确相机已冻结，无需重训或调参。人类需要审阅完整五列/等墨量/overlay及原始字段，接受或拒绝科学解释，并注意首次NPR审计缺口。当前结果不是四场景完整实验或人类GO。
