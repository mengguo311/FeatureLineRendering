# 多视角原轮廓核 → 固定三维支撑区域：实验前研究

研究日期：2026-10-07 JST。本文件区分文献事实、历史实测、以及本轮尚待实验证伪的推断；不是成功报告，也不改写旧认证状态。实际访问记录、短原文摘录和定位见 [SOURCE_LEDGER.json](research/SOURCE_LEDGER.json)。使用 live web search 查找 primary sources，再打开作者全文；没有安装、执行或训练第三方方法。作者 PDF 的本地阅读副本被 research/.gitignore 排除，不随交付再分发。

## 决策：先恢复核的空间支撑，再谈细曲线

建议主空间对象为由原始 Gaussian ID、中心、完整三维协方差和多视角轮廓参与度锚定的**固定 edge-occupancy proxy**。它可以导出局部厚带、椭球支撑区域或支撑合并后的 triangle mesh；不称真实 SDF，也不把其边界认证为物理棱边。主流程应先测试多源支撑有没有带来新的形体覆盖，再用 DEV 在事前有限宽度档位中选一次，seal 后保持几何、宽度和拓扑固定。

选择这个对象并非因为“粗线必定成功”。历史中心图已经把源集合压到两源 0.5% 预算，再丢弃 covariance/footprint，然后通过短距与方向进一步筛边；失败只能否定这条组合路线。它不能证明全量原核的共同轮廓支撑不存在。保留有限厚度允许原始支撑彼此接触，避免把每个核强制解释成精确一维顶点；与此同时，支撑覆盖若逐渐铺满整个表面，也会直接否定“可读轮廓模型”的主张。

## 已实际读到的 primary sources

|来源与实际读取范围|原方法事实|本轮能借鉴什么、不能冒称什么|
|---|---|---|
|[Hao–Mukai 作者预印本](https://mukai-lab.org/content/SA2026PosterHao.pdf)，完整 2 页，§2 Eq.1–5、§3；[作者页](https://mukai-lab.org/publications/sa2026poster-3dgs/)|保留 top-K 原 ID、αT、depth/normal 等 raster states；Eq.3 比较相邻像素归一化支持，Eq.4 还用其他变化与层竞争门控。§3 明确现有输出随视角变化；持久三维笔划是未来方向。|支持“保留 ID/visibility 才能谈来源”的设计；不能援引为作者已经实现固定三维 stroke。作者页现在给出正式 DOI，下载 PDF 自身仍有 DOI/ISBN 占位符，应按取得的作者预印本版本标注。|
|[EdgeGaussians](https://arxiv.org/html/2409.12886v2)，§3.1–3.3、§4.1、§5、附录 A–C|从多视角 edge maps 重新优化 Gaussians，并用 orientation/shape 正则使其像有方向的 edge points，再聚类拟合曲线。纯 rendering loss 下的方向与尺度未必对齐边；附录展示聚类会遗漏正确支撑，也会产生伪边。|不能把原 SH3 RGB 模型的 covariance 主轴直接当已学到的边切向。应分开检验支撑质量和下游成线质量。其重新训练与新 Gaussian 不符合本轮约束，本轮不是复现该法。|
|[EMAP / 3D Neural Edge Reconstruction](https://arxiv.org/html/2405.19295v1)，§3.1–3.2、§4.1|学习到边的 UDF，用距离/梯度移动候选点，再抽方向、连点、拟合及合并。§4.1 的 CAD 子集排除了球、圆柱等具有不一致 edge observations 的模型。|edge-distance 可表达线附近的厚邻域，但本轮未经 Eikonal/距离监督的 Gaussian occupancy 不能叫 UDF。该评测限定也不能证明 rolling silhouette 普遍存在固定精细三维曲线。|
|[CurveGaussian](https://arxiv.org/html/2506.21401v1)，§3.1–3.4、§4.1；[作者页](https://zhirui-gao.github.io/CurveGaussian/)|直接优化 Bézier 控制点、opacity、thickness；curve 决定所绑定 Gaussian 的位置/方向，训练中线性化、合并、切分和剔除。初始化来自随机曲线。|可学习“结构对象需与图像证据共同约束”的思路；不能把其结果当原 SH3 核无需重训即可成线的证据。简单加粗、局部合并、多源 union 本身不是本文新颖性。|
|[Huang 等 L1-Medial Skeleton](https://www.cs.sfu.ca/~haoz/pubs/huang_sig13_l1skel.pdf)，作者完整 8 页 PDF 的 §2–4、§5 limitations|通过局部 L1 中心、逐渐增长邻域和条件正则，将点云收缩为形状内部的一维中心骨架。作者明确指出邻近 surface sheets 仅用位置难区分，可导致错误拓扑，且收缩不可逆。|不把 medial skeleton 与外轮廓混为一谈。它适合体内结构抽象；把轮廓支撑 sheet 强制收向骨架可能毁掉外形和孔洞。只允许作为未来独立结构辅助，当前不作为主模型。|

实际访问时部分 CVF PDF 经 web open 返回 403；这些失败保留于 ledger。EdgeGaussians、EMAP、CurveGaussian 的结论来自随后实际打开的 arXiv 全文，而非搜索摘要。Hao–Mukai 和 L1 的 web PDF 接口失败，但 HTTPS 直接读取作者 PDF 成功并用 pdftotext 阅读、保存 SHA256。LineGS/SketchSplat 仅在检索候选中出现，本文件没有以其未读全文支持方法结论。

## 历史负证据究竟定位了什么

实际阅读了四个指定阶段 REPORT，以及 kernel graph 的 Lego 三维/PCA 图和 Chair 四相机完整板。旧核的空间分布本身并非随机噪声：Lego 底板与部分上部线条、Chair 背部外形可辨。Chair 两个构建视角偏背面；旧 r_1/r_14 的座面、扶手与腿部缺口明显大于 r_7/r_33。该观察说明来源方向与覆盖有关系，不构成新增算法有效证据。

|因素|已有证据|本轮必须分开的检验|
|---|---|---|
|原候选空间分布|旧两源 union：Lego 3057、Chair 1953；相交 ID 为 49、615。背面/底板支撑可见，其他结构少。|在原 ID 和三维位置上比较 two-source 与确定性多方向 construction；新增核数不等于新增正确形体。|
|稀疏预算|旧 automatic accepted 全空、ALL8 REFUSED；0.5% 是诊断预算。object_contours 全 N 活动核曾达 Lego 14920–19073、Chair 8702–12020。|raw participation、relative responsiveness、软 group support 各自记录质量、范围和遗漏；不再把 0.5% 当物理认证默认。|
|足迹丢失|原 full-T 共同参与能够在线形成基本连续外轮廓；center-only 图完全没有利用协方差和有限空间范围。|先导出原 ID 的 native footprint 贡献图，再比较其固定空间区域；贡献存在不等于中心在真实 rim。|
|三维邻接不可靠|旧 B 最大组件 17/9，孤立 1317/814；PCA 是所选点分布的轴，不是原协方差，更不是 surface normal。|原样 thin、同图 widened、new fusion region 三臂分开；记录每个近距合并的来源/距离/方向及拒绝理由。|
|截断与容量|capacity 中 K32 仍改变赢家；固定 full-T capacity 的证书有明确目标和数值条件，部分 perview 未认证。|优先全 native feature adjoint；若 K 截断则保存未捕获质量与 unknown。未收敛或未校准归为 INVALID/UNDETERMINED，不能据此发科学 NO_GO。|

两源到多源和图到区域是两个独立变量。推荐最小 2×2 解释：旧两源图原样及只加宽；两源新选核区域与多源新选核区域。若预算只容许前三主臂，至少保留两源新区域作为低成本对照。不同臂核量、世界宽度和屏幕 ink area 应明示，不能后验宣称同预算胜利。

## 为什么厚区域有时有用，有时必然失败

以下是本轮几何推断，不是文献实验结果。设同一结构的稀疏中心间隙为 d，原有效支持半径为 r_i、r_j；当局部支持本来覆盖该间隙时，中心图的“不连边”并不妨碍区域连续。相邻支撑的交叠保留了这部分信息，允许窄 sheet 或多分叉局部结构，无须人为指定 degree≤2。小量世界宽度可容纳训练模型定位误差、不同视角 rim 的有限漂移和体素离散化误差。

但 rolling silhouette 随观察方向滑动。圆柱侧面的轮廓母线会绕圆周移动；将越来越多观察方向的轮廓支持取 union，极限可以覆盖整个柱侧面。球体更直接：不同方向的剪影对应不同大圆，全面 union 可覆盖球壳。因此“所有方向都完整 + 永远窄线 + 唯一固定资产”一般不能同时满足。扩大视角域通常需要更宽部分，或接受漏线；把整个壳染黑只获得 object mask，不能称轮廓成功。

同样，单一欧氏半径既能填补细小采样缺口，也可能接通两条邻近椅腿、扶手和座面。高斯足迹 overlap 是共同空间支持候选，不是同一部件证明。应尽量让连通来自原支撑交叠，避免无证据的大 closing；若执行额外 filling，需记录原支撑 ID、最长跨越长度和新增无支持体积，且不能借手工部件 mask 选择正确答案。

孔洞分两种：封闭背景孔，以及与画面外背景连通的部件间空隙。旧 object_contours 在证据中填封闭孔洞，故不能用其外轮廓成功推断内孔也恢复。新主模型可优先外轮廓，但评估必须用未填洞 native alpha 独立测这两种负空间的填充；标明未建孔边层，而不是把抹平称完整。

## 路线比较与最早可证伪条件

|候选路线|优点/代价|最早失败假设与便宜证伪|选择|
|---|---|---|---|
|旧选核中心图继续调 k/角度|便宜、原 ID 明确；图先验强|完整图/拒绝图已说明大量短片与孤立，宽度未知；只调邻接不能产生未被选中的前部结构|仅原样基线，不作为新主路线|
|同旧图加宽 tube|世界几何简单，正好测“描粗”贡献|DEV 同 ink 仍漏整个部件，说明仅宽度不足；若它与新法同样好，则不能把增益归于融合|必须控制|
|多源核 covariance 支撑区域|保留有限足迹、原来源可追踪；可直接输出固定 mesh|多源 native footprint 本身仍未补足 DEV rim，或区域在同 ink 下只有内填充增加；则主假设不成立|推荐主 latent|
|核锚定候选空间 + 多视角厚 edge-distance 约束|可在原支持内抑制远离证据的部分；代价为离线约束/可见性校准|支持域为空、对观察角度极敏感、或必须显著离开原支持才覆盖；不得偷换成独立二维 lift|可作为本轮局部约束，但先做小片段|
|体素 closing 后 skeleton / 全点云 medial skeleton|容易得到连通骨架；位置/拓扑可能明显偏离轮廓|两邻近片面被合并、孔洞被杀、骨架移到体内。用两平行片/薄环的合成 fixture 即可暴露|不作为当前主路线|
|重训 EdgeGaussians/EMAP/CurveGaussian|针对 edge 几何设计，可能更适合精确曲线|依赖新训练/新网络，且 provenance 不再是冻结原 SH3 ID|不符合本轮权限，仅读研究|

建议的廉价证伪顺序：

1. 校准 αT 完整和、feature forward/adjoint、相机 convention；独立构造已知点与遮挡 fixture。未通过就停止解释几何效果。
2. 在 construction 的前两个来源和冻结的全多源之间，比较新增原 ID 的三维覆盖、重复观测数、full-T rim captured mass 及宽外域泄漏。一个 ID 的一万个像素票仍只算一个视角。
3. 在不看 reserved 的条件下，检查多源支持对 DEV 的覆盖与 ink/negative-space tradeoff。若多源只增大 ink 而无新正确外形，保留失败，不能用更密核量包装算法优势。
4. 用近邻双片和有孔环 fixture 测区域合并；是否连通、孔是否关闭必须可预测，新增支撑归因非空，超过冻结短距应拒绝。
5. 对同一个 GLB/OBJ 在相机变换前后核对 geometry hash；真实 rasterize triangle mesh，记录世界宽度。没有独立遮挡校准时完整提供 x-ray，不能用逐相机隐藏 mask 装作干净模型。

## 可交给实现的主对象与来源契约

每个视角 v、原核 i 保存完整 native 接受权重对自动多尺度轮廓带 b_v 的参与质量 m_iv=Σ_p w_iv(p)b_v(p)，可见质量 t_iv=Σ_p w_iv(p)，以及相对响应 m_iv/(t_iv+ε)。绝对量与相对量必须同时保留：比值大而绝对量极小不是强支撑，大核绝对量大也不等于局部轮廓。支持选取可采用软强度和自动 hysteresis，避免固定 top0.5%；规则必须在 extraction 前冻结。

针对极小 mass 的比值噪声，可在协议中事前声明收缩形式 r_iv=m_iv/(t_iv+τ_t)，再乘饱和绝对支撑因子 1−exp(−m_iv/τ_m)。τ 使用独立校准误差和明确的像素 α 质量单位冻结，不按结果救门槛；raw m、原始 ratio、收缩值全部保留。该形式只是候选规则，尚无本轮实测优越性。对每核做强 absolute hardcut 也有风险：许多弱核的联合支持可以承载细部件，故 weak group/hysteresis 的消融比一刀切更有诊断价值。

融合应明确允许“多个来源补充不同区域”，不强制每个 rolling-rim 核被所有视角看到。可用最大/饱和 OR 形成候选，弱响应需邻域/多尺度支持；单视角强支撑标低共识，distinct views 与 raw pixel mass 分开。简单求和会偏向被更多相近相机看到的区域，需要记录方向覆盖或归一化。具体阈值、尺度和候选档位由主协议一次冻结，本文不以未运行参数冒充已选择值。

空间 proxy 可写为 F(x)=Σ_i s_i G_i(x)，或有界椭球/短距 capsule 的支持并集。新顶点由这一冻结域离散化产生，需记录所属/最近支撑 ID、相对原中心位移、covariance 标准化距离、有效世界宽度和是否属于额外填补。原协方差只是源 support 形状，不能自称边切向、surface normal 或物体真表面。任何裁剪长轴/最大半径也会损失原支持，需显式保存裁剪因子和受影响 ID。

若使用 construction α 前景作几何可行性约束，它来自原模型的图像证据，不是额外几何输入；但 24 视角 α>.5 的硬交集会放大阈值偏差并切断薄结构。应明确小容差、未知/不可见政策，保存每个拒绝的视角及距 alpha 边界的量。有限体素 closing 也需报告新增无原支持体积和最大填补距离；组件数变少本身不能证明拓扑更正确。CPU replica 若不能对旧同相机 native 完整缓存通过既定数值检验，其实验状态必须是 INVALID，不能借图像看似正确称 native 校准已通过。

最终报告应使用真实投影图与完整 33-camera asset 视频判断可读性和稳定性。允许结论为“固定、可编辑且部分连续的宽轮廓草模”；工程成功、数值有效和视觉成功分别列出。研究没有保证某一方法必然成功，也没有改变历史 REFUSED、NO_GO_FRAGMENTED 或 capacity 证书。
