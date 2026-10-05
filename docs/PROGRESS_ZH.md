# 当前进展总览

## 研究对象与判据

视觉优先：实际静帧与完整轨迹的干净、完整、稳定是最终判据。当前研究对象为冻结vanilla 3DGS上解释二维边缘的固定原始Gaussian ID群，不等于恢复精确几何棱线。mesh、TEST、人工线标注不进入当前选择。固定3D曲线、逐帧二维线、混合视频与固定贡献核群属于不同输出合同，不能互借成功结论。

## 1. 最新：五场景代表性核群选择

两轮实验分别98与147姿态，保留各自报告与冻结协议。Lego/Chair/tree=Ficus重复使用Mic-only归一化、sigma=.8/1.6/3.2、持久性/分块、需求=.5fullalpha和lambda=0/.1/.3；不因C结果调参。TOP32必要时扩展TOP64，对所有F逐视图校准。通过操作贡献覆盖门槛仍不等于数学完整归因。

- [Mic/Materials完整报告](../artifacts/representative_edge_gaussians_v1/REPORT_ZH.md)
- [Lego/Chair/Ficus完整报告](../artifacts/representative_edge_gaussians_three_v1/REPORT_ZH.md)

**目前结论：联合选择显著提高贡献需求覆盖，但非边缘泄漏仍高于旧独立评分，不支持“同时保留主要边缘并减少面内泄漏”的总体成功。** 覆盖是二维证据需求的饱和效用，不是几何准确率。全核投影保留原模型T，没有删除其他核或逐视图剪裁伪造细线。

中档同核数检查视图均值（A旧独立→E联合lambda.3）：
- Mic，1007核：MAJOR覆盖 .0897→.3256；offedge alpha比例 .000463→.081978。
- Materials，2164核：.0475→.1341；.001408→.044879。
- Lego，2682核：.0436→.2633；.002470→.061916。
- Chair，1567核：.0531→.2931；.000328→.073894。
- Ficus，1163核：.0332→.1632；.000242→.049913。

F-only覆盖匹配不能当作C同覆盖比较：Lego联合前缀139核在C覆盖较高但泄漏较高；Chair38核、Ficus91核在C覆盖下降、泄漏较高。Mic73核/Materials247核同样没有满足总体目标。多尺度纹理仍可能持续；饱和覆盖目标容易奖励宽而强的核。不能用少核数、只对lambda0的改善或工程GO冒称科学成功。

Chair原float64 CPU审计误差6.795e-6超过预设5e-6，失败原样保留；补充实际float32存储算术校验通过。没有放宽原native容差或改选核结果。工程验收范围、模型辅助视觉检查与独立人类验收PENDING分开。归因构造C相机已参与GS TRAIN且历史媒体已知，不称新盲测。

## 2. 固定ID贡献回溯基础

[最初Mic/Materials归因](../artifacts/gaussian_edge_attribution_v1/REPORT_ZH.md)：真实alpha*T、多视图支持/非边缘反证、连续评分、固定原ID和可见性归一化。TOP4截断对核责任有重要限制；不能把固定ID等同三维线。两侧增强未证明整体优于独立基线。后续TOP64不追溯更改旧实验。

## 3. 同源二维读出、模型与第三方归属

- [Lego/Chair/Drums/Ficus同源栅格证据](../artifacts/hybrid_raster_evidence_v2/REPORT.md)：更多响应和可追查内部状态，但内部杂纹明显；不等于固定物空间资产。
- [Hotdog/Materials/Mic/Ship训练与全部结果](../artifacts/hybrid_raster_trained_models_v1/REPORT.md)：经批准标准TRAIN vanilla训练后冻结；存储阻塞历史和首次审计缺口保留，后续成功不抹去。
- [高密度混合视频](../artifacts/hybrid_dense_v1/video/REPORT.md)：二维层和旧三维层来源分开，不把混合画质提升算成三维曲线成功。
- [海报公式独立重建](../artifacts/hao_mukai_source_2026_repro/REPORT.md)、[RaDe来源校准](../artifacts/hao_mukai_rade_foundation/REPORT.md)、[native贡献插桩](../artifacts/hao_mukai_rade_native_f1/REPORT.md)：作者方法、第三方RaDe内核、我们的独立插桩/重建严格区分；不是官方复现效果。

## 4. 固定曲线与基础负结果

- [Mic路径对应与固定3D可行性](../artifacts/mic_persistent_line_feasibility_v1/REPORT.md)：221二维路径、34唯一互匹配、1三视图循环，32点仅10一致；未实际三角化，提案/接受0。仅该方法负结果，不证明任意3D资产不可能。
- [四场景直接全局曲线拟合](../artifacts/direct_curve_global_fit_probe/REPORT.md)及[点/场可视化](../artifacts/3dgs_field_visualization/REPORT.md)、[密度ridge](../artifacts/density_ridge_lines/REPORT.md)保留独立合同/实际原图，不把多噪声拼成“进展”。
- [persistent-boundary准备记录](../artifacts/persistent_boundary_v1/REPORT.md)是准备/诊断范围，不能误称已恢复持久几何线。

## 5. 本次补齐的并行负结果

这两条tip不是最新实验祖先。只导入不可变结果快照，不合并其src/scripts或改变主线算法；代码复现请回原固定SHA分支。
- [二维depth2d视频实验](../artifacts/temporal_depth2d_video_probe/REPORT.md)：四场景两条路径264个原生B相机帧；W/CAND仅Lego arc0各33帧，剩余按kill未运行。候选未优于warp+EMA控制，NO_GO。它是二维视角相关合同，不是固定3D墨。
- [独立RGB-D资产实验](../artifacts/independent_rgbd_asset_probe/REPORT.md)：TUM实测Kinect深度与mocap为额外输入，472可编辑ID、552帧全域视频记录，但轮廓存活和传感器支持/遮挡门槛失败，NO_GO。不能拿额外测量救回vanilla-only主张。

## 6. 可运行交互demo与历史综合报告

- [真实交互demo](../artifacts/gaussian_edge_demo_v1/README.md)：首次随此汇总分支出版代码和真实缓存数据。Mic/Materials各3缓存视图、全核几何/冻结分数、ROI选原ID与3D椭球高亮；不是native实时自由视角渲染，也未自动接入新联合选核。
- [2026-10-04历史综合MD](../artifacts/npr_progress_report_sol_v1/REPORT_ZH.md)、[32页PDF](../artifacts/npr_progress_report_sol_v1/REPORT_ZH.pdf)、[离线HTML](../artifacts/npr_progress_report_sol_v1/index.html)：旧阶段回顾，早于本轮五场景联合选择。报告HTML当时播放器实播未验证，阻塞记录保留。正文/真实图/视频/PDF保留，重复缓存与执行日志不发布。

## 7. 历史分支与研究诚实边界

全部远端38分支已固定SHA盘点，见[分支导航](BRANCHES_ZH.md)。历史时间稳定结果有纹理场景等限定，不能迁移成当前贡献群已优于Canny；旧mesh诊断不得进入当前生成。没有重写旧报告、更新旧科学数字或篡改历史模型归属。下一步若继续，应先验证候选核里是否存在边缘专一的责任者，而不是无边界扫阈值。

## 数据与复现范围

Git中保留源码、协议、模型/数据来源散列、选核JSON、图与策展视频。大checkpoint/CSR/逐像素全缓存/并行实验out视频仅按原报告来源索引，不能声称全部大型服务器产物都已上传。新demo数据可随repo运行；其余科学复跑仍需按各REPRODUCE准备原始冻结源。旧SOURCE_MAP含历史绝对路径是原来源元数据，不因汇总移位而修改实验封条。
