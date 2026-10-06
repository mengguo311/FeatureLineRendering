# 可供主报告引用的方法与限制片段

本文件只描述已冻结的方法、代码复核和解释范围，写于真实生产进行中；没有开封本轮 reserved/arc 图像，不含视觉结论或尚未完成的数值。最终主报告应根据实际产物补入数量、宽度、覆盖、错误填充、完整视频检查和科学 verdict。

## 冻结输入、相机与实现

输入为 Lego、Chair 原始 seed1729、iteration30000、SH3 PLY，原始行号作为永久 Gaussian ID。各模型与 metadata SHA256 记录于 INPUT_FREEZE.json。86-frame camera metadata 按 `file_path` 的 stem 匹配相机，不把 r 数字当索引。仅根据 metadata 方向进行确定性覆盖抽样，r_7/r_33 为前两个构建来源，r_1/r_14 强制保留；每场景 24 construction、4 DEV、8 reserved。既有 GS 训练和历史研究已接触其中相机，因此 reserved 的含义只是本轮 construction-holdout，不是 GS-unseen 或完全新盲测。

本轮采用独立 CPU all-N stock-rule αT replica。它按原投影、tile、排序、alpha 接受与提前终止规则计算完整接受贡献；不是调用原 CUDA renderer，也不是新的网络。四个 construction r_7/r_33 图对历史 native 完整缓存执行 RGB、alpha、可见质量与 feature/adjoint 校准，并把 PASS 绑定当前 cpu_native.py SHA256。校准适用范围与剩余局部误差必须同时保留，不能把总体数值接近称为所有新相机逐像素严格相同。all-N 指未再进行 top-K contributor 截断；原 raster 接受阈值及数值近似仍存在。

## 自动原核检测与多来源组合

从完整 alpha>.5 生成 foreground，保留至少 32px 的连通组件。封闭孔洞不填入前景，孔边支持另存；与外部背景连通的间隙同样保留。提取 1.5px 和 3px 两层边界距离软带以及 hole map 的完整 αT 伴随；主选核实际使用 3px 层，1.5px 作为诊断，不声称多尺度共同融合。

逐视角逐原 ID 保存可见质量、rim 绝对质量、相对响应、屏幕中心、完整 conic/cov2d、radius、depth 和 camera hash。这里 raw 表示 αT 对轮廓带的参与质量，不是旧 GAER 相邻权重差 D。raw/relative 的 0.5% captured mass 仅作诊断；新的自动规则不受这个硬预算限制，也不能反写旧 automatic accepted 空、ALL8 REFUSED 或旧 kernel graph NO_GO_FRAGMENTED。

有效可见质量至少 .1、rim mass 至少 .01；软强度为 relative×sqrt(rim_mass/(rim_mass+.05))，跨不同相机取最大。strong seed 要求 relative≥.35 且 rim mass≥.05；weak 要求 relative≥.12，并只允许一次到最近 strong seed 的受限空间连接。绝对质量条件和饱和因子用于抑制极小质量的比值噪声，属于冻结启发式规则，不是物理边认证。单来源强支撑允许保留，distinct-view 数单列；一个视角中的大量像素投票不能冒充多个独立观察。

## 固定三维区域与来源

所选原核的中心与三维 covariance 为唯一几何锚。score>.100001 的候选生成有界椭球 occupancy union：保留原 orientation，原尺度乘 1.25 后加入冻结世界尺度的方差膨胀，再依据 score level=.1 定义范围；长轴截顶于支撑 bbox 对角线的 .025，短轴至少 .55 voxel。体素间距为本臂所选中心 bbox 对角线/224。记录中的 `width_world_floor` 是加到协方差里的尺度参数，最终 region 半径还受 score、截顶和体素下限影响，不能把这个字段直接当作成品最小半径。

只执行一次六邻域 closing，保存所有新增体素的邻域 owner CSR、距离/方向、填补来源和后续拒绝状态。随后在物空间一次执行 construction foreground 可行性裁剪：各来源 foreground 膨胀 2px，画面外/不在有效前方者按 unknown，不作为 veto。该步骤是由原模型 alpha 证据施加的有限 silhouette carving；不是 surface、SDF、mesh 输入或独立二维轮廓回投影。裁剪可能放大 alpha 模型误差，2px 容差也可能容忍局部错误。

Marching cubes 产生可导出的实体三角面。每顶点主 anchor 是最近保留 raw occupied voxel 的原 owner ID；最近核中心另列为诊断。位移与原 covariance Mahalanobis 距离保存，以披露离开原中心/支撑的程度。此来源证明是局部支撑见证，不是顶点精确落在物理轮廓上的证明。owner 表记录一个竞争胜者，不代表全部重叠核；merge 关系含裁剪前候选，不应等同最终连通拓扑。

fusion candidate IDs、过 region level 的 IDs 和最终 retained owner IDs 是不同集合。原核 PLY 可展示候选，最终 full-T footprint 列使用 retained owner IDs；报告应列出各集合数量，避免把最终资产已不包含的候选贡献算作成品覆盖。

## 对照、宽度选择与固定资产

四臂分别为旧 A graph 原样 thin tube、相同 A 拓扑只加宽、两源新选核区域、多源新选核区域。DEV 只在 .4/.8/1.2 voxel 的三个膨胀参数中选择，目标同时计入边界覆盖、远背景墨量、深内部墨量、负空间填充和 ink/foreground 代价。选定后，旧 A widening 用八次世界半径二分匹配 DEV 平均 ink；不能完全匹配时必须报告误差。reserved 不参与选核、聚合、裁剪、宽度或拓扑选择。

two-source 与 multi24 是实际来源数量的整条流程对照：来源核、foreground 可行性约束和 bbox-derived spacing 都会随来源改变。因此不能纯粹把差异归于“额外选核”或“新表示”的某一个因素。世界宽度、网格间距、核量、实际 ink 均应分别披露，也不作与旧 0.5% 核图的同预算优势声明。

导出 seal 后，几何、宽度、拓扑对全部相机固定。媒体渲染的是相同 triangle mesh 的真实投影；相机只改变投影。当前只实现资产 self-zbuffer，对原完整物体仍是 x-ray，后方区域完整保留，未使用逐视角隐藏 mask。full-T 原核 footprint 与实体区域图具有不同表示和遮挡语义，不能互换作证明。

## 文献关系与结论边界

[Hao–Mukai 作者预印本](https://mukai-lab.org/content/SA2026PosterHao.pdf)提供 raster 支持身份与 visibility 的直接相关先例，但其现有输出仍随视角变化；本轮固定区域必须由本轮实验自行证明。[EdgeGaussians](https://arxiv.org/html/2409.12886v2)、[EMAP](https://arxiv.org/html/2405.19295v1)、[CurveGaussian](https://arxiv.org/html/2506.21401v1)分别通过重新优化的边核、距离场或参数曲线恢复结构，不能作为冻结 RGB 模型原核已具有正确边几何的担保。完整研究、访问失败和短原文证据见 RESEARCH_ZH.md 与 SOURCE_LEDGER.json。本轮不声称简单加粗、Gaussian 支撑合并、多视角 union 或后处理具有新颖性。

固定窄线不能普遍精确表示随相机滑动的剪影。增加方向覆盖可能让支撑 union 变成宽 sheet 甚至整个物体壳层。区域带来的连续性应与厚度代价、错误跨接、孔洞闭合、内部大块墨迹分别判断；“覆盖高”不等于“轮廓可读”。没有观测的方向或部件不作完整恢复保证。内部 RGB 纹理细节层如果未运行，明确写 NOT_RUN；alpha 孔边纳入 primary 不等于已经恢复全部内部结构。

四个校准 PASS、mesh/export 正确和完整视频解码属于工程有效性。视觉 GO 必须看同相机完整图、局部负空间/缺口及未剪坏帧的 33-camera 视频。允许最终判定 PARTIAL 或 NO_GO，但执行/数值校准失效只能称 INVALID/UNDETERMINED。旧阶段负结果、容量证书和原始模型保持独立且不可改写。
